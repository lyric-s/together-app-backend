import os
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import MagicMock

from app.core.config import Settings, get_settings
from app.database.database import get_session
from app.models.user import User
from app.models.admin import Admin
from app.core.security import get_password_hash


# Test settings fixture
@pytest.fixture(scope="function")
def test_settings():
    """Provide test settings with mock values."""
    return Settings(
        DATABASE_URL="sqlite:///:memory:",
        SECRET_KEY="test-secret-key-for-testing-only-min-32-chars",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        BACKEND_CORS_ORIGINS=[],
    )


@pytest.fixture(scope="function")
def override_get_settings(test_settings):
    """Override the get_settings dependency."""
    def _get_test_settings():
        return test_settings
    return _get_test_settings


@pytest.fixture(scope="function")
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Provide a test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def test_user(test_session):
    """Create a test user in the database."""
    user = User(
        username="testuser",
        email="testuser@example.com",
        user_type="volunteer",
        hashed_password=get_password_hash("testpassword123"),
        date_creation=datetime.now(),
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(test_session):
    """Create a test admin in the database."""
    admin = Admin(
        first_name="Test",
        last_name="Admin",
        email="admin@example.com",
        username="testadmin",
        hashed_password=get_password_hash("adminpassword123"),
    )
    test_session.add(admin)
    test_session.commit()
    test_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def mock_session():
    """Provide a mock database session."""
    return MagicMock(spec=Session)