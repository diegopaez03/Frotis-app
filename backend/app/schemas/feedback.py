"""
feedback.py
-----------
Modelos de validación Pydantic para el envío de feedback (correcciones del bioquímico).
"""

import uuid
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

class FeedbackItemRequest(BaseModel):
    """
    Representa una corrección individual aplicada a un análisis.
    """
    deteccion_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID de la detección original que se corrige (nulo para nuevas detecciones)."
    )
    tipoCorreccion: Literal["FALSO_POSITIVO", "NUEVA_DETECCION", "CAMBIO_CLASE"] = Field(
        ...,
        description="Tipo de corrección aplicada.",
        examples=["CAMBIO_CLASE"]
    )
    claseCorregida: Optional[str] = Field(
        default=None,
        description="Nombre canónico en español de la clase corregida (requerido para NUEVA_DETECCION y CAMBIO_CLASE).",
        examples=["Neutrófilo"]
    )
    bbox_corregido: Optional[List[float]] = Field(
        default=None,
        min_length=4,
        max_length=4,
        description="Bounding box corregido o nuevo en formato [x_min, y_min, x_max, y_max] (requerido para NUEVA_DETECCION).",
        examples=[[100.0, 150.0, 200.0, 250.0]]
    )

    @field_validator("claseCorregida")
    @classmethod
    def validate_class_required(cls, value: Optional[str], info) -> Optional[str]:
        """Valida que claseCorregida esté presente si no es un FALSO_POSITIVO."""
        tipo = info.data.get("tipoCorreccion")
        if tipo in ("NUEVA_DETECCION", "CAMBIO_CLASE") and not value:
            raise ValueError(f"El campo claseCorregida es obligatorio para correcciones del tipo {tipo}.")
        return value

    @field_validator("bbox_corregido")
    @classmethod
    def validate_bbox_required(cls, value: Optional[List[float]], info) -> Optional[List[float]]:
        """Valida que bbox_corregido esté presente si es una NUEVA_DETECCION."""
        tipo = info.data.get("tipoCorreccion")
        if tipo == "NUEVA_DETECCION" and not value:
            raise ValueError("El campo bbox_corregido es obligatorio para registrar una NUEVA_DETECCION.")
        return value

    @field_validator("deteccion_id")
    @classmethod
    def validate_detection_id_required(cls, value: Optional[uuid.UUID], info) -> Optional[uuid.UUID]:
        """Valida que deteccion_id esté presente si es FALSO_POSITIVO o CAMBIO_CLASE."""
        tipo = info.data.get("tipoCorreccion")
        if tipo in ("FALSO_POSITIVO", "CAMBIO_CLASE") and not value:
            raise ValueError(f"El campo deteccion_id es obligatorio para correcciones del tipo {tipo}.")
        return value


class FeedbackSaveRequest(BaseModel):
    """
    Cuerpo de la solicitud para guardar o actualizar la lista de feedbacks de un análisis.
    """
    feedbacks: List[FeedbackItemRequest] = Field(
        ...,
        description="Lista de correcciones y feedbacks a aplicar sobre el análisis."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "feedbacks": [
                    {
                        "deteccion_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                        "tipoCorreccion": "CAMBIO_CLASE",
                        "claseCorregida": "Neutrófilo"
                    },
                    {
                        "deteccion_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
                        "tipoCorreccion": "FALSO_POSITIVO"
                    },
                    {
                        "deteccion_id": None,
                        "tipoCorreccion": "NUEVA_DETECCION",
                        "claseCorregida": "Linfocito",
                        "bbox_corregido": [50.0, 50.0, 150.0, 150.0]
                    }
                ]
            }
        }
    }
