"""
predictor.py
------------
Módulo para la carga y ejecución de inferencias utilizando el modelo YOLOv8n.
Implementa un patrón de carga única en caché (Singleton) para producción.
"""

import os
import numpy as np
from PIL import Image
from ultralytics import YOLO

# Nombres de las 10 clases en español del dataset RV-PBS
class_names = [
    "Neutrófilo inmaduro", "Basófilo", "Blasto", "Eosinófilo",
    "Linfocito", "Monocito", "Neutrófilo", "Promielocito",
    "Mielocito", "Metamielocito"
]

# Variable global para cachear el modelo
_model = None

def get_model() -> YOLO:
    """
    Carga el modelo YOLOv8n desde el archivo local en memoria y lo cachea.
    Garantiza que la carga pesada ocurra una sola vez.
    """
    global _model
    if _model is None:
        # Resolver la ruta absoluta al modelo independientemente de dónde se ejecute el proceso
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "model", "model.pt")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encontró el archivo del modelo en: {model_path}")
            
        _model = YOLO(model_path)
    return _model

def predict_leukocytes(
    image: Image.Image, 
    conf_threshold: float = 0.35, 
    iou_threshold: float = 0.4
) -> tuple[np.ndarray, list]:
    """
    Realiza la inferencia YOLO sobre una imagen PIL.
    
    Args:
        image: Imagen cargada en formato PIL Image.
        conf_threshold: Umbral de confianza mínimo para las predicciones.
        iou_threshold: Umbral IoU para la supresión de no máximos (NMS).
        
    Returns:
        Tupla con:
          - np.ndarray de la imagen original en formato OpenCV BGR.
          - Lista de detecciones estructuradas (cajas, clase, confianza).
    """
    model = get_model()
    
    # YOLO acepta objetos PIL.Image directamente
    results = model(image, conf=conf_threshold, iou=iou_threshold, verbose=False)
    result = results[0]
    
    detections = []
    
    # Procesar cada caja detectada
    if result.boxes is not None:
        for box in result.boxes:
            # Obtener las coordenadas en formato xyxy en CPU como lista de float
            xyxy = box.xyxy[0].cpu().numpy().tolist()  # [x_min, y_min, x_max, y_max]
            cls_id = int(box.cls[0].cpu().numpy().item())
            conf = float(box.conf[0].cpu().numpy().item())
            
            # Mapear nombre de clase
            class_name = class_names[cls_id] if cls_id < len(class_names) else str(cls_id)
            
            detections.append({
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": conf,
                "bbox": xyxy
            })
            
    return result.orig_img, detections
