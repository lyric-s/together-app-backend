"""Tests for volunteer service CRUD operations. Generated and validated."""

from datetime import date, timedelta
import pytest
from sqlmodel import Session, select

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
    """
    Create a UserCreate prefilled with the test volunteer's credentials.

    Returns:
        UserCreate: Instance containing TEST_VOLUNTEER_USERNAME, TEST_VOLUNTEER_EMAIL, TEST_VOLUNTEER_PASSWORD, and UserType.VOLUNTEER.
    """
    return UserCreate(
        username=TEST_VOLUNTEER_USERNAME,
        email=TEST_VOLUNTEER_EMAIL,
        password=TEST_VOLUNTEER_PASSWORD,
        user_type=UserType.VOLUNTEER,
    )


@pytest.fixture(name="sample_volunteer_create")
def sample_volunteer_create_fixture():
    """
    Create a VolunteerCreate populated with standard test profile data.

    Returns:
        VolunteerCreate: Instance with predefined first_name, last_name, phone_number, birthdate, skills, and bio for use in tests.
    """
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
    """
    Create and persist a Volunteer using the provided user and volunteer creation data.

    Parameters:
        session (Session): Database session used to persist the created records.
        sample_user_create (UserCreate): User creation data for the volunteer's associated user.
        sample_volunteer_create (VolunteerCreate): Volunteer creation data (profile fields).

    Returns:
        Volunteer: The persisted Volunteer instance with its generated identifiers populated.
    """
    volunteer = volunteer_service.create_volunteer(
        session, sample_user_create, sample_volunteer_create
    )
    return volunteer


@pytest.fixture(name="mission_factory")
def mission_factory_fixture(session: Session):
    """
    Create a factory that builds and persists a Mission and its dependent records for tests.

    Returns:
        callable: A function with signature (date_start: date, date_end: date) -> Mission that creates and persists a Location, Category, Association (with its User), and a Mission, then returns the persisted Mission instance.
    """

    def _create_mission(date_start: date, date_end: date) -> Mission:
        """
        Create and persist a Mission and its required dependent records for use in tests.

        Parameters:
            date_start (date): Mission start date.
            date_end (date): Mission end date.

        Returns:
            Mission: The persisted Mission instance with database-generated identifiers.
        """
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
        """
        Check that retrieving a volunteer by its associated user ID returns the corresponding Volunteer.

        Uses the created_volunteer fixture and asserts the returned volunteer is present and has the same id_volunteer as the fixture.
        """
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
    @pytest.mark.asyncio
    async def test_delete_volunteer_success(
        self, session: Session, created_volunteer: Volunteer
    ):
        assert created_volunteer.id_volunteer is not None
        await volunteer_service.delete_volunteer(
            session, created_volunteer.id_volunteer
        )
        assert (
            volunteer_service.get_volunteer(session, created_volunteer.id_volunteer)
            is None
        )
        assert user_service.get_user(session, created_volunteer.id_user) is None

    @pytest.mark.asyncio
    async def test_delete_volunteer_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            await volunteer_service.delete_volunteer(session, NONEXISTENT_ID)


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

    def test_add_favorite_mission_volunteer_not_found(
        self, session: Session, mission_factory
    ):
        mission = mission_factory(date.today(), date.today())
        assert mission.id_mission is not None
        with pytest.raises(NotFoundError) as exc_info:
            volunteer_service.add_favorite_mission(
                session, NONEXISTENT_ID, mission.id_mission
            )
        assert exc_info.value.resource == "Volunteer"
        assert exc_info.value.identifier == NONEXISTENT_ID

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
        """
        Verifies that a volunteer's active and finished mission counts are computed correctly.

        Creates one mission that ends in the future and one mission that ended in the past, attaches an `APPROVED` engagement for the volunteer to each mission, calls `volunteer_service.to_volunteer_public`, and asserts `active_missions_count` and `finished_missions_count` are both 1.
        """
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


class TestGetVolunteers:
    def test_get_volunteers_batch_counts(
        self,
        session: Session,
        sample_user_create: UserCreate,
        sample_volunteer_create: VolunteerCreate,
        mission_factory,
    ):
        # Create 3 volunteers
        volunteers = []
        for i in range(3):
            # Unique user per volunteer
            u_create = sample_user_create.model_copy()
            u_create.username = f"vol_batch_{i}"
            u_create.email = f"vol_batch_{i}@example.com"

            # Unique volunteer info
            v_create = sample_volunteer_create.model_copy()
            v_create.first_name = f"Vol_{i}"

            vol = volunteer_service.create_volunteer(session, u_create, v_create)
            assert vol.id_volunteer is not None
            volunteers.append(vol)

        today = date.today()
        active_mission = mission_factory(today, today + timedelta(days=10))
        finished_mission = mission_factory(
            today - timedelta(days=10), today - timedelta(days=1)
        )

        # Vol 0: 1 active
        session.add(
            Engagement(
                id_volunteer=volunteers[0].id_volunteer,
                id_mission=active_mission.id_mission,
                state=ProcessingStatus.APPROVED,
            )
        )
        # Vol 1: 1 finished
        session.add(
            Engagement(
                id_volunteer=volunteers[1].id_volunteer,
                id_mission=finished_mission.id_mission,
                state=ProcessingStatus.APPROVED,
            )
        )
        # Vol 2: 1 active, 1 finished
        session.add(
            Engagement(
                id_volunteer=volunteers[2].id_volunteer,
                id_mission=active_mission.id_mission,
                state=ProcessingStatus.APPROVED,
            )
        )
        session.add(
            Engagement(
                id_volunteer=volunteers[2].id_volunteer,
                id_mission=finished_mission.id_mission,
                state=ProcessingStatus.APPROVED,
            )
        )
        session.commit()

        # Fetch all volunteers
        results = volunteer_service.get_volunteers(session)

        # Sort by ID to ensure order matches creation
        results.sort(key=lambda v: v.id_volunteer)

        # Filter to only the ones we created (in case other tests left data)
        our_results = [r for r in results if r.first_name.startswith("Vol_")]
        our_results.sort(key=lambda v: v.id_volunteer)

        assert len(our_results) == 3

        # Verify Vol 0 counts
        assert our_results[0].active_missions_count == 1
        assert our_results[0].finished_missions_count == 0

        # Verify Vol 1 counts
        assert our_results[1].active_missions_count == 0
        assert our_results[1].finished_missions_count == 1

        # Verify Vol 2 counts
        assert our_results[2].active_missions_count == 1
        assert our_results[2].finished_missions_count == 1


class TestApplyToMission:
    def test_apply_to_mission_success(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Successfully apply to a mission creates PENDING engagement."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        engagement = volunteer_service.apply_to_mission(
            session,
            created_volunteer.id_volunteer,
            mission.id_mission,
            "I'd love to help!",
        )

        assert engagement.id_volunteer == created_volunteer.id_volunteer
        assert engagement.id_mission == mission.id_mission
        assert engagement.state == ProcessingStatus.PENDING
        assert engagement.message == "I'd love to help!"
        assert engagement.application_date == date.today()

    def test_apply_to_mission_without_message(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Apply to mission without message succeeds."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        engagement = volunteer_service.apply_to_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )

        assert engagement.state == ProcessingStatus.PENDING
        assert engagement.message is None

    def test_apply_to_mission_volunteer_not_found(
        self, session: Session, mission_factory
    ):
        """Applying with non-existent volunteer raises NotFoundError."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert mission.id_mission is not None

        with pytest.raises(NotFoundError) as exc_info:
            volunteer_service.apply_to_mission(
                session, NONEXISTENT_ID, mission.id_mission
            )
        assert exc_info.value.resource == "Volunteer"

    def test_apply_to_mission_mission_not_found(
        self, session: Session, created_volunteer: Volunteer
    ):
        """Applying to non-existent mission raises NotFoundError."""
        assert created_volunteer.id_volunteer is not None

        with pytest.raises(NotFoundError) as exc_info:
            volunteer_service.apply_to_mission(
                session, created_volunteer.id_volunteer, NONEXISTENT_ID
            )
        assert exc_info.value.resource == "Mission"

    def test_apply_to_mission_already_applied(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Applying twice to same mission raises AlreadyExistsError."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        # First application succeeds
        volunteer_service.apply_to_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )

        # Second application fails
        with pytest.raises(AlreadyExistsError):
            volunteer_service.apply_to_mission(
                session, created_volunteer.id_volunteer, mission.id_mission
            )

    def test_apply_to_mission_with_approved_engagement(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Cannot apply if already has APPROVED engagement for mission."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        # Create APPROVED engagement
        engagement = Engagement(
            id_volunteer=created_volunteer.id_volunteer,
            id_mission=mission.id_mission,
            state=ProcessingStatus.APPROVED,
        )
        session.add(engagement)
        session.commit()

        # Try to apply again
        with pytest.raises(AlreadyExistsError):
            volunteer_service.apply_to_mission(
                session, created_volunteer.id_volunteer, mission.id_mission
            )


class TestWithdrawApplication:
    @pytest.mark.asyncio
    async def test_withdraw_application_success(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Successfully withdraw a PENDING application."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        # Create PENDING engagement
        volunteer_service.apply_to_mission(
            session, created_volunteer.id_volunteer, mission.id_mission
        )

        # Withdraw it
        await volunteer_service.withdraw_application(
            session, created_volunteer.id_volunteer, mission.id_mission
        )

        # Verify it's gone
        engagement = session.exec(
            select(Engagement).where(
                Engagement.id_volunteer == created_volunteer.id_volunteer,
                Engagement.id_mission == mission.id_mission,
            )
        ).first()
        assert engagement is None

    @pytest.mark.asyncio
    async def test_withdraw_application_not_found(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Withdrawing non-existent application raises NotFoundError."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        with pytest.raises(NotFoundError):
            await volunteer_service.withdraw_application(
                session, created_volunteer.id_volunteer, mission.id_mission
            )

    @pytest.mark.asyncio
    async def test_withdraw_application_approved_engagement(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Cannot withdraw APPROVED engagement."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        # Create APPROVED engagement
        engagement = Engagement(
            id_volunteer=created_volunteer.id_volunteer,
            id_mission=mission.id_mission,
            state=ProcessingStatus.APPROVED,
        )
        session.add(engagement)
        session.commit()

        # Try to withdraw
        with pytest.raises(NotFoundError):
            await volunteer_service.withdraw_application(
                session, created_volunteer.id_volunteer, mission.id_mission
            )

    @pytest.mark.asyncio
    async def test_withdraw_application_rejected_engagement(
        self, session: Session, created_volunteer: Volunteer, mission_factory
    ):
        """Cannot withdraw REJECTED engagement."""
        mission = mission_factory(date.today(), date.today() + timedelta(days=7))
        assert created_volunteer.id_volunteer is not None
        assert mission.id_mission is not None

        # Create REJECTED engagement
        engagement = Engagement(
            id_volunteer=created_volunteer.id_volunteer,
            id_mission=mission.id_mission,
            state=ProcessingStatus.REJECTED,
        )
        session.add(engagement)
        session.commit()

        # Try to withdraw
        with pytest.raises(NotFoundError):
            await volunteer_service.withdraw_application(
                session, created_volunteer.id_volunteer, mission.id_mission
            )
