"""Root conftest for all tests."""

import os
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Set environment variables for testing before importing app modules that might use them at import time
# Required settings
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test_secret_key_1234567890"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["BACKEND_CORS_ORIGINS"] = "http://localhost:3000"
os.environ["FIRST_SUPERUSER_EMAIL"] = "admin@example.com"
os.environ["FIRST_SUPERUSER_PASSWORD"] = "admin123"
os.environ["FIRST_SUPERUSER_USERNAME"] = "admin"
os.environ["ENVIRONMENT"] = "development"
os.environ["DOCUMENTS_BUCKET"] = "test-bucket"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"
os.environ["MINIO_SECURE"] = "False"
os.environ["SMTP_HOST"] = "localhost"
os.environ["SMTP_PORT"] = "1025"
os.environ["SMTP_USER"] = "test@example.com"
os.environ["SMTP_PASSWORD"] = "testpass"
os.environ["SMTP_FROM_EMAIL"] = "noreply@example.com"
os.environ["SMTP_FROM_NAME"] = "Together Test"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["PASSWORD_RESET_TOKEN_EXPIRE_MINUTES"] = "15"

from app.main import app
from app.database.database import get_session
from app.core.config import get_settings, Settings


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """
    Create a fresh in-memory database session for each test.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """
    Create a TestClient with overridden dependencies.
    """

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    # We can also override get_settings if needed, but we set env vars above.
    # To be safe and explicit, let's override it to ensure isolation.
    def get_settings_override():
        return Settings(
            DATABASE_URL="sqlite:///:memory:",
            SECRET_KEY="test_secret_key_1234567890",
            ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=30,
            REFRESH_TOKEN_EXPIRE_DAYS=7,
            BACKEND_CORS_ORIGINS="http://localhost:3000",
            FIRST_SUPERUSER_EMAIL="admin@example.com",
            FIRST_SUPERUSER_PASSWORD="admin123",
            FIRST_SUPERUSER_USERNAME="admin",
            ENVIRONMENT="development",
            DOCUMENTS_BUCKET="test-bucket",
            MINIO_ENDPOINT="localhost:9000",
            MINIO_ACCESS_KEY="minioadmin",
            MINIO_SECRET_KEY="minioadmin",
            MINIO_SECURE=False,
            SMTP_HOST="localhost",
            SMTP_PORT=1025,
            SMTP_USER="test@example.com",
            SMTP_PASSWORD="testpass",
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_FROM_NAME="Together Test",
            FRONTEND_URL="http://localhost:3000",
            PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=15,
        )

    app.dependency_overrides[get_settings] = get_settings_override

    # Disable rate limiting for tests
    from app.core.limiter import limiter

    limiter.enabled = False

    # Mock storage_service.ensure_bucket_exists to prevent MinIO connection attempts
    from unittest.mock import patch

    with patch("app.services.storage.storage_service.ensure_bucket_exists"):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()
    limiter.enabled = True
