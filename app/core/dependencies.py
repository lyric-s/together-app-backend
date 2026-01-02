from typing import Annotated
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.config import get_settings
from app.database.database import get_session
from app.models.user import User
from app.models.token import TokenData  # Ensure this model exists (see below)
from app.models.admin import Admin


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_session),
) -> User:
    """
    Resolve the authenticated user from an access JWT.

    Returns:
        user (User): The User whose username matches the token's subject.

    Raises:
        HTTPException: 401 Unauthorized if the token is invalid, not an access token, missing the subject, or if no matching user is found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None or payload.get("type") != "access":
            raise credentials_exception

        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    statement = select(User).where(User.username == token_data.username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_session),
) -> Admin:
    """
    Validate an access JWT for an administrator and return the corresponding Admin.

    Validates that the token payload contains a username (`sub`), that `mode` equals "admin", and that `type` equals "access". On success, retrieves and returns the Admin record matching the token's username.

    Returns:
        Admin: The Admin model instance matching the token's `sub` claim.

    Raises:
        HTTPException: 401 Unauthorized if the token is invalid, missing required claims, or no matching admin is found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        username: str | None = payload.get("sub")
        mode: str | None = payload.get("mode")
        token_type: str | None = payload.get("type")  # <--- 1. Extract type

        # SECURITY:
        # 1. Username must exist
        # 2. Mode must be 'admin'
        # 3. Type must be 'access' (Prevents Refresh tokens from being used here)
        if (
            username is None or mode != "admin" or token_type != "access"
        ):  # <--- 2. Add Check
            raise credentials_exception

        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception

    statement = select(Admin).where(Admin.username == token_data.username)
    admin = session.exec(statement).first()

    if admin is None:
        raise credentials_exception

    return admin
