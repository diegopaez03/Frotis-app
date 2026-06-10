# ============================================================
# STAGE 1: Build del frontend React con pnpm
# ============================================================
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Instalar pnpm globalmente
RUN npm install -g pnpm

# Copiar solo manifests primero (cache de Docker para node_modules)
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Instalar dependencias (usa cache si el lockfile no cambió)
RUN pnpm install --frozen-lockfile

# Copiar código fuente y buildear para producción
COPY frontend/ ./

# VITE_API_BASE_URL vacío = misma URL que el backend (mismo origen)
# El archivo .env.production en frontend/ ya lo configura
RUN pnpm run build
# Output: /frontend/dist/

# ============================================================
# STAGE 2: Backend Python — ML + FastAPI
# ============================================================
FROM python:3.11-slim

WORKDIR /backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dependencias del sistema mínimas para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# --- CAPA 1: Actualización de pip ---
RUN pip install --no-cache-dir --upgrade pip

# --- CAPA 2: Resto de dependencias Python ---
# Solo se reconstruye si cambia requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# --- CAPA 3: Código fuente del backend ---
COPY backend/app /backend/app

# --- CAPA 4: Archivos de migración (necesarios para heroku run alembic) ---
COPY backend/alembic /backend/alembic
COPY backend/alembic.ini /backend/alembic.ini

# --- CAPA 5: Build del frontend (servido como estáticos por FastAPI) ---
COPY --from=frontend-builder /frontend/dist /backend/static

# Heroku asigna el puerto dinámicamente via $PORT
EXPOSE $PORT

# --workers 1: un único worker para minimizar uso de RAM en Basic dyno
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
