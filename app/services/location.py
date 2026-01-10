"""Location service module for CRUD operations."""

from sqlmodel import Session, select, func
from sqlalchemy.exc import IntegrityError

from app.models.location import Location, LocationCreate, LocationUpdate
from app.models.mission import Mission
from app.exceptions import NotFoundError, ValidationError


def create_location(session: Session, location_in: LocationCreate) -> Location:
    """
    Create a new location.

    Args:
        session: Database session
        location_in: Location creation data

    Returns:
        Location: The created location instance

    Raises:
        ValidationError: If location data is invalid
    """
    db_location = Location.model_validate(location_in)
    session.add(db_location)
    try:
        session.commit()
        session.refresh(db_location)
    except IntegrityError as e:
        session.rollback()
        raise ValidationError(f"Failed to create location: {str(e)}")
    return db_location


def get_location(session: Session, location_id: int) -> Location | None:
    """
    Retrieve a location by ID.

    Args:
        session: Database session
        location_id: The location's primary key

    Returns:
        Location | None: The location or None if not found
    """
    return session.exec(
        select(Location).where(Location.id_location == location_id)
    ).first()


def get_locations(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[Location]:
    """
    Retrieve a paginated list of locations.

    Args:
        session: Database session
        offset: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        list[Location]: List of locations
    """
    statement = select(Location).offset(offset).limit(limit)
    return list(session.exec(statement).all())


def get_location_with_mission_count(session: Session, location_id: int) -> dict:
    """
    Get location with count of missions using it.

    Args:
        session: Database session
        location_id: The location's primary key

    Returns:
        dict: Location data with mission_count field

    Raises:
        NotFoundError: If location doesn't exist
    """
    location = get_location(session, location_id)
    if not location:
        raise NotFoundError("Location", location_id)

    mission_count = session.exec(
        select(func.count())
        .select_from(Mission)
        .where(Mission.id_location == location_id)
    ).one()

    return {**location.model_dump(), "mission_count": mission_count}


def get_all_locations_with_counts(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[dict]:
    """
    Get all locations with mission counts.

    Args:
        session: Database session
        offset: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        list[dict]: List of locations with mission_count field
    """
    # Query locations with mission counts in a single query
    statement = (
        select(
            Location,
            func.count(Mission.id_mission).label("mission_count"),  # type: ignore
        )
        .outerjoin(Mission, Mission.id_location == Location.id_location)  # type: ignore
        .group_by(Location.id_location)  # type: ignore
        .offset(offset)
        .limit(limit)
    )

    results = session.exec(statement).all()
    return [
        {**location.model_dump(), "mission_count": count} for location, count in results
    ]


def update_location(
    session: Session, location_id: int, location_update: LocationUpdate
) -> Location:
    """
    Update an existing location.

    Args:
        session: Database session
        location_id: The location's primary key
        location_update: Update data

    Returns:
        Location: The updated location

    Raises:
        NotFoundError: If location doesn't exist
    """
    db_location = get_location(session, location_id)
    if not db_location:
        raise NotFoundError("Location", location_id)

    update_data = location_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_location, key, value)

    session.add(db_location)
    try:
        session.commit()
        session.refresh(db_location)
    except IntegrityError as e:
        session.rollback()
        raise ValidationError(f"Failed to update location: {str(e)}")
    return db_location


def delete_location(session: Session, location_id: int) -> None:
    """
    Delete a location.

    Args:
        session: Database session
        location_id: The location's primary key

    Raises:
        NotFoundError: If location doesn't exist
        ValidationError: If location is still referenced by missions
    """
    db_location = get_location(session, location_id)
    if not db_location:
        raise NotFoundError("Location", location_id)

    # Check if any missions reference this location
    mission_count = session.exec(
        select(func.count())
        .select_from(Mission)
        .where(Mission.id_location == location_id)
    ).one()

    if mission_count > 0:
        raise ValidationError(
            f"Cannot delete location: {mission_count} mission(s) still reference it. "
            "Please reassign or delete those missions first."
        )

    session.delete(db_location)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise ValidationError(f"Failed to delete location: {str(e)}")
