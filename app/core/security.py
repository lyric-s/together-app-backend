from jwt.exceptions import PyJWTError
from fastapi.exceptions import HTTPException
from fastapi import status
from typing import Literal
from datetime import datetime, timedelta, timezone

import jwt
import re
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.password import verify_password
from app.models.user import User
from app.models.admin import Admin
from app.services import user as user_service
from app.services import admin as admin_service


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    """
    Authenticate a user by username or RNA code and password.

    Supports both username and RNA code login for associations.
    If the input looks like an RNA code (W + 9 digits), it will also check
    associations by RNA code.

    Args:
        session: Database session
        username: Username or RNA code
        password: User password

    Returns:
        User if authentication succeeds, None otherwise.
    """
    # Try username first
    user = user_service.get_user_by_username(session, username)

    # If not found and looks like RNA code (W + 9 digits), try RNA lookup
    if not user and re.fullmatch(r"W\d{9}", username):
        from app.models.association import Association

        statement = select(Association).where(Association.rna_code == username)
        association = session.exec(statement).first()
        if association:
            user = user_service.get_user(session, association.id_user)

    # Timing-safe password verification (always verify to reduce timing attacks)
    hash_to_verify = (
        user.hashed_password if user else "$argon2id$v=19$m=65536,t=3,p=4$dummy"
    )
    password_ok = verify_password(password, hash_to_verify)
    if user and password_ok:
        return user
    return None


def authenticate_admin(session: Session, username: str, password: str) -> Admin | None:
    """
    Authenticate an admin account using a username and password.

    Returns:
        `Admin` if credentials are valid, `None` otherwise.
    """
    # Get admin from service layer
    admin = admin_service.get_admin_by_username(session, username)
    hash_to_verify = (
        admin.hashed_password if admin else "$argon2id$v=19$m=65536,t=3,p=4$dummy"
    )
    password_ok = verify_password(password, hash_to_verify)
    if admin and password_ok:
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
            to_encode,
            get_settings().SECRET_KEY.get_secret_value(),
            algorithm=get_settings().ALGORITHM,
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
