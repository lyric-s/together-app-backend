"""Tests for engagement service operations."""

from datetime import date, timedelta
from unittest.mock import patch, AsyncMock
import pytest
from sqlmodel import Session

from app.models.mission import MissionCreate
from app.models.engagement import Engagement
from app.models.location import Location
from app.models.category import Category
from app.models.enums import ProcessingStatus
from app.services import engagement as engagement_service
from app.services import mission as mission_service
from app.exceptions import NotFoundError

# Test data constants
VOLUNTEER_EMAIL = "gen_vol@example.com"  # Matches fixture
ASSOC_EMAIL = "gen_asso@example.com"  # Matches fixture
MISSION_NAME = "Engagement Test Mission"
CAPACITY_MIN = 2
CAPACITY_MAX = 5


@pytest.fixture(name="created_mission")
def created_mission_fixture(
    session: Session,
    association_user,
    created_location: Location,
    created_category: Category,
):
    """Create a mission using mission_service."""
    mission_in = MissionCreate(
        name=MISSION_NAME,
        id_location=created_location.id_location,
        category_ids=[created_category.id_categ],
        id_asso=association_user.association_profile.id_asso,
        date_start=date.today(),
        date_end=date.today() + timedelta(days=7),
        skills="Testing",
        description="Testing engagements",
        capacity_min=CAPACITY_MIN,
        capacity_max=CAPACITY_MAX,
    )
    return mission_service.create_mission(session, mission_in)


@pytest.fixture(name="pending_engagement")
def pending_engagement_fixture(session: Session, volunteer_user, created_mission):
    """Create a pending engagement manually."""
    engagement = Engagement(
        id_volunteer=volunteer_user.volunteer_profile.id_volunteer,
        id_mission=created_mission.id_mission,
        state=ProcessingStatus.PENDING,
    )
    session.add(engagement)
    session.commit()
    session.refresh(engagement)
    return engagement


class TestApproveApplication:
    """Test approval logic."""

    @pytest.mark.asyncio
    async def test_approve_application_success(
        self,
        session: Session,
        pending_engagement: Engagement,
        volunteer_user,
        association_user,
    ):
        """Test successful approval sends emails and notifications."""

        with (
            patch(
                "app.services.engagement.send_notification_email",
                new_callable=AsyncMock,
            ) as mock_email,
            patch("app.services.engagement.notification_service") as mock_notification,
            patch("app.services.engagement.get_settings") as mock_settings,
        ):
            mock_settings.return_value.FRONTEND_URL = "http://test.com"

            updated = await engagement_service.approve_application_by_ids(
                session,
                volunteer_user.volunteer_profile.id_volunteer,
                pending_engagement.id_mission,
            )

            assert updated.state == ProcessingStatus.APPROVED
            assert updated.rejection_reason is None

            # Should send 2 emails: one to volunteer, one to association
            assert mock_email.call_count == 2

            # Check volunteer email
            calls = mock_email.call_args_list
            vol_email_call = next(
                c for c in calls if c.kwargs["recipient_email"] == VOLUNTEER_EMAIL
            )
            assert vol_email_call.kwargs["template_name"] == "application_approved"

            # Check association email
            assoc_email_call = next(
                c for c in calls if c.kwargs["recipient_email"] == ASSOC_EMAIL
            )
            assert assoc_email_call.kwargs["template_name"] == "volunteer_joined"

            # Check notification
            mock_notification.create_volunteer_joined_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_application_capacity_reached(
        self, session: Session, pending_engagement: Engagement, created_mission
    ):
        """Test approval triggers capacity reached notification."""
        # Update mission to have capacity_min = 1 so this single approval triggers it
        created_mission.capacity_min = 1
        session.add(created_mission)
        session.commit()

        with (
            patch(
                "app.services.engagement.send_notification_email",
                new_callable=AsyncMock,
            ) as mock_email,
            patch("app.services.engagement.notification_service") as mock_notification,
            patch("app.services.engagement.get_settings"),
        ):
            await engagement_service.approve_application_by_ids(
                session, pending_engagement.id_volunteer, pending_engagement.id_mission
            )

            mock_notification.create_capacity_reached_notification.assert_called_once()

            # Verify capacity reached email was sent (should be one of the calls)
            calls = mock_email.call_args_list
            capacity_emails = [
                c for c in calls if c.kwargs.get("template_name") == "capacity_reached"
            ]
            assert len(capacity_emails) == 1

    @pytest.mark.asyncio
    async def test_approve_application_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            await engagement_service.approve_application_by_ids(session, 99999, 99999)


class TestRejectApplication:
    """Test rejection logic."""

    @pytest.mark.asyncio
    async def test_reject_application_success(
        self, session: Session, pending_engagement: Engagement
    ):
        reason = "Capacity full"

        with patch(
            "app.services.engagement.send_notification_email", new_callable=AsyncMock
        ) as mock_email:
            updated = await engagement_service.reject_application(
                session,
                pending_engagement.id_volunteer,
                pending_engagement.id_mission,
                reason,
            )

            assert updated.state == ProcessingStatus.REJECTED
            assert updated.rejection_reason == reason

            mock_email.assert_called_once()
            assert (
                mock_email.call_args.kwargs["template_name"] == "application_rejected"
            )
            assert mock_email.call_args.kwargs["recipient_email"] == VOLUNTEER_EMAIL

    @pytest.mark.asyncio
    async def test_reject_application_not_found(self, session: Session):
        with pytest.raises(NotFoundError):
            await engagement_service.reject_application(session, 99999, 99999, "reason")
