"""
main.py
-------
Punto de entrada de la aplicación FastAPI — Frotis-App API.

Registra todos los routers de la aplicación y configura los metadatos
de la API para la documentación automática (OpenAPI / Swagger UI).
"""

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.predict import router as predict_router

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


# ---------------------------------------------------------------------------
# Health check — endpoint raíz para verificar que la API está activa
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root() -> dict:
    """Endpoint de health check. Retorna el estado de la API."""
    return {"status": "ok", "message": "Frotis-App API está funcionando"}


# ---------------------------------------------------------------------------
# Registro de routers
# ---------------------------------------------------------------------------

# Router de autenticación: /auth/register, /auth/login, /users/me
app.include_router(auth_router)

# Router de predicción: /predict (detección y clasificación de leucocitos)
app.include_router(predict_router)
