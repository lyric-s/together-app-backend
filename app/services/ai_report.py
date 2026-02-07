"""
AI Report service module.

This module provides CRUD operations for AI-generated moderation reports.
It is primarily used by administrative interfaces to review and manage 
automatically flagged content.
"""

from sqlmodel import Session, select, desc
from app.models.ai_report import AIReport, AIReportUpdate
from app.exceptions import NotFoundError


def get_ai_report(session: Session, report_id: int) -> AIReport | None:
    """
    Retrieves a single AI report by its unique identifier.

    Args:
        session (Session): The database session.
        report_id (int): The primary key of the AI report.

    Returns:
        Optional[AIReport]: The found AI report or None if not found.
    """
    return session.exec(select(AIReport).where(AIReport.id_report == report_id)).first()


def get_ai_reports(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[AIReport]:
    """
    Retrieves a paginated list of AI reports, ordered by creation date (newest first).

    Args:
        session (Session): The database session.
        offset (int): Number of records to skip.
        limit (int): Maximum number of records to return.

    Returns:
        list[AIReport]: A list of AI reports.
    """
    statement = (
        select(AIReport)
        .order_by(desc(AIReport.created_at))
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def update_ai_report_state(
    session: Session, report_id: int, report_update: AIReportUpdate
) -> AIReport:
    """
    Updates the moderation state of an AI report (e.g., APPROVED or REJECTED).

    This function updates the state in memory and flushes the changes to the 
    database, but does not commit the transaction. The caller (e.g., a router) 
    is responsible for committing the changes.

    Args:
        session (Session): The database session.
        report_id (int): The unique identifier of the report to update.
        report_update (AIReportUpdate): The new state data.

    Returns:
        AIReport: The updated AI report instance.

    Raises:
        NotFoundError: If the AI report with the given ID does not exist.
    """
    db_report = get_ai_report(session, report_id)
    if not db_report:
        raise NotFoundError("AIReport", report_id)

    db_report.state = report_update.state
    session.add(db_report)
    session.flush()

    return db_report