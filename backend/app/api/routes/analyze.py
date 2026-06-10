import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Dict
from fastapi import APIRouter, UploadFile, File, status, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import DbSession
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion, Feedback
from app.schemas.analysis import AnalysisResponse
from app.schemas.predict import DeteccionItem, ClaseDistribucion
from app.schemas.feedback import FeedbackSaveRequest
from app.service import process_and_upload_image, ProcessedImageResult

router = APIRouter(tags=["Análisis"])

# ---------------------------------------------------------------------------
# Funciones auxiliares de negocio
# ---------------------------------------------------------------------------

def consolidate_analysis_detections(
    analysis: Analisis
) -> Tuple[int, List[DeteccionItem], Dict[str, ClaseDistribucion]]:
    """
    Combina las detecciones de la IA con el feedback activo del bioquímico
    para devolver el estado actual (corregido) del análisis.
    
    Aplica:
      - Descarte de detecciones con feedback FALSO_POSITIVO.
      - Edición de clase o bbox de detecciones con feedback CAMBIO_CLASE.
      - Adición de detecciones manuales creadas con feedback NUEVA_DETECCION.
    """
    # 1. Recuperar detecciones y feedbacks activos (excluyendo bajas lógicas)
    active_detections = [det for det in analysis.detecciones if det.fechaBaja is None]
    active_feedbacks = [fb for fb in analysis.feedback if fb.fechaBaja is None]

    # Mapas de feedback por deteccion_id para acceso rápido
    falsos_positivos = {fb.deteccion_id for fb in active_feedbacks if fb.tipoCorreccion == "FALSO_POSITIVO"}
    cambios_clase = {fb.deteccion_id: fb for fb in active_feedbacks if fb.tipoCorreccion == "CAMBIO_CLASE"}
    nuevas_detecciones = [fb for fb in active_feedbacks if fb.tipoCorreccion == "NUEVA_DETECCION"]

    detections_items = []
    class_counts = {}

    # 2. Procesar detecciones originales
    for det in active_detections:
        # Si la detección es un falso positivo, se omite de los resultados consolidados
        if det.id in falsos_positivos:
            continue

        cls_name = det.clase.nombre
        bbox_coords = det.bbox if isinstance(det.bbox, list) else list(det.bbox)
        confianza = det.confianza if det.confianza is not None else 0.0

        # Si tiene un cambio de clase, se sobreescriben los datos
        if det.id in cambios_clase:
            fb = cambios_clase[det.id]
            if fb.clase_corregida:
                cls_name = fb.clase_corregida.nombre
            if fb.bbox_corregido:
                bbox_coords = fb.bbox_corregido if isinstance(fb.bbox_corregido, list) else list(fb.bbox_corregido)

        detections_items.append(
            DeteccionItem(
                id=det.id,
                clase=cls_name,
                confianza=confianza,
                bbox=bbox_coords
            )
        )
        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

    # 3. Procesar nuevas detecciones manuales añadidas
    for fb in nuevas_detecciones:
        cls_name = fb.clase_corregida.nombre if fb.clase_corregida else "Desconocido"
        bbox_coords = fb.bbox_corregido if isinstance(fb.bbox_corregido, list) else list(fb.bbox_corregido)

        detections_items.append(
            DeteccionItem(
                id=fb.id,  # El UUID del feedback identifica la nueva detección de forma única
                clase=cls_name,
                confianza=1.0,  # Confianza del 100% por ser etiquetado manual
                bbox=bbox_coords
            )
        )
        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1

    total_detecciones = len(detections_items)

    # 4. Calcular la distribución estadística corregida
    distribucion = {}
    for cls_name, count in class_counts.items():
        percentage = round((count / total_detecciones) * 100, 1) if total_detecciones > 0 else 0.0
        distribucion[cls_name] = ClaseDistribucion(
            cantidad=count,
            porcentaje=percentage
        )

    return total_detecciones, detections_items, distribucion


# ---------------------------------------------------------------------------
# Endpoints HTTP
# ---------------------------------------------------------------------------

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

    return {
        "cloudinary_url": result.cloudinary_url,
    }


@router.get(
    "/analysis",
    response_model=List[AnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Obtener historial de análisis",
    description=(
        "Retorna la lista de todos los análisis clínicos de frotis de sangre realizados por el usuario. "
        "Incluye las detecciones asociadas y la distribución estadística por clase celular corregidas. "
        "Excluye registros eliminados lógicamente (baja lógica)."
    ),
)
def list_user_analysis(
    db: DbSession,
    current_user: Usuario = Depends(get_current_user)
) -> List[AnalysisResponse]:
    """
    Recupera el historial de análisis del usuario autenticado actual, aplicando correcciones de feedback.
    """
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
        total_detecciones, detections_items, distribucion = consolidate_analysis_detections(analysis)

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
        "Incluye las detecciones asociadas y la distribución de clases celulares corregidas. "
        "El análisis debe pertenecer al usuario autenticado y no estar eliminado lógicamente."
    ),
)
def get_analysis_detail(
    analysis_id: uuid.UUID,
    db: DbSession,
    current_user: Usuario = Depends(get_current_user)
) -> AnalysisResponse:
    """
    Recupera el detalle de un análisis específico, consolidando el feedback guardado.
    """
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

    total_detecciones, detections_items, distribucion = consolidate_analysis_detections(analysis)

    return AnalysisResponse(
        id=analysis.id,
        imagen_url=analysis.imagen_url,
        estado=analysis.estado,
        fecha=analysis.fecha,
        total_detecciones=total_detecciones,
        distribucion=distribucion,
        detecciones=detections_items
    )


@router.post(
    "/analysis/{analysis_id}/feedback",
    status_code=status.HTTP_200_OK,
    summary="Registrar feedback y correcciones de análisis",
    description=(
        "Permite al bioquímico registrar correcciones sobre las predicciones de la IA. "
        "Se pueden declarar falsos positivos, re-clasificar células y añadir nuevas detecciones. "
        "Las correcciones previas activas son reemplazadas por el nuevo lote."
    ),
)
def save_analysis_feedback(
    analysis_id: uuid.UUID,
    payload: FeedbackSaveRequest,
    db: DbSession,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Registra el feedback del bioquímico sobre un análisis específico.
    Marca de baja lógica todos los feedbacks activos existentes para el análisis,
    e inserta los nuevos feedbacks validados dentro de una sola transacción.
    """
    # 1. Verificar existencia y pertenencia del análisis
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

    # 2. Validar que las detecciones corregidas pertenezcan a este análisis
    active_detection_ids = {det.id for det in analysis.detecciones if det.fechaBaja is None}
    for item in payload.feedbacks:
        if item.deteccion_id is not None and item.deteccion_id not in active_detection_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La detección con ID '{item.deteccion_id}' no pertenece a este análisis."
            )

    try:
        # Importación diferida para evitar circularidad
        from app.api.routes.predict import ensure_cell_classes_seeded
        class_map = ensure_cell_classes_seeded(db)

        # 3. Dar de baja lógica los feedbacks vigentes anteriores
        db.query(Feedback).filter(
            Feedback.analisis_id == analysis_id,
            Feedback.fechaBaja.is_(None)
        ).update(
            {"fechaBaja": datetime.now(timezone.utc)},
            synchronize_session=False
        )

        # 4. Insertar las nuevas correcciones
        for item in payload.feedbacks:
            clase_id = None
            if item.claseCorregida:
                clase_id = class_map.get(item.claseCorregida)
                if not clase_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"La clase celular '{item.claseCorregida}' no es válida en el catálogo."
                    )

            new_feedback = Feedback(
                analisis_id=analysis_id,
                deteccion_id=item.deteccion_id,
                tipoCorreccion=item.tipoCorreccion,
                claseCorregida=clase_id,
                bbox_corregido=item.bbox_corregido
            )
            db.add(new_feedback)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al registrar el feedback en la base de datos: {str(e)}"
        )

    return {"status": "ok", "message": "Feedback registrado correctamente."}


@router.delete(
    "/analysis/{analysis_id}",
    status_code=status.HTTP_200_OK,
    summary="Dar de baja lógica un análisis",
    description=(
        "Permite al usuario eliminar lógicamente un análisis propio del sistema. "
        "El análisis se marcará con fechaBaja (baja lógica), impidiendo que figure "
        "en listados o consultas de detalle subsiguientes."
    ),
)
def delete_user_analysis(
    analysis_id: uuid.UUID,
    db: DbSession,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Aplica baja lógica a un análisis si el usuario actual es su propietario y no ha sido dado de baja previamente.
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

    try:
        # 2. Aplicar baja lógica (establecer fechaBaja con datetime actual)
        analysis.fechaBaja = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al dar de baja el análisis en la base de datos: {str(e)}"
        )

    return {"status": "ok", "message": "Análisis eliminado correctamente."}

