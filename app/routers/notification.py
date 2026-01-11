"""Notification router for association activity feed."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.notification import NotificationPublic, NotificationMarkRead
from app.services import notification as notification_service
from app.services import association as association_service
from app.exceptions import NotFoundError

router = APIRouter(prefix="/associations/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationPublic])
def get_notifications(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = Query(
        False, description="If true, only return unread notifications"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[NotificationPublic]:
    """
    Get notifications for authenticated association.

    Returns activity feed of mission-related events (volunteers joining/leaving,
    capacity reached, etc.) ordered by date (newest first).

    ### Query Parameters:
    - **unread_only**: Filter to only unread notifications
    - **offset**: Pagination offset
    - **limit**: Max results (1-100, default 50)

    ### Authorization:
    - Must be authenticated as association

    Args:
        session: Database session (automatically injected).
        current_user: Authenticated user (automatically injected from token).
        unread_only: Filter to only unread notifications.
        offset: Pagination offset.
        limit: Maximum number of results to return.

    Returns:
        list[NotificationPublic]: List of notifications ordered by date (newest first).

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile doesn't exist.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association", current_user.id_user)

    assert association.id_asso is not None
    notifications = notification_service.get_association_notifications(
        session=session,
        association_id=association.id_asso,
        unread_only=unread_only,
        offset=offset,
        limit=limit,
    )

    return [NotificationPublic.model_validate(n) for n in notifications]


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Get count of unread notifications.

    Useful for displaying notification badge in UI.

    ### Authorization:
    - Must be authenticated as association

    Args:
        session: Database session (automatically injected).
        current_user: Authenticated user (automatically injected from token).

    Returns:
        dict: Dictionary containing unread_count.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile doesn't exist.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association", current_user.id_user)

    assert association.id_asso is not None
    count = notification_service.get_unread_count(session, association.id_asso)

    return {"unread_count": count}


@router.patch("/mark-read", response_model=dict)
def mark_notifications_as_read(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    mark_read: NotificationMarkRead,
) -> dict:
    """
    Mark notifications as read.

    ### Request Body:
    - **notification_ids**: List of notification IDs to mark as read

    ### Authorization:
    - Must be authenticated as association
    - Can only mark own notifications as read

    Args:
        session: Database session (automatically injected).
        current_user: Authenticated user (automatically injected from token).
        mark_read: Request body containing notification IDs to mark as read.

    Returns:
        dict: Dictionary containing marked_count.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile doesn't exist.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association", current_user.id_user)

    assert association.id_asso is not None
    marked_count = notification_service.mark_notifications_as_read(
        session=session,
        notification_ids=mark_read.notification_ids,
        association_id=association.id_asso,
    )

    return {"marked_count": marked_count}
