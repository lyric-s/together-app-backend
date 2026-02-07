"""AI Report service module for CRUD operations."""

from sqlmodel import Session, select
from app.models.ai_report import AIReport, AIReportUpdate
from app.exceptions import NotFoundError


def get_ai_report(session: Session, report_id: int) -> AIReport | None:
    """
    Retrieve an AI report by ID.
    """
    return session.exec(select(AIReport).where(AIReport.id_report == report_id)).first()


def get_ai_reports(
    session: Session, *, offset: int = 0, limit: int = 100
) -> list[AIReport]:
    """
    Retrieve all AI reports, ordered by most recent first.
    """
    statement = (
        select(AIReport)
        .order_by(AIReport.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def update_ai_report_state(
    session: Session, report_id: int, report_update: AIReportUpdate
) -> AIReport:
    """
    Update an AI report's state (APPROVED/REJECTED).
    """
    db_report = get_ai_report(session, report_id)
    if not db_report:
        raise NotFoundError("AIReport", report_id)

    db_report.state = report_update.state
    session.add(db_report)
    session.commit()
    session.refresh(db_report)

    return db_report