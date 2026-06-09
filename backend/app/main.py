"""
main.py
-------
Punto de entrada de la aplicación FastAPI — Frotis-App API.

Registra todos los routers de la aplicación y configura los metadatos
de la API para la documentación automática (OpenAPI / Swagger UI).
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.auth import router as auth_router
from app.api.routes.analyze import router as analyze_router
from app.core.config import settings

import cloudinary
import cloudinary.uploader
from app.api.routes.predict import router as predict_router

from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Instancia principal de la aplicación FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Frotis-App API",
    description=(
        "API RESTful para el Sistema de Análisis de Frotis Sanguíneo. "
        "Permite el registro, autenticación y gestión de análisis de muestras."
    ),
    version="1.0.0",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
)

# Configuración de CORS
# En producción se define FRONTEND_URL como config var en Heroku.
# Ejemplo: FRONTEND_URL=https://frotis-app.vercel.app
_frontend_url: str = os.getenv("FRONTEND_URL", "").strip().rstrip("/")

origins = [
    "http://localhost:5173",
    "http://localhost:5173/",
]

if _frontend_url:
    origins.append(_frontend_url)
    origins.append(_frontend_url + "/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#  Cloudinary Configuration — lee credenciales desde variables de entorno (.env)
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# ---------------------------------------------------------------------------
# Health check — endpoint raíz para verificar que la API está activa
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Endpoint de health check. Retorna el estado de la API."""
    return {"status": "ok", "message": "Frotis-App API está funcionando"}


# ---------------------------------------------------------------------------
# Registro de routers
# ---------------------------------------------------------------------------

# Router de autenticación: /auth/register, /auth/login, /users/me
app.include_router(auth_router)

# Router de análisis
app.include_router(analyze_router)

# Router de predicción (YOLOv8n)
app.include_router(predict_router)

# ---------------------------------------------------------------------------
# Archivos estáticos del frontend (React/Vite build)
# ---------------------------------------------------------------------------
# STATIC_DIR existe solo en producción (imagen Docker de Heroku).
# En desarrollo local no existe, por lo que este bloque no se activa.

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if _STATIC_DIR.exists():
    # Servir /assets/* (JS, CSS chunks generados por Vite)
    _assets_dir = _STATIC_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")

    # Catch-all: devolver index.html para que React Router maneje la navegación.
    # DEBE ir al final, después de todos los routers de la API.
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(_full_path: str) -> FileResponse:
        """Sirve el index.html del frontend para todas las rutas no capturadas por la API."""
        return FileResponse(str(_STATIC_DIR / "index.html"))