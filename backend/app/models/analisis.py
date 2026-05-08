"""
analysis.py
-----------
Modelos ORM para las tablas `analisis`, `detecciones` y `feedback`.

Estos tres modelos están fuertemente acoplados (un análisis genera
detecciones, y el bioquímico genera feedback sobre ambos), por lo que
se agrupan en un mismo módulo para simplificar las importaciones y
evitar dependencias circulares complejas.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

# Importación diferida del modelo Usuario para evitar circularidad.
if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.clases_celulas import ClaseCelula


# =============================================================================
# Modelo: Analisis
# =============================================================================

class Analisis(Base):
    """
    Modelo ORM que representa la tabla `analisis`.

    Cada registro representa un análisis de imagen de frotis sanguíneo
    solicitado por un usuario. El campo `estado` refleja el ciclo de vida
    del análisis (PENDING → PROCESSING → COMPLETED / FAILED).

    Soporta baja lógica mediante `fechaBaja`.
    """

    __tablename__ = "analisis"

    # --- Columnas ---

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del análisis (UUID v4).",
    )

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al usuario propietario del análisis.",
    )

    imagen_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URL o ruta del archivo de imagen a analizar (almacenado en object storage).",
    )

    estado: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        comment=(
            "Estado del ciclo de vida del análisis. "
            "Valores esperados: PENDING, PROCESSING, COMPLETED, FAILED."
        ),
    )

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp de creación del análisis.",
    )

    fechaBaja: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment=(
            "Timestamp de baja lógica. Si es NULL, el análisis está activo. "
            "Si tiene valor, fue marcado como eliminado sin borrarse de la BD."
        ),
    )

    # --- Relaciones ---

    # Muchos análisis pertenecen a un único usuario.
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        back_populates="analisis",
        lazy="select",
    )

    # Un análisis tiene muchas detecciones generadas por la IA.
    # cascade="all, delete-orphan": borrar el análisis elimina sus detecciones.
    detecciones: Mapped[List["Deteccion"]] = relationship(
        "Deteccion",
        back_populates="analisis",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Un análisis tiene mucho feedback del bioquímico.
    # cascade="all, delete-orphan": borrar el análisis elimina su feedback.
    feedback: Mapped[List["Feedback"]] = relationship(
        "Feedback",
        back_populates="analisis",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Analisis id={self.id!r} estado={self.estado!r}>"


# =============================================================================
# Modelo: Deteccion
# =============================================================================

class Deteccion(Base):
    """
    Modelo ORM que representa la tabla `detecciones`.

    Cada registro almacena un glóbulo blanco detectado automáticamente
    por el modelo de IA (YOLO u otro). El bounding box se guarda en JSONB
    con el formato [x_min, y_min, x_max, y_max].

    Soporta baja lógica mediante `fechaBaja`.
    """

    __tablename__ = "detecciones"

    # --- Columnas ---

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único de la detección (UUID v4).",
    )

    analisis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analisis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al análisis al que pertenece esta detección.",
    )

    clase_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("clases_celulas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK al catálogo de clases celulares (tipo de glóbulo detectado).",
    )

    confianza: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Puntuación de confianza del modelo de IA (valor entre 0.0 y 1.0).",
    )

    bbox: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "Bounding box de la célula detectada en formato JSONB. "
            "Estructura esperada: [x_min, y_min, x_max, y_max]."
        ),
    )

    fechaBaja: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment=(
            "Timestamp de baja lógica. Si es NULL, la detección está activa. "
            "Si tiene valor, fue descartada sin eliminarse de la BD."
        ),
    )

    # --- Relaciones ---

    # Una detección pertenece a un único análisis.
    analisis: Mapped["Analisis"] = relationship(
        "Analisis",
        back_populates="detecciones",
        lazy="select",
    )

    # Una detección pertenece a una única clase celular del catálogo.
    clase: Mapped["ClaseCelula"] = relationship(
        "ClaseCelula",
        back_populates="detecciones",
        lazy="select",
    )

    # Una detección puede tener feedback asociado.
    # cascade="all, delete-orphan": al borrar la detección, se borra su feedback.
    feedback: Mapped[List["Feedback"]] = relationship(
        "Feedback",
        back_populates="deteccion",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Deteccion id={self.id!r} clase_id={self.clase_id!r} "
            f"confianza={self.confianza!r}>"
        )


# =============================================================================
# Modelo: Feedback
# =============================================================================

class Feedback(Base):
    """
    Modelo ORM que representa la tabla `feedback`.

    Almacena las correcciones manuales realizadas por el bioquímico sobre
    las detecciones de la IA. Los tipos de corrección posibles son:
    - FALSO_POSITIVO: La IA detectó algo que no es una célula válida.
    - NUEVA_DETECCION: El bioquímico agrega una célula que la IA no vio.
    - CAMBIO_CLASE: La IA clasificó mal el tipo de glóbulo.

    Cuando `deteccion_id` es NULL, indica que el bioquímico está añadiendo
    una detección completamente nueva (no corrigiendo una existente).

    Soporta baja lógica mediante `fechaBaja`.
    """

    __tablename__ = "feedback"

    # --- Columnas ---

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único del registro de feedback (UUID v4).",
    )

    analisis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analisis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK al análisis sobre el cual se está emitiendo el feedback.",
    )

    deteccion_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detecciones.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
        comment=(
            "FK a la detección original que se está corrigiendo. "
            "Es NULL cuando el bioquímico agrega una célula nueva no detectada por la IA."
        ),
    )

    tipoCorreccion: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment=(
            "Tipo de corrección aplicada. "
            "Valores esperados: FALSO_POSITIVO, NUEVA_DETECCION, CAMBIO_CLASE."
        ),
    )

    claseCorregida: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("clases_celulas.id", ondelete="RESTRICT"),
        nullable=True,
        default=None,
        comment=(
            "FK a la clase celular correcta según el bioquímico. "
            "Usado principalmente en correcciones de tipo CAMBIO_CLASE y NUEVA_DETECCION."
        ),
    )

    bbox_corregido: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment=(
            "Bounding box corregido o nuevo en formato JSONB. "
            "Estructura esperada: [x_min, y_min, x_max, y_max]. "
            "Requerido para NUEVA_DETECCION, opcional para CAMBIO_CLASE."
        ),
    )

    fechaBaja: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment=(
            "Timestamp de baja lógica. Si es NULL, el feedback está vigente. "
            "Si tiene valor, fue anulado sin eliminarse de la BD."
        ),
    )

    # --- Relaciones ---

    # El feedback pertenece a un único análisis.
    analisis: Mapped["Analisis"] = relationship(
        "Analisis",
        back_populates="feedback",
        lazy="select",
    )

    # El feedback puede estar relacionado con una detección existente (opcional).
    deteccion: Mapped[Optional["Deteccion"]] = relationship(
        "Deteccion",
        back_populates="feedback",
        lazy="select",
    )

    # El feedback puede referenciar la clase celular corregida (opcional).
    clase_corregida: Mapped[Optional["ClaseCelula"]] = relationship(
        "ClaseCelula",
        back_populates="feedbacks",
        foreign_keys=[claseCorregida],
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Feedback id={self.id!r} tipo={self.tipoCorreccion!r} "
            f"analisis_id={self.analisis_id!r}>"
        )
