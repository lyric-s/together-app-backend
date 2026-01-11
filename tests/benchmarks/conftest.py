"""Shared fixtures for benchmark tests."""

import uuid
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.enums import UserType


# Session fixture is inherited from root conftest.py


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


@pytest.fixture(name="admin_create_data_factory")
def admin_create_data_factory_fixture():
    """Factory for unique AdminCreate payloads."""
    from app.models.admin import AdminCreate

    def create():
        unique = uuid.uuid4().hex[:8]
        return AdminCreate(
            username=f"bench_admin_{unique}",
            email=f"admin_{unique}@example.com",
            password="AdminPass123",
            first_name="Bench",
            last_name="Admin",
        )

    return create


@pytest.fixture(name="association_create_data_factory")
def association_create_data_factory_fixture():
    """Factory for unique AssociationCreate payloads."""
    from app.models.association import AssociationCreate
    import random

    def create():
        unique = uuid.uuid4().hex[:8]
        # RNA must be W followed by 9 digits
        digits = "".join([str(random.randint(0, 9)) for _ in range(9)])
        return AssociationCreate(
            name=f"Bench Association {unique}",
            rna_code=f"W{digits}",
            company_name=f"Bench Corp {unique}",
            phone_number="+33123456789",
            address="123 Bench St",
            zip_code="75000",
            country="France",
        )

    return create


@pytest.fixture(name="location_create_data_factory")
def location_create_data_factory_fixture():
    """Factory for unique LocationCreate payloads."""
    from app.models.location import LocationCreate

    def create():
        unique = uuid.uuid4().hex[:8]
        return LocationCreate(
            address=f"{unique} Bench St",
            zip_code="75000",
            city="Paris",
            country="France",
        )

    return create


@pytest.fixture(name="category_create_data_factory")
def category_create_data_factory_fixture():
    """Factory for unique CategoryCreate payloads."""
    from app.models.category import CategoryCreate

    def create():
        unique = uuid.uuid4().hex[:8]
        return CategoryCreate(label=f"Category {unique}")

    return create


@pytest.fixture(name="volunteer_create_data")
def volunteer_create_data_fixture():
    """Fixture that supplies a populated VolunteerCreate instance."""
    from datetime import date
    from app.models.volunteer import VolunteerCreate

    return VolunteerCreate(
        last_name="Benchmark",
        first_name="Volunteer",
        phone_number="+33123456789",
        birthdate=date(1990, 1, 1),
        skills="Python, FastAPI, Testing",
        bio="Benchmark volunteer bio",
    )


@pytest.fixture
def tracker(session: Session):
    """
    Provide a list-based tracker for cleaning up objects created during benchmarks.
    Objects in the list will be deleted from the session after the test completes.
    """
    objects = []
    yield objects
    for obj in objects:
        try:
            session.delete(obj)
        except Exception:
            pass
    session.commit()
