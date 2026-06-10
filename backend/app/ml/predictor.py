"""
predictor.py
------------
Módulo para la carga y ejecución de inferencias utilizando el modelo YOLOv8n en formato ONNX.
Implementa un patrón de carga única en caché (Singleton) para producción con onnxruntime.
"""

import os
import cv2
import numpy as np
from PIL import Image
import onnxruntime as ort

# Nombres de las 10 clases en español del dataset RV-PBS
class_names = [
    "Neutrófilo inmaduro", "Basófilo", "Blasto", "Eosinófilo",
    "Linfocito", "Monocito", "Neutrófilo", "Promielocito",
    "Mielocito", "Metamielocito"
]

# Variable global para cachear la sesión de ONNX
_session = None

def get_model() -> ort.InferenceSession:
    """
    Carga la sesión de ONNX Runtime desde el archivo local en memoria y lo cachea.
    Garantiza que la carga pesada ocurra una sola vez.
    """
    global _session
    if _session is None:
        # Resolver la ruta absoluta al modelo independientemente de dónde se ejecute el proceso
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "model", "model.onnx")
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encontró el archivo del modelo ONNX en: {model_path}")
            
        # Forzar CPUExecutionProvider para uso en servidores sin GPU (ej. Heroku)
        _session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    return _session

def predict_leukocytes(
    image: Image.Image, 
    conf_threshold: float = 0.35, 
    iou_threshold: float = 0.4
) -> tuple[np.ndarray, list]:
    """
    Realiza la inferencia del modelo YOLOv8 (ONNX) sobre una imagen PIL.
    
    Args:
        image: Imagen cargada en formato PIL Image.
        conf_threshold: Umbral de confianza mínimo para las predicciones.
        iou_threshold: Umbral IoU para la supresión de no máximos (NMS).
        
    Returns:
        Tupla con:
          - np.ndarray de la imagen original en formato OpenCV BGR.
          - Lista de detecciones estructuradas (cajas, clase, confianza).
    """
    session = get_model()
    
    # 1. Obtener dimensiones originales de la imagen
    orig_width, orig_height = image.size
    
    # 2. Preprocesamiento de la imagen para YOLOv8 (imgsz = 640x640)
    input_size = 640
    # Redimensionar la imagen PIL a 640x640
    resized_image = image.resize((input_size, input_size))
    # Convertir a numpy array y normalizar valores a [0.0, 1.0] (RGB)
    input_data = np.array(resized_image).astype(np.float32) / 255.0
    # Cambiar forma de HWC (640, 640, 3) a CHW (3, 640, 640)
    input_data = input_data.transpose(2, 0, 1)
    # Agregar dimensión de lote (1, 3, 640, 640)
    input_data = np.expand_dims(input_data, axis=0)
    
    # 3. Ejecutar inferencia
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_data})
    
    # YOLOv8 ONNX output shape: (1, 4 + num_classes, 8400) -> (1, 14, 8400)
    output = outputs[0][0]  # shape (14, 8400)
    output = output.T       # shape (8400, 14)
    
    # 4. Procesar candidatos y filtrar por confianza
    boxes = []
    confidences = []
    class_ids = []
    
    for row in output:
        # Bounding box coords (x_center, y_center, w, h) en la escala 640x640
        bbox = row[:4]
        # Puntuaciones de las 10 clases
        scores = row[4:]
        class_id = np.argmax(scores)
        confidence = scores[class_id]
        
        if confidence >= conf_threshold:
            x_center, y_center, w, h = bbox
            # Convertir coordenadas de centro a esquina superior izquierda (top-left)
            # requerido por cv2.dnn.NMSBoxes
            x = x_center - w / 2
            y = y_center - h / 2
            
            boxes.append([float(x), float(y), float(w), float(h)])
            confidences.append(float(confidence))
            class_ids.append(int(class_id))
            
    # 5. Aplicar Supresión de No Máximos (NMS) usando OpenCV
    # NMSBoxes espera boxes como [x, y, w, h], confidences, score_threshold e iou_threshold
    indices = cv2.dnn.NMSBoxes(boxes, confidences, score_threshold=conf_threshold, nms_threshold=iou_threshold)
    
    detections = []
    
    if len(indices) > 0:
        # Aplanar los índices por seguridad (dependiendo de la versión de OpenCV)
        indices = np.array(indices).flatten()
        for idx in indices:
            x, y, w, h = boxes[idx]
            confidence = confidences[idx]
            class_id = class_ids[idx]
            
            # Escalar de regreso a las dimensiones originales
            x_min = (x / input_size) * orig_width
            y_min = (y / input_size) * orig_height
            x_max = ((x + w) / input_size) * orig_width
            y_max = ((y + h) / input_size) * orig_height
            
            # Asegurar que las coordenadas estén dentro del rango de la imagen
            x_min = max(0.0, min(x_min, float(orig_width)))
            y_min = max(0.0, min(y_min, float(orig_height)))
            x_max = max(0.0, min(x_max, float(orig_width)))
            y_max = max(0.0, min(y_max, float(orig_height)))
            
            class_name = class_names[class_id] if class_id < len(class_names) else str(class_id)
            
            detections.append({
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence,
                "bbox": [x_min, y_min, x_max, y_max]
            })
            
    # Convertir la imagen PIL de entrada (RGB) a formato OpenCV BGR para retornar
    orig_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    return orig_img, detections
