"""Shared fixtures for service tests."""

from datetime import date
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.enums import UserType
from app.models.location import Location, LocationCreate
from app.models.category import Category, CategoryCreate
from app.models.association import Association
from app.models.volunteer import Volunteer
from app.services import user as user_service
from app.services import location as location_service
from app.services import category as category_service


# Session fixture is inherited from root conftest.py


@pytest.fixture(name="created_location")
def created_location_fixture(session: Session) -> Location:
    """Create a generic test location."""
    return location_service.create_location(
        session,
        LocationCreate(address="Generic Loc", country="France", zip_code="75000"),
    )


@pytest.fixture(name="created_category")
def created_category_fixture(session: Session) -> Category:
    """Create a generic test category."""
    return category_service.create_category(
        session, CategoryCreate(label="Generic Category")
    )


@pytest.fixture(name="volunteer_user")
def volunteer_user_fixture(session: Session):
    """Create a volunteer user with profile."""
    user_create = UserCreate(
        username="gen_vol",
        email="gen_vol@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_create)

    volunteer = Volunteer(
        id_user=user.id_user,
        first_name="General",
        last_name="Volunteer",
        phone_number="0123456789",
        birthdate=date(1990, 1, 1),
    )
    session.add(volunteer)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="association_user")
def association_user_fixture(session: Session):
    """Create an association user with profile."""
    user_create = UserCreate(
        username="gen_asso",
        email="gen_asso@example.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_create)

    association = Association(
        id_user=user.id_user,
        name="General Association",
        rna_code="W123456789",
        company_name="General Corp",
        phone_number="0987654321",
        address="123 Gen St",
        zip_code="75000",
        country="France",
    )
    session.add(association)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="reporter_user")
def reporter_user_fixture(session: Session):
    """Create a generic user to act as a reporter."""
    user_create = UserCreate(
        username="gen_reporter",
        email="reporter@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_create)
    session.commit()
    session.refresh(user)
    return user
