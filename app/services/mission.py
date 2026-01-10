"""Mission service module for CRUD operations."""

from sqlmodel import Session, select

from app.models.mission import Mission, MissionCreate, MissionUpdate
from app.models.location import Location
from app.models.category import Category
from app.exceptions import NotFoundError, InsufficientPermissionsError


def create_mission(session: Session, mission_in: MissionCreate) -> Mission:
    """
    Create a new mission.

    Validates that the provided location and category IDs exist.

    Parameters:
        session: Database session.
        mission_in: Mission creation data.

    Returns:
        Mission: The created Mission model instance.

    Raises:
        NotFoundError: If the location or category ID does not exist.
    """
    # Validate location exists
    location = session.get(Location, mission_in.id_location)
    if not location:
        raise NotFoundError("Location", mission_in.id_location)

    # Validate category exists
    category = session.get(Category, mission_in.id_categ)
    if not category:
        raise NotFoundError("Category", mission_in.id_categ)

    # Association ID existence is implicitly checked by FK constraint,
    # but logically checked before calling this service in the router usually.
    # However, if we want explicit check:
    # from app.models.association import Association
    # if not session.get(Association, mission_in.id_asso):
    #     raise NotFoundError("Association", mission_in.id_asso)

    mission = Mission.model_validate(mission_in)
    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


def get_mission(session: Session, mission_id: int) -> Mission | None:
    """
    Retrieve a mission by ID.

    Parameters:
        session: Database session.
        mission_id: The mission's primary key.

    Returns:
        Mission | None: The mission record or None if not found.
    """
    return session.get(Mission, mission_id)


def get_missions_by_association(session: Session, association_id: int) -> list[Mission]:
    """
    Retrieve all missions created by a specific association.

    Parameters:
        session: Database session.
        association_id: The association's unique identifier.

    Returns:
        list[Mission]: A list of Mission objects belonging to the association.
    """
    statement = select(Mission).where(Mission.id_asso == association_id)
    return list(session.exec(statement).all())


def update_mission(
    session: Session,
    mission_id: int,
    mission_update: MissionUpdate,
    association_id: int | None = None,
) -> Mission:
    """
    Update an existing mission.

    If association_id is provided, verifies that the mission belongs to that association.

    Parameters:
        session: Database session.
        mission_id: Primary key of the mission to update.
        mission_update: Update data.
        association_id: Optional ID of the association requesting update.

    Returns:
        Mission: The updated Mission model.

    Raises:
        NotFoundError: If no mission exists with the given mission_id.
        InsufficientPermissionsError: If association_id is provided but does not match the mission's owner.
    """
    mission = session.get(Mission, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if association_id is not None and mission.id_asso != association_id:
        raise InsufficientPermissionsError("update this mission")

    update_data = mission_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mission, key, value)

    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


def delete_mission(
    session: Session, mission_id: int, association_id: int | None = None
) -> None:
    """
    Delete a mission.

    If association_id is provided, verifies that the mission belongs to that association.

    Parameters:
        session: Database session.
        mission_id: Primary key of the mission to delete.
        association_id: Optional ID of the association requesting deletion.

    Raises:
        NotFoundError: If no mission exists with the given mission_id.
        InsufficientPermissionsError: If association_id is provided but does not match the mission's owner.
    """
    mission = session.get(Mission, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if association_id is not None and mission.id_asso != association_id:
        raise InsufficientPermissionsError("delete this mission")

    session.delete(mission)
    session.commit()
