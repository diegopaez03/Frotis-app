"""
base.py
-------
Módulo de configuración base para SQLAlchemy 2.0.

Define el `DeclarativeBase` del cual heredarán todos los modelos ORM
del proyecto. Centralizar la base en este archivo evita importaciones
circulares y facilita el uso con Alembic para migraciones.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Clase base para todos los modelos ORM del proyecto.

    Todos los modelos deben heredar de esta clase para que SQLAlchemy
    los reconozca y Alembic pueda generar las migraciones automáticamente.

    Ejemplo de uso:
        from app.models.base import Base

        class MiModelo(Base):
            __tablename__ = "mi_tabla"
            ...
    """
    pass
