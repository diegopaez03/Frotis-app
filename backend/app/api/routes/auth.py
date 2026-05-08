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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import DbSession
from app.models.usuario import Usuario
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

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
    
    Flujo:
      1. Verificar que el email no esté en uso (409 si existe)
      2. Hashear la contraseña con bcrypt
      3. Persistir el usuario en la BD
      4. Retornar los datos del usuario (sin contraseña)
    
    Args:
        user_data: Datos del usuario validados por Pydantic (email + password).
        db: Sesión de BD inyectada por FastAPI.
    
    Returns:
        UserResponse con id, email y fecha de creación.
    
    Raises:
        HTTPException 409: Si el email ya está registrado.
    """
    # Paso 1: Verificar unicidad del email
    existing_user = db.query(Usuario).filter(
        Usuario.email == user_data.email
    ).first()
    
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El email '{user_data.email}' ya está registrado.",
        )
    
    # Paso 2: Hashear la contraseña (NUNCA almacenar en texto plano)
    hashed_pwd = hash_password(user_data.password)
    
    # Paso 3: Crear y persistir el usuario
    new_user = Usuario(
        email=user_data.email,
        password=hashed_pwd,  # Almacenamos el hash, nunca el texto plano
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)  # Recargar para obtener valores generados por la BD (id, fechas)
    
    # Paso 4: Retornar datos sin contraseña (UserResponse excluye el campo password)
    return UserResponse.model_validate(new_user)


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
    
    Seguridad:
      - El mensaje de error es GENÉRICO tanto para email inexistente como
        para password incorrecto. Esto previene ataques de enumeración
        que permitirían descubrir qué emails están registrados.
      - La verificación de password usa comparación en tiempo constante
        (proporcionada por passlib) para prevenir timing attacks.
    
    Args:
        credentials: Email y password del usuario.
        db: Sesión de BD inyectada por FastAPI.
    
    Returns:
        TokenResponse con el JWT y el tipo de token ("bearer").
    
    Raises:
        HTTPException 401: Si las credenciales son inválidas (mensaje genérico).
    """
    # Mensaje genérico para no filtrar información sobre usuarios existentes
    _invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Buscar el usuario por email
    user = db.query(Usuario).filter(
        Usuario.email == credentials.email
    ).first()
    
    # Si el usuario no existe, retornar el mismo error que para password incorrecto
    # (evitar enumeración de usuarios)
    if user is None:
        raise _invalid_credentials_exception
    
    # Verificar que el usuario esté activo
    if user.fechaBaja is not None:
        raise _invalid_credentials_exception
    
    # Verificar la contraseña usando comparación segura (tiempo constante)
    if not verify_password(credentials.password, user.password):
        raise _invalid_credentials_exception
    
    # Crear el JWT con el email como subject (claim 'sub')
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


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
    
    La autenticación es manejada completamente por la dependencia
    `get_current_user`, que valida el JWT y carga el usuario desde la BD.
    Si el token es inválido o expirado, la dependencia lanza un 401
    antes de que este handler sea ejecutado.
    
    Args:
        current_user: Usuario ORM inyectado por la dependencia get_current_user.
    
    Returns:
        UserResponse con los datos del usuario (sin contraseña).
    """
    # La dependencia ya validó el token y cargó el usuario.
    # Solo necesitamos convertirlo al schema de respuesta (que excluye password).
    return UserResponse.model_validate(current_user)
