"""Tests for volunteer router endpoints."""

from datetime import date
import pytest
from sqlmodel import Session
from fastapi.testclient import TestClient

from app.models.user import UserCreate
from app.models.enums import UserType, ProcessingStatus
from app.services import user as user_service
from app.models.volunteer import Volunteer
from app.models.association import Association
from app.models.mission import Mission
from app.models.location import Location
from app.models.engagement import Engagement
from app.core.security import create_access_token

# Test constants
VOLUNTEER_USERNAME = "vol_user"
VOLUNTEER_EMAIL = "vol@example.com"
VOLUNTEER_PASSWORD = "Password123"
VOLUNTEER_FIRST_NAME = "Volunteer"
VOLUNTEER_LAST_NAME = "Test"

ASSO_USERNAME = "asso_user"
ASSO_EMAIL = "asso@example.com"
ASSO_PASSWORD = "Password123"


@pytest.fixture(name="test_volunteer")
def test_volunteer_fixture(session: Session):
    """Create a volunteer user with profile."""
    user_in = UserCreate(
        username=VOLUNTEER_USERNAME,
        email=VOLUNTEER_EMAIL,
        password=VOLUNTEER_PASSWORD,
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_in)
    vol = Volunteer(
        id_user=user.id_user,
        first_name=VOLUNTEER_FIRST_NAME,
        last_name=VOLUNTEER_LAST_NAME,
        phone_number="1234567890",
        birthdate=date(1990, 1, 1),
    )
    session.add(vol)
    session.commit()
    session.refresh(vol)
    return vol


@pytest.fixture(name="vol_token")
def vol_token_fixture(test_volunteer):
    """Generate valid JWT token for test_volunteer."""
    # Note: test_volunteer is the Volunteer model, we need the user's username
    # In a real scenario we'd query the user, but we know it from setup
    return create_access_token(data={"sub": VOLUNTEER_USERNAME})


@pytest.fixture(name="test_mission")
def test_mission_fixture(session: Session):
    """Create a mission with location and association."""
    # Setup location
    loc = Location(address="Test Street", country="France", zip_code="75000")
    session.add(loc)

    # Setup association
    u_asso = user_service.create_user(
        session,
        UserCreate(
            username=ASSO_USERNAME,
            email=ASSO_EMAIL,
            password=ASSO_PASSWORD,
            user_type=UserType.ASSOCIATION,
        ),
    )
    asso = Association(
        id_user=u_asso.id_user,
        name="Test Association",
        rna_code="W123456789",
        company_name="Test Corp",
        phone_number="0102030405",
        address="Asso Street",
        zip_code="75001",
        country="France",
    )
    session.add(asso)
    session.commit()

    # Create mission
    mission = Mission(
        name="Test Mission",
        id_location=loc.id_location,
        id_asso=asso.id_asso,
        date_start=date.today(),
        date_end=date.today(),
        skills="Testing",
        description="Mission for testing",
        capacity_min=1,
        capacity_max=10,
    )
    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


class TestVolunteerProfile:
    """Test volunteer profile management endpoints."""

    def test_read_volunteer_profile_me(
        self, client: TestClient, test_volunteer, vol_token
    ):
        """Retrieve authenticated volunteer's own profile."""
        response = client.get(
            "/volunteers/me", headers={"Authorization": f"Bearer {vol_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == VOLUNTEER_FIRST_NAME
        assert data["user"]["username"] == VOLUNTEER_USERNAME
        assert data["user"]["email"] == VOLUNTEER_EMAIL

    def test_update_volunteer_profile(
        self, session: Session, client: TestClient, test_volunteer, vol_token
    ):
        """Update authenticated volunteer's profile fields."""
        update_data = {"first_name": "UpdatedName", "email": "updated@example.com"}

        response = client.patch(
            f"/volunteers/{test_volunteer.id_volunteer}",
            headers={"Authorization": f"Bearer {vol_token}"},
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "UpdatedName"
        assert data["user"]["email"] == "updated@example.com"

        # Verify database persistence
        session.expire_all()
        # Re-fetch from DB
        from app.models.user import User

        user = session.get(User, test_volunteer.id_user)
        vol = session.get(Volunteer, test_volunteer.id_volunteer)
        assert user is not None
        assert vol is not None
        assert user.email == "updated@example.com"
        assert vol.first_name == "UpdatedName"


class TestVolunteerMissions:
    """Test volunteer mission engagement endpoints."""

    def test_get_volunteer_missions(
        self,
        session: Session,
        client: TestClient,
        test_volunteer,
        test_mission,
        vol_token,
    ):
        """List missions where the volunteer is engaged."""
        # Create approved engagement
        eng = Engagement(
            id_volunteer=test_volunteer.id_volunteer,
            id_mission=test_mission.id_mission,
            state=ProcessingStatus.APPROVED,
        )
        session.add(eng)
        session.commit()

        response = client.get(
            "/volunteers/me/missions", headers={"Authorization": f"Bearer {vol_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id_mission"] == test_mission.id_mission
        assert data[0]["name"] == test_mission.name


class TestFavoriteMissions:
    """Test volunteer favorite mission management endpoints."""

    def test_favorite_mission_lifecycle(
        self, client: TestClient, test_volunteer, test_mission, vol_token
    ):
        """Add, list, and remove a mission from favorites."""
        # 1. Add to favorites
        add_res = client.post(
            f"/volunteers/me/favorites/{test_mission.id_mission}",
            headers={"Authorization": f"Bearer {vol_token}"},
        )
        assert add_res.status_code == 201

        # 2. List favorites
        list_res = client.get(
            "/volunteers/me/favorites", headers={"Authorization": f"Bearer {vol_token}"}
        )
        assert list_res.status_code == 200
        data = list_res.json()
        assert len(data) == 1
        assert data[0]["id_mission"] == test_mission.id_mission
        assert data[0]["name"] == test_mission.name

        # 3. Remove from favorites
        rem_res = client.delete(
            f"/volunteers/me/favorites/{test_mission.id_mission}",
            headers={"Authorization": f"Bearer {vol_token}"},
        )
        assert rem_res.status_code == 204

        # 4. Verify list is empty
        final_res = client.get(
            "/volunteers/me/favorites", headers={"Authorization": f"Bearer {vol_token}"}
        )
        assert final_res.json() == []
