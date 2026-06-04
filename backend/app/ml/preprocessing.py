"""
ml/preprocessing.py
--------------------
Pipeline de preprocesamiento de imágenes de frotis sanguíneo con OpenCV.

Pasos aplicados:
  1. Decodificación desde bytes crudos.
  2. Recorte del borde negro circular del microscopio (bounding rect del
     contorno de mayor área).
  3. Normalización de iluminación mediante CLAHE sobre el canal L del
     espacio de color LAB (preserva los colores de la tinción de Giemsa).
"""

from __future__ import annotations

import cv2
import numpy as np

def preprocess_blood_smear(image_bytes: bytes) -> np.ndarray:
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Error al decodificar la imagen")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Desenfoque fuerte para difuminar las células y el ruido del borde
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    
    # 2. Umbral de Otsu: Calcula el valor de corte automáticamente
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 3. Operaciones morfológicas para "suavizar" los bordes del círculo 
    # y rellenar pequeños huecos que puedan quedar
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Tomar el contorno más grande
        largest_contour = max(contours, key=cv2.contourArea)
        
        # RED DE SEGURIDAD: Solo recortar si el contorno ocupa más del 15% de la imagen.
        # Si la imagen ya viene recortada (sin bordes del microscopio), esto evita 
        # que el código intente recortar erróneamente un glóbulo gigante.
        img_area = img.shape[0] * img.shape[1]
        
        if cv2.contourArea(largest_contour) > (img_area * 0.15):
            mask = np.zeros_like(gray)
            cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
            
            white_bg = np.full(img.shape, 255, dtype=np.uint8)
            foreground = cv2.bitwise_and(img, img, mask=mask)
            mask_inv = cv2.bitwise_not(mask)
            background = cv2.bitwise_and(white_bg, white_bg, mask=mask_inv)
            
            img_masked = cv2.add(foreground, background)
            
            x, y, w, h = cv2.boundingRect(largest_contour)
            img_cropped = img_masked[y:y+h, x:x+w]
        else:
            # Si no hay un círculo dominante, dejar la imagen original
            img_cropped = img
            
    else:
        img_cropped = img

    # --- Normalización de iluminación (CLAHE) ---
    lab = cv2.cvtColor(img_cropped, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    
    limg = cv2.merge((cl, a, b))
    img_normalized = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    return img_normalized