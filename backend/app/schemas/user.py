"""
user.py
-------
Schemas Pydantic v2 para validación de requests y serialización de responses
relacionados con usuarios y autenticación.

Schemas definidos:
  - UserCreate    : Datos para registrar un usuario (POST /auth/register)
  - LoginRequest  : Credenciales para autenticar (POST /auth/login)
  - UserResponse  : Datos del usuario para respuestas (sin contraseña)
  - TokenResponse : Respuesta del endpoint de login con el JWT
"""

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Constantes de validación
# ---------------------------------------------------------------------------

# Regex para validar la complejidad del password:
# - Al menos 8 caracteres (controlado por Field min_length)
# - Al menos una letra [a-zA-Z]
# - Al menos un dígito [0-9]
_PASSWORD_HAS_LETTER = re.compile(r"[a-zA-Z]")
_PASSWORD_HAS_DIGIT = re.compile(r"[0-9]")


# ---------------------------------------------------------------------------
# Schema de creación de usuario (Request)
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """
    Schema para el body del endpoint POST /auth/register.
    
    Aplica validaciones estrictas de seguridad en el password:
      - Mínimo 8 caracteres
      - Al menos una letra
      - Al menos un número
    
    Pydantic v2 valida el formato del email automáticamente con EmailStr.
    """

    email: EmailStr = Field(
        ...,
        description="Dirección de correo electrónico del usuario. Debe ser única.",
        examples=["bioquimico@hospital.com"],
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description=(
            "Contraseña del usuario. "
            "Requisitos: mínimo 8 caracteres, al menos una letra y un número."
        ),
        examples=["Segura123"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        """
        Valida que el password contenga al menos una letra y un dígito.
        
        Se ejecuta DESPUÉS de la validación de min_length/max_length de Field.
        
        Raises:
            ValueError: Si el password no cumple los requisitos de complejidad.
        """
        if not _PASSWORD_HAS_LETTER.search(value):
            raise ValueError("La contraseña debe contener al menos una letra.")
        if not _PASSWORD_HAS_DIGIT.search(value):
            raise ValueError("La contraseña debe contener al menos un número.")
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "bioquimico@hospital.com",
                "password": "Segura123",
            }
        }
    }


# ---------------------------------------------------------------------------
# Schema de login (Request)
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """
    Schema para el body del endpoint POST /auth/login.
    
    Validación mínima: solo verifica que los campos estén presentes
    (la verificación de credenciales se hace contra la BD).
    """

    email: EmailStr = Field(
        ...,
        description="Email registrado del usuario.",
        examples=["bioquimico@hospital.com"],
    )

    password: str = Field(
        ...,
        min_length=1,
        description="Contraseña del usuario.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "bioquimico@hospital.com",
                "password": "Segura123",
            }
        }
    }


# ---------------------------------------------------------------------------
# Schema de respuesta de usuario (Response) — SIN contraseña
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """
    Schema para la respuesta de los endpoints que retornan datos de usuario.
    
    IMPORTANTE: Este schema NUNCA incluye el campo `password` para garantizar
    que las contraseñas (ni en texto plano ni hasheadas) viajen en las respuestas.
    """

    id: uuid.UUID = Field(description="Identificador único del usuario (UUID v4).")
    email: str = Field(description="Dirección de correo electrónico del usuario.")
    fechaCreacion: datetime = Field(description="Fecha de creación de la cuenta.")

    model_config = {
        # `from_attributes=True` permite crear el schema desde objetos ORM de SQLAlchemy
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "bioquimico@hospital.com",
                "fechaCreacion": "2024-01-15T10:30:00Z",
            }
        },
    }


# ---------------------------------------------------------------------------
# Schema de respuesta de token JWT (Response)
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """
    Schema para la respuesta del endpoint POST /auth/login.
    
    Sigue el estándar OAuth2 Bearer Token para compatibilidad con
    clientes que implementen el estándar.
    """

    access_token: str = Field(
        description="JWT de acceso. Incluirlo en el header: Authorization: Bearer <token>"
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo de token. Siempre 'bearer' según el estándar OAuth2.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    }
