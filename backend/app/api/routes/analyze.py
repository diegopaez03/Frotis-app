import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, status, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import DbSession
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion
from app.schemas.analysis import AnalysisResponse
from app.schemas.predict import DeteccionItem, ClaseDistribucion
from app.service import process_and_upload_image, ProcessedImageResult

router = APIRouter(tags=["Análisis"])

@router.post(
    "/analyze",
    status_code=status.HTTP_200_OK,
    summary="Analizar frotis sanguíneo",
    description=(
        "Analiza un frotis sanguíneo y retorna la URL de la imagen procesada y las detecciones."
    ),
)
async def analyze_smear(file: UploadFile = File(...)):
    image_bytes: bytes = await file.read()

    result: ProcessedImageResult = await process_and_upload_image(image_bytes)

    # result.image_array  → directo al modelo YOLOv8
    # result.cloudinary_url → guardar en PostgreSQL
    
    # predictions = yolo_model(result.image_array)

    return {
        "cloudinary_url": result.cloudinary_url,
        # "detections": predictions,
    }


@router.get(
    "/analysis",
    response_model=List[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener historial de análisis",
    description=(
        "Retorna la lista de todos los análisis clínicos de frotis de sangre realizados por el usuario. "
        "Incluye las detecciones asociadas y la distribución estadística por clase celular. "
        "Excluye registros eliminados lógicamente (baja lógica)."
    ),
)
def list_user_analysis(
    db: DbSession,
    current_user: Usuario = Depends(get_current_user)
) -> List[AnalysisResponse]:
    """
    Recupera el historial de análisis del usuario autenticado actual.
    
    Aplica baja lógica de forma estricta:
      - Omitir análisis con fechaBaja no nula.
      - Para cada análisis, omitir detecciones con fechaBaja no nula.
    """
    # 1. Consultar análisis activos del usuario, ordenados por fecha descendente
    db_analysis = (
        db.query(Analisis)
        .filter(
            Analisis.usuario_id == current_user.id,
            Analisis.fechaBaja.is_(None)
        )
        .order_by(Analisis.fecha.desc())
        .all()
    )

    response_list = []

    for analysis in db_analysis:
        # 2. Filtrar detecciones activas para este análisis
        active_detections = [
            det for det in analysis.detecciones 
            if det.fechaBaja is None
        ]

        total_detecciones = len(active_detections)
        detections_items = []
        class_counts = {}

        # 3. Formatear cada detección y contar para distribución
        for det in active_detections:
            cls_name = det.clase.nombre  # ej. "Neutrófilo"
            
            # Asegurar que el bbox tenga el formato de lista correcto
            bbox_coords = det.bbox if isinstance(det.bbox, list) else list(det.bbox)

            detections_items.append(
                DeteccionItem(
                    id=det.id,
                    clase=cls_name,
                    confianza=det.confianza if det.confianza is not None else 0.0,
                    bbox=bbox_coords
                )
            )

            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

        # 4. Calcular la distribución porcentual
        distribucion = {}
        for cls_name, count in class_counts.items():
            percentage = round((count / total_detecciones) * 100, 1) if total_detecciones > 0 else 0.0
            distribucion[cls_name] = ClaseDistribucion(
                cantidad=count,
                porcentaje=percentage
            )

        # 5. Armar el modelo de respuesta estructurado
        response_list.append(
            AnalysisResponse(
                id=analysis.id,
                imagen_url=analysis.imagen_url,
                estado=analysis.estado,
                fecha=analysis.fecha,
                total_detecciones=total_detecciones,
                distribucion=distribucion,
                detecciones=detections_items
            )
        )

    return response_list


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un análisis específico",
    description=(
        "Retorna la información detallada de un análisis clínico específico por su ID. "
        "Incluye las detecciones asociadas y la distribución de clases celulares. "
        "El análisis debe pertenecer al usuario autenticado y no estar eliminado lógicamente."
    ),
)
def get_analysis_detail(
    analysis_id: uuid.UUID,
    db: DbSession,
    current_user: Usuario = Depends(get_current_user)
) -> AnalysisResponse:
    """
    Recupera el detalle de un análisis específico si el usuario actual es su propietario.
    Aplica filtros de baja lógica sobre el análisis y sus detecciones asociadas.
    """
    # 1. Buscar el análisis activo y que pertenezca al usuario
    analysis = (
        db.query(Analisis)
        .filter(
            Analisis.id == analysis_id,
            Analisis.usuario_id == current_user.id,
            Analisis.fechaBaja.is_(None)
        )
        .first()
    )

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Análisis no encontrado o acceso no autorizado."
        )

    # 2. Filtrar detecciones activas
    active_detections = [
        det for det in analysis.detecciones 
        if det.fechaBaja is None
    ]

    total_detecciones = len(active_detections)
    detections_items = []
    class_counts = {}

    # 3. Formatear cada detección
    for det in active_detections:
        cls_name = det.clase.nombre
        bbox_coords = det.bbox if isinstance(det.bbox, list) else list(det.bbox)

        detections_items.append(
            DeteccionItem(
                id=det.id,
                clase=cls_name,
                confianza=det.confianza if det.confianza is not None else 0.0,
                bbox=bbox_coords
            )
        )

        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

    # 4. Calcular distribución
    distribucion = {}
    for cls_name, count in class_counts.items():
        percentage = round((count / total_detecciones) * 100, 1) if total_detecciones > 0 else 0.0
        distribucion[cls_name] = ClaseDistribucion(
            cantidad=count,
            porcentaje=percentage
        )

    # 5. Retornar respuesta estructurada
    return AnalysisResponse(
        id=analysis.id,
        imagen_url=analysis.imagen_url,
        estado=analysis.estado,
        fecha=analysis.fecha,
        total_detecciones=total_detecciones,
        distribucion=distribucion,
        detecciones=detections_items
    )

