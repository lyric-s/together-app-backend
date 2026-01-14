"""Engagement service for handling mission applications with notifications."""

from sqlmodel import Session, select, func
from app.models.engagement import Engagement, EngagementWithVolunteer
from app.models.mission import Mission
from app.models.volunteer import Volunteer
from app.models.association import Association
from app.models.user import User
from app.models.enums import ProcessingStatus
from app.services.email import send_notification_email
from app.services import notification as notification_service
from app.exceptions import NotFoundError, ValidationError
from app.core.config import get_settings
from app.utils.logger import logger


def _get_and_validate_pending_engagement(
    session: Session, volunteer_id: int, mission_id: int, action: str
) -> tuple[Engagement, Mission, Volunteer]:
    """
    Retrieve and validate engagement, mission, and volunteer for approval/rejection.

    Ensures engagement exists and is in PENDING state.

    Args:
        session: Database session
        volunteer_id: Volunteer ID
        mission_id: Mission ID
        action: Action being performed (e.g. "approve", "reject") for error messages

    Returns:
        tuple[Engagement, Mission, Volunteer]: The validated objects

    Raises:
        NotFoundError: If any entity is not found
        ValidationError: If engagement is not PENDING
    """
    # Get engagement
    engagement = session.exec(
        select(Engagement).where(
            Engagement.id_volunteer == volunteer_id,
            Engagement.id_mission == mission_id,
        )
    ).first()

    if not engagement:
        raise NotFoundError(
            "Engagement", f"volunteer_{volunteer_id}_mission_{mission_id}"
        )

    if engagement.state != ProcessingStatus.PENDING:
        raise ValidationError(
            f"Cannot {action} engagement in state {engagement.state.value}",
            field="state",
        )

    # Get mission
    mission = session.exec(
        select(Mission).where(Mission.id_mission == mission_id)
    ).first()

    if not mission:
        raise NotFoundError("Mission", mission_id)

    # Get volunteer
    volunteer = session.exec(
        select(Volunteer).where(Volunteer.id_volunteer == volunteer_id)
    ).first()

    if not volunteer or not volunteer.user:
        raise NotFoundError("Volunteer", volunteer_id)

    return engagement, mission, volunteer


async def approve_application_by_ids(
    session: Session, volunteer_id: int, mission_id: int
) -> Engagement:
    """
    Approve a volunteer's mission application and send notifications.

    Sends email to volunteer and creates notification for association.
    Checks if mission reached minimum capacity.

    Args:
        session: Database session
        volunteer_id: Volunteer ID
        mission_id: Mission ID

    Returns:
        Engagement: Updated engagement
    """
    engagement, mission, volunteer = _get_and_validate_pending_engagement(
        session, volunteer_id, mission_id, "approve"
    )

    # Get association
    association = session.exec(
        select(Association).where(Association.id_asso == mission.id_asso)
    ).first()

    if not association:
        raise NotFoundError("Association", mission.id_asso)

    # Count approved volunteers before approval
    previous_count = session.exec(
        select(func.count())
        .select_from(Engagement)
        .where(
            Engagement.id_mission == mission_id,
            Engagement.state == ProcessingStatus.APPROVED,
        )
    ).one()

    # Check capacity
    if previous_count >= mission.capacity_max:
        raise ValidationError(
            "Cannot approve application: Mission has reached maximum capacity",
            field="mission_id",
        )

    was_below_min = previous_count < mission.capacity_min

    # Update engagement status
    engagement.state = ProcessingStatus.APPROVED
    engagement.rejection_reason = None
    session.add(engagement)
    session.flush()
    session.refresh(engagement)

    # Current count after approval
    current_count = previous_count + 1

    # Get volunteer name
    volunteer_name = f"{volunteer.first_name} {volunteer.last_name}"

    # Send email to volunteer
    settings = get_settings()
    try:
        await send_notification_email(
            template_name="application_approved",
            recipient_email=volunteer.user.email,
            context={
                "volunteer_name": volunteer_name,
                "mission_name": mission.name,
                "mission_id": mission.id_mission,
                "frontend_url": settings.FRONTEND_URL,
            },
        )
    except Exception:
        logger.exception("Failed to send application approval email")

    # Create notification for association
    if (
        association.id_asso is not None
        and mission.id_mission is not None
        and volunteer.user.id_user is not None
    ):
        notification_service.create_volunteer_joined_notification(
            session=session,
            association_id=association.id_asso,
            mission_id=mission.id_mission,
            user_id=volunteer.user.id_user,
            volunteer_name=volunteer_name,
            mission_name=mission.name,
        )

    # Send email to association
    if association.user:
        try:
            await send_notification_email(
                template_name="volunteer_joined",
                recipient_email=association.user.email,
                context={
                    "association_name": association.name,
                    "volunteer_name": volunteer_name,
                    "mission_name": mission.name,
                    "current_count": current_count,
                    "max_capacity": mission.capacity_max,
                },
            )
        except Exception:
            logger.exception("Failed to send volunteer joined email")

    # Check if mission just reached minimum capacity
    if (
        was_below_min
        and current_count >= mission.capacity_min
        and association.id_asso is not None
        and mission.id_mission is not None
    ):
        # Create capacity reached notification
        notification_service.create_capacity_reached_notification(
            session=session,
            association_id=association.id_asso,
            mission_id=mission.id_mission,
            mission_name=mission.name,
            current_count=current_count,
            min_capacity=mission.capacity_min,
        )

        # Send capacity reached email
        if association.user:
            try:
                await send_notification_email(
                    template_name="capacity_reached",
                    recipient_email=association.user.email,
                    context={
                        "association_name": association.name,
                        "mission_name": mission.name,
                        "current_count": current_count,
                        "max_capacity": mission.capacity_max,
                    },
                )
            except Exception:
                logger.exception("Failed to send capacity reached email")

    return engagement


async def reject_application(
    session: Session, volunteer_id: int, mission_id: int, rejection_reason: str
) -> Engagement:
    """
    Reject a volunteer's mission application and send email notification.

    Args:
        session: Database session
        volunteer_id: Volunteer ID
        mission_id: Mission ID
        rejection_reason: Reason for rejection

    Returns:
        Engagement: Updated engagement
    """
    engagement, mission, volunteer = _get_and_validate_pending_engagement(
        session, volunteer_id, mission_id, "reject"
    )

    # Update engagement status
    engagement.state = ProcessingStatus.REJECTED
    engagement.rejection_reason = rejection_reason
    session.add(engagement)
    session.flush()
    session.refresh(engagement)

    # Send email to volunteer
    volunteer_name = f"{volunteer.first_name} {volunteer.last_name}"

    try:
        await send_notification_email(
            template_name="application_rejected",
            recipient_email=volunteer.user.email,
            context={
                "volunteer_name": volunteer_name,
                "mission_name": mission.name,
                "rejection_reason": rejection_reason,
            },
        )
    except Exception:
        logger.exception("Failed to send application rejection email")

    return engagement


def get_mission_engagements(
    session: Session, mission_id: int, status_filter: ProcessingStatus | None = None
) -> list[EngagementWithVolunteer]:
    """
    Get all volunteer engagements (applications) for a specific mission.

    Returns engagements with volunteer information for the association dashboard.
    Optionally filter by engagement status (PENDING, APPROVED, REJECTED).

    Args:
        session: Database session
        mission_id: Mission ID to get engagements for
        status_filter: Optional status filter (PENDING, APPROVED, REJECTED)

    Returns:
        list[EngagementWithVolunteer]: List of engagements with volunteer details,
            ordered by application date (most recent first)

    Raises:
        NotFoundError: If mission doesn't exist
    """
    # Verify mission exists
    mission = session.exec(
        select(Mission).where(Mission.id_mission == mission_id)
    ).first()
    if not mission:
        raise NotFoundError("Mission", mission_id)

    # Build query with joins to get volunteer and user details
    query = (
        select(Engagement, Volunteer, User)
        .join(Volunteer, Engagement.id_volunteer == Volunteer.id_volunteer)  # type: ignore
        .join(User, Volunteer.id_user == User.id_user)  # type: ignore
        .where(Engagement.id_mission == mission_id)
    )

    # Apply status filter if provided
    if status_filter:
        query = query.where(Engagement.state == status_filter)

    # Order by application date (most recent first)
    query = query.order_by(Engagement.application_date.desc())  # type: ignore

    results = session.exec(query).all()

    # Transform to EngagementWithVolunteer
    engagements = []
    for engagement, volunteer, user in results:
        engagements.append(
            EngagementWithVolunteer(
                id_volunteer=engagement.id_volunteer,
                id_mission=engagement.id_mission,
                state=engagement.state,
                message=engagement.message,
                application_date=engagement.application_date,
                rejection_reason=engagement.rejection_reason,
                volunteer_first_name=volunteer.first_name,
                volunteer_last_name=volunteer.last_name,
                volunteer_email=user.email,
                volunteer_phone=volunteer.phone_number,
                volunteer_skills=volunteer.skills,
            )
        )

    return engagements
