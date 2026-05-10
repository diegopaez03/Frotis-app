from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.usuario import Usuario
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)

def register_user(
    user_data: UserCreate,
    db: Session,
) -> UserResponse:
    """
    Registra un nuevo usuario en el sistema.
    
    Flujo:
      1. Verificar que el email no esté en uso (409 si existe)
      2. Hashear la contraseña con bcrypt
      3. Persistir el usuario en la BD
      4. Retornar los datos del usuario (sin contraseña)
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


def login_user(
    credentials: LoginRequest,
    db: Session,
) -> TokenResponse:
    """
    Autentica un usuario y retorna un JWT de acceso.
    
    Seguridad:
      - El mensaje de error es GENÉRICO tanto para email inexistente como
        para password incorrecto. Esto previene ataques de enumeración
        que permitirían descubrir qué emails están registrados.
      - La verificación de password usa comparación en tiempo constante
        (proporcionada por passlib) para prevenir timing attacks.
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


def get_me(
    current_user: Usuario,
) -> UserResponse:
    """
    Retorna los datos del usuario actualmente autenticado.
    """
    # La dependencia ya validó el token y cargó el usuario.
    # Solo necesitamos convertirlo al schema de respuesta (que excluye password).
    return UserResponse.model_validate(current_user)
