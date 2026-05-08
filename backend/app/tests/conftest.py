"""
conftest.py
-----------
Configuración global de Pytest para el proyecto Frotis-App.

Estrategia de testing:
  - Se usa SQLite en memoria (:memory:) para evitar dependencia de PostgreSQL
    durante los tests (no requiere Docker corriendo).
  - Se aplica el patrón "transaction rollback" para aislar cada test:
    cada test se ejecuta dentro de una transacción que se revierte al finalizar,
    garantizando un estado de BD limpio sin recrear las tablas.
  - La dependencia `get_db` de FastAPI se sobreescribe (dependency override)
    para que los endpoints usen la sesión de test en lugar de la de producción.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.base import Base

# ---------------------------------------------------------------------------
# Constantes de configuración del entorno de testing
# ---------------------------------------------------------------------------

# URL de SQLite en memoria. StaticPool garantiza que todos los threads
# compartan la misma conexión (necesario para TestClient + SQLite).
TEST_DATABASE_URL: str = "sqlite:///:memory:"

# ---------------------------------------------------------------------------
# Fixtures de base de datos
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """
    Crea el engine de SQLite en memoria UNA SOLA VEZ por sesión de tests.
    
    `check_same_thread=False` es necesario para SQLite cuando se usa con
    FastAPI (que puede usar múltiples threads internamente).
    `StaticPool` asegura que todos los accesos usen la misma conexión.
    """
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crear todas las tablas al inicio de la sesión
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    # Eliminar todas las tablas al finalizar la sesión
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session(engine) -> Session:
    """
    Provee una sesión de BD aislada por test usando el patrón de rollback.
    
    Cada test obtiene una conexión con una transacción abierta. Al terminar
    el test, se hace rollback en lugar de commit, dejando la BD en estado limpio
    para el siguiente test. Esto es más rápido que recrear las tablas.
    """
    connection = engine.connect()
    transaction = connection.begin()
    
    TestingSessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session: Session = TestingSessionLocal()

    yield session

    # Teardown: revertir la transacción para dejar la BD limpia
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """
    Provee un TestClient de FastAPI con la BD de test inyectada.
    
    Sobreescribe la dependencia `get_db` de la aplicación para que todos
    los endpoints usen la sesión de test (con rollback automático).
    """
    def override_get_db():
        """Dependencia de test que provee la sesión de BD aislada."""
        try:
            yield db_session
        finally:
            pass  # El cierre se maneja en el fixture db_session

    # Sobreescribir la dependencia en la instancia de la app
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Limpiar overrides después de cada test para no contaminar otros tests
    app.dependency_overrides.clear()
