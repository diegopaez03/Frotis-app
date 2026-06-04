"""
predict.py
----------
Router de FastAPI para el endpoint de predicción e inferencia de frotis de sangre.

Endpoints:
  POST /predict → Inferencia sobre imagen de frotis de sangre, con autenticación opcional
                  y persistencia condicional de análisis/detecciones.
"""

import io
import uuid
from typing import Annotated, Optional
import requests
from PIL import Image, UnidentifiedImageError

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import DbSession, get_db
from app.core.security import decode_access_token
from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion
from app.models.clases_celulas import ClaseCelula
from app.ml.predictor import predict_leukocytes, class_names
from app.schemas.predict import PredictRequest, PredictResponse, DeteccionItem, ClaseDistribucion

# ---------------------------------------------------------------------------
# Router y Esquema de Autenticación Opcional
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Predicción"])

_optional_bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_optional_bearer_scheme)],
    db: Session = Depends(get_db)
) -> Optional[Usuario]:
    """
    Dependencia de FastAPI que valida un JWT de forma opcional.
    
    Comportamiento:
      - Si el header Authorization no está presente, retorna None.
      - Si el token está presente, se valida obligatoriamente. Si es inválido, 
        está expirado o el usuario está dado de baja, retorna HTTP 401 Unauthorized.
    """
    if credentials is None:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decodificar el token JWT
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    # Extraer el subject (email del usuario)
    email: Optional[str] = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Buscar el usuario en la BD
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise credentials_exception

    # Verificar baja lógica
    if user.fechaBaja is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario dado de baja",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

# ---------------------------------------------------------------------------
# Utilidades de Base de Datos
# ---------------------------------------------------------------------------

def ensure_cell_classes_seeded(db: Session) -> dict[str, int]:
    """
    Garantiza que las 10 clases celulares existan en la tabla `clases_celulas`.
    Retorna un diccionario mapeando el nombre canónico de la clase a su ID primario.
    """
    existing_classes = db.query(ClaseCelula).all()
    class_map = {c.nombre: c.id for c in existing_classes}

    missing_classes = [name for name in class_names if name not in class_map]
    if missing_classes:
        for name in missing_classes:
            new_class = ClaseCelula(nombre=name)
            db.add(new_class)
        db.commit()
        
        # Re-consultar para mapear los nuevos IDs generados por la base de datos
        existing_classes = db.query(ClaseCelula).all()
        class_map = {c.nombre: c.id for c in existing_classes}

    return class_map

# ---------------------------------------------------------------------------
# Endpoint POST /predict
# ---------------------------------------------------------------------------

@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Realizar predicción sobre frotis sanguíneo",
    description=(
        "Acepta una URL de imagen de Cloudinary para detectar y clasificar 10 tipos de leucocitos. "
        "Si el usuario está autenticado, la predicción se almacena en el historial médico (base de datos) "
        "asociada a su cuenta. Si la petición es anónima, se procesa la predicción sin persistir datos."
    ),
)
def predict_image(
    request: PredictRequest,
    db: DbSession,
    current_user: Annotated[Optional[Usuario], Depends(get_current_user_optional)] = None
) -> PredictResponse:
    """
    Controlador principal para el procesamiento de imágenes de frotis y predicción de leucocitos.
    """
    # 1. Descargar la imagen
    try:
        response = requests.get(request.image_url, timeout=15)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo descargar la imagen desde la URL proporcionada. Estado HTTP: {response.status_code}"
            )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de red al intentar descargar la imagen: {str(e)}"
        )

    # 2. Validar formato de la imagen con PIL
    try:
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except (UnidentifiedImageError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL no contiene una imagen válida o los datos están corruptos."
        )

    # 3. Ejecutar Inferencia de YOLOv8n
    try:
        _, raw_detections = predict_leukocytes(image)
    except Exception as e:
        # Aseguramos que fallos inesperados del modelo se capturen limpiamente
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno durante el procesamiento del modelo de predicción: {str(e)}"
        )

    # 4. Calcular métricas de distribución y conteo
    total_count = len(raw_detections)
    distribution_summary = {}
    
    if total_count > 0:
        # Contar ocurrencias por clase
        class_counts = {}
        for det in raw_detections:
            name = det["class_name"]
            class_counts[name] = class_counts.get(name, 0) + 1
            
        # Calcular porcentajes
        for name, count in class_counts.items():
            percentage = round((count / total_count) * 100, 1)
            distribution_summary[name] = ClaseDistribucion(
                cantidad=count,
                porcentaje=percentage
            )

    # 5. Persistencia Condicional (Solo si el usuario está autenticado)
    analisis_id: Optional[uuid.UUID] = None
    response_detections = []

    if current_user is not None:
        try:
            # Obtener el mapa de clases celulares en la base de datos (y autoseed si falta)
            class_map = ensure_cell_classes_seeded(db)
            
            # Crear y registrar el Análisis
            new_analisis = Analisis(
                usuario_id=current_user.id,
                imagen_url=request.image_url,
                estado="COMPLETED"
            )
            db.add(new_analisis)
            db.flush() # Genera el new_analisis.id (UUID)
            analisis_id = new_analisis.id

            # Registrar Detecciones
            for det in raw_detections:
                cls_name = det["class_name"]
                clase_id = class_map.get(cls_name)
                
                if clase_id is None:
                    # Fallback de seguridad en caso de inconsistencia con predictor
                    raise ValueError(f"La clase celular '{cls_name}' no existe en el catálogo.")
                
                new_detection = Deteccion(
                    analisis_id=analisis_id,
                    clase_id=clase_id,
                    confianza=det["confidence"],
                    bbox=det["bbox"] # Guarda formato JSONB [x_min, y_min, x_max, y_max]
                )
                db.add(new_detection)
                db.flush() # Genera new_detection.id
                
                response_detections.append(DeteccionItem(
                    id=new_detection.id,
                    clase=cls_name,
                    confianza=det["confidence"],
                    bbox=det["bbox"]
                ))
                
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al guardar los resultados en la base de datos: {str(e)}"
            )
    else:
        # Petición anónima: no se guarda en BD, los IDs de los registros son nulos
        for det in raw_detections:
            response_detections.append(DeteccionItem(
                id=None,
                clase=det["class_name"],
                confianza=det["confidence"],
                bbox=det["bbox"]
            ))

    return PredictResponse(
        analisis_id=analisis_id,
        total_detecciones=total_count,
        distribucion=distribution_summary,
        detecciones=response_detections
    )
