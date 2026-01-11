"""Tests for association router endpoints."""

from datetime import date
from unittest.mock import patch, AsyncMock
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
from app.models.category import Category
from app.models.engagement import Engagement
from app.models.notification import Notification, NotificationType

# Test constants
ASSO_USERNAME = "test_asso"
ASSO_EMAIL = "test@asso.com"
ASSO_PASSWORD = "Password123"
ASSO_NAME = "Test Association"


@pytest.fixture(name="test_asso")
def test_asso_fixture(session: Session):
    """Create a verified association for testing."""
    user_in = UserCreate(
        username=ASSO_USERNAME,
        email=ASSO_EMAIL,
        password=ASSO_PASSWORD,
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_in)
    asso = Association(
        id_user=user.id_user,
        name=ASSO_NAME,
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


@pytest.fixture(name="asso_token")
def asso_token_fixture(test_asso):
    """Generate valid JWT token for test_asso."""
    from app.core.security import create_access_token

    return create_access_token(data={"sub": ASSO_USERNAME})


class TestAssociationAccount:
    """Test association account management endpoints."""

    def test_create_association_success(self, client: TestClient):
        """Register a new association with user and profile data."""
        payload = {
            "user_in": {
                "username": "new_asso_user",
                "email": "new@asso.com",
                "password": "Password123",
                "user_type": "association",
            },
            "association_in": {
                "name": "New Association",
                "rna_code": "W987654321",
                "company_name": "New Corp",
                "phone_number": "0605040302",
                "address": "123 Street",
                "zip_code": "75001",
                "country": "France",
                "description": "Association description",
            },
        }

        response = client.post("/associations/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Association"
        assert data["user"]["username"] == "new_asso_user"

    def test_read_current_association_me(
        self, client: TestClient, test_asso, asso_token
    ):
        """Retrieve the currently authenticated association's profile."""
        response = client.get(
            "/associations/me", headers={"Authorization": f"Bearer {asso_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == ASSO_NAME
        assert data["rna_code"] == "W123456789"


class TestAssociationMissionManagement:
    """Test mission lifecycle management by associations."""

    def test_create_mission_success(
        self, session: Session, client: TestClient, test_asso, asso_token
    ):
        """Create a new mission with location and categories."""
        # Setup prerequisites
        loc = Location(address="Mission Loc", country="France", zip_code="75000")
        cat = Category(label="Environment")
        session.add(loc)
        session.add(cat)
        session.commit()

        mission_in = {
            "name": "Save the Planet",
            "id_location": loc.id_location,
            "category_ids": [cat.id_categ],
            "id_asso": 0,  # Backend overrides this with current asso ID
            "date_start": str(date.today()),
            "date_end": str(date.today()),
            "skills": "Motivation",
            "description": "Mission description",
            "capacity_min": 1,
            "capacity_max": 10,
        }

        response = client.post(
            "/associations/me/missions",
            headers={"Authorization": f"Bearer {asso_token}"},
            json=mission_in,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Save the Planet"
        assert data["id_asso"] == test_asso.id_asso


class TestEngagementManagement:
    """Test volunteer engagement approval and management."""

    def test_approve_engagement_lifecycle(
        self, session: Session, client: TestClient, test_asso, asso_token
    ):
        """Approve a pending volunteer engagement for a mission."""
        # Setup mission
        loc = Location(address="L", country="F", zip_code="0")
        session.add(loc)
        session.commit()

        mission = Mission(
            name="M",
            id_location=loc.id_location,
            id_asso=test_asso.id_asso,
            date_start=date.today(),
            date_end=date.today(),
            skills="S",
            description="D",
            capacity_min=1,
            capacity_max=5,
        )
        session.add(mission)

        # Setup volunteer
        uv = user_service.create_user(
            session,
            UserCreate(
                username="vol_test",
                email="vol@test.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        vol = Volunteer(
            id_user=uv.id_user,
            first_name="Vol",
            last_name="Test",
            phone_number="123",
            birthdate=date(1990, 1, 1),
        )
        session.add(vol)
        session.commit()

        # Create pending engagement
        eng = Engagement(
            id_volunteer=vol.id_volunteer,
            id_mission=mission.id_mission,
            state=ProcessingStatus.PENDING,
        )
        session.add(eng)
        session.commit()

        with (
            patch(
                "app.services.engagement.send_notification_email",
                new_callable=AsyncMock,
            ) as mock_email,
            patch("app.services.engagement.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "http://localhost:3000"

            response = client.patch(
                f"/associations/me/engagements/{vol.id_volunteer}/{mission.id_mission}/approve",
                headers={"Authorization": f"Bearer {asso_token}"},
            )
            assert response.status_code == 200
            # multiple emails are sent (approval, volunteer joined, and capacity reached because min=1)
            assert mock_email.call_count >= 1


class TestAssociationNotifications:
    """Test unread count and notification listing for associations."""

    def test_get_notifications_workflow(
        self, session: Session, client: TestClient, test_asso, asso_token
    ):
        """Retrieve and mark as read association notifications."""
        # Setup: Create 2 unread notifications
        session.add(
            Notification(
                id_asso=test_asso.id_asso,
                notification_type=NotificationType.MISSION_DELETED,
                message="Message 1",
            )
        )
        session.add(
            Notification(
                id_asso=test_asso.id_asso,
                notification_type=NotificationType.MISSION_DELETED,
                message="Message 2",
            )
        )
        session.commit()

        # 1. Check unread count
        count_res = client.get(
            "/associations/notifications/unread-count",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert count_res.status_code == 200
        assert count_res.json()["unread_count"] == 2

        # 2. Get list of notifications
        list_res = client.get(
            "/associations/notifications",
            headers={"Authorization": f"Bearer {asso_token}"},
        )
        assert list_res.status_code == 200
        notifs = list_res.json()
        assert len(notifs) == 2

        # 3. Mark notifications as read
        ids = [n["id_notification"] for n in notifs]
        mark_res = client.patch(
            "/associations/notifications/mark-read",
            headers={"Authorization": f"Bearer {asso_token}"},
            json={"notification_ids": ids},
        )
        assert mark_res.status_code == 200
        assert mark_res.json()["marked_count"] == 2
