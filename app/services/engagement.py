"""Engagement service for handling mission applications with notifications."""

from sqlmodel import Session, select, func
from app.models.engagement import Engagement
from app.models.mission import Mission
from app.models.volunteer import Volunteer
from app.models.association import Association
from app.models.enums import ProcessingStatus
from app.services.email import send_notification_email
from app.services import notification as notification_service
from app.exceptions import NotFoundError, ValidationError
from app.core.config import get_settings
from app.utils.logger import logger


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
            f"Cannot approve engagement in state {engagement.state.value}",
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
            f"Cannot reject engagement in state {engagement.state.value}",
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
