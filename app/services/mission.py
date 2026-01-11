"""Mission service module for CRUD operations."""

from datetime import date
from sqlmodel import Session, select, func, or_
from sqlalchemy.orm import selectinload

from app.models.mission import Mission, MissionCreate, MissionUpdate, MissionPublic
from app.models.location import Location, LocationPublic
from app.models.category import Category, CategoryPublic
from app.models.association import AssociationPublic
from app.models.engagement import Engagement
from app.models.enums import ProcessingStatus
from app.exceptions import NotFoundError, InsufficientPermissionsError


def create_mission(session: Session, mission_in: MissionCreate) -> Mission:
    """
    Create a new mission with multiple categories.

    Validates that the provided location and all category IDs exist.

    Parameters:
        session: Database session.
        mission_in: Mission creation data including category_ids list.

    Returns:
        Mission: The created Mission model instance with categories relationship.

    Raises:
        NotFoundError: If the location or any category ID does not exist.
    """
    # Validate location exists
    location = session.get(Location, mission_in.id_location)
    if not location:
        raise NotFoundError("Location", mission_in.id_location)

    # Validate all categories exist
    categories = []
    for cat_id in mission_in.category_ids:
        category = session.get(Category, cat_id)
        if not category:
            raise NotFoundError("Category", cat_id)
        categories.append(category)

    # Create mission (exclude category_ids from dict as it's not a db field)
    mission_data = mission_in.model_dump(exclude={"category_ids"})
    mission = Mission.model_validate(mission_data)
    mission.categories = categories  # Set many-to-many relationship

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
        mission_update: Update data (can include category_ids to update categories).
        association_id: Optional ID of the association requesting update.

    Returns:
        Mission: The updated Mission model.

    Raises:
        NotFoundError: If no mission exists with the given mission_id or category doesn't exist.
        InsufficientPermissionsError: If association_id is provided but does not match the mission's owner.
    """
    mission = session.get(Mission, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if association_id is not None and mission.id_asso != association_id:
        raise InsufficientPermissionsError("update this mission")

    update_data = mission_update.model_dump(exclude_unset=True)

    # Handle category_ids separately (many-to-many relationship)
    category_ids = update_data.pop("category_ids", None)
    if category_ids is not None:
        # Validate all categories exist
        categories = []
        for cat_id in category_ids:
            category = session.get(Category, cat_id)
            if not category:
                raise NotFoundError("Category", cat_id)
            categories.append(category)
        mission.categories = categories

    # Update other fields
    for key, value in update_data.items():
        setattr(mission, key, value)

    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


async def delete_mission(
    session: Session, mission_id: int, association_id: int | None = None
) -> None:
    """
    Delete a mission and notify all affected users.

    If association_id is provided, verifies that the mission belongs to that association.
    When deleted by admin (association_id=None), sends email to association and all volunteers.
    When deleted by association, only sends email to volunteers.

    Parameters:
        session: Database session.
        mission_id: Primary key of the mission to delete.
        association_id: Optional ID of the association requesting deletion.
                       If None, assumes admin deletion.

    Raises:
        NotFoundError: If no mission exists with the given mission_id.
        InsufficientPermissionsError: If association_id is provided but does not match the mission's owner.
    """
    from sqlmodel import select
    from app.models.engagement import Engagement
    from app.models.volunteer import Volunteer
    from app.models.association import Association
    from app.models.enums import ProcessingStatus
    from app.services.email import send_notification_email
    from app.services import notification as notification_service
    import logging

    mission = session.get(Mission, mission_id)
    if not mission:
        raise NotFoundError("Mission", mission_id)

    if association_id is not None and mission.id_asso != association_id:
        raise InsufficientPermissionsError("delete this mission")

    # Get association
    association = session.exec(
        select(Association).where(Association.id_asso == mission.id_asso)
    ).first()

    # Get all volunteers with approved applications
    engagements = session.exec(
        select(Engagement).where(
            Engagement.id_mission == mission_id,
            Engagement.state == ProcessingStatus.APPROVED,
        )
    ).all()

    volunteer_emails = []
    for engagement in engagements:
        volunteer = session.exec(
            select(Volunteer).where(Volunteer.id_volunteer == engagement.id_volunteer)
        ).first()

        if volunteer and volunteer.user:
            volunteer_name = f"{volunteer.first_name} {volunteer.last_name}"
            volunteer_emails.append((volunteer.user.email, volunteer_name))

    # Determine if deleted by admin (association_id is None)
    deleted_by_admin = association_id is None

    # Create notification and send email to association if deleted by admin
    if deleted_by_admin and association and association.id_asso is not None:
        notification_service.create_mission_deleted_notification(
            session=session,
            association_id=association.id_asso,
            mission_name=mission.name,
        )

        # Send email to association
        if association.user:
            try:
                await send_notification_email(
                    template_name="mission_deleted_association",
                    recipient_email=association.user.email,
                    context={
                        "association_name": association.name,
                        "mission_name": mission.name,
                    },
                )
            except Exception as e:
                logging.error(
                    f"Failed to send mission deletion email to association: {e}"
                )

    # Send emails to all approved volunteers
    for email, volunteer_name in volunteer_emails:
        try:
            await send_notification_email(
                template_name="mission_deleted_volunteer",
                recipient_email=email,
                context={
                    "volunteer_name": volunteer_name,
                    "mission_name": mission.name,
                },
            )
        except Exception as e:
            logging.error(
                f"Failed to send mission deletion email to volunteer {email}: {e}"
            )

    # Delete mission (cascades to engagements)
    session.delete(mission)
    session.commit()


def search_missions(
    session: Session,
    *,
    category_ids: list[int] | None = None,
    country: str | None = None,
    zip_code: str | None = None,
    date_available: date | None = None,
    search: str | None = None,
    show_full: bool = True,
    offset: int = 0,
    limit: int = 100,
    sort_by: str = "date_start",
) -> list[Mission]:
    """
    Search missions with filters and pagination.

    Parameters:
        session: Database session.
        category_ids: Filter by categories (missions matching ANY category - OR logic).
        country: Filter by location country (exact match).
        zip_code: Filter by zip code prefix.
        date_available: Show missions active on/after this date (defaults to today).
        search: Text search in mission name and description (case-insensitive).
        show_full: Include full missions (default: True). When False, filters out missions at capacity.
        offset: Pagination offset (default: 0).
        limit: Pagination limit (default: 100).
        sort_by: Sort field - "date_start", "name", or "created_at" (default: "date_start").

    Returns:
        list[Mission]: Missions matching filters with eager-loaded relationships.
    """
    # Build query with eager loading
    from app.models.mission_category import MissionCategory

    statement = select(Mission).options(
        selectinload(Mission.location),  # type: ignore
        selectinload(Mission.categories),  # type: ignore
        selectinload(Mission.association),  # type: ignore
    )

    # Filter by categories (OR logic - mission must have at least one of the categories)
    if category_ids:
        statement = (
            statement.join(
                MissionCategory,
                Mission.id_mission == MissionCategory.id_mission,  # type: ignore
            )
            .join(Category, MissionCategory.id_categ == Category.id_categ)  # type: ignore
            .where(Category.id_categ.in_(category_ids))  # type: ignore
            .distinct()
        )

    # Filter by location
    if country or zip_code:
        statement = statement.join(
            Location,
            Mission.id_location == Location.id_location,  # type: ignore
        )
        if country:
            statement = statement.where(Location.country == country)
        if zip_code:
            statement = statement.where(Location.zip_code.startswith(zip_code))  # type: ignore

    # Filter by date availability
    if date_available:
        statement = statement.where(Mission.date_end >= date_available)
    else:
        # Default: only show future/active missions
        today = date.today()
        statement = statement.where(Mission.date_end >= today)

    # Text search in name and description
    if search:
        search_term = f"%{search}%"
        statement = statement.where(
            or_(
                Mission.name.ilike(search_term),  # type: ignore
                Mission.description.ilike(search_term),  # type: ignore
            )
        )

    # Capacity filter (hide full missions if requested)
    if not show_full:
        # Subquery to count approved volunteers per mission
        enrolled_subquery = (
            select(Engagement.id_mission, func.count().label("enrolled_count"))
            .where(Engagement.state == ProcessingStatus.APPROVED)
            .group_by(Engagement.id_mission)  # type: ignore
            .subquery()
        )
        statement = statement.outerjoin(
            enrolled_subquery,
            Mission.id_mission == enrolled_subquery.c.id_mission,  # type: ignore
        ).where(
            or_(
                enrolled_subquery.c.enrolled_count < Mission.capacity_max,  # type: ignore
                enrolled_subquery.c.enrolled_count.is_(None),  # type: ignore
            )
        )

    # Sorting
    if sort_by == "name":
        statement = statement.order_by(Mission.name)
    elif sort_by == "created_at":
        statement = statement.order_by(Mission.id_mission.desc())  # type: ignore
    else:  # default: date_start
        statement = statement.order_by(Mission.date_start)  # type: ignore

    # Pagination
    statement = statement.offset(offset).limit(limit)

    return list(session.exec(statement).all())


def to_mission_public(session: Session, mission: Mission) -> MissionPublic:
    """
    Convert Mission to MissionPublic with computed capacity fields.

    Counts APPROVED volunteers and calculates availability information.

    Parameters:
        session: Database session.
        mission: Mission instance with relationships loaded.

    Returns:
        MissionPublic: Mission with embedded relationships and capacity tracking.
    """
    # Count APPROVED volunteers for this mission
    enrolled_count = session.exec(
        select(func.count())
        .select_from(Engagement)
        .where(
            Engagement.id_mission == mission.id_mission,
            Engagement.state == ProcessingStatus.APPROVED,
        )
    ).one()

    # Compute derived fields
    available_slots = max(0, mission.capacity_max - enrolled_count)
    is_full = enrolled_count >= mission.capacity_max

    # Convert relationships to public models
    location_public = (
        LocationPublic.model_validate(mission.location) if mission.location else None
    )
    categories_public = [CategoryPublic.model_validate(c) for c in mission.categories]
    association_public = (
        AssociationPublic.model_validate(mission.association)
        if mission.association
        else None
    )

    return MissionPublic(
        **mission.model_dump(exclude={"location", "categories", "association"}),
        location=location_public,
        categories=categories_public,
        association=association_public,
        volunteers_enrolled=enrolled_count,
        available_slots=available_slots,
        is_full=is_full,
    )
