"""Analytics service for admin dashboard statistics."""

from datetime import date, datetime
from typing import cast
from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select, func

from app.models.association import Association
from app.models.mission import Mission
from app.models.user import User
from app.models.report import Report
from app.models.enums import ProcessingStatus, UserType


def get_overview_statistics(session: Session) -> dict:
    """
    Get overview statistics for admin dashboard.

    Returns:
        dict: Dictionary containing counts for validated associations, completed missions,
              total users, pending reports, and pending associations.
    """
    # Count validated associations
    validated_associations = session.exec(
        select(func.count())
        .select_from(Association)
        .where(Association.verification_status == ProcessingStatus.APPROVED)
    ).one()

    # Count completed missions (date_end < today)
    today = date.today()
    completed_missions = session.exec(
        select(func.count()).select_from(Mission).where(Mission.date_end < today)
    ).one()

    # Count total users
    total_users = session.exec(select(func.count()).select_from(User)).one()

    # Count pending reports
    pending_reports = session.exec(
        select(func.count())
        .select_from(Report)
        .where(Report.state == ProcessingStatus.PENDING)
    ).one()

    # Count pending associations
    pending_associations = session.exec(
        select(func.count())
        .select_from(Association)
        .where(Association.verification_status == ProcessingStatus.PENDING)
    ).one()

    return {
        "total_validated_associations": validated_associations,
        "total_completed_missions": completed_missions,
        "total_users": total_users,
        "pending_reports_count": pending_reports,
        "pending_associations_count": pending_associations,
    }


def get_volunteers_by_month(session: Session, months: int = 12) -> list[dict]:
    """
    Get volunteer registration counts by month.

    Args:
        session: Database session
        months: Number of months to include (default: 12)

    Returns:
        list[dict]: List of monthly data points with format {"month": "YYYY-MM", "value": count}
    """
    today = date.today()
    start_of_current_month = datetime(today.year, today.month, 1)
    start_date: datetime = cast(
        datetime, start_of_current_month - relativedelta(months=months - 1)
    )

    # Query volunteer registrations grouped by month
    results = session.exec(
        select(
            func.date_trunc("month", User.date_creation).label("month"),
            func.count().label("count"),
        )
        .where(User.user_type == UserType.VOLUNTEER, User.date_creation >= start_date)
        .group_by("month")
        .order_by("month")
    ).all()

    # Convert results to dict for easy lookup
    data_by_month = {r[0].strftime("%Y-%m"): r[1] for r in results}

    # Fill all months including zeros for months with no data
    result = []
    current: datetime = start_date
    for _ in range(months):
        month_str = current.strftime("%Y-%m")
        result.append({"month": month_str, "value": data_by_month.get(month_str, 0)})
        current = cast(datetime, current + relativedelta(months=1))
    return result


def get_missions_by_month(session: Session, months: int = 12) -> list[dict]:
    """
    Get completed mission counts by month.

    Args:
        session: Database session
        months: Number of months to include (default: 12)

    Returns:
        list[dict]: List of monthly data points with format {"month": "YYYY-MM", "value": count}
    """
    today = date.today()
    start_of_current_month = datetime(today.year, today.month, 1)
    temp_start: datetime = cast(
        datetime, start_of_current_month - relativedelta(months=months - 1)
    )
    start_date: date = temp_start.date()

    # Query completed missions grouped by month (where date_end is in that month and before today)
    results = session.exec(
        select(
            func.date_trunc("month", Mission.date_end).label("month"),
            func.count().label("count"),
        )
        .where(Mission.date_end >= start_date, Mission.date_end < today)
        .group_by("month")
        .order_by("month")
    ).all()

    # Convert results to dict for easy lookup
    data_by_month = {r[0].strftime("%Y-%m"): r[1] for r in results}

    # Fill all months including zeros
    result = []
    current: datetime = datetime(start_date.year, start_date.month, 1)
    for _ in range(months):
        month_str = current.strftime("%Y-%m")
        result.append({"month": month_str, "value": data_by_month.get(month_str, 0)})
        current = cast(datetime, current + relativedelta(months=1))
    return result


def get_report_statistics(session: Session) -> dict:
    """
    Get report counts by processing state.

    Returns:
        dict: Dictionary containing counts for pending, accepted, and rejected reports.
    """
    pending = session.exec(
        select(func.count())
        .select_from(Report)
        .where(Report.state == ProcessingStatus.PENDING)
    ).one()

    accepted = session.exec(
        select(func.count())
        .select_from(Report)
        .where(Report.state == ProcessingStatus.APPROVED)
    ).one()

    rejected = session.exec(
        select(func.count())
        .select_from(Report)
        .where(Report.state == ProcessingStatus.REJECTED)
    ).one()

    return {"pending": pending, "accepted": accepted, "rejected": rejected}
