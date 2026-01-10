"""Association router module for CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User, UserCreate
from app.models.association import (
    AssociationCreate,
    AssociationPublic,
    AssociationUpdate,
)
from app.models.mission import MissionCreate, MissionPublic, MissionUpdate
from app.services import association as association_service
from app.services import mission as mission_service
from app.exceptions import NotFoundError, InsufficientPermissionsError

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
        `400 AlreadyExistsError`: If the username or email already exists.
        `422 ValidationError`: If the RNA code format is invalid.
    """
    association = association_service.create_association(
        session, user_in, association_in
    )
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
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssociationPublic:
    """
    Retrieve the authenticated user's association profile.

    Returns the authenticated user's association profile with all public information
    including active and finished mission counts.

    ### Authentication Required:
    This endpoint requires a valid authentication token.

    Args:
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `AssociationPublic`: The authenticated user's association profile including
            organization details, mission statistics, and linked user account details.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If no association profile exists for the authenticated user.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)
    return association_service.to_association_public(session, association)


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
    return association_service.to_association_public(session, updated)


@router.delete("/{association_id}", status_code=204)
def delete_association(
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
    association = association_service.get_association(session, association_id)
    if not association:
        raise NotFoundError("Association", association_id)

    if association.id_user != current_user.id_user:
        raise InsufficientPermissionsError("delete this association profile")

    association_service.delete_association(session, association_id)


# Mission endpoints


@router.post("/me/missions", response_model=MissionPublic)
def create_association_mission(
    *,
    session: Annotated[Session, Depends(get_session)],
    mission_in: MissionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
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
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `MissionPublic`: The newly created mission with its unique ID.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the current user is not an association or if
            referenced location/category does not exist.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    assert association.id_asso is not None
    # Enforce the association ID to be the current authenticated one
    mission_in.id_asso = association.id_asso

    mission = mission_service.create_mission(session, mission_in)
    return MissionPublic.model_validate(mission)


@router.get("/me/missions", response_model=list[MissionPublic])
def read_association_missions(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[MissionPublic]:
    """
    Retrieve all missions created by the authenticated association.

    Returns a list of all missions owned by the current association profile.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token.
    - **Association only**: The current user must have an association profile.

    Args:
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `list[MissionPublic]`: A list of missions created by the association.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the current user has no association profile.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    assert association.id_asso is not None
    missions = mission_service.get_missions_by_association(session, association.id_asso)
    return [MissionPublic.model_validate(m) for m in missions]


@router.patch("/me/missions/{mission_id}", response_model=MissionPublic)
def update_association_mission(
    mission_id: int,
    mission_update: MissionUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
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
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `MissionPublic`: The updated mission.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the mission or association profile does not exist.
        `403 InsufficientPermissionsError`: If the mission belongs to another association.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    updated_mission = mission_service.update_mission(
        session, mission_id, mission_update, association_id=association.id_asso
    )
    return MissionPublic.model_validate(updated_mission)


@router.delete("/me/missions/{mission_id}", status_code=204)
def delete_association_mission(
    mission_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    Delete a mission owned by the authenticated association.

    Permanently removes a mission. This action is only permitted for the
    association that created the mission.

    ### Authorization:
    - **Authentication required**: Must provide valid authentication token.
    - **Owner only**: The mission must belong to the authenticated association.

    Args:
        `mission_id`: The unique identifier of the mission to delete.
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `None`: Returns 204 No Content on successful deletion.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `404 NotFoundError`: If the mission does not exist or user has no profile.
        `403 InsufficientPermissionsError`: If the mission belongs to a different association.
    """
    assert current_user.id_user is not None
    association = association_service.get_association_by_user_id(
        session, current_user.id_user
    )
    if not association:
        raise NotFoundError("Association profile", current_user.id_user)

    mission = mission_service.get_mission(session, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    mission_service.delete_mission(
        session, mission_id, association_id=association.id_asso
    )
