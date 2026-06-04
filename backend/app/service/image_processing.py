"""
service/image_processing.py
----------------------------
Servicio orquestador del flujo completo de procesamiento de imágenes.

Responsabilidades:
  1. Recibir los bytes crudos de una imagen de frotis sanguíneo.
  2. Aplicar preprocesamiento (recorte de borde negro + normalización CLAHE).
  3. Codificar el resultado en memoria como JPEG (sin tocar el disco).
  4. Subir la imagen procesada a Cloudinary.
  5. Retornar el numpy.ndarray listo para YOLOv8 y el secure_url de Cloudinary.

Este módulo NO conoce nada de FastAPI (rutas, requests, responses).
La única excepción es HTTPException, usada para convertir errores de
infraestructura en respuestas HTTP con código de estado apropiado.
"""

from __future__ import annotations

import io
import logging
from typing import NamedTuple

import cloudinary.uploader
import cv2
import numpy as np
from fastapi import HTTPException, status

from app.ml.preprocessing import preprocess_blood_smear

# ---------------------------------------------------------------------------
# Logger del módulo
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tipo de retorno explícito — evita tuplas "mágicas" sin nombre
# ---------------------------------------------------------------------------
class ProcessedImageResult(NamedTuple):
    """
    Resultado del pipeline de procesamiento + subida a Cloudinary.

    Attributes
    ----------
    image_array : np.ndarray
        Imagen preprocesada en formato BGR (H x W x 3, dtype=uint8).
        Lista para ser pasada directamente al modelo YOLOv8.
    cloudinary_url : str
        URL HTTPS permanente de la imagen procesada almacenada en Cloudinary.
        Persistir este valor en la base de datos PostgreSQL.
    """

    image_array: np.ndarray
    cloudinary_url: str


# ---------------------------------------------------------------------------
# Función principal del servicio
# ---------------------------------------------------------------------------
async def process_and_upload_image(
    image_bytes: bytes,
    *,
    cloudinary_folder: str = "frotis/processed",
) -> ProcessedImageResult:
    """
    Orquesta el flujo completo: preprocesamiento → codificación → upload a Cloudinary.

    Parameters
    ----------
    image_bytes : bytes
        Bytes crudos de la imagen recibida desde el cliente (PNG, JPEG, etc.).
    cloudinary_folder : str, optional
        Carpeta destino dentro del cloud de Cloudinary.
        Valor por defecto: ``"frotis/processed"``.

    Returns
    -------
    ProcessedImageResult
        NamedTuple con ``image_array`` (ndarray BGR) y ``cloudinary_url`` (str).

    Raises
    ------
    HTTPException (422)
        Si los bytes no representan una imagen válida o el preprocesamiento falla.
    HTTPException (502)
        Si la subida a Cloudinary falla por un error externo.
    """

    # ------------------------------------------------------------------
    # PASO 1 — Preprocesamiento: recorte de borde negro + CLAHE
    # ------------------------------------------------------------------
    processed_array: np.ndarray = _preprocess(image_bytes)

    # ------------------------------------------------------------------
    # PASO 2 — Codificar ndarray → JPEG en memoria (sin disco)
    # ------------------------------------------------------------------
    jpeg_buffer: io.BytesIO = _encode_to_jpeg(processed_array)

    # ------------------------------------------------------------------
    # PASO 3 — Subir a Cloudinary y obtener la URL segura
    # ------------------------------------------------------------------
    secure_url: str = await _upload_to_cloudinary(jpeg_buffer, folder=cloudinary_folder)

    logger.info("Imagen procesada y subida correctamente. URL: %s", secure_url)

    return ProcessedImageResult(
        image_array=processed_array,
        cloudinary_url=secure_url,
    )


# ---------------------------------------------------------------------------
# Helpers privados (prefijados con _ para denotar que son internos)
# ---------------------------------------------------------------------------

def _preprocess(image_bytes: bytes) -> np.ndarray:
    """
    Aplica el pipeline de preprocesamiento de OpenCV a los bytes de la imagen.

    Delega en ``preprocess_blood_smear`` del módulo ``ml.preprocessing`` y
    convierte cualquier excepción de decodificación en un HTTP 422.

    Parameters
    ----------
    image_bytes : bytes
        Bytes crudos de la imagen original.

    Returns
    -------
    np.ndarray
        Imagen preprocesada en formato BGR.

    Raises
    ------
    HTTPException (422)
        Si la imagen no puede ser decodificada o el preprocesamiento falla.
    """
    try:
        return preprocess_blood_smear(image_bytes)
    except ValueError as exc:
        # ValueError lo lanza preprocess_blood_smear cuando cv2.imdecode retorna None
        logger.warning("Error al decodificar la imagen: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La imagen enviada no es válida o está corrupta: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Error inesperado durante el preprocesamiento.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Error interno durante el preprocesamiento de la imagen.",
        ) from exc


def _encode_to_jpeg(image_array: np.ndarray) -> io.BytesIO:
    """
    Codifica un numpy.ndarray BGR a formato JPEG completamente en memoria.

    Parameters
    ----------
    image_array : np.ndarray
        Array BGR (H x W x 3, dtype=uint8) a codificar.

    Returns
    -------
    io.BytesIO
        Buffer en memoria listo para ser leído (posición en 0).

    Raises
    ------
    HTTPException (422)
        Si cv2.imencode no puede codificar el array.
    """
    # Parámetros de compresión JPEG: calidad 95 preserva detalle diagnóstico
    encode_params: list[int] = [cv2.IMWRITE_JPEG_QUALITY, 95]

    success, encoded_image = cv2.imencode(".jpg", image_array, encode_params)

    if not success:
        logger.error("cv2.imencode no pudo codificar el array a JPEG.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pudo codificar la imagen procesada a formato JPEG.",
        )

    # Convertir el buffer de cv2 (numpy array) a BytesIO para enviarlo a Cloudinary
    buffer = io.BytesIO(encoded_image.tobytes())
    buffer.seek(0)  # Resetear el puntero al inicio antes de leer

    return buffer


async def _upload_to_cloudinary(
    image_buffer: io.BytesIO,
    *,
    folder: str,
) -> str:
    """
    Sube un buffer de imagen JPEG a Cloudinary completamente en memoria.

    Parameters
    ----------
    image_buffer : io.BytesIO
        Buffer JPEG con el puntero en posición 0.
    folder : str
        Carpeta destino en Cloudinary (ej. ``"frotis/processed"``).

    Returns
    -------
    str
        ``secure_url`` HTTPS permanente de la imagen subida.

    Raises
    ------
    HTTPException (502)
        Si la subida a Cloudinary falla o la respuesta no contiene ``secure_url``.
    """
    try:
        # cloudinary.uploader.upload acepta un objeto file-like (BytesIO)
        # resource_type="image" es explícito por claridad aunque es el valor por defecto
        upload_result: dict = cloudinary.uploader.upload(
            image_buffer,
            folder=folder,
            resource_type="image",
        )
    except Exception as exc:
        logger.exception("Fallo en la subida a Cloudinary.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo subir la imagen a Cloudinary: {exc}",
        ) from exc

    secure_url: str | None = upload_result.get("secure_url")

    if not secure_url:
        logger.error(
            "Cloudinary no retornó secure_url. Respuesta completa: %s", upload_result
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudinary no retornó una URL segura. Verifica las credenciales.",
        )

    return secure_url
