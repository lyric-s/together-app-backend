"""Performance benchmarks for volunteer service operations."""

import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.volunteer import VolunteerCreate
from app.models.enums import UserType
from app.services import volunteer as volunteer_service


@pytest.fixture(name="user_create_data")
def user_create_data_fixture():
    """Provide test data for user creation."""
    return UserCreate(
        username="bench_volunteer",
        email="bench_vol@example.com",
        password="VolPass123",
        user_type=UserType.VOLUNTEER,
    )


@pytest.fixture(name="volunteer_create_data")
def volunteer_create_data_fixture():
    """Provide test data for volunteer creation."""
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
    """Benchmark volunteer creation operation."""

    @benchmark
    def create_volunteer():
        volunteer = volunteer_service.create_volunteer(
            session=session,
            user_in=user_create_data,
            volunteer_in=volunteer_create_data,
        )
        # Clean up after each iteration
        session.delete(volunteer.user)
        session.delete(volunteer)
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
        return volunteer_service.get_volunteer(
            session=session, volunteer_id=volunteer_id
        )
