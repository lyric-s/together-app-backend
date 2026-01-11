"""Tests for authentication and token utilities."""

from sqlmodel import Session
import jwt

from app.core.security import (
    authenticate_user,
    authenticate_admin,
    create_access_token,
    create_refresh_token,
)
from app.core.config import get_settings
from app.models.user import UserCreate
from app.models.enums import UserType
from app.models.admin import AdminCreate
from app.services import user as user_service
from app.services import admin as admin_service
from app.models.association import Association


class TestAuthenticateUser:
    """Test user authentication logic."""

    def test_authenticate_user_username_success(self, session: Session):
        """Authentication succeeds with correct username and password."""
        password = "secret_password"
        user_in = UserCreate(
            username="testuser",
            email="test@example.com",
            password=password,
            user_type=UserType.VOLUNTEER,
        )
        user = user_service.create_user(session, user_in)

        authenticated_user = authenticate_user(session, "testuser", password)
        assert authenticated_user is not None
        assert authenticated_user.id_user == user.id_user

    def test_authenticate_user_rna_success(self, session: Session):
        """Authentication succeeds with correct RNA code for associations."""
        password = "asso_password"
        rna_code = "W123456789"
        user_in = UserCreate(
            username="assouser",
            email="asso@example.com",
            password=password,
            user_type=UserType.ASSOCIATION,
        )
        user = user_service.create_user(session, user_in)

        association = Association(
            id_user=user.id_user,
            name="Test Association",
            rna_code=rna_code,
            company_name="Test Corp",
            phone_number="0123456789",
            address="Test Address",
            zip_code="75000",
            country="France",
        )
        session.add(association)
        session.commit()

        authenticated_user = authenticate_user(session, rna_code, password)
        assert authenticated_user is not None
        assert authenticated_user.id_user == user.id_user

    def test_authenticate_user_wrong_password(self, session: Session):
        """Authentication fails with incorrect password."""
        password = "secret_password"
        user_in = UserCreate(
            username="testuser2",
            email="test2@example.com",
            password=password,
            user_type=UserType.VOLUNTEER,
        )
        user_service.create_user(session, user_in)

        authenticated_user = authenticate_user(session, "testuser2", "wrong_password")
        assert authenticated_user is None

    def test_authenticate_user_not_found(self, session: Session):
        """Authentication fails for non-existent user."""
        authenticated_user = authenticate_user(session, "nonexistent", "any_password")
        assert authenticated_user is None


class TestAuthenticateAdmin:
    """Test admin authentication logic."""

    def test_authenticate_admin_success(self, session: Session):
        """Admin authentication succeeds with correct credentials."""
        password = "admin_password"
        admin_in = AdminCreate(
            username="adminuser",
            email="admin@example.com",
            password=password,
            first_name="Admin",
            last_name="User",
        )
        admin = admin_service.create_admin(session, admin_in)

        authenticated_admin = authenticate_admin(session, "adminuser", password)
        assert authenticated_admin is not None
        assert authenticated_admin.id_admin == admin.id_admin

    def test_authenticate_admin_failure(self, session: Session):
        """Admin authentication fails with incorrect credentials."""
        password = "admin_password"
        admin_in = AdminCreate(
            username="adminuser2",
            email="admin2@example.com",
            password=password,
            first_name="Admin",
            last_name="Two",
        )
        admin_service.create_admin(session, admin_in)

        authenticated_admin = authenticate_admin(session, "adminuser2", "wrong")
        assert authenticated_admin is None


class TestTokenCreation:
    """Test JWT token generation."""

    def test_create_access_token(self):
        """Generated access token has correct type and payload."""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )

        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self):
        """Generated refresh token has correct type and payload."""
        data = {"sub": "testuser"}
        token = create_refresh_token(data)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )

        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"
        assert "exp" in payload
