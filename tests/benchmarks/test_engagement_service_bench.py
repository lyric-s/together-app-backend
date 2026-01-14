"""Performance benchmarks for engagement service operations."""

import asyncio
from unittest.mock import patch, AsyncMock
from datetime import date, timedelta
import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.enums import ProcessingStatus, UserType
from app.models.engagement import Engagement
from app.models.location import Location
from app.models.category import Category
from app.models.mission import MissionCreate
from app.models.user import UserCreate
from app.models.volunteer import Volunteer
from app.services import engagement as engagement_service
from app.services import association as association_service
from app.services import mission as mission_service
from app.services import volunteer as volunteer_service
from app.services import user as user_service


@pytest.fixture(name="engagement_setup_data")
def engagement_setup_fixture(
    session: Session,
    user_create_data_factory,
    association_create_data_factory,
    location_create_data_factory,
    category_create_data_factory,
    volunteer_create_data,
):
    """Setup dependencies for engagement benchmarks."""

    # 1. Create Association
    association = association_service.create_association(
        session=session,
        user_in=user_create_data_factory(),
        association_in=association_create_data_factory(),
    )

    # 2. Create Location and Category
    location = Location.model_validate(location_create_data_factory())
    session.add(location)
    category = Category.model_validate(category_create_data_factory())
    session.add(category)
    session.flush()

    # 3. Create Mission
    mission_in = MissionCreate(
        name="Bench Mission",
        description="Bench description",
        date_start=date.today(),
        date_end=date.today() + timedelta(days=1),
        skills="Skills",
        capacity_min=1,
        capacity_max=10,
        id_asso=association.id_asso,
        id_location=location.id_location,
        category_ids=[category.id_categ],
    )
    mission = mission_service.create_mission(session=session, mission_in=mission_in)

    # 4. Create Volunteer
    volunteer = volunteer_service.create_volunteer(
        session=session,
        user_in=user_create_data_factory(),
        volunteer_in=volunteer_create_data,
    )

    session.flush()

    return {
        "volunteer_id": volunteer.id_volunteer,
        "mission_id": mission.id_mission,
    }


def test_approve_application_performance(
    benchmark: BenchmarkFixture, session: Session, engagement_setup_data
):
    """Benchmark approving a mission application."""
    vid = engagement_setup_data["volunteer_id"]
    mid = engagement_setup_data["mission_id"]

    # Run the async code using a helper that doesn't use the @benchmark on an async function directly
    # because pytest-codspeed might have issues with it depending on version

    with (
        patch(
            "app.services.engagement.send_notification_email", new_callable=AsyncMock
        ),
        patch("app.services.engagement.notification_service"),
    ):

        @benchmark
        def approve_sync():
            # Setup pending engagement
            engagement = Engagement(
                id_volunteer=vid,
                id_mission=mid,
                state=ProcessingStatus.PENDING,
            )
            session.add(engagement)
            session.commit()  # Must commit because service uses it

            asyncio.run(
                engagement_service.approve_application_by_ids(
                    session=session, volunteer_id=vid, mission_id=mid
                )
            )

            # Cleanup
            session.delete(engagement)
            session.commit()


def test_get_mission_engagements_performance(
    benchmark: BenchmarkFixture, session: Session, engagement_setup_data
):
    """Benchmark retrieving all engagements for a mission."""
    mid = engagement_setup_data["mission_id"]

    # Setup: Create 5 engagements for the mission
    engagements = []
    for i in range(5):
        # Create additional volunteers for variety
        user_in = UserCreate(
            username=f"bench_vol_{i}",
            email=f"bench_vol_{i}@test.com",
            password="Password123",
            user_type=UserType.VOLUNTEER,
        )
        user = user_service.create_user(session, user_in)
        volunteer = Volunteer(
            id_user=user.id_user,
            first_name=f"Vol{i}",
            last_name="Bench",
            phone_number="0601020304",
            birthdate=date(1995, 1, 1),
            skills="Testing",
        )
        session.add(volunteer)
        session.flush()

        engagement = Engagement(
            id_volunteer=volunteer.id_volunteer,
            id_mission=mid,
            state=ProcessingStatus.PENDING,
        )
        session.add(engagement)
        engagements.append((engagement, volunteer, user))

    session.commit()

    # Benchmark the retrieval
    @benchmark
    def get_engagements():
        result = engagement_service.get_mission_engagements(session, mid)
        return result

    # Cleanup (delete in correct order to avoid cascade warnings)
    for engagement, volunteer, user in engagements:
        session.delete(engagement)
    session.commit()

    for _, volunteer, user in engagements:
        session.delete(volunteer)
        session.delete(user)
    session.commit()
