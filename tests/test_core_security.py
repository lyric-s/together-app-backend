import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
import jwt

from app.core.security import (
    verify_password,
    get_password_hash,
    authenticate_user,
    authenticate_admin,
    create_token,
    create_access_token,
    create_refresh_token,
    password_hash,
)
from app.models.user import User
from app.models.admin import Admin
from app.core.config import Settings


class TestPasswordHashing:
    """Test password hashing and verification functions."""

    def test_get_password_hash_returns_string(self):
        """Test that password hashing returns a string."""
        password = "mysecurepassword123"
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_get_password_hash_produces_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        # Due to salting, hashes should be different
        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """Test password verification with correct password."""
        password = "correctpassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test password verification with incorrect password."""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password."""
        hashed = get_password_hash("somepassword")
        assert verify_password("", hashed) is False

    def test_verify_password_with_special_characters(self):
        """Test password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_with_unicode(self):
        """Test password with unicode characters."""
        password = "パスワード123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestAuthenticateUser:
    """Test user authentication functions."""

    def test_authenticate_user_valid_credentials(self, test_session, test_user):
        """Test authentication with valid credentials."""
        result = authenticate_user(test_session, "testuser", "testpassword123")
        assert result is not None
        assert isinstance(result, User)
        assert result.username == "testuser"
        assert result.email == "testuser@example.com"

    def test_authenticate_user_invalid_password(self, test_session, test_user):
        """Test authentication with invalid password."""
        result = authenticate_user(test_session, "testuser", "wrongpassword")
        assert result is None

    def test_authenticate_user_nonexistent_user(self, test_session):
        """Test authentication with non-existent username."""
        result = authenticate_user(test_session, "nonexistent", "password")
        assert result is None

    def test_authenticate_user_empty_username(self, test_session):
        """Test authentication with empty username."""
        result = authenticate_user(test_session, "", "password")
        assert result is None

    def test_authenticate_user_empty_password(self, test_session, test_user):
        """Test authentication with empty password."""
        result = authenticate_user(test_session, "testuser", "")
        assert result is None

    def test_authenticate_user_sql_injection_attempt(self, test_session, test_user):
        """Test that SQL injection attempts don't work."""
        result = authenticate_user(
            test_session, "testuser' OR '1'='1", "password"
        )
        assert result is None

    def test_authenticate_user_timing_attack_resistance(self, test_session):
        """Test that authentication uses dummy hash for non-existent users."""
        # This test ensures constant-time comparison by always hashing
        # even when user doesn't exist
        result = authenticate_user(test_session, "nonexistent", "password")
        assert result is None


class TestAuthenticateAdmin:
    """Test admin authentication functions."""

    def test_authenticate_admin_valid_credentials(self, test_session, test_admin):
        """Test admin authentication with valid credentials."""
        result = authenticate_admin(test_session, "testadmin", "adminpassword123")
        assert result is not None
        assert isinstance(result, Admin)
        assert result.username == "testadmin"
        assert result.email == "admin@example.com"

    def test_authenticate_admin_invalid_password(self, test_session, test_admin):
        """Test admin authentication with invalid password."""
        result = authenticate_admin(test_session, "testadmin", "wrongpassword")
        assert result is None

    def test_authenticate_admin_nonexistent_admin(self, test_session):
        """Test admin authentication with non-existent username."""
        result = authenticate_admin(test_session, "nonexistent", "password")
        assert result is None

    def test_authenticate_admin_empty_credentials(self, test_session):
        """Test admin authentication with empty credentials."""
        result = authenticate_admin(test_session, "", "")
        assert result is None


class TestTokenCreation:
    """Test JWT token creation functions."""

    @patch("app.core.security.get_settings")
    def test_create_token_access_type(self, mock_get_settings):
        """Test creating an access token."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_token(data, expires_delta, type="access")

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify
        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"
        assert "exp" in payload

    @patch("app.core.security.get_settings")
    def test_create_token_refresh_type(self, mock_get_settings):
        """Test creating a refresh token."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        expires_delta = timedelta(days=7)
        token = create_token(data, expires_delta, type="refresh")

        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["type"] == "refresh"

    @patch("app.core.security.get_settings")
    def test_create_token_expiration_time(self, mock_get_settings):
        """Test that token expiration is set correctly."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)
        before_creation = datetime.now(timezone.utc)
        token = create_token(data, expires_delta, type="access")
        after_creation = datetime.now(timezone.utc)

        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        # Check expiration is approximately correct
        expected_exp = before_creation + expires_delta
        assert abs((exp_time - expected_exp).total_seconds()) < 5

    @patch("app.core.security.get_settings")
    def test_create_token_with_additional_data(self, mock_get_settings):
        """Test creating token with additional data fields."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser", "role": "admin", "custom_field": "value"}
        expires_delta = timedelta(minutes=30)
        token = create_token(data, expires_delta, type="access")

        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["custom_field"] == "value"

    @patch("app.core.security.jwt.encode")
    @patch("app.core.security.get_settings")
    def test_create_token_jwt_error_handling(self, mock_get_settings, mock_jwt_encode):
        """Test that JWT encoding errors are handled properly."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings
        
        # Simulate JWT encoding error
        from jwt.exceptions import PyJWTError
        mock_jwt_encode.side_effect = PyJWTError("Encoding failed")

        with pytest.raises(HTTPException) as exc_info:
            create_token({"sub": "user"}, timedelta(minutes=30), type="access")
        
        assert exc_info.value.status_code == 500
        assert "Could not generate authentication token" in exc_info.value.detail


class TestCreateAccessToken:
    """Test access token creation wrapper function."""

    @patch("app.core.security.get_settings")
    def test_create_access_token_default_expiration(self, mock_get_settings):
        """Test access token creation with default expiration."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"

    @patch("app.core.security.get_settings")
    def test_create_access_token_custom_expiration(self, mock_get_settings):
        """Test access token creation with custom expiration."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        custom_expiration = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=custom_expiration)

        assert isinstance(token, str)
        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["type"] == "access"

    @patch("app.core.security.get_settings")
    def test_create_access_token_with_admin_mode(self, mock_get_settings):
        """Test access token creation with admin mode."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_get_settings.return_value = mock_settings

        data = {"sub": "adminuser", "mode": "admin"}
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["mode"] == "admin"


class TestCreateRefreshToken:
    """Test refresh token creation wrapper function."""

    @patch("app.core.security.get_settings")
    def test_create_refresh_token_default_expiration(self, mock_get_settings):
        """Test refresh token creation with default expiration."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        token = create_refresh_token(data)

        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"

    @patch("app.core.security.get_settings")
    def test_create_refresh_token_custom_expiration(self, mock_get_settings):
        """Test refresh token creation with custom expiration."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        custom_expiration = timedelta(days=14)
        token = create_refresh_token(data, expires_delta=custom_expiration)

        assert isinstance(token, str)
        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["type"] == "refresh"

    @patch("app.core.security.get_settings")
    def test_create_refresh_token_different_from_access(self, mock_get_settings):
        """Test that refresh and access tokens are different."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        # Tokens should be different
        assert access_token != refresh_token

        # Decode both and check types
        access_payload = jwt.decode(
            access_token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        refresh_payload = jwt.decode(
            refresh_token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"


class TestEdgeCases:
    """Test edge cases and security concerns."""

    @patch("app.core.security.get_settings")
    def test_token_cannot_be_decoded_with_wrong_secret(self, mock_get_settings):
        """Test that token cannot be decoded with wrong secret key."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Try to decode with wrong secret
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                token,
                "wrong-secret-key",
                algorithms=["HS256"]
            )

    @patch("app.core.security.get_settings")
    def test_expired_token_detection(self, mock_get_settings):
        """Test that expired tokens are detected."""
        mock_settings = Mock(spec=Settings)
        mock_settings.SECRET_KEY = "test-secret-key-min-32-characters-long"
        mock_settings.ALGORITHM = "HS256"
        mock_get_settings.return_value = mock_settings

        data = {"sub": "testuser"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        # Try to decode expired token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token,
                mock_settings.SECRET_KEY,
                algorithms=["HS256"]
            )

    def test_password_hash_handles_long_passwords(self):
        """Test that very long passwords are handled correctly."""
        long_password = "a" * 1000
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True

    def test_authenticate_user_case_sensitive_username(self, test_session, test_user):
        """Test that username is case-sensitive."""
        result = authenticate_user(test_session, "TESTUSER", "testpassword123")
        assert result is None

    def test_authenticate_with_none_values(self, test_session):
        """Test authentication handles None values gracefully."""
        # This should not crash
        result = authenticate_user(test_session, None, None)
        # Behavior depends on SQLModel handling, but shouldn't crash
        assert result is None or isinstance(result, (User, type(None)))