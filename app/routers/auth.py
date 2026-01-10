from app.models.token import TokenRefreshRequest
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
import jwt
from jwt.exceptions import InvalidTokenError

from app.database.database import get_session
from app.core.config import get_settings, Settings
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
)
from app.models.token import Token
from app.models.user import User
from sqlmodel import select

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Authenticate user credentials and issue access and refresh tokens.

    Authenticates user credentials from the OAuth2 form and issues a new access token
    and refresh token for authorized API access.

    ### OAuth2 Password Flow:
    - Accepts `username` and `password` via form data
    - Returns both access and refresh tokens on successful authentication
    - Access token expires based on configured duration
    - Refresh token can be used to obtain new access tokens

    Args:
        `form_data`: OAuth2 form data containing `username` and `password`.
        `session`: Database session (automatically injected).
        `settings`: Application settings (automatically injected).

    Returns:
        `Token`: Token object containing `access_token`, `refresh_token`, and `token_type` set to "bearer".

    Raises:
        `401 Unauthorized`: If the provided username or password is incorrect.
    """
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_refresh_token(
        data={"sub": user.username}, expires_delta=refresh_token_expires
    )

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


# TODO rate limit on refresh token to prevent bruteforce
@router.post("/refresh", response_model=Token)
async def refresh_token(
    request_data: TokenRefreshRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Validate a refresh token and issue a new access token.

    Validates the provided refresh token, ensures it belongs to an existing user and is of
    type "refresh", then returns a Token containing a newly created access token and the
    original refresh token.

    ### Token Refresh Flow:
    - Validates the refresh token signature and expiration
    - Verifies the token type is "refresh"
    - Confirms the user still exists in the database
    - Issues a new access token with updated expiration

    Args:
        `request_data`: Request body containing the `refresh_token` string.
        `session`: Database session (automatically injected).
        `settings`: Application settings (automatically injected).

    Returns:
        `Token`: Object with `access_token` (newly issued), `refresh_token` (the incoming token),
            and `token_type` set to "bearer".

    Raises:
        `401 Unauthorized`: If the refresh token is invalid, expired, missing required claims,
            or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    incoming_refresh_token = request_data.refresh_token

    try:
        payload = jwt.decode(
            incoming_refresh_token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        username: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if username is None or token_type != "refresh":
            raise credentials_exception
        # TODO Optional: Check if user still exists / is active in DB (ex: banned -> disabled == true)
        # For now this isn't implemented in the DB, so it should be
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    return Token(
        access_token=new_access_token,
        # TODO Optional: Token rotation when possible
        # (current implementation is enough but could be improved when time don't lack)
        refresh_token=incoming_refresh_token,
        token_type="bearer",
    )
