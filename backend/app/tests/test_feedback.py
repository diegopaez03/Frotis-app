"""
test_feedback.py
----------------
Tests unitarios y de integración TDD para el endpoint de guardado y aplicación
de feedback: `POST /analysis/{analysis_id}/feedback`.
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion, Feedback
from app.models.clases_celulas import ClaseCelula

# ---------------------------------------------------------------------------
# Constantes y URLs
# ---------------------------------------------------------------------------
REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

EMAIL_USER_A = "doctor_a@lab.com"
EMAIL_USER_B = "doctor_b@lab.com"
COMMON_PASSWORD = "PasswordA123"

# ---------------------------------------------------------------------------
# Fixtures auxiliares
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a_credentials(client: TestClient) -> dict:
    payload = {"email": EMAIL_USER_A, "password": COMMON_PASSWORD}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201
    return payload

@pytest.fixture
def user_b_credentials(client: TestClient) -> dict:
    payload = {"email": EMAIL_USER_B, "password": COMMON_PASSWORD}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201
    return payload

@pytest.fixture
def auth_headers_user_a(client: TestClient, user_a_credentials: dict) -> dict:
    response = client.post(LOGIN_URL, json=user_a_credentials)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_user_b(client: TestClient, user_b_credentials: dict) -> dict:
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

def test_save_feedback_success(
    client: TestClient, 
    auth_headers_user_a: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO un usuario autenticado y un análisis propio con 2 detecciones,
    CUANDO envía feedback para reportar un FALSO_POSITIVO y un CAMBIO_CLASE,
    Y además reporta una NUEVA_DETECCION manual,
    ENTONCES se retorna HTTP 200 con un mensaje de éxito,
    Y las posteriores consultas GET muestran el análisis corregido.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    # 1. Crear análisis original de la IA
    analisis = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/frotis1.jpg", estado="COMPLETED")
    db_session.add(analisis)
    db_session.flush()

    det1 = Deteccion(analisis_id=analisis.id, clase_id=seed_classes["Neutrófilo"], confianza=0.90, bbox=[10.0, 10.0, 50.0, 50.0])
    det2 = Deteccion(analisis_id=analisis.id, clase_id=seed_classes["Basófilo"], confianza=0.85, bbox=[100.0, 100.0, 150.0, 150.0])
    db_session.add_all([det1, det2])
    db_session.commit()

    # 2. Enviar Feedback
    # det1 -> CAMBIO_CLASE a Linfocito
    # det2 -> FALSO_POSITIVO (se descarta)
    # manual -> NUEVA_DETECCION de Neutrófilo
    feedback_payload = {
        "feedbacks": [
            {
                "deteccion_id": str(det1.id),
                "tipoCorreccion": "CAMBIO_CLASE",
                "claseCorregida": "Linfocito"
            },
            {
                "deteccion_id": str(det2.id),
                "tipoCorreccion": "FALSO_POSITIVO"
            },
            {
                "deteccion_id": None,
                "tipoCorreccion": "NUEVA_DETECCION",
                "claseCorregida": "Neutrófilo",
                "bbox_corregido": [20.0, 20.0, 80.0, 80.0]
            }
        ]
    }

    url_feedback = f"/analysis/{analisis.id}/feedback"
    response_post = client.post(url_feedback, json=feedback_payload, headers=auth_headers_user_a)
    
    assert response_post.status_code == 200
    assert "feedback registrado" in response_post.json()["message"].lower()

    # 3. Verificar en BD física que los feedbacks estén guardados y activos
    db_feedbacks = db_session.query(Feedback).filter(Feedback.analisis_id == analisis.id, Feedback.fechaBaja.is_(None)).all()
    assert len(db_feedbacks) == 3

    # 4. Consultar el detalle del análisis (GET /analysis/{id}) para verificar la consolidación
    url_detail = f"/analysis/{analisis.id}"
    response_get = client.get(url_detail, headers=auth_headers_user_a)
    
    assert response_get.status_code == 200
    data = response_get.json()

    # El frotis final consolidado debe tener exactamente 2 detecciones (1 modificada y 1 nueva; el falso positivo se eliminó)
    assert data["total_detecciones"] == 2

    # Verificar presencia de las detecciones finales
    detecciones = data["detecciones"]
    clases_detectadas = {d["clase"] for d in detecciones}
    assert clases_detectadas == {"Linfocito", "Neutrófilo"}

    # La detección modificada (anteriormente Neutrófilo) ahora es Linfocito
    det_linfocito = next(d for d in detecciones if d["clase"] == "Linfocito")
    assert det_linfocito["id"] == str(det1.id)
    assert det_linfocito["confianza"] == 0.90 # Mantiene confianza original

    # La nueva detección es Neutrófilo manual
    det_neutrofilo = next(d for d in detecciones if d["clase"] == "Neutrófilo")
    assert det_neutrofilo["id"] is not None
    assert det_neutrofilo["bbox"] == [20.0, 20.0, 80.0, 80.0]
    
    # La distribución estadística debe reflejar: 1 Linfocito (50.0%) y 1 Neutrófilo (50.0%)
    assert data["distribucion"]["Linfocito"]["cantidad"] == 1
    assert data["distribucion"]["Linfocito"]["porcentaje"] == 50.0
    assert data["distribucion"]["Neutrófilo"]["cantidad"] == 1
    assert data["distribucion"]["Neutrófilo"]["porcentaje"] == 50.0


def test_save_feedback_overwrite(
    client: TestClient, 
    auth_headers_user_a: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO un análisis que ya tenía feedbacks previos,
    CUANDO se envía un nuevo lote de feedbacks,
    ENTONCES los feedbacks anteriores se marcan con baja lógica (fechaBaja no nula)
    Y sólo los nuevos rigen la respuesta.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()

    analisis = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/frotis2.jpg", estado="COMPLETED")
    db_session.add(analisis)
    db_session.flush()

    det = Deteccion(analisis_id=analisis.id, clase_id=seed_classes["Neutrófilo"], confianza=0.90, bbox=[10.0, 10.0, 50.0, 50.0])
    db_session.add(det)
    db_session.commit()

    # 1. Enviar primer feedback (CAMBIO_CLASE a Linfocito)
    first_payload = {
        "feedbacks": [
            {
                "deteccion_id": str(det.id),
                "tipoCorreccion": "CAMBIO_CLASE",
                "claseCorregida": "Linfocito"
            }
        ]
    }
    url = f"/analysis/{analisis.id}/feedback"
    client.post(url, json=first_payload, headers=auth_headers_user_a)

    # 2. Enviar segundo feedback (FALSO_POSITIVO) sobreescribiendo el anterior
    second_payload = {
        "feedbacks": [
            {
                "deteccion_id": str(det.id),
                "tipoCorreccion": "FALSO_POSITIVO"
            }
        ]
    }
    client.post(url, json=second_payload, headers=auth_headers_user_a)

    # 3. Comprobar en BD
    # El primer feedback de tipo CAMBIO_CLASE debe estar dado de baja
    old_feedbacks = db_session.query(Feedback).filter(
        Feedback.analisis_id == analisis.id, 
        Feedback.tipoCorreccion == "CAMBIO_CLASE"
    ).all()
    assert len(old_feedbacks) == 1
    assert old_feedbacks[0].fechaBaja is not None # Dado de baja

    # El nuevo feedback debe estar activo
    active_feedbacks = db_session.query(Feedback).filter(
        Feedback.analisis_id == analisis.id, 
        Feedback.fechaBaja.is_(None)
    ).all()
    assert len(active_feedbacks) == 1
    assert active_feedbacks[0].tipoCorreccion == "FALSO_POSITIVO"


def test_save_feedback_unauthorized(client: TestClient) -> None:
    """
    DADO un cliente sin token,
    CUANDO intenta enviar feedback,
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    random_uuid = uuid.uuid4()
    response = client.post(f"/analysis/{random_uuid}/feedback", json={"feedbacks": []})
    assert response.status_code == 401


def test_save_feedback_isolation(
    client: TestClient, 
    auth_headers_user_a: dict, 
    auth_headers_user_b: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO el análisis del Usuario A,
    CUANDO el Usuario B intenta enviarle feedback,
    ENTONCES se retorna HTTP 404 Not Found.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()
    analisis_a = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/privado.jpg", estado="COMPLETED")
    db_session.add(analisis_a)
    db_session.commit()

    # Usuario B envía feedback a análisis de Usuario A
    payload = {"feedbacks": []}
    url = f"/analysis/{analisis_a.id}/feedback"
    response = client.post(url, json=payload, headers=auth_headers_user_b)
    
    assert response.status_code == 404


def test_save_feedback_invalid_detection_id(
    client: TestClient, 
    auth_headers_user_a: dict, 
    auth_headers_user_b: dict, 
    db_session: Session, 
    seed_classes: dict[str, int]
) -> None:
    """
    DADO un análisis del Usuario A,
    CUANDO envía feedback referenciando un deteccion_id que no existe o pertenece a otro análisis,
    ENTONCES se retorna HTTP 400 Bad Request.
    """
    user_a = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_A).one()
    user_b = db_session.query(Usuario).filter(Usuario.email == EMAIL_USER_B).one()

    # Análisis A (del Usuario A)
    analisis_a = Analisis(usuario_id=user_a.id, imagen_url="http://cloudinary.com/analisis_a.jpg", estado="COMPLETED")
    db_session.add(analisis_a)
    db_session.flush()

    # Análisis B (del Usuario B)
    analisis_b = Analisis(usuario_id=user_b.id, imagen_url="http://cloudinary.com/analisis_b.jpg", estado="COMPLETED")
    db_session.add(analisis_b)
    db_session.flush()

    det_b = Deteccion(analisis_id=analisis_b.id, clase_id=seed_classes["Neutrófilo"], confianza=0.90, bbox=[10.0, 10.0, 50.0, 50.0])
    db_session.add(det_b)
    db_session.commit()

    # El Usuario A envía feedback a su análisis A, pero referencia una detección del análisis B
    payload = {
        "feedbacks": [
            {
                "deteccion_id": str(det_b.id), # Pertenece a análisis B, no A
                "tipoCorreccion": "CAMBIO_CLASE",
                "claseCorregida": "Linfocito"
            }
        ]
    }
    url = f"/analysis/{analisis_a.id}/feedback"
    response = client.post(url, json=payload, headers=auth_headers_user_a)
    
    assert response.status_code == 400
    assert "no pertenece" in response.json()["detail"].lower()
