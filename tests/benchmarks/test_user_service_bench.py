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
    """
    Provide a reusable UserCreate payload for benchmarks.

    This fixture returns a UserCreate instance with a preset username, email, password, and user_type set to VOLUNTEER for use in performance tests.

    Returns:
        UserCreate: A preconfigured user creation payload.
    """
    return UserCreate(
        username="bench_user",
        email="bench@example.com",
        password="BenchPass123",
        user_type=UserType.VOLUNTEER,
    )


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


def test_user_creation_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data_factory
):
    """Benchmark user creation operation."""

    @benchmark
    def create_user():
        """
        Create a new user using the provided factory and return the created user instance.

        Returns:
            The created user model instance.
        """
        return user_service.create_user(
            session=session, user_in=user_create_data_factory()
        )


def test_user_retrieval_by_id_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data: UserCreate
):
    """
    Measure retrieval performance for a user by ID.

    Creates and commits a user from `user_create_data`, then benchmarks `user_service.get_user`
    using the created user's `id_user`.
    """
    # Setup: Create a user to retrieve
    user = user_service.create_user(session=session, user_in=user_create_data)
    session.commit()
    user_id: int = user.id_user  # type: ignore[assignment]

    @benchmark
    def get_user():
        """
        Retrieve a user record by its identifier from the database.

        Returns:
            The user record matching the provided `user_id`, or `None` if no such user exists.
        """
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
        """
        Call the user service to retrieve a user record by the benchmark-provided email.

        Returns:
            user: The user model instance matching the given email, or `None` if no match is found.
        """
        return user_service.get_user_by_email(session=session, email=user.email)
