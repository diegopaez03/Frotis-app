"""
security.py
-----------
Módulo de seguridad central: hashing de contraseñas y operaciones JWT.

Funciones expuestas:
  - hash_password(plain_password)      → str (hash bcrypt)
  - verify_password(plain, hashed)     → bool
  - create_access_token(data, expires) → str (JWT firmado)
  - decode_access_token(token)         → dict | None

Dependencias de FastAPI:
  - get_current_user(token, db)        → Usuario (para inyección con Depends)
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db

# ---------------------------------------------------------------------------
# Configuración del esquema de autenticación
# ---------------------------------------------------------------------------

# Esquema de autenticación Bearer para FastAPI (extrae el token del header)
_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Funciones de hashing de contraseñas
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """
    Genera un hash bcrypt de la contraseña en texto plano.
    
    Args:
        plain_password: La contraseña en texto plano del usuario.
    
    Returns:
        El hash bcrypt de la contraseña para almacenar en BD.
    """
    # bcrypt requiere bytes, codificamos el string a utf-8
    pwd_bytes = plain_password.encode('utf-8')
    # Generamos un salt y calculamos el hash
    salt = bcrypt.gensalt(rounds=12)
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    # Retornamos como string para almacenar en la BD
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que una contraseña en texto plano coincida con su hash bcrypt.
    
    Args:
        plain_password: La contraseña ingresada por el usuario.
        hashed_password: El hash almacenado en la base de datos.
    
    Returns:
        True si la contraseña es correcta, False en caso contrario.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_password_bytes = hashed_password.encode('utf-8')
    
    try:
        return bcrypt.checkpw(password=password_bytes, hashed_password=hashed_password_bytes)
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Funciones JWT
# ---------------------------------------------------------------------------

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Crea y firma un JWT de acceso con los datos proporcionados.
    
    El claim 'exp' se agrega automáticamente con el tiempo de expiración.
    Se recomienda incluir 'sub' (subject) con el identificador del usuario.
    
    Args:
        data: Payload del token. Debe incluir al menos {'sub': email}.
        expires_delta: Tiempo de vida personalizado. Si es None, usa
                       ACCESS_TOKEN_EXPIRE_MINUTES de la configuración.
    
    Returns:
        El JWT firmado como string (formato: header.payload.signature).
    
    Example:
        token = create_access_token({"sub": "usuario@email.com"})
    """
    to_encode = data.copy()
    
    # Calcular la fecha de expiración
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    # Firmar el token con la clave secreta
    encoded_jwt: str = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodifica y valida un JWT. Retorna el payload si es válido, None si no.
    
    Valida automáticamente:
      - La firma del token (SECRET_KEY)
      - La fecha de expiración (claim 'exp')
      - El algoritmo usado
    
    Args:
        token: El JWT a decodificar.
    
    Returns:
        El payload decodificado como dict, o None si el token es inválido.
    """
    try:
        payload: dict = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        # Token inválido, expirado o con firma incorrecta
        return None


# ---------------------------------------------------------------------------
# Dependencia de FastAPI: obtener el usuario actual desde el JWT
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Dependencia de FastAPI que extrae y valida el JWT del header Authorization.
    
    Flujo:
      1. HTTPBearer extrae el token del header `Authorization: Bearer <token>`
      2. Se decodifica y valida el JWT
      3. Se extrae el email del claim 'sub'
      4. Se busca el usuario en la BD
      5. Se verifica que el usuario esté activo (fechaBaja es None)
    
    Raises:
        HTTPException 401: Si el token es inválido, expirado, o el usuario
                          no existe / fue dado de baja.
    
    Returns:
        El objeto Usuario ORM del usuario autenticado.
    """
    # Importación local para evitar importación circular con models
    from app.models.usuario import Usuario

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decodificar el token
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    # Extraer el subject (email del usuario)
    email: Optional[str] = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Buscar el usuario en la BD
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise credentials_exception

    # Verificar que el usuario esté activo (baja lógica)
    if user.fechaBaja is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario dado de baja",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
