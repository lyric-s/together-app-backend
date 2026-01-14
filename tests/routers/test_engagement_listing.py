"""Tests for engagement listing endpoint."""

from datetime import date
import pytest
from sqlmodel import Session
from fastapi.testclient import TestClient

from app.models.user import UserCreate
from app.models.enums import UserType, ProcessingStatus
from app.services import user as user_service
from app.models.association import Association
from app.models.volunteer import Volunteer
from app.models.mission import Mission
from app.models.location import Location
from app.models.engagement import Engagement


@pytest.fixture
def test_asso(session: Session):
    """Create a verified association for testing."""
    user_in = UserCreate(
        username="test_asso",
        email="test@asso.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_in)
    asso = Association(
        id_user=user.id_user,
        name="Test Association",
        rna_code="W123456789",
        company_name="Test Corp",
        phone_number="0102030405",
        address="Test Address",
        zip_code="75000",
        country="France",
        verification_status=ProcessingStatus.APPROVED,
    )
    session.add(asso)
    session.commit()
    session.refresh(asso)
    return asso


@pytest.fixture
def asso_token(test_asso):
    """Generate valid JWT token for test_asso."""
    from app.core.security import create_access_token

    return create_access_token(data={"sub": "test_asso"})


@pytest.fixture
def setup_mission(session: Session, test_asso):
    """Create a mission with location for testing."""
    location = Location(
        address="123 Test St", zip_code="75001", city="Paris", country="France"
    )
    session.add(location)
    session.commit()
    session.refresh(location)

    mission = Mission(
        id_asso=test_asso.id_asso,
        name="Test Mission",
        description="Test description for mission",
        date_start=date(2026, 2, 1),
        date_end=date(2026, 2, 1),
        skills="Python, SQL",
        capacity_min=5,
        capacity_max=10,
        id_location=location.id_location,
    )
    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


def create_volunteer_with_engagement(
    session: Session,
    mission_id: int,
    username: str,
    status: ProcessingStatus = ProcessingStatus.PENDING,
    application_date: date | None = None,
):
    """Helper to create a volunteer with an engagement."""
    user_in = UserCreate(
        username=username,
        email=f"{username}@test.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_in)
    volunteer = Volunteer(
        id_user=user.id_user,
        first_name=username.capitalize(),
        last_name="Test",
        phone_number="0601020304",
        birthdate=date(1995, 1, 1),
        skills="Python, Testing",
    )
    session.add(volunteer)
    session.commit()
    session.refresh(volunteer)

    engagement = Engagement(
        id_volunteer=volunteer.id_volunteer,
        id_mission=mission_id,
        state=status,
        message=f"Application from {username}",
        application_date=application_date or date.today(),
    )
    session.add(engagement)
    session.commit()
    return volunteer


class TestEngagementListing:
    """Test engagement listing endpoint for associations."""

    def test_get_mission_engagements_success(
        self, client: TestClient, session: Session, test_asso, asso_token, setup_mission
    ):
        """Test successful retrieval of all engagements for a mission."""
        mission = setup_mission

        # Create 2 volunteers with engagements
        create_volunteer_with_engagement(session, mission.id_mission, "alice")
        create_volunteer_with_engagement(session, mission.id_mission, "bob")

        # Test endpoint
        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["volunteer_first_name"] in ["Alice", "Bob"]
        assert data[0]["volunteer_email"] in ["alice@test.com", "bob@test.com"]
        assert data[0]["state"] == ProcessingStatus.PENDING.value
        assert "volunteer_phone" in data[0]
        assert "volunteer_skills" in data[0]

    def test_get_mission_engagements_filter_by_status(
        self, client: TestClient, session: Session, test_asso, asso_token, setup_mission
    ):
        """Test filtering engagements by status."""
        mission = setup_mission

        # Create volunteers with different statuses
        create_volunteer_with_engagement(
            session, mission.id_mission, "pending_vol", ProcessingStatus.PENDING
        )
        create_volunteer_with_engagement(
            session, mission.id_mission, "approved_vol", ProcessingStatus.APPROVED
        )
        create_volunteer_with_engagement(
            session, mission.id_mission, "rejected_vol", ProcessingStatus.REJECTED
        )

        # Test filter by PENDING
        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements?status=PENDING",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["state"] == ProcessingStatus.PENDING.value

        # Test filter by APPROVED
        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements?status=APPROVED",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["state"] == ProcessingStatus.APPROVED.value

        # Test filter by REJECTED
        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements?status=REJECTED",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["state"] == ProcessingStatus.REJECTED.value

    def test_get_mission_engagements_ordering(
        self, client: TestClient, session: Session, test_asso, asso_token, setup_mission
    ):
        """Test engagements are ordered by application date (most recent first)."""
        mission = setup_mission

        # Create volunteers with different application dates
        create_volunteer_with_engagement(
            session, mission.id_mission, "vol1", application_date=date(2026, 1, 10)
        )
        create_volunteer_with_engagement(
            session, mission.id_mission, "vol2", application_date=date(2026, 1, 14)
        )
        create_volunteer_with_engagement(
            session, mission.id_mission, "vol3", application_date=date(2026, 1, 12)
        )

        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Should be ordered by most recent first
        assert data[0]["application_date"] == "2026-01-14"
        assert data[1]["application_date"] == "2026-01-12"
        assert data[2]["application_date"] == "2026-01-10"

    def test_get_mission_engagements_empty(
        self, client: TestClient, session: Session, test_asso, asso_token, setup_mission
    ):
        """Test mission with no applications returns empty list."""
        mission = setup_mission

        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_mission_engagements_wrong_association(
        self, client: TestClient, session: Session, test_asso, asso_token
    ):
        """Test 403 error when trying to access another association's mission."""
        # Create another association
        other_user_in = UserCreate(
            username="other_asso",
            email="other@asso.com",
            password="Password123",
            user_type=UserType.ASSOCIATION,
        )
        other_user = user_service.create_user(session, other_user_in)
        other_asso = Association(
            id_user=other_user.id_user,
            name="Other Association",
            rna_code="W987654321",
            company_name="Other Corp",
            phone_number="0102030406",
            address="Other Address",
            zip_code="75001",
            country="France",
            verification_status=ProcessingStatus.APPROVED,
        )
        session.add(other_asso)
        session.commit()
        session.refresh(other_asso)

        # Create mission for other association
        location = Location(
            address="123 Test St", zip_code="75001", city="Paris", country="France"
        )
        session.add(location)
        session.commit()
        session.refresh(location)

        mission = Mission(
            id_asso=other_asso.id_asso,
            name="Other Mission",
            description="Test description",
            date_start=date(2026, 2, 1),
            date_end=date(2026, 2, 1),
            skills="Testing",
            capacity_min=5,
            capacity_max=10,
            id_location=location.id_location,
        )
        session.add(mission)
        session.commit()
        session.refresh(mission)

        # Try to access with test_asso's token
        response = client.get(
            f"/associations/me/missions/{mission.id_mission}/engagements",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 403

    def test_get_mission_engagements_mission_not_found(
        self, client: TestClient, test_asso, asso_token
    ):
        """Test 404 error for non-existent mission."""
        response = client.get(
            "/associations/me/missions/99999/engagements",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert response.status_code == 404
