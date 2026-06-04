"""
config.py
---------
Configuración centralizada de la aplicación usando Pydantic Settings.

Lee variables de entorno o valores por defecto para:
- SECRET_KEY: clave secreta para firmar JWTs (CRÍTICO: cambiar en producción)
- ALGORITHM: algoritmo de firma JWT (HS256 por defecto)
- ACCESS_TOKEN_EXPIRE_MINUTES: tiempo de vida del token
- CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET: credenciales Cloudinary
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Carga explícita del archivo .env
# ---------------------------------------------------------------------------
# El .env vive en la raíz del proyecto (un nivel arriba de /backend).
# Se calcula la ruta de forma absoluta para que funcione sin importar desde
# dónde se ejecute uvicorn.
_ENV_FILE: Path = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_FILE)


class Settings:
    """
    Configuración de la aplicación cargada desde variables de entorno.
    
    En producción, todas estas variables DEBEN estar definidas en el entorno
    o en el archivo .env. Los valores por defecto son SOLO para desarrollo local.
    """

    # Clave secreta para firmar JWTs.
    # IMPORTANTE: Usar `openssl rand -hex 32` para generar una clave segura.
    # NUNCA usar el valor por defecto en producción.
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "frotis-dev-secret-key-change-in-production-openssl-rand-hex-32"
    )

    # Algoritmo de firma JWT. HS256 es el estándar para APIs internas.
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    # Tiempo de expiración del token de acceso en minutos (30 minutos por defecto).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # ---------------------------------------------------------------------------
    # Cloudinary — Almacenamiento de imágenes en la nube
    # ---------------------------------------------------------------------------
    # Nombre del cloud de Cloudinary (visible en el dashboard).
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")

    # API Key pública de Cloudinary.
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")

    # API Secret de Cloudinary (NUNCA exponer en el cliente).
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna la instancia singleton de Settings.
    
    El decorador `lru_cache` garantiza que Settings se instancie una sola vez
    durante el ciclo de vida de la aplicación (patrón Singleton).
    """
    return Settings()


# Instancia global accesible directamente
settings: Settings = get_settings()
