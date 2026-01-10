"""Report service module for CRUD operations."""

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.report import Report, ReportCreate, ReportUpdate
from app.models.user import User
from app.models.enums import ProcessingStatus
from app.exceptions import NotFoundError, AlreadyExistsError, ValidationError


def create_report(
    session: Session, reporter_user_id: int, report_in: ReportCreate
) -> Report:
    """
    Create a new report from one user about another user.

    Parameters:
        session: Database session.
        reporter_user_id: The ID of the user making the report.
        report_in: Report data (type, target, reason, id_user_reported).

    Returns:
        Report: The created report with state=PENDING.

    Raises:
        NotFoundError: If the reported user doesn't exist.
        ValidationError: If user tries to report themselves.
        AlreadyExistsError: If reporter already has a PENDING report against this user.
    """
    # Prevent self-reporting
    if reporter_user_id == report_in.id_user_reported:
        raise ValidationError("You cannot report yourself")

    # Check reported user exists
    reported_user = session.exec(
        select(User).where(User.id_user == report_in.id_user_reported)
    ).first()
    if not reported_user:
        raise NotFoundError("User", report_in.id_user_reported)

    # Check for existing PENDING report
    existing = session.exec(
        select(Report).where(
            Report.id_user_reporter == reporter_user_id,
            Report.id_user_reported == report_in.id_user_reported,
            Report.state == ProcessingStatus.PENDING,
        )
    ).first()
    if existing:
        raise AlreadyExistsError("Pending report", "user", report_in.id_user_reported)

    # Create report
    db_report = Report.model_validate(
        report_in, update={"id_user_reporter": reporter_user_id}
    )
    session.add(db_report)
    try:
        session.commit()
        session.refresh(db_report)
    except IntegrityError:
        session.rollback()
        raise AlreadyExistsError("Pending report", "user", report_in.id_user_reported)

    return db_report


def get_report(session: Session, report_id: int) -> Report | None:
    """
    Retrieve a report by ID.

    Parameters:
        session: Database session.
        report_id: The report's primary key.

    Returns:
        Report | None: The report or None if not found.
    """
    return session.exec(select(Report).where(Report.id_report == report_id)).first()


def get_reports_by_reporter(
    session: Session, reporter_user_id: int, *, offset: int = 0, limit: int = 100
) -> list[Report]:
    """
    Retrieve reports made by a specific user.

    Parameters:
        session: Database session.
        reporter_user_id: The user ID of the reporter.
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        list[Report]: Reports made by this user, ordered by most recent first.
    """
    statement = (
        select(Report)
        .where(Report.id_user_reporter == reporter_user_id)
        .order_by(Report.date_reporting.desc())  # type: ignore
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_reports_by_reported_user(
    session: Session, reported_user_id: int, *, offset: int = 0, limit: int = 100
) -> list[Report]:
    """
    Retrieve reports against a specific user.

    Typically used by admins to view all reports against a user.

    Parameters:
        session: Database session.
        reported_user_id: The user ID being reported.
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        list[Report]: Reports against this user, ordered by most recent first.
    """
    statement = (
        select(Report)
        .where(Report.id_user_reported == reported_user_id)
        .order_by(Report.date_reporting.desc())  # type: ignore
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_all_reports(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[Report]:
    """
    Retrieve all reports with relationships eager-loaded (admin function).

    Parameters:
        session: Database session.
        offset: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        list[Report]: All reports with reporter and reported_user relationships loaded,
                     ordered by most recent first.
    """
    statement = (
        select(Report)
        .options(
            selectinload(Report.reporter).selectinload(User.volunteer_profile),  # type: ignore
            selectinload(Report.reporter).selectinload(User.association_profile),  # type: ignore
            selectinload(Report.reported_user).selectinload(User.volunteer_profile),  # type: ignore
            selectinload(Report.reported_user).selectinload(User.association_profile),  # type: ignore
        )
        .order_by(Report.date_reporting.desc())  # type: ignore
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def update_report(
    session: Session, report_id: int, report_update: ReportUpdate
) -> Report:
    """
    Update a report's state (admin function).

    Parameters:
        session: Database session.
        report_id: The report's primary key.
        report_update: Update data (currently only state can be updated).

    Returns:
        Report: The updated report.

    Raises:
        NotFoundError: If the report doesn't exist.
    """
    db_report = get_report(session, report_id)
    if not db_report:
        raise NotFoundError("Report", report_id)

    update_data = report_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_report, key, value)

    session.add(db_report)
    session.commit()
    session.refresh(db_report)

    return db_report


def delete_report(session: Session, report_id: int) -> None:
    """
    Delete a report (admin function).

    Parameters:
        session: Database session.
        report_id: The report's primary key.

    Raises:
        NotFoundError: If the report doesn't exist.
    """
    db_report = get_report(session, report_id)
    if not db_report:
        raise NotFoundError("Report", report_id)

    session.delete(db_report)
    session.commit()


def _get_user_display_name(user: User) -> str:
    """
    Get display name for a user based on their type.

    For volunteers: Returns "FirstName LastName"
    For associations: Returns the association name
    Otherwise: Returns the username

    Args:
        user: User instance with relationships loaded

    Returns:
        str: Display name for the user
    """
    from app.models.enums import UserType

    if user.user_type == UserType.VOLUNTEER and user.volunteer_profile:
        return f"{user.volunteer_profile.first_name} {user.volunteer_profile.last_name}"
    elif user.user_type == UserType.ASSOCIATION and user.association_profile:
        return user.association_profile.name
    return user.username


def to_report_public(report: Report) -> dict:
    """
    Convert Report to ReportPublic with computed name fields.

    Args:
        report: Report instance with reporter and reported_user relationships loaded

    Returns:
        dict: Dictionary suitable for ReportPublic model validation
    """
    reporter_name = _get_user_display_name(report.reporter) if report.reporter else ""
    reported_name = (
        _get_user_display_name(report.reported_user) if report.reported_user else ""
    )

    return {
        **report.model_dump(exclude={"reporter", "reported_user"}),
        "reporter_name": reporter_name,
        "reported_name": reported_name,
    }
