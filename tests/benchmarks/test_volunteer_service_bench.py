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


def test_volunteer_creation_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data_factory,
    volunteer_create_data: VolunteerCreate,
    tracker,
):
    """
    Benchmark the volunteer creation path and measure its performance.
    """

    @benchmark
    def create_volunteer():
        """
        Create a volunteer using the test fixtures.
        """
        volunteer = volunteer_service.create_volunteer(
            session=session,
            user_in=user_create_data_factory(),
            volunteer_in=volunteer_create_data,
        )
        tracker.append(volunteer)
        tracker.append(volunteer.user)
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


def test_get_volunteers_list_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data_factory,
    volunteer_create_data: VolunteerCreate,
):
    """Benchmark retrieving a paginated list of volunteers with mission counts."""
    # Setup: Create some volunteers
    for _ in range(10):
        volunteer_service.create_volunteer(
            session=session,
            user_in=user_create_data_factory(),
            volunteer_in=volunteer_create_data,
        )
    session.flush()

    @benchmark
    def get_volunteers():
        session.expire_all()
        return volunteer_service.get_volunteers(session=session, limit=10)
