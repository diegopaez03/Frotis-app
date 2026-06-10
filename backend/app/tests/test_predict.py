"""
test_predict.py
---------------
Tests unitarios y de integración TDD para el endpoint de predicción `POST /predict`.
Utiliza mocks para llamadas HTTP externas y para la inferencia de YOLO,
haciendo que los tests sean 100% herméticos, rápidos y confiables.
"""

import uuid
import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.models.analisis import Analisis, Deteccion
from app.models.clases_celulas import ClaseCelula

# ---------------------------------------------------------------------------
# Constantes y URLs
# ---------------------------------------------------------------------------
PREDICT_URL = "/predict"
REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"

VALID_EMAIL = "doctor_predict@lab.com"
VALID_PASSWORD = "ClinicaPredict456"
CLOUDINARY_URL = "https://res.cloudinary.com/frotis/image/upload/v1/blood_smear.jpg"

# ---------------------------------------------------------------------------
# Auxiliares y Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_user(client: TestClient) -> dict:
    """Registra un usuario para pruebas de autenticación."""
    payload = {"email": VALID_EMAIL, "password": VALID_PASSWORD}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201
    return payload

@pytest.fixture
def auth_headers(client: TestClient, test_user: dict) -> dict:
    """Realiza el login y retorna las cabeceras de autorización JWT."""
    response = client.post(LOGIN_URL, json=test_user)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_valid_image_bytes():
    """Genera bytes de una imagen PNG válida usando PIL para simular descargas."""
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    return img_byte_arr.getvalue()

@pytest.fixture
def seed_classes(db_session: Session):
    """Inicializa las 10 clases celulares en la base de datos de pruebas SQLite."""
    standard_classes = [
        "Neutrófilo inmaduro", "Basófilo", "Blasto", "Eosinófilo",
        "Linfocito", "Monocito", "Neutrófilo", "Promielocito",
        "Mielocito", "Metamielocito"
    ]
    db_classes = []
    for name in standard_classes:
        c = ClaseCelula(nombre=name)
        db_session.add(c)
        db_classes.append(c)
    db_session.commit()
    return db_classes

# ---------------------------------------------------------------------------
# Mocks de Inferencia YOLO
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Casos de Test TDD
# ---------------------------------------------------------------------------

@patch("requests.get")
@patch("app.api.routes.predict.predict_leukocytes")
def test_predict_anonymous_success(
    mock_predict, mock_requests_get, client: TestClient, 
    mock_valid_image_bytes, seed_classes, db_session: Session
) -> None:
    """
    DADO un usuario anónimo (sin cabecera Authorization) y una URL de imagen válida,
    CUANDO se hace POST /predict con la URL de Cloudinary,
    ENTONCES se retorna HTTP 200 con las predicciones y distribución,
    PERO no se guarda ningún registro en las tablas `analisis` ni `detecciones`.
    """
    # Configurar mocks
    # Mock de descarga de imagen
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_valid_image_bytes
    mock_requests_get.return_value = mock_response
    
    # Mock de la inferencia
    import numpy as np
    mock_orig_img = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_predict.return_value = (mock_orig_img, [
        {"class_id": 6, "class_name": "Neutrófilo", "confidence": 0.94, "bbox": [10.5, 20.0, 110.5, 120.0]},
        {"class_id": 4, "class_name": "Linfocito", "confidence": 0.89, "bbox": [200.0, 150.5, 300.0, 250.5]}
    ])
    
    payload = {"image_url": CLOUDINARY_URL}
    
    response = client.post(PREDICT_URL, json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["analisis_id"] is None
    assert data["total_detecciones"] == 2
    
    # Verificar la distribución
    assert "Neutrófilo" in data["distribucion"]
    assert data["distribucion"]["Neutrófilo"]["cantidad"] == 1
    assert data["distribucion"]["Neutrófilo"]["porcentaje"] == 50.0
    
    assert "Linfocito" in data["distribucion"]
    assert data["distribucion"]["Linfocito"]["cantidad"] == 1
    assert data["distribucion"]["Linfocito"]["porcentaje"] == 50.0
    
    # Verificar detecciones
    assert len(data["detecciones"]) == 2
    assert data["detecciones"][0]["clase"] == "Neutrófilo"
    assert data["detecciones"][0]["confianza"] == 0.94
    assert data["detecciones"][0]["bbox"] == [10.5, 20.0, 110.5, 120.0]
    assert data["detecciones"][0]["id"] is None
    
    assert data["detecciones"][1]["clase"] == "Linfocito"
    assert data["detecciones"][1]["confianza"] == 0.89
    assert data["detecciones"][1]["bbox"] == [200.0, 150.5, 300.0, 250.5]
    assert data["detecciones"][1]["id"] is None
    
    # Verificar aislamiento de base de datos
    assert db_session.query(Analisis).count() == 0
    assert db_session.query(Deteccion).count() == 0
 
 
@patch("requests.get")
@patch("app.api.routes.predict.predict_leukocytes")
def test_predict_authenticated_success(
    mock_predict, mock_requests_get, client: TestClient, 
    auth_headers: dict, mock_valid_image_bytes, seed_classes, db_session: Session
) -> None:
    """
    DADO un usuario autenticado y una URL de imagen válida,
    CUANDO se hace POST /predict con la cabecera Authorization y URL de Cloudinary,
    ENTONCES se retorna HTTP 200 con predicciones completas,
    Y se persiste un registro `Analisis` y registros `Deteccion` en la base de datos,
    vinculados correctamente con IDs correspondientes.
    """
    # Configurar mocks
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_valid_image_bytes
    mock_requests_get.return_value = mock_response
    
    # Mock de la inferencia
    import numpy as np
    mock_orig_img = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_predict.return_value = (mock_orig_img, [
        {"class_id": 6, "class_name": "Neutrófilo", "confidence": 0.94, "bbox": [10.5, 20.0, 110.5, 120.0]},
        {"class_id": 4, "class_name": "Linfocito", "confidence": 0.89, "bbox": [200.0, 150.5, 300.0, 250.5]}
    ])
    
    payload = {"image_url": CLOUDINARY_URL}
    
    response = client.post(PREDICT_URL, json=payload, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    analisis_id_str = data["analisis_id"]
    assert analisis_id_str is not None
    analisis_uuid = uuid.UUID(analisis_id_str)
    
    assert data["total_detecciones"] == 2
    assert len(data["detecciones"]) == 2
    
    # Verificar persistencia en base de datos
    db_analisis = db_session.query(Analisis).filter(Analisis.id == analisis_uuid).first()
    assert db_analisis is not None
    assert db_analisis.imagen_url == CLOUDINARY_URL
    assert db_analisis.estado == "COMPLETED"
    
    # Verificar detecciones en la base de datos
    db_detecciones = db_session.query(Deteccion).filter(Deteccion.analisis_id == analisis_uuid).all()
    assert len(db_detecciones) == 2
    
    # Verificar que los IDs retornados en el JSON correspondan a los generados en la base de datos
    json_ids = {uuid.UUID(d["id"]) for d in data["detecciones"]}
    db_ids = {d.id for d in db_detecciones}
    assert json_ids == db_ids
 
 
def test_predict_invalid_token(client: TestClient) -> None:
    """
    DADO un token JWT inválido,
    CUANDO se hace POST /predict con dicho token,
    ENTONCES se retorna inmediatamente HTTP 401 Unauthorized.
    """
    payload = {"image_url": CLOUDINARY_URL}
    bad_headers = {"Authorization": "Bearer token.invalido.expirado"}
    
    response = client.post(PREDICT_URL, json=payload, headers=bad_headers)
    
    assert response.status_code == 401
    assert "detail" in response.json()
 
 
@patch("requests.get")
def test_predict_invalid_url_download_failure(
    mock_requests_get, client: TestClient
) -> None:
    """
    DADO una URL inválida o que falla al descargar (ej. HTTP 404),
    CUANDO se hace POST /predict,
    ENTONCES se retorna HTTP 400 Bad Request con un mensaje explícito.
    """
    # Simular error de descarga
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_requests_get.return_value = mock_response
    
    payload = {"image_url": "https://url-inexistente.com/no_existe.jpg"}
    
    response = client.post(PREDICT_URL, json=payload)
    
    assert response.status_code == 400
    assert "No se pudo descargar" in response.json()["detail"]
 
 
@patch("requests.get")
def test_predict_corrupt_image_format(
    mock_requests_get, client: TestClient
) -> None:
    """
    DADO una URL de un archivo que se descarga exitosamente pero no es una imagen válida,
    CUANDO se hace POST /predict,
    ENTONCES se retorna HTTP 400 Bad Request indicando que el archivo está corrupto o es inválido.
    """
    # Simular la descarga de un archivo de texto en lugar de una imagen
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"esto no es una imagen, es texto plano"
    mock_requests_get.return_value = mock_response
    
    payload = {"image_url": "https://example.com/not_an_image.txt"}
    
    response = client.post(PREDICT_URL, json=payload)
    
    assert response.status_code == 400
    assert "corrupto" in response.json()["detail"].lower()
 
 
@patch("requests.get")
@patch("app.api.routes.predict.predict_leukocytes")
def test_predict_yolo_internal_error(
    mock_predict, mock_requests_get, client: TestClient, 
    mock_valid_image_bytes, seed_classes
) -> None:
    """
    DADO un error interno inesperado en el modelo de inferencia YOLO,
    CUANDO se procesa la petición de predicción,
    ENTONCES se retorna de manera limpia HTTP 500 Internal Server Error.
    """
    # Descarga exitosa de la imagen
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = mock_valid_image_bytes
    mock_requests_get.return_value = mock_response
    
    # Simular una excepción en la ejecución del modelo YOLO
    mock_predict.side_effect = RuntimeError("ONNX Runtime internal error")
    
    payload = {"image_url": CLOUDINARY_URL}
    
    response = client.post(PREDICT_URL, json=payload)
    
    assert response.status_code == 500
    assert "error interno" in response.json()["detail"].lower()

