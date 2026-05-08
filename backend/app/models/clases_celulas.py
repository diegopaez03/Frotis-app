"""
cell_class.py
-------------
Modelo ORM para la tabla `clases_celulas`.

Actúa como un catálogo inmutable de los tipos de glóbulos blancos
que el modelo de IA puede detectar (ej. Neutrófilo, Linfocito, etc.).
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from datetime import datetime

from app.models.base import Base

# Importaciones diferidas para evitar referencias circulares.
if TYPE_CHECKING:
    from app.models.analisis import Deteccion, Feedback


class ClaseCelula(Base):
    """
    Modelo ORM que representa la tabla `clases_celulas`.

    Catálogo de los tipos de células (glóbulos blancos) reconocidos por el sistema.
    Este catálogo es la referencia para las detecciones de la IA y las correcciones
    del bioquímico. Soporta baja lógica mediante `fechaBaja`.
    """

    __tablename__ = "clases_celulas"

    # --- Columnas ---

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Identificador numérico único de la clase de célula.",
    )

    nombre: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment=(
            "Nombre canónico de la clase celular, ej: 'Neutrofilo', 'Linfocito', "
            "'Monocito', 'Eosinofilo', 'Basofilo'."
        ),
    )

    fechaBaja: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment=(
            "Timestamp de baja lógica. Si es NULL, la clase está activa. "
            "Si tiene valor, fue deshabilitada sin eliminarse del catálogo."
        ),
    )

    # --- Relaciones ---

    # Una clase puede estar referenciada en muchas detecciones.
    detecciones: Mapped[List["Deteccion"]] = relationship(
        "Deteccion",
        back_populates="clase",
        lazy="select",
    )

    # Una clase puede estar referenciada en muchos registros de feedback
    # como la clase corregida por el bioquímico.
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback",
        back_populates="clase_corregida",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ClaseCelula id={self.id!r} nombre={self.nombre!r}>"
