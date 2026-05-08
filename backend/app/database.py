"""
database.py
-----------
Configuración central de la conexión a la base de datos PostgreSQL.

Este módulo expone:
- `engine`: el motor de SQLAlchemy, reutilizable en toda la app.
- `SessionLocal`: fábrica de sesiones de base de datos.
- `get_db`: dependencia de FastAPI (Depends) para inyección de sesión en los endpoints.

Variables de entorno requeridas (leer desde el archivo .env en la raíz del proyecto):
    DB_USER     — usuario de PostgreSQL
    DB_PASSWORD — contraseña de PostgreSQL
    DB_HOST     — host del servidor (default: "db" para Docker Compose)
    DB_PORT     — puerto del servidor (default: 5432)
    DB_NAME     — nombre de la base de datos

Ejemplo de DATABASE_URL generada:
    postgresql://user:frotis123@db:5432/frotis_db
"""

import os
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base  # noqa: F401 — importado para que Alembic detecte los modelos

# ---------------------------------------------------------------------------
# 1. Construcción de la DATABASE_URL desde variables de entorno
# ---------------------------------------------------------------------------

DB_USER: str = os.getenv("DB_USER", "user")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "frotis123")
DB_HOST: str = os.getenv("DB_HOST", "db")       # "db" = nombre del servicio en Docker Compose
DB_PORT: str = os.getenv("DB_PORT", "5432")
DB_NAME: str = os.getenv("DB_NAME", "frotis_db")

DATABASE_URL: str = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------------------------------------------------------------------------
# 2. Engine — conexión al servidor PostgreSQL
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    # Pool de conexiones para producción; ajustar según la carga esperada.
    pool_size=10,           # Conexiones persistentes en el pool.
    max_overflow=20,        # Conexiones extra permitidas sobre pool_size.
    pool_pre_ping=True,     # Verifica la conexión antes de usarla (evita "broken pipe").
    pool_recycle=1800,      # Recicla conexiones tras 30 minutos (evita timeouts del server).
    echo=os.getenv("DB_ECHO", "false").lower() == "true",  # Loguea SQL si DB_ECHO=true
)

# ---------------------------------------------------------------------------
# 3. SessionLocal — fábrica de sesiones
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # El commit debe hacerse explícitamente.
    autoflush=False,    # El flush se realiza manualmente o al hacer commit.
    expire_on_commit=False,  # Los objetos no expiran tras commit (útil con Pydantic/schemas).
)

# ---------------------------------------------------------------------------
# 4. Dependencia para FastAPI (inyección de sesión en endpoints)
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Generador que provee una sesión de base de datos por request.

    Garantiza que la sesión se cierre siempre al finalizar el request,
    incluso si ocurre una excepción.

    Uso en un endpoint de FastAPI:

        @router.get("/analisis")
        def listar_analisis(db: DbSession):
            return db.query(Analisis).all()
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias de tipo para simplificar la firma de los endpoints.
# Uso: `def mi_endpoint(db: DbSession)` en lugar del Annotated completo.
DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# 5. Utilidad: crear todas las tablas (útil en desarrollo/testing)
# ---------------------------------------------------------------------------

def create_all_tables() -> None:
    """
    Crea todas las tablas definidas en los modelos ORM si no existen.

    ADVERTENCIA: En producción se debe usar Alembic para migraciones.
    Esta función es útil para entornos de desarrollo o pruebas unitarias.
    """
    # Importar todos los modelos para que Base los registre antes de crear las tablas.
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
