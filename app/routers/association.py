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
from app.models.engagement import (
    Engagement,
    RejectEngagementRequest,
    EngagementPublic,
    EngagementWithVolunteer,
)
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
    Register a new association (non-profit organization) with user account.

    Creates both a User account (with user_type=ASSOCIATION) and the associated
    Association profile in a single atomic operation. This is the signup endpoint
    for non-profit organizations joining the platform.

    ## Request Body

    The request must include two nested objects:

    **user_in**:
    - `username` (string, required): Unique username for login (3-50 characters)
    - `email` (string, required): Organization's contact email
    - `password` (string, required): Strong password (8-100 characters)

    **association_in**:
    - `name` (string, required): Organization's legal name
    - `rna` (string, required): French RNA registration number (format: W + 9 digits)
    - `address` (string, required): Organization's physical address
    - `zip_code` (string, required): Postal code
    - `phone_number` (string, required): Contact phone number
    - `description` (string, optional): Brief description of the organization's mission

    ## Example Request

    ```json
    {
      "user_in": {
        "username": "paris_food_bank",
        "email": "contact@parisfoodbank.org",
        "password": "SecureOrgPass123!"
      },
      "association_in": {
        "name": "Paris Food Bank",
        "rna": "W751234567",
        "address": "123 Avenue de la République",
        "zip_code": "75011",
        "phone_number": "+33143556677",
        "description": "Fighting food insecurity in Paris since 1995"
      }
    }
    ```

    ## Example Response

    ```json
    {
      "id_asso": 5,
      "id_user": 129,
      "name": "Paris Food Bank",
      "rna": "W751234567",
      "address": "123 Avenue de la République",
      "zip_code": "75011",
      "phone_number": "+33143556677",
      "description": "Fighting food insecurity in Paris since 1995",
      "verif_state": "PENDING",
      "user": {
        "id_user": 129,
        "username": "paris_food_bank",
        "email": "contact@parisfoodbank.org",
        "user_type": "ASSOCIATION"
      }
    }
    ```

    ## Verification Process

    After registration:
    1. **Status**: Account created with `PENDING` verification status
    2. **Document Upload**: Association must upload verification documents (RNA certificate, etc.)
    3. **Admin Review**: Platform admin verifies documents and organization legitimacy
    4. **Activation**: Status changes to `APPROVED` and organization can create missions

    ## What Gets Created

    - **User account**: Authentication credentials with `user_type=ASSOCIATION`
    - **Association profile**: Organization details with `PENDING` verification status
    - **Automatic linking**: User and association records are connected

    Parameters:
        user_in: User account data including username, email, and password.
        association_in: Association profile data including name, RNA code, address, phone, and optional description.
        session: Database session (automatically injected via `Depends(get_session)`).

    Returns:
        `AssociationPublic`: The newly created association profile with user information and verification status.

    Raises:
        `409 AlreadyExistsError`: If the username, email, or RNA code already exists.
        `422 ValidationError`: If RNA code format is invalid (must be W followed by 9 digits), or other validation failures.
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
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).
        `unread_only`: Filter to only unread notifications.
        `offset`: Pagination offset.
        `limit`: Maximum number of results to return.

    Returns:
        `list[NotificationPublic]`: List of notifications ordered by date (newest first).

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the association profile doesn't exist.
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
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).

    Returns:
        `dict`: Dictionary containing `unread_count`.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the association profile doesn't exist.
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
        `session`: Database session (automatically injected).
        `current_association`: Authenticated association profile (automatically injected).
        `mark_read`: Request body containing notification IDs to mark as read.

    Returns:
        `dict`: Dictionary containing `marked_count`.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the association profile doesn't exist.
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


@router.get(
    "/me/missions/{mission_id}/engagements",
    response_model=list[EngagementWithVolunteer],
)
def get_mission_engagements(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_association: Annotated[Association, Depends(get_current_association)],
    status: Annotated[
        ProcessingStatus | None,
        Query(description="Filter by engagement status (PENDING, APPROVED, REJECTED)"),
    ] = None,
) -> list[EngagementWithVolunteer]:
    """
    Retrieve all volunteer engagements (applications) for a specific mission.

    Returns a list of all volunteers who have applied to the mission, including
    their application details and contact information. Useful for displaying an
    application management dashboard where associations can review and process
    volunteer applications.

    ## Query Parameters

    - `status` (optional): Filter engagements by status
      - `PENDING`: Show only pending applications awaiting review
      - `APPROVED`: Show only approved volunteers
      - `REJECTED`: Show only rejected applications
      - Omit to show all engagements regardless of status

    ## Example Requests

    **All engagements for a mission:**
    ```
    GET /associations/me/missions/42/engagements
    Authorization: Bearer your_jwt_token
    ```

    **Only pending applications:**
    ```
    GET /associations/me/missions/42/engagements?status=PENDING
    Authorization: Bearer your_jwt_token
    ```

    ## Example Response

    ```json
    [
      {
        "id_volunteer": 15,
        "id_mission": 42,
        "state": "PENDING",
        "message": "I have 5 years of experience with food bank volunteering and would love to contribute to this mission.",
        "application_date": "2026-01-14",
        "rejection_reason": null,
        "volunteer_first_name": "Sarah",
        "volunteer_last_name": "Johnson",
        "volunteer_email": "sarah@example.com",
        "volunteer_phone": "+33612345678",
        "volunteer_skills": "First aid certified, Fluent in English and French"
      },
      {
        "id_volunteer": 23,
        "id_mission": 42,
        "state": "APPROVED",
        "message": "Looking forward to helping out!",
        "application_date": "2026-01-13",
        "rejection_reason": null,
        "volunteer_first_name": "Michael",
        "volunteer_last_name": "Chen",
        "volunteer_email": "mchen@example.com",
        "volunteer_phone": "+33698765432",
        "volunteer_skills": "Experience with logistics and inventory management"
      }
    ]
    ```

    ## Response Details

    Each engagement includes:
    - **Application info**: Status, optional message from volunteer, application date
    - **Volunteer details**: Name, email, phone, skills
    - **Rejection reason**: Present if status is `REJECTED`, otherwise `null`

    Results are ordered by application date (most recent first).

    ## Use Cases

    - **Application dashboard**: Display all pending applications for review
    - **Volunteer roster**: See approved volunteers for mission coordination
    - **Application history**: Review all applications including rejected ones

    Parameters:
        mission_id: The unique identifier of the mission to get engagements for.
        session: Database session (automatically injected via `Depends(get_session)`).
        current_association: Authenticated association profile (automatically injected via `Depends(get_current_association)`).
        status: Optional filter by engagement status (PENDING, APPROVED, REJECTED).

    Returns:
        `list[EngagementWithVolunteer]`: List of engagements with volunteer details, ordered by application date (most recent first).

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `403 InsufficientPermissionsError`: If the mission doesn't belong to the authenticated association.
        `404 NotFoundError`: If the mission doesn't exist.
    """
    # Verify mission belongs to the authenticated association
    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if mission.id_asso != current_association.id_asso:
        raise InsufficientPermissionsError("access engagements for this mission")

    # Get engagements with optional status filter
    return engagement_service.get_mission_engagements(session, mission_id, status)


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
