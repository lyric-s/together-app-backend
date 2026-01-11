"""Tests for location service operations."""

from datetime import date, timedelta
import pytest
from sqlmodel import Session

from app.models.location import Location, LocationCreate, LocationUpdate
from app.models.mission import MissionCreate
from app.models.category import Category
from app.models.association import Association
from app.models.user import UserCreate
from app.models.enums import UserType
from app.services import location as location_service
from app.services import mission as mission_service
from app.services import user as user_service
from app.exceptions import NotFoundError, ValidationError

# Test data constants
TEST_ADDRESS = "123 Test St"
TEST_CITY = "Test City"
TEST_COUNTRY = "Testland"
TEST_ZIP = "12345"


@pytest.fixture(name="sample_location_create")
def sample_location_create_fixture():
    return LocationCreate(
        address=TEST_ADDRESS, country=TEST_COUNTRY, zip_code=TEST_ZIP, city=TEST_CITY
    )


@pytest.fixture(name="created_location")
def created_location_fixture(session: Session, sample_location_create: LocationCreate):
    location = location_service.create_location(session, sample_location_create)
    return location


@pytest.fixture(name="location_factory")
def location_factory_fixture(session: Session):
    def _create_location(index: int = 0):
        loc = LocationCreate(
            address=f"{index} Test St",
            country=TEST_COUNTRY,
            zip_code=f"1000{index}",
            city=TEST_CITY,
        )
        return location_service.create_location(session, loc)

    return _create_location


# Fixtures for Mission creation (needed for delete/count tests)
@pytest.fixture(name="association_user")
def association_user_fixture(session: Session):
    user_create = UserCreate(
        username="loc_test_asso",
        email="loc_test@example.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_create)

    association = Association(
        id_user=user.id_user,
        name="Loc Test Asso",
        rna_code="W111111111",
        phone_number="0123456789",
        address="Address",
        zip_code="00000",
        country="France",
        company_name="Loc Corp",
    )
    session.add(association)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="created_category")
def created_category_fixture(session: Session):
    category = Category(label="LocCategory")
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


class TestCreateLocation:
    def test_create_location_success(self, created_location: Location):
        assert created_location.id_location is not None
        assert created_location.address == TEST_ADDRESS
        assert created_location.country == TEST_COUNTRY


class TestGetLocation:
    def test_get_location_success(self, session: Session, created_location: Location):
        assert created_location.id_location is not None
        loc = location_service.get_location(session, created_location.id_location)
        assert loc is not None
        assert loc.id_location == created_location.id_location

    def test_get_location_not_found(self, session: Session):
        loc = location_service.get_location(session, 99999)
        assert loc is None

    def test_get_locations_pagination(self, session: Session, location_factory):
        for i in range(5):
            location_factory(i)

        locations = location_service.get_locations(session, limit=3)
        assert len(locations) == 3

        locations_offset = location_service.get_locations(session, offset=3, limit=3)
        assert len(locations_offset) == 2


class TestUpdateLocation:
    def test_update_location_success(
        self, session: Session, created_location: Location
    ):
        assert created_location.id_location is not None
        update_data = LocationUpdate(address="Updated Address")
        updated = location_service.update_location(
            session, created_location.id_location, update_data
        )
        assert updated.address == "Updated Address"
        # Check persistence
        refetched = location_service.get_location(session, created_location.id_location)
        assert refetched is not None
        assert refetched.address == "Updated Address"

    def test_update_location_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            location_service.update_location(
                session, 99999, LocationUpdate(address="New")
            )


class TestDeleteLocation:
    def test_delete_location_success(
        self, session: Session, created_location: Location
    ):
        assert created_location.id_location is not None
        location_service.delete_location(session, created_location.id_location)
        assert (
            location_service.get_location(session, created_location.id_location) is None
        )

    def test_delete_location_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            location_service.delete_location(session, 99999)

    def test_delete_location_with_existing_mission(
        self,
        session: Session,
        created_location: Location,
        association_user,
        created_category,
    ):
        assert created_location.id_location is not None
        assert created_category.id_categ is not None
        # Create a mission using this location
        mission_in = MissionCreate(
            name="Loc Mission",
            id_location=created_location.id_location,
            category_ids=[created_category.id_categ],
            id_asso=association_user.association_profile.id_asso,
            date_start=date.today(),
            date_end=date.today() + timedelta(days=1),
            skills="Skills",
            description="Desc",
            capacity_min=1,
            capacity_max=5,
        )
        mission_service.create_mission(session, mission_in)

        # Try to delete location
        with pytest.raises(ValidationError) as exc:
            location_service.delete_location(session, created_location.id_location)

        assert "mission(s) still reference it" in str(exc.value)


class TestLocationCounts:
    def test_get_location_with_mission_count(
        self,
        session: Session,
        created_location: Location,
        association_user,
        created_category,
    ):
        assert created_location.id_location is not None
        assert created_category.id_categ is not None
        # Create 2 missions for this location
        for i in range(2):
            mission_in = MissionCreate(
                name=f"Mission {i}",
                id_location=created_location.id_location,
                category_ids=[created_category.id_categ],
                id_asso=association_user.association_profile.id_asso,
                date_start=date.today(),
                date_end=date.today() + timedelta(days=1),
                skills="Skills",
                description="Desc",
                capacity_min=1,
                capacity_max=5,
            )
            mission_service.create_mission(session, mission_in)

        result = location_service.get_location_with_mission_count(
            session, created_location.id_location
        )
        assert result["mission_count"] == 2
        assert result["id_location"] == created_location.id_location

    def test_get_all_locations_with_counts(
        self,
        session: Session,
        created_location: Location,
        association_user,
        created_category,
    ):
        assert created_location.id_location is not None
        assert created_category.id_categ is not None
        # Create a mission for the location
        mission_in = MissionCreate(
            name="Mission",
            id_location=created_location.id_location,
            category_ids=[created_category.id_categ],
            id_asso=association_user.association_profile.id_asso,
            date_start=date.today(),
            date_end=date.today() + timedelta(days=1),
            skills="Skills",
            description="Desc",
            capacity_min=1,
            capacity_max=5,
        )
        mission_service.create_mission(session, mission_in)

        # Create another location with no missions
        loc2 = location_service.create_location(
            session, LocationCreate(address="Loc 2", country="FR", zip_code="000")
        )
        assert loc2.id_location is not None

        results = location_service.get_all_locations_with_counts(session)

        loc1_res = next(
            r for r in results if r["id_location"] == created_location.id_location
        )
        loc2_res = next(r for r in results if r["id_location"] == loc2.id_location)

        assert loc1_res["mission_count"] == 1
        assert loc2_res["mission_count"] == 0
