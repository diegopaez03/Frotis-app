"""
__init__.py
-----------
Punto de entrada del paquete `app.models`.

Exporta todos los modelos ORM del sistema para que:
1. Alembic los detecte automáticamente al generar migraciones.
2. El resto de la aplicación pueda importarlos desde un único lugar.

Uso recomendado:
    from app.models import Usuario, Analisis, Deteccion, Feedback, ClaseCelula
"""

from app.models.base import Base
from app.models.clases_celulas import ClaseCelula
from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion, Feedback

__all__ = [
    "Base",
    "ClaseCelula",
    "Usuario",
    "Analisis",
    "Deteccion",
    "Feedback",
]
