"""Tests for FastAPI dependencies."""

import pytest
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.dependencies import get_current_user, get_current_admin
from app.core.security import create_access_token
from app.models.user import UserCreate
from app.models.enums import UserType
from app.models.admin import AdminCreate
from app.services import user as user_service
from app.services import admin as admin_service


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    def test_get_current_user_success(self, session: Session):
        """Returns user for valid access token."""
        user_in = UserCreate(
            username="depuser",
            email="dep@example.com",
            password="password",
            user_type=UserType.VOLUNTEER,
        )
        user = user_service.create_user(session, user_in)

        token = create_access_token(data={"sub": user.username})

        current_user = get_current_user(token=token, session=session)
        assert current_user.id_user == user.id_user
        assert current_user.username == user.username

    def test_get_current_user_invalid_token(self, session: Session):
        """Raises 401 for invalid token."""
        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token="invalid-token", session=session)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == "Could not validate credentials"

    def test_get_current_user_wrong_type(self, session: Session):
        """Raises 401 for non-access token."""
        from app.core.security import create_refresh_token

        token = create_refresh_token(data={"sub": "someuser"})

        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token=token, session=session)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_not_found(self, session: Session):
        """Raises 401 if user in token doesn't exist."""
        token = create_access_token(data={"sub": "ghost"})

        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token=token, session=session)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentAdmin:
    """Test get_current_admin dependency."""

    def test_get_current_admin_success(self, session: Session):
        """Returns admin for valid access token with admin mode."""
        admin_in = AdminCreate(
            username="depadmin",
            email="depadmin@example.com",
            password="password",
            first_name="Dep",
            last_name="Admin",
        )
        admin = admin_service.create_admin(session, admin_in)

        token = create_access_token(data={"sub": admin.username, "mode": "admin"})

        current_admin = get_current_admin(token=token, session=session)
        assert current_admin.id_admin == admin.id_admin
        assert current_admin.username == admin.username

    def test_get_current_admin_not_admin_mode(self, session: Session):
        """Raises 401 if mode is not admin."""
        token = create_access_token(data={"sub": "admin", "mode": "user"})

        with pytest.raises(HTTPException) as excinfo:
            get_current_admin(token=token, session=session)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_admin_wrong_type(self, session: Session):
        """Raises 401 for refresh token."""
        from app.core.security import create_refresh_token

        token = create_refresh_token(data={"sub": "admin", "mode": "admin"})

        with pytest.raises(HTTPException) as excinfo:
            get_current_admin(token=token, session=session)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
