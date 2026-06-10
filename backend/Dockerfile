# ============================================================
# STAGE: runtime
# ============================================================
FROM python:3.11-slim

WORKDIR /backend

# Evita que Python escriba archivos .pyc y fuerza output sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependencias del sistema mínimas requeridas por OpenCV y GLib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# --- CAPA 1: Actualización de pip ---
RUN pip install --no-cache-dir --upgrade pip

# --- CAPA 2: Dependencias de la aplicación (FastAPI, onnxruntime, opencv, etc.) ---
# Se reconstruye solo cuando cambia requirements.txt, no al cambiar el código.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# --- CAPA 3: Código fuente de la aplicación ---
# Esta es la capa que cambia con más frecuencia. Al estar al final,
# los cambios aquí NO invalidan el cache de las capas de dependencias.
COPY ./app /backend/app

# Heroku asigna el puerto dinámicamente via $PORT — no usar un puerto fijo.
EXPOSE $PORT

# Shell form (no JSON array) para que $PORT se expanda correctamente en runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}