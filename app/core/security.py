from jwt.exceptions import PyJWTError
from fastapi.exceptions import HTTPException
from fastapi import status
from typing import Literal
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.user import User
from app.models.admin import Admin


# pwdlib is the modern, recommended way (Argon2 by default)
password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plaintext password matches a stored hashed password.

    Returns:
        `true` if the plaintext password matches the hashed password, `false` otherwise.
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using the recommended hashing algorithm (Argon2).

    Parameters:
        password (str): Plaintext password to hash.

    Returns:
        str: Password hash suitable for secure storage.
    """
    return password_hash.hash(password)


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    """
    Authenticate a user by username and password.

    Returns:
        User if authentication succeeds, `None` otherwise.
    """
    # Query the database for the user
    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    hash_to_verify = (
        user.hashed_password if user else "$argon2id$v=19$m=65536,t=3,p=4$dummy"
    )
    if user and verify_password(password, hash_to_verify):
        return user
    return None


def authenticate_admin(session: Session, username: str, password: str) -> Admin | None:
    """
    Authenticate an admin by username and password.

    Returns:
        Admin: The matching Admin object if credentials are valid, `None` otherwise.
    """
    statement = select(Admin).where(Admin.username == username)
    admin = session.exec(statement).first()
    hash_to_verify = (
        admin.hashed_password if admin else "$argon2id$v=19$m=65536,t=3,p=4$dummy"
    )
    if admin and verify_password(password, hash_to_verify):
        return admin
    return None


def create_token(
    data: dict, expires_delta: timedelta, type: Literal["access", "refresh"]
) -> str:
    """
    Create a JSON Web Token with the given payload, expiration, and token type.

    Parameters:
        data (dict): Payload claims to include in the token.
        expires_delta (timedelta): Time span from now after which the token expires.
        type (Literal["access", "refresh"]): Token classification included in the token claims.

    Returns:
        token (str): Encoded JWT string.

    Raises:
        HTTPException: HTTP 500 error if the token cannot be generated.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": type})
    try:
        return jwt.encode(
            to_encode, get_settings().SECRET_KEY, algorithm=get_settings().ALGORITHM
        )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate authentication token.",
        )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token containing the provided payload.

    Parameters:
        data (dict): Claims to include in the token payload.
        expires_delta (timedelta | None): Optional time until expiration. If `None`, the expiration is set using ACCESS_TOKEN_EXPIRE_MINUTES from application settings.

    Returns:
        str: Encoded JWT access token string.
    """
    expires_delta = (
        expires_delta
        if expires_delta
        else timedelta(minutes=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return create_token(data, expires_delta=expires_delta, type="access")


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT refresh token containing the provided payload.

    Parameters:
        data (dict): Claims to include in the token payload.
        expires_delta (timedelta | None): Time until the token expires; if None, uses REFRESH_TOKEN_EXPIRE_DAYS from settings.

    Returns:
        str: Encoded JWT refresh token.
    """
    expires_delta = (
        expires_delta
        if expires_delta
        else timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return create_token(data, expires_delta=expires_delta, type="refresh")
