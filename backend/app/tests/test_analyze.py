"""
test_analyze.py
---------------
Tests unitarios y de integración TDD para el endpoint de consulta del historial
de análisis del usuario: `GET /analysis`.
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion
from app.models.clases_celulas import ClaseCelula

# ---------------------------------------------------------------------------
# Constantes y URLs
# ---------------------------------------------------------------------------
ANALYSIS_LIST_URL = "/analysis"
REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

EMAIL_USER_A = "user_a@lab.com"
EMAIL_USER_B = "user_b@lab.com"
COMMON_PASSWORD = "PasswordA123"

# ---------------------------------------------------------------------------
# Fixtures auxiliares
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a_credentials(client: TestClient) -> dict:
    """Registra y retorna las credenciales del usuario A."""
    payload = {"email": EMAIL_USER_A, "password": COMMON_PASSWORD}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201
    return payload

@pytest.fixture
def user_b_credentials(client: TestClient) -> dict:
    """Registra y retorna las credenciales del usuario B."""
    payload = {"email": EMAIL_USER_B, "password": COMMON_PASSWORD}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201
    return payload

@pytest.fixture
def auth_headers_user_a(client: TestClient, user_a_credentials: dict) -> dict:
    """Retorna las cabeceras de autorización JWT del usuario A."""
    response = client.post(LOGIN_URL, json=user_a_credentials)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_user_b(client: TestClient, user_b_credentials: dict) -> dict:
    """Retorna las cabeceras de autorización JWT del usuario B."""
    response = client.post(LOGIN_URL, json=user_b_credentials)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def seed_classes(db_session: Session) -> dict[str, int]:
    """Inicializa clases celulares de prueba en la base de datos."""
    classes = ["Neutrófilo", "Linfocito", "Basófilo"]
    class_map = {}
    for name in classes:
        c = ClaseCelula(nombre=name)
        db_session.add(c)
        db_session.flush()
        class_map[name] = c.id
    db_session.commit()
    return class_map

# ---------------------------------------------------------------------------
# Tests unitarios e integración
# ---------------------------------------------------------------------------

def test_list_analysis_empty(client: TestClient, auth_headers_user_a: dict) -> None:
    """
    DADO un usuario autenticado sin análisis registrados en el sistema,
    CUANDO solicita GET /analysis,
    ENTONCES se retorna HTTP 200 con una lista vacía.
    """
    response = client.get(ANALYSIS_LIST_URL, headers=auth_headers_user_a)
    assert response.status_code == 200
    assert response.json() == []


def test_list_analysis_unauthorized(client: TestClient) -> None:
    """
    DADO un cliente sin token o con token inválido,
    CUANDO solicita GET /analysis,
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    # Sin cabecera
    response = client.get(ANALYSIS_LIST_URL)
    assert response.status_code == 401

    # Token inválido
    bad_headers = {"Authorization": "Bearer token.expirado.invalido"}
    response = client.get(ANALYSIS_LIST_URL, headers=bad_headers)
    assert response.status_code == 401


def test_list_analysis_success_and_isolation(
    client: TestClient, 
    auth_headers_user_a: dict, 
    auth_headers_user_b: dict,
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO el Usuario A con 2 análisis y el Usuario B con 1 análisis en la BD,
    CUANDO el Usuario A solicita GET /analysis,
    ENTONCES se retorna HTTP 200 conteniendo únicamente sus 2 análisis,
    con sus detecciones asociadas y la distribución de clases correcta.
    """
    # 1. Obtener los IDs de los usuarios desde la BD
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()
    user_b = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_B).one()

    # 2. Registrar análisis para Usuario A
    # Análisis A1
    analisis_a1 = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/img_a1.jpg", estado="COMPLETED")
    db_session.add(analisis_a1)
    db_session.flush()

    det_a1_1 = Deteccion(
        analisis_id=analisis_a1.id, 
        clase_id=seed_classes["Neutrófilo"], 
        confianza=0.95, 
        bbox=[10.0, 20.0, 110.0, 120.0]
    )
    det_a1_2 = Deteccion(
        analisis_id=analisis_a1.id, 
        clase_id=seed_classes["Linfocito"], 
        confianza=0.88, 
        bbox=[200.0, 210.0, 300.0, 310.0]
    )
    db_session.add_all([det_a1_1, det_a1_2])

    # Análisis A2
    analisis_a2 = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/img_a2.jpg", estado="COMPLETED")
    db_session.add(analisis_a2)
    db_session.flush()

    det_a2_1 = Deteccion(
        analisis_id=analisis_a2.id, 
        clase_id=seed_classes["Neutrófilo"], 
        confianza=0.91, 
        bbox=[50.0, 50.0, 150.0, 150.0]
    )
    db_session.add(det_a2_1)

    # 3. Registrar análisis para Usuario B
    analisis_b1 = Analisis(usuario_id=user_b.id, imagen_url="http://cloudinary.com/img_b1.jpg", estado="COMPLETED")
    db_session.add(analisis_b1)
    db_session.flush()

    det_b1_1 = Deteccion(
        analisis_id=analisis_b1.id, 
        clase_id=seed_classes["Basófilo"], 
        confianza=0.75, 
        bbox=[30.0, 40.0, 130.0, 140.0]
    )
    db_session.add(det_b1_1)

    db_session.commit()

    # 4. Solicitar historial del Usuario A
    response = client.get(ANALYSIS_LIST_URL, headers=auth_headers_user_a)
    assert response.status_code == 200
    data = response.json()

    # El Usuario A debe ver exactamente 2 análisis
    assert len(data) == 2
    
    # Validar orden por fecha descendente (a2 y a1)
    # Buscamos el análisis A1 en la lista por ID
    a1_json = next(x for x in data if x["id"] == str(analisis_a1.id))
    a2_json = next(x for x in data if x["id"] == str(analisis_a2.id))

    # Verificar estructura de A1 (2 detecciones)
    assert a1_json["imagen_url"] == "http://cloudinary.com/img_a1.jpg"
    assert a1_json["total_detecciones"] == 2
    assert len(a1_json["detecciones"]) == 2
    
    # Distribución en A1: 50% Neutrófilo y 50% Linfocito
    assert a1_json["distribucion"]["Neutrófilo"]["cantidad"] == 1
    assert a1_json["distribucion"]["Neutrófilo"]["porcentaje"] == 50.0
    assert a1_json["distribucion"]["Linfocito"]["cantidad"] == 1
    assert a1_json["distribucion"]["Linfocito"]["porcentaje"] == 50.0

    # Verificar estructura de A2 (1 detección)
    assert a2_json["imagen_url"] == "http://cloudinary.com/img_a2.jpg"
    assert a2_json["total_detecciones"] == 1
    assert len(a2_json["detecciones"]) == 1
    assert a2_json["detecciones"][0]["clase"] == "Neutrófilo"
    assert a2_json["detecciones"][0]["confianza"] == 0.91

    # Distribución en A2: 100% Neutrófilo
    assert a2_json["distribucion"]["Neutrófilo"]["cantidad"] == 1
    assert a2_json["distribucion"]["Neutrófilo"]["porcentaje"] == 100.0


def test_list_analysis_soft_delete_filter(
    client: TestClient, 
    auth_headers_user_a: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO un usuario que tiene análisis y detecciones activas mezcladas con otras eliminadas lógicamente,
    CUANDO solicita GET /analysis,
    ENTONCES sólo se retornan los análisis y detecciones con fechaBaja nula.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    # 1. Análisis A1: Activo
    analisis_activo = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/img_activo.jpg", estado="COMPLETED")
    db_session.add(analisis_activo)
    db_session.flush()

    # Detección activa
    det_activa = Deteccion(
        analisis_id=analisis_activo.id, 
        clase_id=seed_classes["Neutrófilo"], 
        confianza=0.90, 
        bbox=[10.0, 20.0, 110.0, 120.0]
    )
    # Detección eliminada lógicamente (baja lógica)
    det_eliminada = Deteccion(
        analisis_id=analisis_activo.id, 
        clase_id=seed_classes["Linfocito"], 
        confianza=0.85, 
        bbox=[20.0, 30.0, 120.0, 130.0],
        fechaBaja=datetime.now(timezone.utc)
    )
    db_session.add_all([det_activa, det_eliminada])

    # 2. Análisis A2: Eliminado lógicamente (baja lógica)
    analisis_eliminado = Analisis(
        usuario_id=user_a.id, 
        imagen_url="http://cloudinary.com/img_eliminado.jpg", 
        estado="COMPLETED",
        fechaBaja=datetime.now(timezone.utc)
    )
    db_session.add(analisis_eliminado)
    db_session.flush()

    det_a2 = Deteccion(
        analisis_id=analisis_eliminado.id, 
        clase_id=seed_classes["Basófilo"], 
        confianza=0.70, 
        bbox=[30.0, 40.0, 130.0, 140.0]
    )
    db_session.add(det_a2)

    db_session.commit()

    # 3. Solicitar historial
    response = client.get(ANALYSIS_LIST_URL, headers=auth_headers_user_a)
    assert response.status_code == 200
    data = response.json()

    # Debe retornar únicamente 1 análisis activo
    assert len(data) == 1
    activo_json = data[0]
    assert activo_json["id"] == str(analisis_activo.id)
    assert activo_json["imagen_url"] == "http://cloudinary.com/img_activo.jpg"
    
    # Debe contener sólo 1 detección activa (la eliminada se omite)
    assert activo_json["total_detecciones"] == 1
    assert len(activo_json["detecciones"]) == 1
    assert activo_json["detecciones"][0]["id"] == str(det_activa.id)
    assert activo_json["detecciones"][0]["clase"] == "Neutrófilo"

    # La distribución debe calcularse sólo sobre la detección activa (100% Neutrófilo, 0% Linfocito)
    assert "Neutrófilo" in activo_json["distribucion"]
    assert "Linfocito" not in activo_json["distribucion"]
    assert activo_json["distribucion"]["Neutrófilo"]["cantidad"] == 1
    assert activo_json["distribucion"]["Neutrófilo"]["porcentaje"] == 100.0


# ---------------------------------------------------------------------------
# Tests para GET /analysis/{analysis_id} (Detalle de análisis)
# ---------------------------------------------------------------------------

def test_get_analysis_detail_success(
    client: TestClient, 
    auth_headers_user_a: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO un usuario autenticado y un análisis propio y activo,
    CUANDO solicita GET /analysis/{analysis_id},
    ENTONCES se retorna HTTP 200 con la estructura detallada del análisis.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    analisis = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/detail.jpg", estado="COMPLETED")
    db_session.add(analisis)
    db_session.flush()

    det = Deteccion(
        analisis_id=analisis.id,
        clase_id=seed_classes["Linfocito"],
        confianza=0.92,
        bbox=[10.0, 10.0, 50.0, 50.0]
    )
    db_session.add(det)
    db_session.commit()

    # Petición exitosa
    url = f"/analysis/{analisis.id}"
    response = client.get(url, headers=auth_headers_user_a)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(analisis.id)
    assert data["imagen_url"] == "http://cloudinary.com/detail.jpg"
    assert data["total_detecciones"] == 1
    assert data["detecciones"][0]["clase"] == "Linfocito"
    assert data["distribucion"]["Linfocito"]["cantidad"] == 1


def test_get_analysis_detail_not_found(client: TestClient, auth_headers_user_a: dict) -> None:
    """
    DADO un ID de análisis inexistente,
    CUANDO solicita GET /analysis/{analysis_id},
    ENTONCES se retorna HTTP 404 Not Found.
    """
    random_uuid = uuid.uuid4()
    response = client.get(f"/analysis/{random_uuid}", headers=auth_headers_user_a)
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"].lower()


def test_get_analysis_detail_unauthorized(client: TestClient) -> None:
    """
    DADO una petición sin token válido para un análisis específico,
    CUANDO solicita GET /analysis/{analysis_id},
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    random_uuid = uuid.uuid4()
    response = client.get(f"/analysis/{random_uuid}")
    assert response.status_code == 401


def test_get_analysis_detail_isolation(
    client: TestClient, 
    auth_headers_user_a: dict, 
    auth_headers_user_b: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO el análisis de un Usuario A,
    CUANDO el Usuario B intenta acceder a su detalle mediante GET /analysis/{analysis_id},
    ENTONCES se retorna HTTP 404 Not Found por privacidad.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    analisis_a = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/privado.jpg", estado="COMPLETED")
    db_session.add(analisis_a)
    db_session.commit()

    # Usuario B consulta análisis del Usuario A
    url = f"/analysis/{analisis_a.id}"
    response = client.get(url, headers=auth_headers_user_b)
    
    # Debe retornar 404
    assert response.status_code == 404


def test_get_analysis_detail_soft_delete(
    client: TestClient, 
    auth_headers_user_a: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO un análisis eliminado lógicamente (baja lógica),
    CUANDO solicita GET /analysis/{analysis_id},
    ENTONCES se retorna HTTP 404 Not Found.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    # Análisis eliminado lógicamente
    analisis_soft_deleted = Analisis(
        usuario_id=user_a.id, 
        imagen_url="http://cloudinary.com/deleted.jpg", 
        estado="COMPLETED",
        fechaBaja=datetime.now(timezone.utc)
    )
    db_session.add(analisis_soft_deleted)
    db_session.commit()

    url = f"/analysis/{analisis_soft_deleted.id}"
    response = client.get(url, headers=auth_headers_user_a)
    
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests para DELETE /analysis/{analysis_id} (Baja lógica de análisis)
# ---------------------------------------------------------------------------

def test_delete_analysis_success(
    client: TestClient, 
    auth_headers_user_a: dict, 
    db_session: Session
) -> None:
    """
    DADO un usuario autenticado y un análisis propio y activo,
    CUANDO solicita DELETE /analysis/{analysis_id},
    ENTONCES se retorna HTTP 200 con un mensaje de éxito,
    Y el análisis se marca con fechaBaja (baja lógica) en la base de datos.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    analisis = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/frotis_delete.jpg", estado="COMPLETED")
    db_session.add(analisis)
    db_session.commit()

    url = f"/analysis/{analisis.id}"
    response = client.delete(url, headers=auth_headers_user_a)
    
    assert response.status_code == 200
    assert "eliminado" in response.json()["message"].lower()

    # Verificar baja lógica en BD
    db_session.expire_all()
    db_analisis = db_session.query(Analisis).filter(Analisis.id == analisis.id).one()
    assert db_analisis.fechaBaja is not None


def test_delete_analysis_not_found(client: TestClient, auth_headers_user_a: dict) -> None:
    """
    DADO un ID de análisis inexistente,
    CUANDO solicita DELETE /analysis/{analysis_id},
    ENTONCES se retorna HTTP 404 Not Found.
    """
    random_uuid = uuid.uuid4()
    response = client.delete(f"/analysis/{random_uuid}", headers=auth_headers_user_a)
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"].lower()


def test_delete_analysis_unauthorized(client: TestClient) -> None:
    """
    DADO una petición sin token válido,
    CUANDO solicita DELETE /analysis/{analysis_id},
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    random_uuid = uuid.uuid4()
    response = client.delete(f"/analysis/{random_uuid}")
    assert response.status_code == 401


def test_delete_analysis_isolation(
    client: TestClient, 
    auth_headers_user_a: dict, 
    auth_headers_user_b: dict, 
    db_session: Session
) -> None:
    """
    DADO el análisis del Usuario A,
    CUANDO el Usuario B intenta darlo de baja mediante DELETE /analysis/{analysis_id},
    ENTONCES se retorna HTTP 404 Not Found,
    Y el análisis del Usuario A permanece activo (fechaBaja es NULL).
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    analisis_a = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/privado_del.jpg", estado="COMPLETED")
    db_session.add(analisis_a)
    db_session.commit()

    # Usuario B intenta eliminar análisis del Usuario A
    url = f"/analysis/{analisis_a.id}"
    response = client.delete(url, headers=auth_headers_user_b)
    
    assert response.status_code == 404

    # Verificar que el análisis de A siga activo en la BD
    db_session.expire_all()
    db_analisis_a = db_session.query(Analisis).filter(Analisis.id == analisis_a.id).one()
    assert db_analisis_a.fechaBaja is None


