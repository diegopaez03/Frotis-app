"""
alembic/env.py
--------------
Configuración del entorno de ejecución de Alembic.

Conecta Alembic con:
1. La DATABASE_URL de la aplicación (leída desde variables de entorno / .env).
2. Los metadatos de todos los modelos ORM para el soporte de `--autogenerate`.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Asegurarse de que el paquete `app` sea importable desde este directorio.
# Agrega el directorio `backend/` al sys.path.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Cargar variables de entorno desde el archivo .env en la raíz del proyecto.
# Esto es necesario cuando se ejecuta alembic desde la línea de comandos
# fuera del contenedor Docker.
# ---------------------------------------------------------------------------
env_file = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_file)

# ---------------------------------------------------------------------------
# Configuración de Alembic
# ---------------------------------------------------------------------------
config = context.config

# Configurar el logging de Python usando el alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Inyectar la DATABASE_URL dinámica (construida desde variables de entorno).
# Esto sobreescribe el valor estático de `sqlalchemy.url` en alembic.ini.
# ---------------------------------------------------------------------------
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# ---------------------------------------------------------------------------
# Registrar los metadatos de todos los modelos ORM para autogenerate.
# La importación de `app.models` registra todos los modelos en Base.metadata.
# ---------------------------------------------------------------------------
import app.models  # noqa: F401, E402 — importación necesaria para registrar modelos
from app.models.base import Base  # noqa: E402

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Funciones de migración
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Ejecuta las migraciones en modo 'offline'.

    En este modo, Alembic genera el SQL sin necesidad de una conexión
    activa a la base de datos. Útil para generar scripts de migración
    para revisar antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Comparar tipos de columna para detectar cambios de tipo en autogenerate.
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta las migraciones en modo 'online'.

    Crea una conexión real a la base de datos y aplica las migraciones
    directamente.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Comparar tipos de columna para detectar cambios de tipo en autogenerate.
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
