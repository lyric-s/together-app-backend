"""Tests for volunteer service CRUD operations."""

from datetime import date, timedelta
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.volunteer import (
    Volunteer,
    VolunteerCreate,
    VolunteerUpdate,
)
from app.models.mission import Mission
from app.models.location import Location
from app.models.category import Category
from app.models.association import Association
from app.models.engagement import Engagement
from app.models.enums import UserType, ProcessingStatus
from app.services import volunteer as volunteer_service
from app.services import user as user_service
from app.exceptions import NotFoundError, AlreadyExistsError

# Test data constants
TEST_VOLUNTEER_USERNAME = "volunteer_user"
TEST_VOLUNTEER_EMAIL = "volunteer@example.com"
TEST_VOLUNTEER_PASSWORD = "Password123"
TEST_VOLUNTEER_FIRST_NAME = "John"
TEST_VOLUNTEER_LAST_NAME = "Doe"
TEST_VOLUNTEER_PHONE = "0123456789"
TEST_VOLUNTEER_BIRTHDATE = date(1990, 1, 1)

NONEXISTENT_ID = 99999


@pytest.fixture(name="sample_user_create")
def sample_user_create_fixture():
    return UserCreate(
        username=TEST_VOLUNTEER_USERNAME,
        email=TEST_VOLUNTEER_EMAIL,
        password=TEST_VOLUNTEER_PASSWORD,
        user_type=UserType.VOLUNTEER,
    )


@pytest.fixture(name="sample_volunteer_create")
def sample_volunteer_create_fixture():
    return VolunteerCreate(
        first_name=TEST_VOLUNTEER_FIRST_NAME,
        last_name=TEST_VOLUNTEER_LAST_NAME,
        phone_number=TEST_VOLUNTEER_PHONE,
        birthdate=TEST_VOLUNTEER_BIRTHDATE,
        skills="Python, SQL",
        bio="Enthusiastic volunteer",
    )


@pytest.fixture(name="created_volunteer")
def created_volunteer_fixture(
    session: Session,
    sample_user_create: UserCreate,
    sample_volunteer_create: VolunteerCreate,
) -> Volunteer:
    volunteer = volunteer_service.create_volunteer(
        session, sample_user_create, sample_volunteer_create
    )
    return volunteer


@pytest.fixture(name="mission_factory")
def mission_factory_fixture(session: Session):
    def _create_mission(date_start: date, date_end: date) -> Mission:
        # Create dependencies if they don't exist (simplification for tests)
        location = Location(address="123 St", country="France", zip_code="75001")
        session.add(location)

        category = Category(label="Environment")
        session.add(category)

        # Association requires a user
        asso_user = user_service.create_user(
            session,
            UserCreate(
                username=f"asso_{date_start}",
                email=f"asso_{date_start}@example.com",
                password="SecurePass123",
                user_type=UserType.ASSOCIATION,
            ),
        )
        association = Association(
            name="Asso",
            address="456 Av",
            country="France",
            phone_number="0101010101",
            zip_code="75002",
            rna_code=f"W123_{date_start}",
            company_name="Asso Corp",
            id_user=asso_user.id_user,
        )
        session.add(association)
        session.commit()

        mission = Mission(
            name="Test Mission",
            id_location=location.id_location,
            id_categ=category.id_categ,
            id_asso=association.id_asso,
            date_start=date_start,
            date_end=date_end,
            skills="None",
            description="Desc",
            capacity_min=1,
            capacity_max=5,
        )
        session.add(mission)
        session.commit()
        return mission

    return _create_mission


class TestCreateVolunteer:
    def test_create_volunteer_success(self, created_volunteer: Volunteer):
        assert created_volunteer.id_volunteer is not None
        assert created_volunteer.first_name == TEST_VOLUNTEER_FIRST_NAME
        assert created_volunteer.user.username == TEST_VOLUNTEER_USERNAME
        assert created_volunteer.user.user_type == UserType.VOLUNTEER

    def test_create_volunteer_duplicate_user(
        self,
        session: Session,
        sample_user_create: UserCreate,
        sample_volunteer_create: VolunteerCreate,
    ):
        volunteer_service.create_volunteer(
            session, sample_user_create, sample_volunteer_create
        )
        with pytest.raises(AlreadyExistsError):
            volunteer_service.create_volunteer(
                session, sample_user_create, sample_volunteer_create
            )


class TestGetVolunteer:
    def test_get_volunteer_by_id(self, session: Session, created_volunteer: Volunteer):
        assert created_volunteer.id_volunteer is not None
        fetched = volunteer_service.get_volunteer(
            session, created_volunteer.id_volunteer
        )
        assert fetched is not None
        assert fetched.id_volunteer == created_volunteer.id_volunteer
        assert fetched.user.email == TEST_VOLUNTEER_EMAIL

    def test_get_volunteer_by_user_id(
        self, session: Session, created_volunteer: Volunteer
    ):
        fetched = volunteer_service.get_volunteer_by_user_id(
            session, created_volunteer.id_user
        )
        assert fetched is not None
        assert fetched.id_volunteer == created_volunteer.id_volunteer

    def test_get_volunteer_not_found(self, session: Session):
        assert volunteer_service.get_volunteer(session, NONEXISTENT_ID) is None


class TestUpdateVolunteer:
    def test_update_volunteer_profile(
        self, session: Session, created_volunteer: Volunteer
    ):
        assert created_volunteer.id_volunteer is not None
        update_data = VolunteerUpdate(first_name="Jane", bio="Updated bio")
        updated = volunteer_service.update_volunteer(
            session, created_volunteer.id_volunteer, update_data
        )
        assert updated.first_name == "Jane"
        assert updated.bio == "Updated bio"
        assert updated.last_name == TEST_VOLUNTEER_LAST_NAME  # Unchanged

    def test_update_volunteer_user_info(
        self, session: Session, created_volunteer: Volunteer
    ):
        assert created_volunteer.id_volunteer is not None
        new_email = "new_volunteer@example.com"
        update_data = VolunteerUpdate(email=new_email)
        updated = volunteer_service.update_volunteer(
            session, created_volunteer.id_volunteer, update_data
        )
        assert updated.user.email == new_email

    def test_update_volunteer_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            volunteer_service.update_volunteer(
                session, NONEXISTENT_ID, VolunteerUpdate(first_name="Jane")
            )


class TestDeleteVolunteer:
    def test_delete_volunteer_success(
        self, session: Session, created_volunteer: Volunteer
    ):
        assert created_volunteer.id_volunteer is not None
        volunteer_service.delete_volunteer(session, created_volunteer.id_volunteer)
        assert (
            volunteer_service.get_volunteer(session, created_volunteer.id_volunteer)
            is None
        )
        assert user_service.get_user(session, created_volunteer.id_user) is None

    def test_delete_volunteer_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            volunteer_service.delete_volunteer(session, NONEXISTENT_ID)


class TestFavoriteMissions:
    def test_add_favorite_mission(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        mission = mission_factory(date.today(), date.today())
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None
        volunteer_service.add_favorite_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )
        favorites = volunteer_service.get_favorite_missions(
            session, created_volunteer.id_volunteer
        )
        assert len(favorites) == 1
        assert favorites[0].id_mission == mission.id_mission

    def test_add_favorite_mission_already_exists(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        mission = mission_factory(date.today(), date.today())
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None
        volunteer_service.add_favorite_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )
        with pytest.raises(AlreadyExistsError):
            volunteer_service.add_favorite_mission(
                session, created_volunteer.id_volunteer, mission.id_mission
            )

    def test_remove_favorite_mission(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        mission = mission_factory(date.today(), date.today())
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None
        volunteer_service.add_favorite_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )
        volunteer_service.remove_favorite_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )
        favorites = volunteer_service.get_favorite_missions(
            session, created_volunteer.id_volunteer
        )
        assert len(favorites) == 0


class TestVolunteerMissionCounts:
    def test_mission_counts(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        today = date.today()
        # Active mission (ends in future)
        active_mission = mission_factory(today, today + timedelta(days=10))
        # Finished mission (ended yesterday)
        finished_mission = mission_factory(
            today - timedelta(days=10), today - timedelta(days=1)
        )

        assert created_volunteer.id_volunteer is not None
        assert active_mission.id_mission is not None
        assert finished_mission.id_mission is not None

        # Create engagements
        eng_active = Engagement(
            id_volunteer=created_volunteer.id_volunteer,
            id_mission=active_mission.id_mission,
            state=ProcessingStatus.APPROVED,
        )
        eng_finished = Engagement(
            id_volunteer=created_volunteer.id_volunteer,
            id_mission=finished_mission.id_mission,
            state=ProcessingStatus.APPROVED,
        )
        session.add(eng_active)
        session.add(eng_finished)
        session.commit()

        # Check counts via to_volunteer_public helper
        public_vol = volunteer_service.to_volunteer_public(session, created_volunteer)
        assert public_vol.active_missions_count == 1
        assert public_vol.finished_missions_count == 1
