from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_admin

from app.models.admin import AdminCreate, AdminPublic
from app.services import admin as admin_service

router = APIRouter(prefix="/internal/admin", tags=["Internal Admin"])


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
