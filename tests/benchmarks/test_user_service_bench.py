"""Performance benchmarks for user service operations."""

import uuid
import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.enums import UserType
from app.services import user as user_service


@pytest.fixture(name="user_create_data")
def user_create_data_fixture():
    """Provide test data for user creation."""
    return UserCreate(
        username="bench_user",
        email="bench@example.com",
        password="BenchPass123",
        user_type=UserType.VOLUNTEER,
    )


@pytest.fixture(name="user_create_data_factory")
def user_create_data_factory_fixture():
    """Factory for unique user creation data."""

    def create():
        unique = uuid.uuid4().hex[:8]
        return UserCreate(
            username=f"bench_user_{unique}",
            email=f"bench_{unique}@example.com",
            password="BenchPass123",
            user_type=UserType.VOLUNTEER,
        )

    return create


def test_user_creation_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data_factory
):
    """Benchmark user creation operation."""

    @benchmark
    def create_user():
        return user_service.create_user(
            session=session, user_in=user_create_data_factory()
        )


def test_user_retrieval_by_id_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data: UserCreate
):
    """Benchmark user retrieval by ID operation."""
    # Setup: Create a user to retrieve
    user = user_service.create_user(session=session, user_in=user_create_data)
    session.commit()
    user_id: int = user.id_user  # type: ignore[assignment]

    @benchmark
    def get_user():
        return user_service.get_user(session=session, user_id=user_id)


def test_user_retrieval_by_email_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data: UserCreate
):
    """Benchmark user retrieval by email operation."""
    # Setup: Create a user to retrieve
    user = user_service.create_user(session=session, user_in=user_create_data)
    session.commit()

    @benchmark
    def get_user():
        return user_service.get_user_by_email(session=session, email=user.email)
