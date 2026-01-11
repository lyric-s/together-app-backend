from typing import Annotated
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import get_settings
from app.database.database import get_session
from app.models.user import User
from app.models.admin import Admin
from app.models.volunteer import Volunteer
from app.models.association import Association
from app.services import user as user_service
from app.services import admin as admin_service
from app.services import volunteer as volunteer_service
from app.services import association as association_service
from app.exceptions import NotFoundError
from app.utils.validation import ensure_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_session),
) -> User:
    """
    Resolve and return the authenticated User represented by an access JWT.

    Returns:
        User: The User corresponding to the token's subject.

    Raises:
        HTTPException: 401 Unauthorized if the token is invalid, missing the subject, not an access token, or if no matching user is found.
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
    except InvalidTokenError:
        raise credentials_exception

    # Get user from service layer
    # username is guaranteed to be str at this point due to validation above
    user = user_service.get_user_by_username(session, username)
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
    except InvalidTokenError:
        raise credentials_exception

    # Get admin from service layer
    # username is guaranteed to be str at this point due to validation above
    admin = admin_service.get_admin_by_username(session, username)

    if admin is None:
        raise credentials_exception

    return admin


def get_current_volunteer(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> Volunteer:
    """
    Resolve and return the Volunteer profile associated with the authenticated user.

    Returns:
        Volunteer: The profile linked to the current user.

    Raises:
        AuthenticationError: If the user ID is missing from the token.
        NotFoundError: If no volunteer profile exists for the user.
        AppException: If the volunteer ID is missing.
    """
    user_id = ensure_id(current_user.id_user, "User")

    volunteer = volunteer_service.get_volunteer_by_user_id(session, user_id)
    if not volunteer:
        raise NotFoundError("Volunteer profile", user_id)

    ensure_id(volunteer.id_volunteer, "Volunteer")

    return volunteer


def get_current_association(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Session = Depends(get_session),
) -> Association:
    """
    Resolve and return the Association profile associated with the authenticated user.

    Returns:
        Association: The profile linked to the current user.

    Raises:
        AuthenticationError: If the user ID is missing from the token.
        NotFoundError: If no association profile exists for the user.
        AppException: If the association ID is missing.
    """
    user_id = ensure_id(current_user.id_user, "User")

    association = association_service.get_association_by_user_id(session, user_id)
    if not association:
        raise NotFoundError("Association profile", user_id)

    ensure_id(association.id_asso, "Association")

    return association
