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
    Verifies a plain password against the hashed version.
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a password using the recommended algorithm (Argon2).
    """
    return password_hash.hash(password)


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    """
    Checks if user exists in DB and if password matches.
    Returns the User object if successful, None otherwise.
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
    Specific authentication for the Admin table.
    """
    statement = select(Admin).where(Admin.username == username)
    admin = session.exec(statement).first()
    hash_to_verify = (
        admin.hashed_password if admin else "$argon2id$v=19$m=65536,t=3,p=4$dummy"
    )
    if admin and verify_password(password, hash_to_verify):
        return admin
    return None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode, get_settings().SECRET_KEY, algorithm=get_settings().ALGORITHM
    )


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode, get_settings().SECRET_KEY, algorithm=get_settings().ALGORITHM
    )
