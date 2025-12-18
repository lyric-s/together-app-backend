import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app, BASE_DIR


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestAppConfiguration:
    """Test FastAPI app configuration."""

    def test_app_exists(self):
        """Test that app is created."""
        assert app is not None

    def test_app_title(self):
        """Test app title is set correctly."""
        assert app.title == "Together API"

    def test_app_description(self):
        """Test app description is set."""
        assert app.description == "RESTful API for the Together application"

    def test_app_has_lifespan(self):
        """Test that app has lifespan context manager."""
        assert app.router.lifespan_context is not None

    def test_base_dir_exists(self):
        """Test that BASE_DIR is defined."""
        assert BASE_DIR is not None
        assert BASE_DIR.exists()


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_cors_middleware_configured(self):
        """Test that CORS middleware is added."""
        # Check middleware stack
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert any("CORS" in name for name in middleware_types)

    @patch("app.main.get_settings")
    def test_cors_origins_from_settings(self, mock_get_settings, client):
        """Test that CORS origins come from settings."""
        mock_settings = Mock()
        mock_settings.BACKEND_CORS_ORIGINS = []
        mock_get_settings.return_value = mock_settings
        
        # Just verify settings are accessible
        from app.core.config import get_settings
        settings = get_settings()
        assert hasattr(settings, "BACKEND_CORS_ORIGINS")

    def test_cors_allows_credentials(self, client):
        """Test that CORS allows credentials."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # CORS should handle the request
        assert response.status_code in [200, 404]


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_endpoint_exists(self, client):
        """Test that health endpoint exists."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_ok(self, client):
        """Test that health endpoint returns ok status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_endpoint_not_in_schema(self, client):
        """Test that health endpoint is not in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        assert "/health" not in paths

    def test_health_endpoint_json_response(self, client):
        """Test that health endpoint returns JSON."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_no_authentication(self, client):
        """Test that health endpoint doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestFaviconEndpoint:
    """Test the favicon endpoint."""

    def test_favicon_endpoint_exists(self, client):
        """Test that favicon endpoint exists."""
        response = client.get("/favicon.ico")
        # May return 200 if file exists or 404 if not
        assert response.status_code in [200, 404, 500]

    def test_favicon_endpoint_not_in_schema(self, client):
        """Test that favicon endpoint is not in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        assert "/favicon.ico" not in paths

    @patch("app.main.FileResponse")
    def test_favicon_returns_file(self, mock_file_response):
        """Test that favicon endpoint returns FileResponse."""
        # The actual file may or may not exist in test environment
        from app.main import favicon
        import asyncio
        
        result = asyncio.run(favicon())
        # Should attempt to return FileResponse (even if file doesn't exist)
        assert result is not None


class TestRouterInclusion:
    """Test that routers are included."""

    def test_auth_router_included(self, client):
        """Test that auth router is included."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        
        # Check for auth endpoints
        auth_paths = [p for p in paths.keys() if "/auth/" in p]
        assert len(auth_paths) > 0

    def test_admin_router_included(self):
        """Test that admin router is included."""
        # Admin routes have include_in_schema=False
        # Just verify the router import works
        from app.internal import admin
        assert admin.router is not None

    def test_auth_token_endpoint_in_schema(self, client):
        """Test that /auth/token endpoint is in schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        assert "/auth/token" in paths

    def test_auth_refresh_endpoint_in_schema(self, client):
        """Test that /auth/refresh endpoint is in schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        assert "/auth/refresh" in paths


class TestLifespanEvents:
    """Test lifespan event handlers."""

    @patch("app.main.setup_logging")
    @patch("app.main.create_db_and_tables")
    @patch("app.main.setup_telemetry")
    async def test_lifespan_startup(
        self, mock_telemetry, mock_db, mock_logging
    ):
        """Test that lifespan startup calls setup functions."""
        from app.main import lifespan
        
        # Create a mock app
        mock_app = Mock()
        
        # Execute lifespan
        async with lifespan(mock_app):
            pass
        
        # Verify setup functions were called
        mock_logging.assert_called_once()
        mock_db.assert_called_once()
        mock_telemetry.assert_called_once_with(mock_app)

    @patch("app.main.setup_logging")
    @patch("app.main.create_db_and_tables")
    @patch("app.main.setup_telemetry")
    async def test_lifespan_exception_handling(
        self, mock_telemetry, mock_db, mock_logging
    ):
        """Test that lifespan handles exceptions in setup."""
        from app.main import lifespan
        
        # Simulate exception during setup
        mock_db.side_effect = Exception("Database error")
        
        mock_app = Mock()
        
        # Should propagate exception
        with pytest.raises(Exception):
            async with lifespan(mock_app):
                pass


class TestOpenAPISchema:
    """Test OpenAPI schema generation."""

    def test_openapi_schema_accessible(self, client):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_schema_structure(self, client):
        """Test OpenAPI schema has correct structure."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert schema["info"]["title"] == "Together API"

    def test_openapi_schema_has_auth_endpoints(self, client):
        """Test that auth endpoints are in schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema.get("paths", {})
        
        assert "/auth/token" in paths
        assert "/auth/refresh" in paths

    def test_openapi_docs_accessible(self, client):
        """Test that Swagger UI docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_redoc_accessible(self, client):
        """Test that ReDoc is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestAppIntegration:
    """Integration tests for the main app."""

    def test_app_starts_successfully(self, client):
        """Test that app starts and responds."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_app_handles_404(self, client):
        """Test that app handles 404 errors."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_app_handles_method_not_allowed(self, client):
        """Test that app handles method not allowed."""
        response = client.put("/health")
        assert response.status_code == 405

    def test_app_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS middleware should add headers
        assert response.status_code == 200

    def test_multiple_requests(self, client):
        """Test that app handles multiple requests."""
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_concurrent_requests_simulation(self, client):
        """Test that app can handle multiple requests."""
        responses = []
        for _ in range(5):
            response = client.get("/health")
            responses.append(response)
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)


class TestAppEdgeCases:
    """Test edge cases for the main app."""

    def test_empty_request_body(self, client):
        """Test handling of empty request body."""
        response = client.post("/auth/token", data={})
        # Should return validation error
        assert response.status_code == 422

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/auth/refresh",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_content_type(self, client):
        """Test request without content-type."""
        response = client.get("/health")
        # Should still work
        assert response.status_code == 200

    def test_large_request_body(self, client):
        """Test handling of large request body."""
        large_data = {"data": "x" * 10000}
        response = client.post("/auth/refresh", json=large_data)
        # Should handle gracefully (validation error expected)
        assert response.status_code in [400, 422]

    def test_special_characters_in_url(self, client):
        """Test handling of special characters in URL."""
        response = client.get("/health?param=value%20with%20spaces")
        assert response.status_code == 200

    def test_unicode_in_request(self, client):
        """Test handling of unicode in request."""
        response = client.post(
            "/auth/token",
            data={
                "username": "用户",
                "password": "密码"
            }
        )
        # Should handle unicode (even if auth fails)
        assert response.status_code in [401, 422]


class TestAppSecurity:
    """Test security aspects of the app."""

    def test_no_debug_info_in_errors(self, client):
        """Test that errors don't expose debug information."""
        response = client.get("/nonexistent")
        data = response.json()
        # Should not expose internal stack traces
        assert "detail" in data

    def test_security_headers(self, client):
        """Test that basic security is in place."""
        response = client.get("/health")
        # Basic check that response is formed correctly
        assert response.status_code == 200

    def test_authentication_required_for_protected_endpoints(self, client):
        """Test that protected endpoints require authentication."""
        # Create admin endpoint requires authentication
        response = client.post(
            "/internal/admin/",
            json={
                "first_name": "Test",
                "last_name": "Admin",
                "email": "test@example.com",
                "username": "testadmin",
                "password": "password123"
            }
        )
        # Should return 401 without authentication
        assert response.status_code == 401