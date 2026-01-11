"""Notification service for creating and managing notifications."""

from sqlmodel import Session, select, func

from app.models.notification import (
    Notification,
    NotificationCreate,
    NotificationType,
)


def create_notification(
    session: Session, notification_in: NotificationCreate
) -> Notification:
    """
    Create a notification in the database.

    Args:
        session: Database session
        notification_in: Notification creation data

    Returns:
        Notification: Created notification
    """
    notification = Notification.model_validate(notification_in)
    session.add(notification)
    session.flush()
    session.refresh(notification)
    return notification


def get_association_notifications(
    session: Session,
    association_id: int,
    *,
    unread_only: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> list[Notification]:
    """
    Get notifications for an association.

    Args:
        session: Database session
        association_id: Association ID
        unread_only: If True, only return unread notifications
        offset: Pagination offset
        limit: Maximum notifications to return

    Returns:
        list[Notification]: List of notifications ordered by date (newest first)
    """
    statement = select(Notification).where(Notification.id_asso == association_id)

    if unread_only:
        statement = statement.where(Notification.is_read == False)  # noqa: E712

    statement = (
        statement.order_by(Notification.created_at.desc())  # type: ignore
        .offset(offset)
        .limit(limit)
    )

    return list(session.exec(statement).all())


def mark_notifications_as_read(
    session: Session, notification_ids: list[int], association_id: int
) -> int:
    """
    Mark notifications as read.

    Args:
        session: Database session
        notification_ids: List of notification IDs to mark as read
        association_id: Association ID (for security - only mark own notifications)

    Returns:
        int: Number of notifications marked as read
    """
    statement = select(Notification).where(
        Notification.id_notification.in_(notification_ids),  # type: ignore
        Notification.id_asso == association_id,
    )

    notifications = session.exec(statement).all()
    count = 0

    for notification in notifications:
        if not notification.is_read:
            notification.is_read = True
            session.add(notification)
            count += 1

    session.flush()
    return count


def get_unread_count(session: Session, association_id: int) -> int:
    """
    Get count of unread notifications for an association.

    Args:
        session: Database session
        association_id: Association ID

    Returns:
        int: Number of unread notifications
    """
    count = session.exec(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.id_asso == association_id,
            Notification.is_read == False,  # noqa: E712
        )
    ).one()

    return count


# Helper functions to create specific notification types


def create_volunteer_joined_notification(
    session: Session,
    association_id: int,
    mission_id: int,
    user_id: int,
    volunteer_name: str,
    mission_name: str,
) -> Notification:
    """Create notification when volunteer joins a mission."""
    message = f'{volunteer_name} a rejoint la mission "{mission_name}"'

    notification_in = NotificationCreate(
        id_asso=association_id,
        notification_type=NotificationType.VOLUNTEER_JOINED,
        message=message,
        related_mission_id=mission_id,
        related_user_id=user_id,
    )

    return create_notification(session, notification_in)


def create_volunteer_left_notification(
    session: Session,
    association_id: int,
    mission_id: int,
    user_id: int,
    volunteer_name: str,
    mission_name: str,
) -> Notification:
    """Create notification when volunteer leaves a mission."""
    message = f'{volunteer_name} s\'est désisté de la mission "{mission_name}"'

    notification_in = NotificationCreate(
        id_asso=association_id,
        notification_type=NotificationType.VOLUNTEER_LEFT,
        message=message,
        related_mission_id=mission_id,
        related_user_id=user_id,
    )

    return create_notification(session, notification_in)


def create_volunteer_withdrew_notification(
    session: Session,
    association_id: int,
    mission_id: int,
    user_id: int,
    volunteer_name: str,
    mission_name: str,
) -> Notification:
    """Create notification when volunteer withdraws application."""
    message = f'{volunteer_name} a retiré sa candidature pour "{mission_name}"'

    notification_in = NotificationCreate(
        id_asso=association_id,
        notification_type=NotificationType.VOLUNTEER_WITHDREW,
        message=message,
        related_mission_id=mission_id,
        related_user_id=user_id,
    )

    return create_notification(session, notification_in)


def create_capacity_reached_notification(
    session: Session,
    association_id: int,
    mission_id: int,
    mission_name: str,
    current_count: int,
    min_capacity: int,
) -> Notification:
    """Create notification when mission reaches minimum capacity."""
    message = (
        f'La mission "{mission_name}" a atteint sa capacité minimale '
        f"({current_count}/{min_capacity} bénévoles)"
    )

    notification_in = NotificationCreate(
        id_asso=association_id,
        notification_type=NotificationType.CAPACITY_REACHED,
        message=message,
        related_mission_id=mission_id,
    )

    return create_notification(session, notification_in)


def create_mission_deleted_notification(
    session: Session, association_id: int, mission_name: str
) -> Notification:
    """Create notification when mission is deleted by admin."""
    message = f'La mission "{mission_name}" a été supprimée par un administrateur'

    notification_in = NotificationCreate(
        id_asso=association_id,
        notification_type=NotificationType.MISSION_DELETED,
        message=message,
    )

    return create_notification(session, notification_in)
