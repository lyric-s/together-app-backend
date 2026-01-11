"Tests for mission service CRUD operations."

from datetime import date, timedelta
from unittest.mock import patch, AsyncMock
import pytest
from sqlmodel import Session

from app.models.mission import MissionCreate, MissionUpdate
from app.models.location import Location
from app.models.category import Category
from app.models.association import Association
from app.models.user import UserCreate
from app.models.enums import UserType, ProcessingStatus
from app.models.engagement import Engagement
from app.services import mission as mission_service
from app.services import user as user_service
from app.exceptions import NotFoundError, InsufficientPermissionsError

# Test data constants
TEST_MISSION_NAME = "Food Drive"
TEST_MISSION_SKILLS = "Driving, Packing"
TEST_MISSION_DESC = "Help distribute food."


@pytest.fixture(name="created_association")
def created_association_fixture(association_user):
    """Reuse association_user from conftest but return Association object for compatibility."""
    return association_user.association_profile


@pytest.fixture(name="sample_mission_create")
def sample_mission_create_fixture(
    created_association: Association,
    created_location: Location,
    created_category: Category,
) -> MissionCreate:
    assert created_category.id_categ is not None
    assert created_location.id_location is not None
    assert created_association.id_asso is not None
    return MissionCreate(
        name=TEST_MISSION_NAME,
        id_location=created_location.id_location,
        category_ids=[created_category.id_categ],
        id_asso=created_association.id_asso,
        date_start=date.today(),
        date_end=date.today() + timedelta(days=1),
        skills=TEST_MISSION_SKILLS,
        description=TEST_MISSION_DESC,
        capacity_min=1,
        capacity_max=5,
    )


class TestCreateMission:
    def test_create_mission_success(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None
        assert mission.name == TEST_MISSION_NAME
        assert mission.id_asso == sample_mission_create.id_asso
        assert len(mission.categories) == 1

    def test_create_mission_invalid_location(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        invalid_mission = sample_mission_create.model_copy()
        invalid_mission.id_location = 99999
        with pytest.raises(NotFoundError) as exc_info:
            mission_service.create_mission(session, invalid_mission)
        assert exc_info.value.resource == "Location"

    def test_create_mission_invalid_category(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        invalid_mission = sample_mission_create.model_copy()
        invalid_mission.category_ids = [99999]
        with pytest.raises(NotFoundError) as exc_info:
            mission_service.create_mission(session, invalid_mission)
        assert exc_info.value.resource == "Category"


class TestUpdateMission:
    def test_update_mission_success(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

        update_data = MissionUpdate(name="Updated Mission Name", capacity_max=10)
        updated_mission = mission_service.update_mission(
            session, mission.id_mission, update_data, association_id=mission.id_asso
        )

        assert updated_mission.name == "Updated Mission Name"
        assert updated_mission.capacity_max == 10
        # Check other fields remained unchanged
        assert updated_mission.skills == TEST_MISSION_SKILLS

    def test_update_mission_categories(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        """Test updating mission categories."""
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

        # Create a new category
        new_cat = Category(label="New Category")
        session.add(new_cat)
        session.commit()
        session.refresh(new_cat)
        assert new_cat.id_categ is not None

        update_data = MissionUpdate(category_ids=[new_cat.id_categ])
        updated_mission = mission_service.update_mission(
            session, mission.id_mission, update_data
        )

        assert len(updated_mission.categories) == 1
        assert updated_mission.categories[0].id_categ == new_cat.id_categ

    def test_update_mission_insufficient_permissions(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None
        assert mission.id_asso is not None

        update_data = MissionUpdate(name="Hacked Mission")
        wrong_association_id = mission.id_asso + 1

        with pytest.raises(InsufficientPermissionsError):
            mission_service.update_mission(
                session,
                mission.id_mission,
                update_data,
                association_id=wrong_association_id,
            )

        # Verify no change
        refetched = mission_service.get_mission(session, mission.id_mission)
        assert refetched is not None
        assert refetched.name == TEST_MISSION_NAME

    def test_update_mission_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            mission_service.update_mission(session, 99999, MissionUpdate(name="New"))


class TestDeleteMission:
    @pytest.mark.asyncio
    async def test_delete_mission_success(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert isinstance(mission.id_mission, int)
        with patch(
            "app.services.mission.send_notification_email", new_callable=AsyncMock
        ) as mock_email:
            await mission_service.delete_mission(
                session, mission.id_mission, association_id=mission.id_asso
            )
            # Association deletion shouldn't trigger emails to association (only to volunteers if any)
            # Since no volunteers, 0 calls
            assert mock_email.call_count == 0

        assert mission_service.get_mission(session, mission.id_mission) is None

    @pytest.mark.asyncio
    async def test_delete_mission_by_admin(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        """Test admin deletion triggers notification to association."""
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

        with (
            patch(
                "app.services.mission.send_notification_email", new_callable=AsyncMock
            ) as mock_email,
            patch(
                "app.services.notification.create_mission_deleted_notification"
            ) as mock_notif,
        ):
            # association_id=None implies admin
            await mission_service.delete_mission(
                session, mission.id_mission, association_id=None
            )

            # Should send email to association
            assert mock_email.call_count == 1
            assert (
                mock_email.call_args.kwargs["template_name"]
                == "mission_deleted_association"
            )
            mock_notif.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_mission_with_volunteers(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        """Test deletion notifies volunteers."""
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None
        assert mission.id_asso is not None

        # Create volunteer and engagement
        vol_user = user_service.create_user(
            session,
            UserCreate(
                username="vol_del",
                email="vol@del.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        from app.models.volunteer import Volunteer

        assert vol_user.id_user is not None
        vol_profile = Volunteer(
            id_user=vol_user.id_user,
            first_name="V",
            last_name="L",
            phone_number="123",
            birthdate=date(1990, 1, 1),
        )
        session.add(vol_profile)
        session.commit()
        assert vol_profile.id_volunteer is not None

        engagement = Engagement(
            id_mission=mission.id_mission,
            id_volunteer=vol_profile.id_volunteer,
            state=ProcessingStatus.APPROVED,
        )
        session.add(engagement)
        session.commit()

        with patch(
            "app.services.mission.send_notification_email", new_callable=AsyncMock
        ) as mock_email:
            await mission_service.delete_mission(
                session, mission.id_mission, association_id=mission.id_asso
            )

            # Should email volunteer
            assert mock_email.call_count == 1
            assert (
                mock_email.call_args.kwargs["template_name"]
                == "mission_deleted_volunteer"
            )

    @pytest.mark.asyncio
    async def test_delete_mission_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            await mission_service.delete_mission(session, 99999)

    @pytest.mark.asyncio
    async def test_delete_mission_insufficient_permissions(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        """Test that providing a mismatched association_id raises InsufficientPermissionsError."""
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None
        assert mission.id_asso is not None

        # Try to delete with a different association ID
        wrong_association_id = mission.id_asso + 1

        with pytest.raises(InsufficientPermissionsError):
            await mission_service.delete_mission(
                session,
                mission.id_mission,
                association_id=wrong_association_id,
            )

        # Verify mission was NOT deleted
        assert mission_service.get_mission(session, mission.id_mission) is not None


class TestSearchMissions:
    def test_search_missions_basic(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        m1 = mission_service.create_mission(session, sample_mission_create)
        assert m1.id_mission is not None

        # Create another mission
        m2_in = sample_mission_create.model_copy()
        m2_in.name = "Another Mission"
        m2_in.description = "Something else completely"
        _ = mission_service.create_mission(session, m2_in)

        # Search by text
        results = mission_service.search_missions(session, search="Food")
        assert len(results) == 1
        assert results[0].id_mission == m1.id_mission

        # Search all
        results_all = mission_service.search_missions(session)
        assert len(results_all) == 2

    def test_search_missions_filters(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        # Create mission with specific country
        # Note: sample_mission_create uses created_location which has country="France"
        _ = mission_service.create_mission(session, sample_mission_create)

        # Filter by country
        results = mission_service.search_missions(session, country="France")
        assert len(results) == 1

        results_none = mission_service.search_missions(session, country="Spain")
        assert len(results_none) == 0

        # Filter by zip
        results_zip = mission_service.search_missions(session, zip_code="75")
        assert len(results_zip) == 1


class TestToMissionPublic:
    def test_to_mission_public(
        self,
        session: Session,
        sample_mission_create: MissionCreate,
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

        # Add a volunteer
        vol_user = user_service.create_user(
            session,
            UserCreate(
                username="vol_pub",
                email="vol@pub.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        from app.models.volunteer import Volunteer

        assert vol_user.id_user is not None
        vol_profile = Volunteer(
            id_user=vol_user.id_user,
            first_name="V",
            last_name="L",
            phone_number="123",
            birthdate=date(1990, 1, 1),
        )
        session.add(vol_profile)
        session.commit()
        assert vol_profile.id_volunteer is not None

        engagement = Engagement(
            id_mission=mission.id_mission,
            id_volunteer=vol_profile.id_volunteer,
            state=ProcessingStatus.APPROVED,
        )
        session.add(engagement)
        session.commit()

        public_mission = mission_service.to_mission_public(session, mission)

        assert public_mission.volunteers_enrolled == 1
        assert public_mission.available_slots == 4  # max was 5
        assert public_mission.is_full is False
