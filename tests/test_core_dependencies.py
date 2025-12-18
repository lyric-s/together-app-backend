import pytest
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, status
import jwt

from app.core.dependencies import (
    get_current_user,
    get_current_admin,
    oauth2_scheme,
)
from app.models.user import User
from app.models.admin import Admin
from app.core.security import create_access_token, create_refresh_token


class TestGetCurrentUser:
    """Test the get_current_user dependency."""

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_valid_token(self, mock_get_settings, test_session, test_user):
        """Test getting current user with valid access token."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create valid access token
        token = create_access_token({"sub": test_user.username})

        # Get current user
        user = get_current_user(token=token, session=test_session)
        
        assert user is not None
        assert isinstance(user, User)
        assert user.username == test_user.username
        assert user.email == test_user.email

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_invalid_token(self, mock_get_settings, test_session):
        """Test that invalid token raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="invalid_token", session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_expired_token(self, mock_get_settings, test_session, test_user):
        """Test that expired token raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        # Create expired token
        token = create_access_token(
            {"sub": test_user.username},
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_token_without_username(self, mock_get_settings, test_session):
        """Test that token without 'sub' claim raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token without 'sub'
        token = create_access_token({"user_id": "123"})

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_refresh_token_rejected(self, mock_get_settings, test_session, test_user):
        """Test that refresh token is rejected for get_current_user."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
        mock_get_settings.return_value = mock_settings

        # Create refresh token
        token = create_refresh_token({"sub": test_user.username})

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_nonexistent_user(self, mock_get_settings, test_session):
        """Test that token for non-existent user raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token for non-existent user
        token = create_access_token({"sub": "nonexistent_user"})

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_wrong_secret_key(self, mock_get_settings, test_session, test_user):
        """Test that token signed with wrong key raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token with different secret
        with patch("app.core.security.get_settings") as mock_sec_settings:
            mock_sec_settings.return_value = Mock(
                SECRET_KEY="different-secret-key-min-32-char",
                ALGORITHM="HS256",
                ACCESS_TOKEN_EXPIRE_MINUTES=30
            )
            token = create_access_token({"sub": test_user.username})

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_malformed_token(self, mock_get_settings, test_session):
        """Test that malformed token raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        malformed_tokens = [
            "not.a.valid.jwt",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Incomplete
            "",
            "Bearer token",
        ]

        for token in malformed_tokens:
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token=token, session=test_session)
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_www_authenticate_header(self, mock_get_settings, test_session):
        """Test that HTTPException includes WWW-Authenticate header."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token="invalid", session=test_session)
        
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


class TestGetCurrentAdmin:
    """Test the get_current_admin dependency."""

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_valid_token(self, mock_get_settings, test_session, test_admin):
        """Test getting current admin with valid token."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create valid admin access token
        token = create_access_token({
            "sub": test_admin.username,
            "mode": "admin"
        })

        # Get current admin
        admin = get_current_admin(token=token, session=test_session)
        
        assert admin is not None
        assert isinstance(admin, Admin)
        assert admin.username == test_admin.username
        assert admin.email == test_admin.email

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_without_mode(self, mock_get_settings, test_session, test_admin):
        """Test that token without 'mode' claim raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token without mode
        token = create_access_token({"sub": test_admin.username})

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate admin credentials" in exc_info.value.detail

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_wrong_mode(self, mock_get_settings, test_session, test_admin):
        """Test that token with wrong mode raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token with wrong mode
        token = create_access_token({
            "sub": test_admin.username,
            "mode": "user"
        })

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_refresh_token_rejected(self, mock_get_settings, test_session, test_admin):
        """Test that refresh token is rejected for get_current_admin."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
        mock_get_settings.return_value = mock_settings

        # Create refresh token with admin mode
        token = create_refresh_token({
            "sub": test_admin.username,
            "mode": "admin"
        })

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_nonexistent_admin(self, mock_get_settings, test_session):
        """Test that token for non-existent admin raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token for non-existent admin
        token = create_access_token({
            "sub": "nonexistent_admin",
            "mode": "admin"
        })

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_invalid_token(self, mock_get_settings, test_session):
        """Test that invalid token raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token="invalid_token", session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_without_username(self, mock_get_settings, test_session):
        """Test that token without username raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token without 'sub' but with mode
        token = create_access_token({"mode": "admin"})

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_www_authenticate_header(self, mock_get_settings, test_session):
        """Test that HTTPException includes WWW-Authenticate header."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token="invalid", session=test_session)
        
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_expired_token(self, mock_get_settings, test_session, test_admin):
        """Test that expired admin token raises HTTPException."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        # Create expired token
        token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"},
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin(token=token, session=test_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestOAuth2Scheme:
    """Test the OAuth2PasswordBearer scheme configuration."""

    def test_oauth2_scheme_configuration(self):
        """Test that oauth2_scheme is configured correctly."""
        assert oauth2_scheme is not None
        # Check that tokenUrl is set correctly
        assert hasattr(oauth2_scheme, "model")
        # OAuth2PasswordBearer should have tokenUrl in its model
        if hasattr(oauth2_scheme.model, "flows"):
            assert oauth2_scheme.model.flows is not None


class TestEdgeCases:
    """Test edge cases for dependencies."""

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_token_with_extra_claims(self, mock_get_settings, test_session, test_user):
        """Test that extra claims in token don't cause issues."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token with extra claims
        token = create_access_token({
            "sub": test_user.username,
            "extra_field": "extra_value",
            "another_field": 123
        })

        user = get_current_user(token=token, session=test_session)
        assert user.username == test_user.username

    @patch("app.core.dependencies.get_settings")
    def test_get_current_admin_token_with_extra_claims(self, mock_get_settings, test_session, test_admin):
        """Test that extra claims in admin token don't cause issues."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create token with extra claims
        token = create_access_token({
            "sub": test_admin.username,
            "mode": "admin",
            "extra_field": "extra_value"
        })

        admin = get_current_admin(token=token, session=test_session)
        assert admin.username == test_admin.username

    @patch("app.core.dependencies.get_settings")
    def test_get_current_user_with_username_containing_special_chars(self, mock_get_settings, test_session):
        """Test user with special characters in username."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        # Create user with special chars
        from app.core.security import get_password_hash
        from datetime import datetime
        user = User(
            username="user@example.com",
            email="user@example.com",
            user_type="volunteer",
            hashed_password=get_password_hash("password"),
            date_creation=datetime.now(),
        )
        test_session.add(user)
        test_session.commit()
        test_session.refresh(user)

        token = create_access_token({"sub": "user@example.com"})
        retrieved_user = get_current_user(token=token, session=test_session)
        assert retrieved_user.username == "user@example.com"

    @patch("app.core.dependencies.get_settings")
    def test_token_data_model_usage(self, mock_get_settings, test_session, test_user):
        """Test that TokenData model is used correctly."""
        mock_settings = Mock()
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        token = create_access_token({"sub": test_user.username})
        user = get_current_user(token=token, session=test_session)
        
        # Verify TokenData was used internally (indirectly)
        assert user is not None
        assert user.username == test_user.username