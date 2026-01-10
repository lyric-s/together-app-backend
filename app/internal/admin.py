from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.database.database import get_session
from app.core.security import (
    authenticate_admin,
    create_access_token,
)
from app.core.dependencies import get_current_admin
from app.core.config import get_settings, Settings

from app.models.admin import AdminCreate, AdminPublic
from app.models.token import Token
from app.services import admin as admin_service

router = APIRouter(
    prefix="/internal/admin", tags=["Internal Admin"], include_in_schema=False
)


# TODO Add rate limit on login to prevent bruteforce
@router.post("/login", response_model=Token)
def login_admin(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Authenticate an admin user and issue a JWT bearer access token.

    Authenticates administrator credentials and issues an access token with admin privileges.
    The token includes a "mode": "admin" claim for authorization purposes.

    ### OAuth2 Password Flow (Admin):
    - Accepts `username` and `password` via form data
    - Validates credentials against admin accounts
    - Returns access token with admin mode claim
    - No refresh token issued (admin sessions use access token only)

    Args:
        `form_data`: OAuth2 form data containing `username` and `password`.
        `session`: Database session (automatically injected).
        `settings`: Application settings (automatically injected).

    Returns:
        `Token`: Token object with `access_token` set to the issued JWT and `token_type` set to "bearer".

    Raises:
        `401 Unauthorized`: When authentication fails with detail "Incorrect admin username or password".
    """
    admin = authenticate_admin(session, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": admin.username, "mode": "admin"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/", response_model=AdminPublic, dependencies=[Depends(get_current_admin)])
def create_new_admin(
    *,
    session: Session = Depends(get_session),
    admin_in: AdminCreate,
):
    """
    Create a new admin account.

    Creates a new administrator account with the provided credentials. This endpoint
    requires admin authentication and can only be accessed by existing administrators.

    ### Authorization Required:
    - **Admin authentication**: Requires valid admin access token
    - **Admin mode**: Token must include "mode": "admin" claim

    ### Security:
    - Password is provided in plaintext and will be hashed before storage
    - Username and email must be unique
    - Created admin has full administrative privileges

    Args:
        `session`: Database session (automatically injected).
        `admin_in`: Data for the new admin including username, email, and plaintext password.

    Returns:
        `AdminPublic`: The created admin record with sensitive fields (password hash) removed.

    Raises:
        `401 Unauthorized`: If no valid admin authentication token is provided.
        `400 Bad Request`: If the username or email already exists.
    """
    return admin_service.create_admin(session, admin_in)
