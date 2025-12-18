from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database.database import get_session
from app.core.security import (
    authenticate_admin,
    create_access_token,
    # We do NOT import create_refresh_token here, ensuring safety
    get_password_hash,
)
from app.core.dependencies import get_current_admin
from app.core.config import get_settings, Settings

from app.models.admin import Admin, AdminCreate, AdminPublic
from app.models.token import Token

router = APIRouter(
    prefix="/internal/admin", tags=["Internal Admin"], include_in_schema=False
)


@router.post("/login", response_model=Token)
def login_admin(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    # 1. Authenticate
    admin = authenticate_admin(session, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
            # We KEEP this header because we are following the standard now
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Create Access Token (No Refresh Token generated)
    access_token = create_access_token(
        data={"sub": admin.username, "mode": "admin"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # 3. Return Standard Response
    # We explicitly say "bearer".
    # We omit refresh_token, which is allowed because we made it Optional in step 1.
    return Token(access_token=access_token, token_type="bearer")


# --- 2. CREATE NEW ADMIN (Unchanged) ---
@router.post("/", response_model=AdminPublic, dependencies=[Depends(get_current_admin)])
def create_new_admin(
    *,
    session: Session = Depends(get_session),
    admin_in: AdminCreate,
):
    # Uniqueness Checks
    if session.exec(select(Admin).where(Admin.username == admin_in.username)).first():
        raise HTTPException(status_code=400, detail="Username taken")
    if session.exec(select(Admin).where(Admin.email == admin_in.email)).first():
        raise HTTPException(status_code=400, detail="Email taken")

    hashed_pwd = get_password_hash(admin_in.password)

    db_admin = Admin.model_validate(admin_in, update={"hashed_password": hashed_pwd})

    session.add(db_admin)
    session.commit()
    session.refresh(db_admin)
    return db_admin
