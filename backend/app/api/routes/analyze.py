from fastapi import APIRouter, UploadFile, File, status
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
