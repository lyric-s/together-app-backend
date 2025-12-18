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
