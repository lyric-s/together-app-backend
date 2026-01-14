"""Association router module for CRUD endpoints."""

from typing import Annotated, cast
from anyio import to_thread
from loguru import logger

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload, InstrumentedAttribute

from app.database.database import get_session
from app.core.dependencies import get_current_user, get_current_association
from app.models.user import User, UserCreate
from app.models.association import (
    Association,
    AssociationCreate,
    AssociationPublic,
    AssociationUpdate,
)
from app.models.mission import Mission, MissionCreate, MissionPublic, MissionUpdate
from app.models.engagement import Engagement, RejectEngagementRequest, EngagementPublic
from app.models.volunteer import Volunteer
from app.models.notification import (
    BulkEmailRequest,
    NotificationPublic,
    NotificationMarkRead,
)
from app.models.enums import ProcessingStatus
from app.services import association as association_service
from app.services import mission as mission_service
from app.services import engagement as engagement_service
from app.services import notification as notification_service
from app.services.email import send_notification_email
from app.exceptions import NotFoundError, InsufficientPermissionsError, ValidationError
from app.utils.validation import ensure_id

router = APIRouter(prefix="/associations", tags=["associations"])


@router.post("/", response_model=AssociationPublic)
def create_association(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_in: UserCreate,
    association_in: AssociationCreate,
) -> AssociationPublic:
    """
    Register a new association with user account.

    Creates both a User account (with user_type=ASSOCIATION) and the associated
    Association profile in a single atomic operation.

    ### What Gets Created:
    - User account with authentication credentials
    - Association profile with organization details
    - Automatic linking between user and association records

    Args:
        `user_in`: User account data including username, email, and password.
        `association_in`: Association profile data including name, address, phone,
            RNA code, etc.
        `session`: Database session (automatically injected).

    Returns:
        `AssociationPublic`: The newly created association profile with user information,
            including id_asso and id_user.

    Raises:
        `409 AlreadyExistsError`: If the username or email already exists.
        `422 ValidationError`: If the RNA code format is invalid.
    """
    association = association_service.create_association(
        session, user_in, association_in
    )
    session.commit()
    session.refresh(association)
    return association_service.to_association_public(session, association)


@router.get("/", response_model=list[AssociationPublic])
def read_associations(
    session: Annotated[Session, Depends(get_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AssociationPublic]:
    """
    Retrieve a paginated list of all associations.

    Returns a list of all registered associations with their public profile information.
    Pagination parameters control the number of results returned.

    ### Pagination:
    - Default: Returns first 100 associations
    - Maximum limit: 100 associations per request
    - Use offset to skip records for subsequent pages

    Args:
        `offset`: Number of records to skip (default: 0, minimum: 0).
        `limit`: Maximum number of records to return (default: 100, range: 1-100).
        `session`: Database session (automatically injected).

    Returns:
        `list[AssociationPublic]`: List of association profiles with their public information,
            including mission counts and user details.
    """
    return association_service.get_associations(session, offset=offset, limit=limit)


@router.get("/me", response_model=AssociationPublic)
def read_current_association(
    association: Annotated[Association, Depends(get_current_association)],
    session: Annotated[Session, Depends(get_session)],
) -> AssociationPublic:
    """
    Retrieve the authenticated user's association profile.

    Returns the authenticated user's association profile with all public information
    including active and finished mission counts.

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `session`: Database session (automatically injected).
        `association`: Authenticated association profile (automatically injected).

    Returns:
        `AssociationPublic`: The authenticated user's association profile including
            organization details, mission statistics, and linked user account details.

    ### Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If no association profile exists for the authenticated user.
    """
    return association_service.to_association_public(session, association)


@router.get("/notifications", response_model=list[NotificationPublic])
def get_notifications(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
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
        current_association: Authenticated association profile (automatically injected).
        unread_only: Filter to only unread notifications.
        offset: Pagination offset.
        limit: Maximum number of results to return.

    Returns:
        list[NotificationPublic]: List of notifications ordered by date (newest first).

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile doesn't exist.
    """
    # current_association.id_asso is guaranteed to be int by dependency
    notifications = notification_service.get_association_notifications(
        session=session,
        association_id=current_association.id_asso,  # type: ignore
        unread_only=unread_only,
        offset=offset,
        limit=limit,
    )

    return [NotificationPublic.model_validate(n) for n in notifications]


@router.get("/notifications/unread-count", response_model=dict)
def get_unread_count(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> dict:
    """
    Get count of unread notifications.

    Useful for displaying notification badge in UI.

    ### Authorization:
    - Must be authenticated as association

    Args:
        session: Database session (automatically injected).
        current_association: Authenticated association profile (automatically injected).

    Returns:
        dict: Dictionary containing unread_count.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile doesn't exist.
    """
    count = notification_service.get_unread_count(
        session,
        current_association.id_asso,  # type: ignore
    )

    return {"unread_count": count}


@router.patch("/notifications/mark-read", response_model=dict)
def mark_notifications_as_read(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
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
        current_association: Authenticated association profile (automatically injected).
        mark_read: Request body containing notification IDs to mark as read.

    Returns:
        dict: Dictionary containing marked_count.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile doesn't exist.
    """
    marked_count = notification_service.mark_notifications_as_read(
        session=session,
        notification_ids=mark_read.notification_ids,
        association_id=current_association.id_asso,  # type: ignore
    )
    session.commit()

    return {"marked_count": marked_count}


@router.get("/{association_id}", response_model=AssociationPublic)
def read_association(
    association_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> AssociationPublic:
    """
    Retrieve detailed association profile information by ID.

    Retrieves complete public profile information for a specific association,
    including their organization details, mission statistics, and user account information.

    Args:
        `association_id`: The unique identifier of the association to retrieve.
        `session`: Database session (automatically injected).

    Returns:
        `AssociationPublic`: The association's complete public profile.

    Raises:
        `404 NotFoundError`: If no association exists with the given ID.
    """
    association = association_service.get_association(session, association_id)
    if not association:
        raise NotFoundError("Association", association_id)
    return association_service.to_association_public(session, association)


@router.patch("/{association_id}", response_model=AssociationPublic)
def update_association(
    association_id: int,
    association_update: AssociationUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssociationPublic:
    """
    Update the authenticated user's association profile information.

    Allows partial updates to association profile fields. Only the fields included
    in the request body will be updated; omitted fields remain unchanged.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Only the profile owner can perform updates

    ### Updatable Fields:
    - Organization info: name, address, phone_number, company_name
    - Location: country, zip_code
    - Registry: rna_code (format validated)
    - Additional: description
    - Account: email, password

    Args:
        `association_id`: The unique identifier of the association profile to update.
        `association_update`: Object containing the fields to update. Only provided
            fields will be changed; others remain unchanged.
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `AssociationPublic`: The updated association profile with all current information.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `403 InsufficientPermissionsError`: If the authenticated user is not the profile owner.
        `404 NotFoundError`: If no association exists with the given ID.
        `422 ValidationError`: If the new RNA code format is invalid.
    """
    association = association_service.get_association(session, association_id)
    if not association:
        raise NotFoundError("Association", association_id)

    if association.id_user != current_user.id_user:
        raise InsufficientPermissionsError("update this association profile")

    updated = association_service.update_association(
        session, association_id, association_update
    )
    session.commit()
    session.refresh(updated)
    return association_service.to_association_public(session, updated)


@router.delete("/{association_id}", status_code=204)
async def delete_association(
    association_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete the association profile and associated user account permanently.

    **⚠️ Warning**: This action is irreversible and will permanently delete:
    - The association profile
    - The associated user account
    - All missions created by this association
    - Related documents and data

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token
    - **Owner only**: Only the profile owner can perform deletion

    Args:
        `association_id`: The unique identifier of the association profile to delete.
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `403 InsufficientPermissionsError`: If the authenticated user is not the profile owner.
        `404 NotFoundError`: If no association exists with the given ID.
    """
    association = session.get(Association, association_id)
    if not association:
        raise NotFoundError("Association", association_id)

    if association.id_user != current_user.id_user:
        raise InsufficientPermissionsError("delete this association profile")

    await association_service.delete_association(session, association_id)
    await to_thread.run_sync(session.commit)


# Mission endpoints


@router.post("/me/missions", response_model=MissionPublic)
def create_association_mission(
    *,
    session: Annotated[Session, Depends(get_session)],
    mission_in: MissionCreate,
    current_association: Annotated[Association, Depends(get_current_association)],
) -> MissionPublic:
    """
    Create a new mission for the authenticated association.

    Registers a new volunteering mission under the authenticated association.
    The mission will be immediately associated with the current user's profile.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token.
    - **Association only**: The current user must have an association profile.

    Args:
        `mission_in`: Mission details including name, dates, description,
            location ID, and category ID.
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `MissionPublic`: The newly created mission with its unique ID.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the current user is not an association or if
            referenced location/category does not exist.
    """
    # Check if association is verified/approved
    if current_association.verification_status != ProcessingStatus.APPROVED:
        raise ValidationError(
            f"Your association must be verified before creating missions. "
            f"Current status: {current_association.verification_status.value}. "
            f"Please upload a validation document and wait for admin approval.",
            field="verification_status",
        )

    # Enforce the association ID to be the current authenticated one
    mission_in.id_asso = ensure_id(current_association.id_asso, "Association")

    mission = mission_service.create_mission(session, mission_in)
    session.commit()
    session.refresh(mission)
    return MissionPublic.model_validate(mission)


@router.get("/me/missions", response_model=list[MissionPublic])
def read_association_missions(
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> list[MissionPublic]:
    """
    Retrieve all missions created by the authenticated association.

    Returns a list of all missions owned by the current association profile.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token.
    - **Association only**: The current user must have an association profile.

    Args:
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `list[MissionPublic]`: A list of missions created by the association.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the current user has no association profile.
    """
    missions = mission_service.get_missions_by_association(
        session,
        current_association.id_asso,  # type: ignore
    )
    return [MissionPublic.model_validate(m) for m in missions]


@router.patch("/me/missions/{mission_id}", response_model=MissionPublic)
def update_association_mission(
    mission_id: int,
    mission_update: MissionUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> MissionPublic:
    """
    Update a mission owned by the authenticated association.

    Allows partial updates to mission details. Only the mission owner can
    perform updates.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token.
    - **Owner only**: The mission must belong to the authenticated association.

    Args:
        `mission_id`: The unique identifier of the mission to update.
        `mission_update`: Object containing the fields to update.
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `MissionPublic`: The updated mission.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the mission or association profile does not exist.
        `403 InsufficientPermissionsError`: If the mission belongs to another association.
    """
    updated_mission = mission_service.update_mission(
        session,
        mission_id,
        mission_update,
        association_id=current_association.id_asso,
    )
    session.commit()
    session.refresh(updated_mission)
    return MissionPublic.model_validate(updated_mission)


@router.delete("/me/missions/{mission_id}", status_code=204)
async def delete_association_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> None:
    """
    Delete a mission owned by the authenticated association.

    Permanently removes a mission. This action is only permitted for the
    association that created the mission.

    Sends email notifications to all volunteers with approved applications.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token.
    - **Owner only**: The mission must belong to the authenticated association.

    Args:
        `mission_id`: The unique identifier of the mission to delete.
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the mission does not exist or user has no profile.
        `403 InsufficientPermissionsError`: If the mission belongs to a different association.
    """
    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    await mission_service.delete_mission(
        session, mission_id, association_id=current_association.id_asso
    )
    await to_thread.run_sync(session.commit)


# ============================================================================
# ENGAGEMENT MANAGEMENT ENDPOINTS
# ============================================================================


@router.patch(
    "/me/engagements/{volunteer_id}/{mission_id}/approve",
    response_model=EngagementPublic,
)
async def approve_engagement(
    volunteer_id: int,
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> EngagementPublic:
    """
    Approve a volunteer's application to a mission.

    Sends email to volunteer and creates notification for association.
    If mission reaches minimum capacity, sends additional notification.

    ### Authorization:
    - Must be authenticated as association
    - Mission must belong to the authenticated association

    Args:
        volunteer_id: The volunteer's ID.
        mission_id: The mission's ID.
        session: Database session (automatically injected).
        current_association: Authenticated association profile (automatically injected).

    Returns:
        EngagementPublic: The approved engagement.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile, mission, volunteer, or engagement doesn't exist.
    """
    # Verify mission belongs to association
    mission = session.get(Mission, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if mission.id_asso != current_association.id_asso:
        raise InsufficientPermissionsError("approve applications for this mission")

    engagement = await engagement_service.approve_application_by_ids(
        session, volunteer_id, mission_id
    )
    await to_thread.run_sync(lambda: (session.commit(), session.refresh(engagement)))
    return EngagementPublic.model_validate(engagement)


@router.patch(
    "/me/engagements/{volunteer_id}/{mission_id}/reject",
    response_model=EngagementPublic,
)
async def reject_engagement(
    volunteer_id: int,
    mission_id: int,
    rejection: RejectEngagementRequest,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> EngagementPublic:
    """
    Reject a volunteer's application to a mission.

    Sends email notification to volunteer with rejection reason.

    ### Authorization:
    - Must be authenticated as association
    - Mission must belong to the authenticated association

    Args:
        volunteer_id: The volunteer's ID.
        mission_id: The mission's ID.
        rejection: Request body containing rejection reason.
        session: Database session (automatically injected).
        current_association: Authenticated association profile (automatically injected).

    Returns:
        EngagementPublic: The rejected engagement.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile, mission, volunteer, or engagement doesn't exist.
    """
    # Verify mission belongs to association
    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if mission.id_asso != current_association.id_asso:
        raise InsufficientPermissionsError("reject applications for this mission")

    engagement = await engagement_service.reject_application(
        session, volunteer_id, mission_id, rejection.rejection_reason
    )
    await to_thread.run_sync(lambda: (session.commit(), session.refresh(engagement)))
    return EngagementPublic.model_validate(engagement)


# ============================================================================
# BULK EMAIL ENDPOINT
# ============================================================================


@router.post("/me/missions/{mission_id}/send-email")
async def send_bulk_email_to_volunteers(
    mission_id: int,
    email_request: BulkEmailRequest,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
) -> dict:
    """
    Send email to all volunteers with approved applications for a mission.

    ### Authorization:
    - Must be authenticated as association
    - Mission must belong to the authenticated association

    ### Request Body:
    - **subject**: Email subject (1-200 chars)
    - **message**: Email body (1-2000 chars, plain text/simple HTML)

    ### Response:
    - **sent_count**: Number of emails successfully sent
    - **failed_count**: Number of failed sends

    Args:
        mission_id: The mission's ID.
        email_request: Email request containing subject and message.
        session: Database session (automatically injected).
        current_association: Authenticated association profile (automatically injected).

    Returns:
        dict: Dictionary with sent_count, failed_count, and total_recipients.

    Raises:
        401 Unauthorized: If no valid authentication token is provided.
        404 NotFoundError: If the association profile or mission doesn't exist.
        403 InsufficientPermissionsError: If mission doesn't belong to association.
    """
    # Get mission and verify ownership
    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if mission.id_asso != current_association.id_asso:
        raise InsufficientPermissionsError("send emails for this mission")

    # Get all approved volunteers

    engagements = await to_thread.run_sync(
        lambda: session.exec(
            select(Engagement).where(
                Engagement.id_mission == mission_id,
                Engagement.state == ProcessingStatus.APPROVED,
            )
        ).all()
    )

    volunteer_ids = [e.id_volunteer for e in engagements]

    def get_volunteers():
        return session.exec(
            select(Volunteer)
            .where(
                cast(InstrumentedAttribute, Volunteer.id_volunteer).in_(volunteer_ids)
            )
            .options(selectinload(cast(InstrumentedAttribute, Volunteer.user)))
        ).all()

    if volunteer_ids:
        volunteers = await to_thread.run_sync(get_volunteers)
        volunteers_by_id = {v.id_volunteer: v for v in volunteers}
    else:
        volunteers_by_id = {}

    sent_count = 0
    failed_count = 0

    for engagement in engagements:
        volunteer = volunteers_by_id.get(engagement.id_volunteer)

        if volunteer and volunteer.user:
            volunteer_name = f"{volunteer.first_name} {volunteer.last_name}"

            try:
                await send_notification_email(
                    template_name="bulk_message",
                    recipient_email=volunteer.user.email,
                    context={
                        "volunteer_name": volunteer_name,
                        "association_name": current_association.name,
                        "mission_name": mission.name,
                        "subject": email_request.subject,
                        "custom_message": email_request.message,
                    },
                )
                sent_count += 1
            except Exception:
                # Avoid logging full recipient emails (PII)
                logger.exception(
                    "Failed to send bulk email (mission_id={})", mission_id
                )
                failed_count += 1

    return {
        "sent_count": sent_count,
        "failed_count": failed_count,
        "total_recipients": len(engagements),
    }
