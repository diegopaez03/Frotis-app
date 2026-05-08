"""
user.py
-------
Modelo ORM para la tabla `usuarios`.

Representa a los bioquímicos o usuarios del sistema que realizan
y corrigen los análisis de frotis sanguíneos.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

# Importaciones diferidas para evitar referencias circulares entre modelos.
if TYPE_CHECKING:
    from app.models.analisis import Analisis


class Usuario(Base):
    """
    Modelo ORM que representa la tabla `usuarios`.

    Almacena las credenciales y metadatos de los usuarios del sistema.
    Soporta baja lógica mediante el campo `fechaBaja`.
    """

    __tablename__ = "usuarios"

    # --- Columnas ---

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del usuario (UUID v4).",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Dirección de correo electrónico, debe ser única en el sistema.",
    )

    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hash de la contraseña del usuario (ej. bcrypt).",
    )

    fechaCreacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación del registro en la base de datos.",
    )

    fechaModificacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp de la última modificación del registro.",
    )

    fechaBaja: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment=(
            "Timestamp de baja lógica. Si es NULL, el usuario está activo. "
            "Si tiene valor, el usuario fue dado de baja sin eliminarse de la BD."
        ),
    )

    # --- Relaciones ---

    # Un usuario puede tener muchos análisis asociados.
    # cascade="all, delete-orphan": si se elimina un usuario, sus análisis se eliminan.
    analisis: Mapped[List["Analisis"]] = relationship(
        "Analisis",
        back_populates="usuario",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Usuario id={self.id!r} email={self.email!r}>"
