# Paquete de servicios — lógica de negocio independiente de los transportes (API)
from app.service.image_processing import ProcessedImageResult, process_and_upload_image

__all__ = ["process_and_upload_image", "ProcessedImageResult"]
