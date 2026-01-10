"""Performance benchmarks for user service operations."""

import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.user import UserCreate
from app.services import user as user_service


@pytest.fixture(name="user_create_data")
def user_create_data_fixture(user_create_data_factory):
    """
    Provide a reusable UserCreate payload for benchmarks.

    This fixture returns a unique UserCreate instance by invoking the user_create_data_factory.

    Returns:
        UserCreate: A unique user creation payload.
    """
    return user_create_data_factory()


def test_user_creation_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data_factory
):
    """
    Benchmark user creation operation.

    Each iteration uses a DB savepoint so cleanup is rolled back and excluded from timing.
    """

    @benchmark
    def create_user():
        """
        Create a new user using the provided factory and return the created user instance.

        Uses a savepoint to rollback after each iteration, preventing database row leaks.

        Returns:
            The created user model instance.
        """
        # Roll back each iteration via a savepoint to avoid accumulating work/rows.
        # NOTE: This assumes `user_service.create_user` does NOT call `session.commit()`.
        with session.begin_nested():
            user = user_service.create_user(
                session=session, user_in=user_create_data_factory()
            )
            session.flush()
            return user.id_user


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
    session.flush()
    user_id: int = user.id_user  # type: ignore[assignment]

    @benchmark
    def get_user():
        """
        Retrieve a user record by its identifier from the database.

        Returns:
            The user record matching the provided `user_id`, or `None` if no such user exists.
        """
        session.expire_all()
        return user_service.get_user(session=session, user_id=user_id)


def test_user_retrieval_by_email_performance(
    benchmark: BenchmarkFixture, session: Session, user_create_data: UserCreate
):
    """Benchmark user retrieval by email operation."""
    # Setup: Create a user to retrieve
    user = user_service.create_user(session=session, user_in=user_create_data)
    session.flush()

    @benchmark
    def get_user():
        """
        Call the user service to retrieve a user record by the benchmark-provided email.

        Returns:
            user: The user model instance matching the given email, or `None` if no match is found.
        """
        session.expire_all()
        return user_service.get_user_by_email(session=session, email=user.email)

    session.delete(user)
    session.flush()
