"""Tests for notification service."""

from datetime import date, timedelta
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.volunteer import Volunteer
from app.models.association import Association
from app.models.mission import MissionCreate
from app.models.enums import UserType
from app.models.notification import NotificationType
from app.services import notification as notification_service
from app.services import mission as mission_service
from app.services import user as user_service
from app.services import location as location_service
from app.models.location import LocationCreate
from app.models.category import CategoryCreate
from app.services import category as category_service


# Fixtures from test_engagement_service.py
@pytest.fixture(name="volunteer_user")
def volunteer_user_fixture(session: Session):
    user_create = UserCreate(
        username="vol_notif",
        email="vol_notif@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_create)
    volunteer = Volunteer(
        id_user=user.id_user,
        first_name="Vol",
        last_name="Unteer",
        phone_number="1234567890",
        birthdate=date(1990, 1, 1),
    )
    session.add(volunteer)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="association_user")
def association_user_fixture(session: Session):
    user_create = UserCreate(
        username="asso_notif",
        email="asso_notif@example.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_create)
    association = Association(
        id_user=user.id_user,
        name="Asso Notif",
        rna_code="W123456789",
        phone_number="0123456789",
        address="Addr",
        zip_code="00000",
        country="France",
        company_name="Corp",
    )
    session.add(association)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="created_mission")
def created_mission_fixture(session: Session, association_user):
    loc = location_service.create_location(
        session, LocationCreate(address="L", country="F", zip_code="0")
    )
    cat = category_service.create_category(session, CategoryCreate(label="C"))

    mission_in = MissionCreate(
        name="Mission Notif",
        id_location=loc.id_location,
        category_ids=[cat.id_categ],
        id_asso=association_user.association_profile.id_asso,
        date_start=date.today(),
        date_end=date.today() + timedelta(days=7),
        skills="S",
        description="D",
        capacity_min=1,
        capacity_max=5,
    )
    return mission_service.create_mission(session, mission_in)


class TestCreateNotificationHelpers:
    def test_create_volunteer_joined(
        self, session: Session, association_user, created_mission, volunteer_user
    ):
        notif = notification_service.create_volunteer_joined_notification(
            session,
            association_id=association_user.association_profile.id_asso,
            mission_id=created_mission.id_mission,
            volunteer_id=volunteer_user.id_user,
            volunteer_name="Vol Unteer",
            mission_name=created_mission.name,
        )
        assert notif.notification_type == NotificationType.VOLUNTEER_JOINED
        assert notif.id_asso == association_user.association_profile.id_asso
        assert "Vol Unteer" in notif.message
        assert "Mission Notif" in notif.message

    def test_create_volunteer_left(
        self, session: Session, association_user, created_mission, volunteer_user
    ):
        notif = notification_service.create_volunteer_left_notification(
            session,
            association_id=association_user.association_profile.id_asso,
            mission_id=created_mission.id_mission,
            volunteer_id=volunteer_user.id_user,
            volunteer_name="Vol Unteer",
            mission_name=created_mission.name,
        )
        assert notif.notification_type == NotificationType.VOLUNTEER_LEFT
        assert "s'est désisté" in notif.message

    def test_create_volunteer_withdrew(
        self, session: Session, association_user, created_mission, volunteer_user
    ):
        notif = notification_service.create_volunteer_withdrew_notification(
            session,
            association_id=association_user.association_profile.id_asso,
            mission_id=created_mission.id_mission,
            volunteer_id=volunteer_user.id_user,
            volunteer_name="Vol Unteer",
            mission_name=created_mission.name,
        )
        assert notif.notification_type == NotificationType.VOLUNTEER_WITHDREW
        assert "retiré sa candidature" in notif.message

    def test_create_capacity_reached(
        self, session: Session, association_user, created_mission
    ):
        notif = notification_service.create_capacity_reached_notification(
            session,
            association_id=association_user.association_profile.id_asso,
            mission_id=created_mission.id_mission,
            mission_name=created_mission.name,
            current_count=5,
            min_capacity=5,
        )
        assert notif.notification_type == NotificationType.CAPACITY_REACHED
        assert "atteint sa capacité" in notif.message

    def test_create_mission_deleted(self, session: Session, association_user):
        notif = notification_service.create_mission_deleted_notification(
            session,
            association_id=association_user.association_profile.id_asso,
            mission_name="Deleted Mission",
        )
        assert notif.notification_type == NotificationType.MISSION_DELETED
        assert "supprimée par un administrateur" in notif.message
        assert notif.related_mission_id is None


class TestGetNotifications:
    def test_get_association_notifications(self, session: Session, association_user):
        asso_id = association_user.association_profile.id_asso
        # Create 3 notifications
        for i in range(3):
            notification_service.create_mission_deleted_notification(
                session, asso_id, f"M{i}"
            )

        notifs = notification_service.get_association_notifications(session, asso_id)
        assert len(notifs) == 3
        # Check order (newest first)
        assert "M2" in notifs[0].message
        assert "M0" in notifs[2].message

    def test_get_unread_count(self, session: Session, association_user):
        asso_id = association_user.association_profile.id_asso
        notification_service.create_mission_deleted_notification(session, asso_id, "M1")
        notification_service.create_mission_deleted_notification(session, asso_id, "M2")

        count = notification_service.get_unread_count(session, asso_id)
        assert count == 2

    def test_mark_notifications_as_read(self, session: Session, association_user):
        asso_id = association_user.association_profile.id_asso
        n1 = notification_service.create_mission_deleted_notification(
            session, asso_id, "M1"
        )
        n2 = notification_service.create_mission_deleted_notification(
            session, asso_id, "M2"
        )

        assert n1.id_notification is not None
        # Mark only n1
        count = notification_service.mark_notifications_as_read(
            session, [n1.id_notification], asso_id
        )
        assert count == 1

        session.refresh(n1)
        session.refresh(n2)
        assert n1.is_read is True
        assert n2.is_read is False

        # Verify unread count
        assert notification_service.get_unread_count(session, asso_id) == 1
