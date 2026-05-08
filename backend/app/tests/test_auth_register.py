"""
test_auth_register.py
---------------------
Tests TDD para el endpoint POST /auth/register.

Casos cubiertos:
  1. Registro exitoso → 201 con datos del usuario (sin password)
  2. Email duplicado → 409 Conflict
  3. Password débil (menos de 8 caracteres) → 422 Unprocessable Entity
  4. Password sin número → 422 Unprocessable Entity
  5. Password sin letra → 422 Unprocessable Entity
  6. Email con formato inválido → 422 Unprocessable Entity
  7. El campo password nunca aparece en la respuesta
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Constantes para los tests (evitar "magic strings")
# ---------------------------------------------------------------------------

REGISTER_URL = "/auth/register"

VALID_EMAIL = "bioquimico@hospital.com"
VALID_PASSWORD = "Segura123"


# ---------------------------------------------------------------------------
# Caso 1: Registro exitoso
# ---------------------------------------------------------------------------

def test_register_success(client: TestClient) -> None:
    """
    DADO un email único y password válido,
    CUANDO se hace POST /auth/register,
    ENTONCES se retorna HTTP 201 con los datos del usuario.
    """
    payload = {"email": VALID_EMAIL, "password": VALID_PASSWORD}
    
    response = client.post(REGISTER_URL, json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    # Debe retornar el email y un id
    assert data["email"] == VALID_EMAIL
    assert "id" in data
    assert "fechaCreacion" in data


# ---------------------------------------------------------------------------
# Caso 2: La contraseña NUNCA debe aparecer en la respuesta
# ---------------------------------------------------------------------------

def test_password_not_in_response(client: TestClient) -> None:
    """
    DADO un registro exitoso,
    CUANDO se revisa la respuesta,
    ENTONCES el campo `password` (en texto plano o hasheado) NO debe estar presente.
    """
    payload = {"email": "otro@hospital.com", "password": VALID_PASSWORD}
    
    response = client.post(REGISTER_URL, json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    # Verificar que ninguna variante del campo password esté en la respuesta
    assert "password" not in data
    assert "hashed_password" not in data
    assert "contraseña" not in data


# ---------------------------------------------------------------------------
# Caso 3: Email duplicado
# ---------------------------------------------------------------------------

def test_register_duplicate_email(client: TestClient) -> None:
    """
    DADO un usuario ya registrado con un email,
    CUANDO se intenta registrar otro usuario con el mismo email,
    ENTONCES se retorna HTTP 409 Conflict.
    """
    payload = {"email": VALID_EMAIL, "password": VALID_PASSWORD}
    
    # Primer registro (debe exitoso)
    first_response = client.post(REGISTER_URL, json=payload)
    assert first_response.status_code == 201
    
    # Segundo registro con el mismo email (debe fallar)
    second_response = client.post(REGISTER_URL, json=payload)
    
    assert second_response.status_code == 409
    assert "email" in second_response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Caso 4: Password demasiado corto (< 8 caracteres)
# ---------------------------------------------------------------------------

def test_register_password_too_short(client: TestClient) -> None:
    """
    DADO un password con menos de 8 caracteres,
    CUANDO se hace POST /auth/register,
    ENTONCES se retorna HTTP 422 Unprocessable Entity.
    """
    payload = {"email": VALID_EMAIL, "password": "Abc1"}
    
    response = client.post(REGISTER_URL, json=payload)
    
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Caso 5: Password sin número
# ---------------------------------------------------------------------------

def test_register_password_no_number(client: TestClient) -> None:
    """
    DADO un password que no contiene ningún dígito,
    CUANDO se hace POST /auth/register,
    ENTONCES se retorna HTTP 422 Unprocessable Entity.
    """
    payload = {"email": VALID_EMAIL, "password": "SoloLetras"}
    
    response = client.post(REGISTER_URL, json=payload)
    
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Caso 6: Password sin letra
# ---------------------------------------------------------------------------

def test_register_password_no_letter(client: TestClient) -> None:
    """
    DADO un password que no contiene ninguna letra,
    CUANDO se hace POST /auth/register,
    ENTONCES se retorna HTTP 422 Unprocessable Entity.
    """
    payload = {"email": VALID_EMAIL, "password": "12345678"}
    
    response = client.post(REGISTER_URL, json=payload)
    
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Caso 7: Email con formato inválido
# ---------------------------------------------------------------------------

def test_register_invalid_email_format(client: TestClient) -> None:
    """
    DADO un email con formato inválido (sin @, sin dominio, etc.),
    CUANDO se hace POST /auth/register,
    ENTONCES se retorna HTTP 422 Unprocessable Entity (validación Pydantic).
    """
    payload = {"email": "esto-no-es-un-email", "password": VALID_PASSWORD}
    
    response = client.post(REGISTER_URL, json=payload)
    
    assert response.status_code == 422
