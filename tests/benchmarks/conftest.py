"""Shared fixtures for benchmark tests."""

import uuid
import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.models.user import UserCreate
from app.models.enums import UserType


@pytest.fixture(name="session")
def session_fixture():
    """
    Create and yield a SQLModel Session bound to a fresh in-memory SQLite database.

    Yields:
        Session: A SQLModel Session connected to the created in-memory SQLite database; the session is closed when the fixture tears down.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="user_create_data_factory")
def user_create_data_factory_fixture():
    """
    Create a factory that produces unique UserCreate payloads for benchmarks.

    Each generated UserCreate has a unique username and email; password and user_type are fixed
    ("BenchPass123" and UserType.VOLUNTEER respectively).

    Returns:
        create_callable (Callable[[], UserCreate]): A no-argument callable that returns a new,
        unique UserCreate instance on each call.
    """

    def create():
        """
        Create a unique UserCreate payload for benchmark tests.

        Generates a UserCreate with a short random hex suffix appended to the username and email to ensure uniqueness. The password is set to "BenchPass123" and the user_type is UserType.VOLUNTEER.

        Returns:
            UserCreate: A user creation model with unique `username` and `email`, fixed `password`, and `user_type` set to `UserType.VOLUNTEER`.
        """
        unique = uuid.uuid4().hex[:8]
        return UserCreate(
            username=f"bench_user_{unique}",
            email=f"bench_{unique}@example.com",
            password="BenchPass123",
            user_type=UserType.VOLUNTEER,
        )

    return create
