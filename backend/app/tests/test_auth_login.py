"""
test_auth_login.py
------------------
Tests TDD para los endpoints POST /auth/login y GET /users/me.

Casos cubiertos:
  1. Login exitoso → 200 con access_token JWT
  2. Login con password incorrecto → 401 Unauthorized
  3. Login con email inexistente → 401 Unauthorized (sin filtrar si el email existe)
  4. /users/me con token válido → 200 con datos del usuario (sin password)
  5. /users/me sin token → 401 Unauthorized
  6. /users/me con token inválido/malformado → 401 Unauthorized
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Constantes para los tests
# ---------------------------------------------------------------------------

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
ME_URL = "/users/me"

VALID_EMAIL = "doctor@lab.com"
VALID_PASSWORD = "Clinica456"


# ---------------------------------------------------------------------------
# Fixture auxiliar: usuario ya registrado (reutilizable en múltiples tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def registered_user(client: TestClient) -> dict:
    """Registra un usuario de prueba y retorna sus datos."""
    payload = {"email": VALID_EMAIL, "password": VALID_PASSWORD}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201, f"Fallo en registro: {response.json()}"
    return {"email": VALID_EMAIL, "password": VALID_PASSWORD}


# ---------------------------------------------------------------------------
# Caso 1: Login exitoso
# ---------------------------------------------------------------------------

def test_login_success(client: TestClient, registered_user: dict) -> None:
    """
    DADO un usuario registrado con credenciales válidas,
    CUANDO se hace POST /auth/login,
    ENTONCES se retorna HTTP 200 con access_token y token_type.
    """
    response = client.post(LOGIN_URL, json=registered_user)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar estructura del token
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


# ---------------------------------------------------------------------------
# Caso 2: Login con password incorrecto
# ---------------------------------------------------------------------------

def test_login_wrong_password(client: TestClient, registered_user: dict) -> None:
    """
    DADO un usuario registrado,
    CUANDO se hace POST /auth/login con password incorrecto,
    ENTONCES se retorna HTTP 401 Unauthorized.
    
    El mensaje de error NO debe especificar si el email o la password es
    lo que falló (para no facilitar ataques de enumeración de usuarios).
    """
    payload = {"email": VALID_EMAIL, "password": "WrongPass999"}
    
    response = client.post(LOGIN_URL, json=payload)
    
    assert response.status_code == 401
    # El mensaje genérico protege contra enumeración de usuarios
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Caso 3: Login con email inexistente
# ---------------------------------------------------------------------------

def test_login_nonexistent_user(client: TestClient) -> None:
    """
    DADO un email que no existe en la BD,
    CUANDO se hace POST /auth/login,
    ENTONCES se retorna HTTP 401 (mismo error que password incorrecto,
    para no filtrar información sobre usuarios existentes).
    """
    payload = {"email": "noexiste@hospital.com", "password": VALID_PASSWORD}
    
    response = client.post(LOGIN_URL, json=payload)
    
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Caso 4: Acceso a /users/me con token válido
# ---------------------------------------------------------------------------

def test_users_me_authenticated(client: TestClient, registered_user: dict) -> None:
    """
    DADO un usuario autenticado con un JWT válido,
    CUANDO se hace GET /users/me con el token en el header,
    ENTONCES se retorna HTTP 200 con los datos del usuario (sin password).
    """
    # Primero hacer login para obtener el token
    login_response = client.post(LOGIN_URL, json=registered_user)
    assert login_response.status_code == 200
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(ME_URL, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar datos del usuario
    assert data["email"] == VALID_EMAIL
    assert "id" in data
    
    # El password NO debe estar en la respuesta
    assert "password" not in data
    assert "hashed_password" not in data


# ---------------------------------------------------------------------------
# Caso 5: /users/me sin token
# ---------------------------------------------------------------------------

def test_users_me_no_token(client: TestClient) -> None:
    """
    DADO una request sin Authorization header,
    CUANDO se hace GET /users/me,
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    response = client.get(ME_URL)
    
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Caso 6: /users/me con token inválido
# ---------------------------------------------------------------------------

def test_users_me_invalid_token(client: TestClient) -> None:
    """
    DADO un token JWT malformado o con firma inválida,
    CUANDO se hace GET /users/me,
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    headers = {"Authorization": "Bearer token.invalido.firmafalsificada"}
    
    response = client.get(ME_URL, headers=headers)
    
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Caso 7: /users/me con token expirado (simulado con subject inválido)
# ---------------------------------------------------------------------------

def test_users_me_token_without_subject(client: TestClient) -> None:
    """
    DADO un token que no tiene el claim 'sub' (email del usuario),
    CUANDO se hace GET /users/me,
    ENTONCES se retorna HTTP 401 Unauthorized.
    """
    from app.core.security import create_access_token
    from datetime import timedelta
    
    # Token sin 'sub' en el payload
    bad_token = create_access_token(data={"role": "admin"})
    headers = {"Authorization": f"Bearer {bad_token}"}
    
    response = client.get(ME_URL, headers=headers)
    
    assert response.status_code == 401
