"""Performance benchmarks for volunteer service operations."""

import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.volunteer import VolunteerCreate
from app.services import volunteer as volunteer_service


@pytest.fixture(name="user_create_data")
def user_create_data_fixture(user_create_data_factory):
    """
    Provide a unique UserCreate instance populated with sample volunteer user data for tests.

    Returns:
        UserCreate: A UserCreate object with unique username and email.
    """
    return user_create_data_factory()


@pytest.fixture(name="volunteer_create_data")
def volunteer_create_data_fixture():
    """
    Fixture that supplies a populated VolunteerCreate instance for volunteer creation benchmarks.

    The returned instance contains realistic sample values for last_name, first_name, phone_number, birthdate, skills, and bio to be used in performance tests.

    Returns:
        VolunteerCreate: A VolunteerCreate instance initialized with benchmark test data.
    """
    from datetime import date

    return VolunteerCreate(
        last_name="Benchmark",
        first_name="Volunteer",
        phone_number="+33123456789",
        birthdate=date(1990, 1, 1),
        skills="Python, FastAPI, Testing",
        bio="Benchmark volunteer bio",
    )


def test_volunteer_creation_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data: UserCreate,
    volunteer_create_data: VolunteerCreate,
):
    """
    Benchmark the volunteer creation path and measure its performance.

    This test repeatedly creates a volunteer using the provided database session and input fixtures, and removes the created volunteer and its associated user after each measured iteration to keep the database state clean.

    Parameters:
        benchmark (BenchmarkFixture): pytest-benchmark fixture used to measure execution.
        session (Session): SQLModel database session used for creating and deleting records.
        user_create_data (UserCreate): Input data for the user associated with the volunteer.
        volunteer_create_data (VolunteerCreate): Input data for the volunteer to be created.
    """

    @benchmark
    def create_volunteer():
        """
        Create a volunteer using the test fixtures and remove it from the session afterwards.

        Creates a volunteer via volunteer_service.create_volunteer with the test session and fixture inputs, deletes the created volunteer and its associated user from the session, commits the transaction, and returns the created volunteer.

        Returns:
            volunteer: The created Volunteer model instance.
        """
        volunteer = volunteer_service.create_volunteer(
            session=session,
            user_in=user_create_data,
            volunteer_in=volunteer_create_data,
        )
        # Clean up after each iteration
        session.delete(volunteer)
        session.delete(volunteer.user)
        session.commit()
        return volunteer


def test_volunteer_retrieval_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data: UserCreate,
    volunteer_create_data: VolunteerCreate,
):
    """Benchmark volunteer retrieval by ID operation."""
    # Setup: Create a volunteer to retrieve
    volunteer = volunteer_service.create_volunteer(
        session=session,
        user_in=user_create_data,
        volunteer_in=volunteer_create_data,
    )
    session.commit()
    volunteer_id: int = volunteer.id_volunteer  # type: ignore[assignment]

    @benchmark
    def get_volunteer():
        """
        Retrieve a volunteer record by its identifier.

        Returns:
            Volunteer: The volunteer model instance matching the provided ID.
        """
        return volunteer_service.get_volunteer(
            session=session, volunteer_id=volunteer_id
        )
