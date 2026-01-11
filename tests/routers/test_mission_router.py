"""Tests for mission router endpoints."""

from datetime import date
import pytest
from sqlmodel import Session
from fastapi.testclient import TestClient

from app.models.user import UserCreate
from app.models.enums import UserType
from app.services import user as user_service
from app.models.association import Association
from app.models.mission import Mission
from app.models.location import Location
from app.models.category import Category

# Test constants
MISSION_NAME = "Help Seniors"
MISSION_DESCRIPTION = "Mission helping seniors with technology"
ASSO_NAME = "Together Association"


@pytest.fixture(name="mission_setup")
def mission_setup_fixture(session: Session):
    """Setup location, category, and association for mission tests."""
    loc = Location(address="75001 Paris", country="France", zip_code="75001")
    cat = Category(label="Social")
    session.add(loc)
    session.add(cat)

    user_in = UserCreate(
        username="mission_asso",
        email="asso@mission.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_in)
    asso = Association(
        id_user=user.id_user,
        name=ASSO_NAME,
        rna_code="W123456780",
        company_name="Mission Corp",
        phone_number="0101010101",
        address="Mission St",
        zip_code="75001",
        country="France",
    )
    session.add(asso)
    session.commit()

    return {"location": loc, "category": cat, "association": asso}


class TestMissionPublicSearch:
    """Test public mission listing and search endpoints."""

    def test_search_missions_filters(
        self, session: Session, client: TestClient, mission_setup
    ):
        """Search missions using text query and category filters."""
        # Setup: Create two distinct missions
        m1 = Mission(
            name=MISSION_NAME,
            id_location=mission_setup["location"].id_location,
            id_asso=mission_setup["association"].id_asso,
            date_start=date.today(),
            date_end=date.today(),
            skills="Technology",
            description=MISSION_DESCRIPTION,
            capacity_min=1,
            capacity_max=5,
        )
        m1.categories = [mission_setup["category"]]
        session.add(m1)

        m2 = Mission(
            name="Clean the Park",
            id_location=mission_setup["location"].id_location,
            id_asso=mission_setup["association"].id_asso,
            date_start=date.today(),
            date_end=date.today(),
            skills="Physical",
            description="Cleaning up the local park",
            capacity_min=2,
            capacity_max=20,
        )
        session.add(m2)
        session.commit()

        # 1. Test fetch all
        response = client.get("/missions/")
        assert response.status_code == 200
        assert len(response.json()) == 2

        # 2. Test text search query
        response = client.get(f"/missions/?search={MISSION_NAME}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == MISSION_NAME

        # 3. Test category ID filter
        cat_id = mission_setup["category"].id_categ
        response = client.get(f"/missions/?category_ids={cat_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == MISSION_NAME


class TestGetMission:
    """Test individual mission retrieval endpoints."""

    def test_read_mission_by_id(
        self, session: Session, client: TestClient, mission_setup
    ):
        """Retrieve a specific mission by its unique ID."""
        mission = Mission(
            name=MISSION_NAME,
            id_location=mission_setup["location"].id_location,
            id_asso=mission_setup["association"].id_asso,
            date_start=date.today(),
            date_end=date.today(),
            skills="Test",
            description="Test description",
            capacity_min=1,
            capacity_max=5,
        )
        session.add(mission)
        session.commit()

        response = client.get(f"/missions/{mission.id_mission}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == MISSION_NAME
        assert data["association"]["name"] == ASSO_NAME

    def test_read_mission_not_found(self, client: TestClient):
        """Returns 404 error for non-existent mission ID."""
        response = client.get("/missions/9999")
        assert response.status_code == 404
