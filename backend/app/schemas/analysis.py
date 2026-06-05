"""
analysis.py
-----------
Modelos de validación Pydantic para las respuestas del historial de análisis del usuario.
"""

import uuid
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field

from app.schemas.predict import DeteccionItem, ClaseDistribucion

class AnalysisResponse(BaseModel):
    """
    Estructura de respuesta que detalla un análisis histórico realizado por el usuario.
    Incluye las detecciones asociadas y la distribución de clases calculada.
    """
    id: uuid.UUID = Field(
        ...,
        description="Identificador único del análisis (UUID v4)."
    )
    imagen_url: str = Field(
        ...,
        description="URL de la imagen almacenada y analizada."
    )
    estado: str = Field(
        ...,
        description="Estado del ciclo de vida del análisis (ej: PENDING, COMPLETED, FAILED)."
    )
    fecha: datetime = Field(
        ...,
        description="Timestamp de creación del análisis."
    )
    total_detecciones: int = Field(
        ...,
        ge=0,
        description="Cantidad total de detecciones activas en este análisis."
    )
    distribucion: Dict[str, ClaseDistribucion] = Field(
        ...,
        description="Distribución estadística del conteo de células por clase."
    )
    detecciones: List[DeteccionItem] = Field(
        ...,
        description="Lista de todas las detecciones individuales válidas del análisis."
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "imagen_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "estado": "COMPLETED",
                "fecha": "2026-06-05T19:00:00Z",
                "total_detecciones": 1,
                "distribucion": {
                    "Neutrófilo": {"cantidad": 1, "porcentaje": 100.0}
                },
                "detecciones": [
                    {
                        "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                        "clase": "Neutrófilo",
                        "confianza": 0.94,
                        "bbox": [10.5, 20.0, 110.5, 120.0]
                    }
                ]
            }
        }
    }
