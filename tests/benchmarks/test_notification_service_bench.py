"""Performance benchmarks for notification service operations."""

import pytest
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.notification import NotificationCreate, NotificationType
from app.services import notification as notification_service


@pytest.fixture(name="notification_setup_data")
def notification_setup_fixture(
    session: Session, user_create_data_factory, association_create_data_factory
):
    """Setup an association for notification benchmarks."""
    from app.services import association as association_service

    association = association_service.create_association(
        session=session,
        user_in=user_create_data_factory(),
        association_in=association_create_data_factory(),
    )
    session.flush()
    return {"id_asso": association.id_asso}


def test_notification_creation_performance(
    benchmark: BenchmarkFixture, session: Session, notification_setup_data, tracker
):
    """Benchmark notification creation operation."""

    @benchmark
    def create_notification():
        notification_in = NotificationCreate(
            id_asso=notification_setup_data["id_asso"],
            notification_type=NotificationType.VOLUNTEER_JOINED,
            message="Bench notification message",
        )
        notification = notification_service.create_notification(
            session=session, notification_in=notification_in
        )
        tracker.append(notification)
        return notification.id_notification


def test_get_association_notifications_performance(
    benchmark: BenchmarkFixture, session: Session, notification_setup_data
):
    """Benchmark retrieving notifications for an association."""
    # Setup: Create some notifications
    for i in range(10):
        notification_in = NotificationCreate(
            id_asso=notification_setup_data["id_asso"],
            notification_type=NotificationType.VOLUNTEER_JOINED,
            message=f"Bench notification {i}",
        )
        notification_service.create_notification(
            session=session, notification_in=notification_in
        )
    session.flush()

    @benchmark
    def get_notifications():
        session.expire_all()
        return notification_service.get_association_notifications(
            session=session, association_id=notification_setup_data["id_asso"]
        )
