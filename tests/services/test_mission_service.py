"""Tests for mission service CRUD operations."""

from datetime import date, timedelta
import pytest
from sqlmodel import Session

from app.models.mission import MissionCreate, MissionUpdate
from app.models.location import Location
from app.models.category import Category
from app.models.association import Association
from app.models.user import UserCreate
from app.models.enums import UserType
from app.services import mission as mission_service
from app.services import user as user_service
from app.exceptions import NotFoundError, InsufficientPermissionsError

# Test data constants
TEST_MISSION_NAME = "Food Drive"
TEST_MISSION_SKILLS = "Driving, Packing"
TEST_MISSION_DESC = "Help distribute food."


@pytest.fixture(name="created_association")
def created_association_fixture(session: Session) -> Association:
    user = user_service.create_user(
        session,
        UserCreate(
            username="asso_mission_test",
            email="asso_mission@example.com",
            password="Password123",
            user_type=UserType.ASSOCIATION,
        ),
    )
    association = Association(
        name="Mission Test Asso",
        address="123 St",
        country="France",
        phone_number="0102030405",
        zip_code="75001",
        rna_code="W123456789",
        company_name="Mission Test Corp",
        id_user=user.id_user,
    )
    session.add(association)
    session.commit()
    session.refresh(association)
    return association


@pytest.fixture(name="created_location")
def created_location_fixture(session: Session) -> Location:
    location = Location(address="Mission Loc", country="France", zip_code="75002")
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


@pytest.fixture(name="created_category")
def created_category_fixture(session: Session) -> Category:
    category = Category(label="Social")
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@pytest.fixture(name="sample_mission_create")
def sample_mission_create_fixture(
    created_association: Association,
    created_location: Location,
    created_category: Category,
) -> MissionCreate:
    return MissionCreate(
        name=TEST_MISSION_NAME,
        id_location=created_location.id_location,
        id_categ=created_category.id_categ,
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
        self, session: Session, sample_mission_create: MissionCreate
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None
        assert mission.name == TEST_MISSION_NAME
        assert mission.id_asso == sample_mission_create.id_asso

    def test_create_mission_invalid_location(
        self, session: Session, sample_mission_create: MissionCreate
    ):
        invalid_mission = sample_mission_create.model_copy()
        invalid_mission.id_location = 99999
        with pytest.raises(NotFoundError) as exc_info:
            mission_service.create_mission(session, invalid_mission)
        assert exc_info.value.resource == "Location"

    def test_create_mission_invalid_category(
        self, session: Session, sample_mission_create: MissionCreate
    ):
        invalid_mission = sample_mission_create.model_copy()
        invalid_mission.id_categ = 99999
        with pytest.raises(NotFoundError) as exc_info:
            mission_service.create_mission(session, invalid_mission)
        assert exc_info.value.resource == "Category"


class TestUpdateMission:
    def test_update_mission_success(
        self, session: Session, sample_mission_create: MissionCreate
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

    def test_update_mission_insufficient_permissions(
        self, session: Session, sample_mission_create: MissionCreate
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

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
    def test_delete_mission_success(
        self, session: Session, sample_mission_create: MissionCreate
    ):
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

        mission_service.delete_mission(session, mission.id_mission)

        assert mission_service.get_mission(session, mission.id_mission) is None

    def test_delete_mission_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            mission_service.delete_mission(session, 99999)

    def test_delete_mission_insufficient_permissions(
        self, session: Session, sample_mission_create: MissionCreate
    ):
        """Test that providing a mismatched association_id raises InsufficientPermissionsError."""
        mission = mission_service.create_mission(session, sample_mission_create)
        assert mission.id_mission is not None

        # Try to delete with a different association ID
        wrong_association_id = mission.id_asso + 1

        with pytest.raises(InsufficientPermissionsError):
            mission_service.delete_mission(
                session, mission.id_mission, association_id=wrong_association_id
            )

        # Verify mission was NOT deleted
        assert mission_service.get_mission(session, mission.id_mission) is not None

        # Now delete correctly to clean up (optional in test but good practice)
        mission_service.delete_mission(
            session, mission.id_mission, association_id=mission.id_asso
        )
        assert mission_service.get_mission(session, mission.id_mission) is None


class TestGetMissionsByAssociation:
    def test_get_missions_by_association(
        self, session: Session, sample_mission_create: MissionCreate
    ):
        """Test retrieving missions for a specific association."""
        # Create first mission
        mission1 = mission_service.create_mission(session, sample_mission_create)

        # Create second mission for same association
        mission2_data = sample_mission_create.model_copy()
        mission2_data.name = "Second Mission"
        mission2 = mission_service.create_mission(session, mission2_data)

        # Retrieve missions
        missions = mission_service.get_missions_by_association(
            session, sample_mission_create.id_asso
        )

        assert len(missions) == 2
        mission_ids = [m.id_mission for m in missions]
        assert mission1.id_mission in mission_ids
        assert mission2.id_mission in mission_ids

    def test_get_missions_by_association_empty(self, session: Session):
        """Test retrieving missions for an association with no missions."""
        missions = mission_service.get_missions_by_association(session, 99999)
        assert missions == []
