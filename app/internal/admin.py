from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.database.database import get_session
from app.core.security import (
    authenticate_admin,
    create_access_token,
    get_password_hash,
)
from app.core.dependencies import get_current_admin
from app.core.config import get_settings, Settings

from app.models.admin import Admin, AdminCreate, AdminPublic
from app.models.token import Token

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

    Parameters:
        form_data (OAuth2PasswordRequestForm): OAuth2 form data containing `username` and `password`.

    Returns:
        Token: Token object with `access_token` set to the issued JWT and `token_type` set to `"bearer"`.

    Raises:
        HTTPException: Raised with status 401 and detail "Incorrect admin username or password" when authentication fails.
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
    Create a new admin account and persist it to the database.

    Parameters:
        admin_in (AdminCreate): Input data for the new admin (including plaintext password).

    Returns:
        Admin: The created admin record with hashed password and populated persistence fields.

    Raises:
        HTTPException: Raised with status 400 if the username or email already exists.
    """
    hashed_pwd = get_password_hash(admin_in.password)

    db_admin = Admin.model_validate(admin_in, update={"hashed_password": hashed_pwd})

    session.add(db_admin)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")
    session.refresh(db_admin)
    return db_admin
