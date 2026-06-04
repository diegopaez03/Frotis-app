"""
predict.py
----------
Modelos de validación Pydantic para el request y response del endpoint de predicción.
"""

import uuid
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, HttpUrl

class PredictRequest(BaseModel):
    """
    Representa el cuerpo de la solicitud para el endpoint de predicción.
    Requiere una URL válida de Cloudinary u otro servidor de imágenes.
    """
    image_url: str = Field(
        ...,
        description="URL de la imagen almacenada en Cloudinary para analizar.",
        examples=["https://res.cloudinary.com/demo/image/upload/sample.jpg"]
    )

class DeteccionItem(BaseModel):
    """
    Estructura individual para representar una detección de leucocito.
    """
    id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID de la detección en la base de datos (nulo si es anónimo)."
    )
    clase: str = Field(
        ...,
        description="Nombre del tipo de leucocito clasificado.",
        examples=["Neutrófilo"]
    )
    confianza: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de confianza de la predicción, entre 0 y 1.",
        examples=[0.92]
    )
    bbox: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Bounding box en formato [x_min, y_min, x_max, y_max].",
        examples=[[100.5, 150.0, 200.0, 250.2]]
    )

class ClaseDistribucion(BaseModel):
    """
    Métricas de conteo y porcentaje para una clase específica de célula.
    """
    cantidad: int = Field(
        ...,
        ge=0,
        description="Cantidad total de células detectadas de esta clase."
    )
    porcentaje: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Porcentaje del total que representa esta clase de célula.",
        examples=[60.0]
    )

class PredictResponse(BaseModel):
    """
    Cuerpo de la respuesta del endpoint de predicción.
    """
    analisis_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID del análisis creado en la base de datos (nulo si es anónimo)."
    )
    total_detecciones: int = Field(
        ...,
        ge=0,
        description="Cantidad total de leucocitos detectados en la imagen."
    )
    distribucion: Dict[str, ClaseDistribucion] = Field(
        ...,
        description="Distribución estadística del conteo de células por clase."
    )
    detecciones: List[DeteccionItem] = Field(
        ...,
        description="Lista detallada de todas las detecciones individuales en la imagen."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "analisis_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_detecciones": 2,
                "distribucion": {
                    "Neutrófilo": {"cantidad": 1, "porcentaje": 50.0},
                    "Linfocito": {"cantidad": 1, "porcentaje": 50.0}
                },
                "detecciones": [
                    {
                        "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
                        "clase": "Neutrófilo",
                        "confianza": 0.94,
                        "bbox": [10.5, 20.0, 110.5, 120.0]
                    },
                    {
                        "id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
                        "clase": "Linfocito",
                        "confianza": 0.89,
                        "bbox": [200.0, 150.5, 300.0, 250.5]
                    }
                ]
            }
        }
    }
