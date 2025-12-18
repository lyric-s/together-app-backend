import pytest
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.models.user import User
from app.models.token import Token, TokenRefreshRequest
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.database.database import get_session
from app.core.config import get_settings


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def override_dependencies(test_session, test_settings):
    """Override FastAPI dependencies for testing."""
    def _get_test_session():
        yield test_session
    
    def _get_test_settings():
        return test_settings
    
    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_settings] = _get_test_settings
    
    yield
    
    app.dependency_overrides.clear()


class TestLoginForAccessToken:
    """Test the /auth/token endpoint for user login."""

    def test_login_success_returns_tokens(self, client, test_session, test_user, test_settings, override_dependencies):
        """Test successful login returns access and refresh tokens."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify tokens are valid JWTs
        access_payload = jwt.decode(
            data["access_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert access_payload["sub"] == "testuser"
        assert access_payload["type"] == "access"
        
        refresh_payload = jwt.decode(
            data["refresh_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert refresh_payload["sub"] == "testuser"
        assert refresh_payload["type"] == "refresh"

    def test_login_invalid_username(self, client, override_dependencies):
        """Test login with invalid username returns 401."""
        response = client.post(
            "/auth/token",
            data={
                "username": "nonexistent",
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    def test_login_invalid_password(self, client, test_user, override_dependencies):
        """Test login with invalid password returns 401."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "wrongpassword",
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    def test_login_empty_username(self, client, override_dependencies):
        """Test login with empty username."""
        response = client.post(
            "/auth/token",
            data={
                "username": "",
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_login_empty_password(self, client, test_user, override_dependencies):
        """Test login with empty password."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "",
            }
        )
        
        assert response.status_code == 401

    def test_login_missing_username(self, client, override_dependencies):
        """Test login with missing username field."""
        response = client.post(
            "/auth/token",
            data={
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 422  # Validation error

    def test_login_missing_password(self, client, override_dependencies):
        """Test login with missing password field."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
            }
        )
        
        assert response.status_code == 422  # Validation error

    def test_login_case_sensitive_username(self, client, test_user, override_dependencies):
        """Test that username is case-sensitive."""
        response = client.post(
            "/auth/token",
            data={
                "username": "TESTUSER",
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_login_sql_injection_attempt(self, client, override_dependencies):
        """Test that SQL injection attempts are handled safely."""
        response = client.post(
            "/auth/token",
            data={
                "username": "admin' OR '1'='1",
                "password": "password' OR '1'='1",
            }
        )
        
        assert response.status_code == 401

    def test_login_with_special_characters_in_password(self, client, test_session, test_settings, override_dependencies):
        """Test login with special characters in password."""
        # Create user with special char password
        from datetime import datetime
        special_user = User(
            username="specialuser",
            email="special@example.com",
            user_type="volunteer",
            hashed_password=get_password_hash("p@ssw0rd!#$%"),
            date_creation=datetime.now(),
        )
        test_session.add(special_user)
        test_session.commit()
        
        response = client.post(
            "/auth/token",
            data={
                "username": "specialuser",
                "password": "p@ssw0rd!#$%",
            }
        )
        
        assert response.status_code == 200

    def test_login_www_authenticate_header(self, client, override_dependencies):
        """Test that 401 response includes WWW-Authenticate header."""
        response = client.post(
            "/auth/token",
            data={
                "username": "nonexistent",
                "password": "password",
            }
        )
        
        assert response.status_code == 401
        assert "www-authenticate" in response.headers

    def test_login_token_expiration_configuration(self, client, test_user, test_settings, override_dependencies):
        """Test that tokens use configured expiration times."""
        response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Decode tokens and check expiration
        access_payload = jwt.decode(
            data["access_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        refresh_payload = jwt.decode(
            data["refresh_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        
        # Check that exp fields exist
        assert "exp" in access_payload
        assert "exp" in refresh_payload
        
        # Refresh token should expire later than access token
        assert refresh_payload["exp"] > access_payload["exp"]


class TestRefreshToken:
    """Test the /auth/refresh endpoint for token refresh."""

    def test_refresh_token_success(self, client, test_user, test_settings, override_dependencies):
        """Test successful token refresh."""
        # Create a valid refresh token
        refresh_token = create_refresh_token({"sub": test_user.username})
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify new access token
        access_payload = jwt.decode(
            data["access_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert access_payload["sub"] == test_user.username
        assert access_payload["type"] == "access"

    def test_refresh_token_returns_same_refresh_token(self, client, test_user, test_settings, override_dependencies):
        """Test that refresh returns the same refresh token (no rotation)."""
        refresh_token = create_refresh_token({"sub": test_user.username})
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["refresh_token"] == refresh_token

    def test_refresh_with_access_token_rejected(self, client, test_user, test_settings, override_dependencies):
        """Test that access token cannot be used for refresh."""
        access_token = create_access_token({"sub": test_user.username})
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": access_token
            }
        )
        
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client, override_dependencies):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": "invalid_token"
            }
        )
        
        assert response.status_code == 401

    def test_refresh_with_expired_token(self, client, test_user, test_settings, override_dependencies):
        """Test refresh with expired token."""
        expired_token = create_refresh_token(
            {"sub": test_user.username},
            expires_delta=timedelta(seconds=-1)
        )
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": expired_token
            }
        )
        
        assert response.status_code == 401

    def test_refresh_token_nonexistent_user(self, client, test_settings, override_dependencies):
        """Test refresh token for non-existent user."""
        refresh_token = create_refresh_token({"sub": "nonexistent_user"})
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        
        assert response.status_code == 401

    def test_refresh_token_without_sub_claim(self, client, test_settings, override_dependencies):
        """Test refresh token without 'sub' claim."""
        # Manually create token without 'sub'
        from datetime import datetime, timezone
        import jwt
        
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "type": "refresh"
        }
        token = jwt.encode(
            payload,
            test_settings.SECRET_KEY,
            algorithm=test_settings.ALGORITHM
        )
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": token
            }
        )
        
        assert response.status_code == 401

    def test_refresh_token_wrong_secret_key(self, client, test_user, override_dependencies):
        """Test refresh with token signed by different secret."""
        # Create token with different secret
        from datetime import datetime, timezone
        
        payload = {
            "sub": test_user.username,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "type": "refresh"
        }
        wrong_token = jwt.encode(
            payload,
            "wrong-secret-key",
            algorithm="HS256"
        )
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": wrong_token
            }
        )
        
        assert response.status_code == 401

    def test_refresh_token_missing_type_claim(self, client, test_user, test_settings, override_dependencies):
        """Test refresh token without 'type' claim."""
        from datetime import datetime, timezone
        
        payload = {
            "sub": test_user.username,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        token = jwt.encode(
            payload,
            test_settings.SECRET_KEY,
            algorithm=test_settings.ALGORITHM
        )
        
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": token
            }
        )
        
        assert response.status_code == 401

    def test_refresh_token_missing_request_body(self, client, override_dependencies):
        """Test refresh without request body."""
        response = client.post("/auth/refresh", json={})
        
        assert response.status_code == 422  # Validation error

    def test_refresh_token_empty_string(self, client, override_dependencies):
        """Test refresh with empty string token."""
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": ""
            }
        )
        
        assert response.status_code == 401

    def test_refresh_token_www_authenticate_header(self, client, override_dependencies):
        """Test that 401 response includes WWW-Authenticate header."""
        response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": "invalid"
            }
        )
        
        assert response.status_code == 401
        assert "www-authenticate" in response.headers


class TestAuthRouterIntegration:
    """Integration tests for auth router."""

    def test_full_auth_flow(self, client, test_user, test_settings, override_dependencies):
        """Test complete authentication flow: login -> use token -> refresh."""
        # 1. Login
        login_response = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword123",
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # 2. Verify access token works (would be used in protected endpoint)
        access_token = tokens["access_token"]
        access_payload = jwt.decode(
            access_token,
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert access_payload["sub"] == "testuser"
        
        # 3. Refresh token
        refresh_response = client.post(
            "/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"]
            }
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        
        # 4. Verify new access token is different
        assert new_tokens["access_token"] != access_token
        
        # 5. Verify new access token is valid
        new_payload = jwt.decode(
            new_tokens["access_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert new_payload["sub"] == "testuser"

    def test_multiple_logins_generate_different_tokens(self, client, test_user, override_dependencies):
        """Test that multiple logins generate different tokens."""
        response1 = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword123",
            }
        )
        response2 = client.post(
            "/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword123",
            }
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        tokens1 = response1.json()
        tokens2 = response2.json()
        
        # Tokens should be different due to different exp times
        assert tokens1["access_token"] != tokens2["access_token"]
        assert tokens1["refresh_token"] != tokens2["refresh_token"]

    def test_refresh_multiple_times(self, client, test_user, test_settings, override_dependencies):
        """Test refreshing token multiple times."""
        refresh_token = create_refresh_token({"sub": test_user.username})
        
        # First refresh
        response1 = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response1.status_code == 200
        
        # Second refresh with same token
        response2 = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response2.status_code == 200
        
        # Both should succeed since token rotation is not implemented
        tokens1 = response1.json()
        tokens2 = response2.json()
        assert tokens1["refresh_token"] == tokens2["refresh_token"]


class TestAuthEndpointSecurity:
    """Test security aspects of auth endpoints."""

    def test_login_timing_attack_resistance(self, client, test_user, override_dependencies):
        """Test that login has consistent timing for valid/invalid users."""
        # This is a basic test - real timing attack testing would need precise measurements
        response1 = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "wrongpassword"}
        )
        response2 = client.post(
            "/auth/token",
            data={"username": "nonexistent", "password": "wrongpassword"}
        )
        
        # Both should return 401
        assert response1.status_code == 401
        assert response2.status_code == 401

    def test_refresh_token_reuse(self, client, test_user, override_dependencies):
        """Test that refresh token can be reused (no rotation implemented)."""
        refresh_token = create_refresh_token({"sub": test_user.username})
        
        # Use same refresh token twice
        response1 = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        response2 = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200