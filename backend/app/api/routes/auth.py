"""
auth.py
-------
Router de FastAPI para los endpoints de autenticación y perfil de usuario.

Endpoints:
  POST /auth/register → Registra un nuevo usuario
  POST /auth/login    → Autentica y retorna un JWT
  GET  /users/me      → Retorna datos del usuario autenticado (ruta protegida)

Seguridad aplicada:
  - Contraseñas hasheadas con bcrypt antes de persistir
  - Las respuestas NUNCA incluyen passwords (ni planos ni hasheados)
  - Los errores 401 son genéricos para evitar enumeración de usuarios
  - Validación de complejidad de password delegada a Pydantic schemas
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.security import get_current_user
from app.database import DbSession
from app.models.usuario import Usuario
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.service import auth as auth_service

# ---------------------------------------------------------------------------
# Router principal — los prefijos se definen al incluirlo en main.py
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Autenticación"])


# ---------------------------------------------------------------------------
# POST /auth/register — Registro de nuevo usuario
# ---------------------------------------------------------------------------

@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description=(
        "Crea una nueva cuenta de usuario. "
        "Valida que el email no esté registrado y que el password cumpla "
        "los requisitos mínimos de seguridad."
    ),
)
def register_user(
    user_data: UserCreate,
    db: DbSession,
) -> UserResponse:
    """
    Registra un nuevo usuario en el sistema.
    Delega la lógica de negocio al servicio de autenticación.
    """
    return auth_service.register_user(user_data=user_data, db=db)


# ---------------------------------------------------------------------------
# POST /auth/login — Inicio de sesión
# ---------------------------------------------------------------------------

@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión",
    description=(
        "Autentica al usuario con email y password. "
        "Si las credenciales son válidas, retorna un JWT Bearer Token."
    ),
)
def login_user(
    credentials: LoginRequest,
    db: DbSession,
) -> TokenResponse:
    """
    Autentica un usuario y retorna un JWT de acceso.
    Delega la lógica de negocio al servicio de autenticación.
    """
    return auth_service.login_user(credentials=credentials, db=db)


# ---------------------------------------------------------------------------
# GET /users/me — Ruta protegida: información del usuario actual
# ---------------------------------------------------------------------------

@router.get(
    "/users/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario autenticado",
    description=(
        "Retorna los datos del usuario cuyo JWT se envía en el header "
        "`Authorization: Bearer <token>`. "
        "Requiere autenticación válida."
    ),
)
def get_me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UserResponse:
    """
    Retorna los datos del usuario actualmente autenticado.
    Delega la lógica de negocio al servicio de autenticación.
    """
    return auth_service.get_me(current_user=current_user)
