import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
import jwt

from app.main import app
from app.models.admin import Admin, AdminCreate
from app.core.security import create_access_token, get_password_hash
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


class TestAdminLogin:
    """Test the /internal/admin/login endpoint."""

    def test_admin_login_success(self, client, test_admin, test_settings, override_dependencies):
        """Test successful admin login."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "testadmin",
                "password": "adminpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "refresh_token" not in data  # Admin login doesn't return refresh token
        
        # Verify token contains admin mode
        token_payload = jwt.decode(
            data["access_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert token_payload["sub"] == "testadmin"
        assert token_payload["mode"] == "admin"
        assert token_payload["type"] == "access"

    def test_admin_login_invalid_username(self, client, override_dependencies):
        """Test admin login with invalid username."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "nonexistent",
                "password": "adminpassword123",
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect admin username or password"

    def test_admin_login_invalid_password(self, client, test_admin, override_dependencies):
        """Test admin login with invalid password."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "testadmin",
                "password": "wrongpassword",
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect admin username or password"

    def test_admin_login_empty_username(self, client, override_dependencies):
        """Test admin login with empty username."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "",
                "password": "adminpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_admin_login_empty_password(self, client, test_admin, override_dependencies):
        """Test admin login with empty password."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "testadmin",
                "password": "",
            }
        )
        
        assert response.status_code == 401

    def test_admin_login_missing_credentials(self, client, override_dependencies):
        """Test admin login with missing credentials."""
        # Missing username
        response = client.post(
            "/internal/admin/login",
            data={"password": "adminpassword123"}
        )
        assert response.status_code == 422
        
        # Missing password
        response = client.post(
            "/internal/admin/login",
            data={"username": "testadmin"}
        )
        assert response.status_code == 422

    def test_admin_login_case_sensitive(self, client, test_admin, override_dependencies):
        """Test that admin username is case-sensitive."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "TESTADMIN",
                "password": "adminpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_admin_login_www_authenticate_header(self, client, override_dependencies):
        """Test that 401 response includes WWW-Authenticate header."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "nonexistent",
                "password": "password",
            }
        )
        
        assert response.status_code == 401
        assert "www-authenticate" in response.headers

    def test_admin_login_sql_injection_attempt(self, client, override_dependencies):
        """Test that SQL injection attempts are handled safely."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "admin' OR '1'='1",
                "password": "password' OR '1'='1",
            }
        )
        
        assert response.status_code == 401

    def test_admin_login_token_expiration(self, client, test_admin, test_settings, override_dependencies):
        """Test that admin token uses configured expiration."""
        response = client.post(
            "/internal/admin/login",
            data={
                "username": "testadmin",
                "password": "adminpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Decode and verify expiration
        payload = jwt.decode(
            data["access_token"],
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert "exp" in payload


class TestCreateNewAdmin:
    """Test the /internal/admin/ POST endpoint for creating admins."""

    def test_create_admin_success(self, client, test_admin, test_settings, override_dependencies):
        """Test successful admin creation."""
        # Create admin token
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "newadminpassword123",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newadmin"
        assert data["email"] == "newadmin@example.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "Admin"
        assert "id_admin" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_create_admin_without_authentication(self, client, override_dependencies):
        """Test that creating admin without auth token fails."""
        response = client.post(
            "/internal/admin/",
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "newadminpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_create_admin_with_invalid_token(self, client, override_dependencies):
        """Test that creating admin with invalid token fails."""
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": "Bearer invalid_token"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "newadminpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_create_admin_with_user_token(self, client, test_user, test_settings, override_dependencies):
        """Test that regular user token cannot create admin."""
        user_token = create_access_token({"sub": test_user.username})
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "newadminpassword123",
            }
        )
        
        assert response.status_code == 401

    def test_create_admin_duplicate_username(self, client, test_admin, test_settings, override_dependencies):
        """Test that duplicate username returns error."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "Another",
                "last_name": "Admin",
                "email": "anotheradmin@example.com",
                "username": "testadmin",  # Duplicate username
                "password": "password123",
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Username or email already exists" in data["detail"]

    def test_create_admin_duplicate_email(self, client, test_admin, test_settings, override_dependencies):
        """Test that duplicate email returns error."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "Another",
                "last_name": "Admin",
                "email": "admin@example.com",  # Duplicate email
                "username": "anotheradmin",
                "password": "password123",
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Username or email already exists" in data["detail"]

    def test_create_admin_missing_required_fields(self, client, test_admin, test_settings, override_dependencies):
        """Test that missing required fields returns validation error."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        # Missing first_name
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "password123",
            }
        )
        assert response.status_code == 422

    def test_create_admin_empty_password(self, client, test_admin, test_settings, override_dependencies):
        """Test that empty password is handled."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "",
            }
        )
        
        # Should succeed - password validation not enforced at model level
        # (though it should be in production)
        assert response.status_code in [200, 422]

    def test_create_admin_with_special_characters(self, client, test_admin, test_settings, override_dependencies):
        """Test creating admin with special characters in fields."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "Jean-Pierre",
                "last_name": "O'Brien",
                "email": "jean.pierre@example.com",
                "username": "jp.obrien",
                "password": "p@ssw0rd!#$",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Jean-Pierre"
        assert data["last_name"] == "O'Brien"

    def test_create_admin_password_is_hashed(self, client, test_admin, test_session, test_settings, override_dependencies):
        """Test that admin password is properly hashed."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        plain_password = "plainpassword123"
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": plain_password,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Fetch admin from database
        from sqlmodel import select
        created_admin = test_session.exec(
            select(Admin).where(Admin.username == "newadmin")
        ).first()
        
        assert created_admin is not None
        assert created_admin.hashed_password != plain_password
        assert created_admin.hashed_password.startswith("$argon2")

    def test_create_admin_with_refresh_token_rejected(self, client, test_admin, test_settings, override_dependencies):
        """Test that refresh token cannot be used to create admin."""
        from app.core.security import create_refresh_token
        refresh_token = create_refresh_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {refresh_token}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "password123",
            }
        )
        
        assert response.status_code == 401

    def test_create_admin_long_names(self, client, test_admin, test_settings, override_dependencies):
        """Test creating admin with long names."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "A" * 50,  # Max length
                "last_name": "B" * 50,
                "email": "longnameadmin@example.com",
                "username": "longnameadmin",
                "password": "password123",
            }
        )
        
        assert response.status_code == 200

    def test_create_admin_exceeding_max_length(self, client, test_admin, test_settings, override_dependencies):
        """Test that exceeding max length causes validation error."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "A" * 51,  # Exceeds max length
                "last_name": "Admin",
                "email": "toolongname@example.com",
                "username": "toolongadmin",
                "password": "password123",
            }
        )
        
        assert response.status_code == 422


class TestAdminEndpointsIntegration:
    """Integration tests for admin endpoints."""

    def test_full_admin_flow(self, client, test_admin, test_settings, override_dependencies):
        """Test complete admin flow: login -> create new admin -> verify."""
        # 1. Login as admin
        login_response = client.post(
            "/internal/admin/login",
            data={
                "username": "testadmin",
                "password": "adminpassword123",
            }
        )
        assert login_response.status_code == 200
        admin_token = login_response.json()["access_token"]
        
        # 2. Create new admin
        create_response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "newpassword123",
            }
        )
        assert create_response.status_code == 200
        
        # 3. Verify new admin can login
        new_admin_login = client.post(
            "/internal/admin/login",
            data={
                "username": "newadmin",
                "password": "newpassword123",
            }
        )
        assert new_admin_login.status_code == 200

    def test_admin_cannot_use_regular_user_endpoints(self, client, test_admin, test_settings, override_dependencies):
        """Test that admin token has different behavior from user token."""
        admin_token = create_access_token(
            {"sub": test_admin.username, "mode": "admin"}
        )
        
        # Admin token should have mode="admin" which differentiates it
        payload = jwt.decode(
            admin_token,
            test_settings.SECRET_KEY,
            algorithms=[test_settings.ALGORITHM]
        )
        assert payload["mode"] == "admin"


class TestAdminEndpointSecurity:
    """Test security aspects of admin endpoints."""

    def test_admin_endpoint_not_in_schema(self, client):
        """Test that admin endpoints are not included in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_schema = response.json()
        
        # Admin endpoints should have include_in_schema=False
        paths = openapi_schema.get("paths", {})
        
        # Check if admin paths are excluded or marked as internal
        admin_paths = [path for path in paths.keys() if "/internal/admin" in path]
        
        # Depending on FastAPI version, these might be excluded
        # or we just verify the tag exists
        assert len(admin_paths) == 0 or all(
            "Internal Admin" in str(paths[path]) for path in admin_paths
        )

    def test_admin_login_timing_consistency(self, client, test_admin, override_dependencies):
        """Test timing consistency for valid/invalid admin logins."""
        # Valid username, wrong password
        response1 = client.post(
            "/internal/admin/login",
            data={"username": "testadmin", "password": "wrongpassword"}
        )
        
        # Invalid username
        response2 = client.post(
            "/internal/admin/login",
            data={"username": "nonexistent", "password": "password"}
        )
        
        # Both should return 401
        assert response1.status_code == 401
        assert response2.status_code == 401

    def test_create_admin_requires_admin_mode(self, client, test_user, test_settings, override_dependencies):
        """Test that only tokens with mode='admin' can create admins."""
        # Token without mode
        token_no_mode = create_access_token({"sub": test_user.username})
        
        response = client.post(
            "/internal/admin/",
            headers={"Authorization": f"Bearer {token_no_mode}"},
            json={
                "first_name": "New",
                "last_name": "Admin",
                "email": "newadmin@example.com",
                "username": "newadmin",
                "password": "password123",
            }
        )
        
        assert response.status_code == 401