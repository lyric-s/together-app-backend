from typing import List, Optional

from loguru import logger
from sqlmodel import Session, select
from fastapi import HTTPException

from app.models.ai_report import AIReport, AIReportUpdate
from app.models.enums import ProcessingStatus
from app.exceptions import NotFoundError


def get_ai_report_by_id(db: Session, report_id: int) -> AIReport:
    """
    Retrieve a single AI report by its ID.

    Args:
        db (Session): The database session.
        report_id (int): The ID of the AI report to retrieve.

    Returns:
        AIReport: The requested AI report.

    Raises:
        NotFoundError: If no AI report with the given ID is found.
    """
    db_report = db.get(AIReport, report_id)
    if not db_report:
        raise NotFoundError("AI Report", report_id)
    return db_report


def get_all_ai_reports(
    db: Session,
    offset: int = 0,
    limit: int = 100,
    status: Optional[ProcessingStatus] = None,
) -> List[AIReport]:
    """
    Retrieve a list of all AI reports with optional filtering by status.

    Args:
        db (Session): The database session.
        offset (int): The number of items to skip before returning results.
        limit (int): The maximum number of items to return.
        status (Optional[ProcessingStatus]): Filter reports by their processing status.

    Returns:
        List[AIReport]: A list of AI reports.
    """
    query = select(AIReport)
    if status:
        query = query.where(AIReport.state == status)
    reports = db.exec(query.offset(offset).limit(limit)).all()
    return reports


def update_ai_report_state(
    db: Session, report_id: int, report_update: AIReportUpdate
) -> AIReport:
    """
    Update the state of an existing AI report.

    Args:
        db (Session): The database session.
        report_id (int): The ID of the AI report to update.
        report_update (AIReportUpdate): The update schema containing the new state.

    Returns:
        AIReport: The updated AI report.

    Raises:
        NotFoundError: If no AI report with the given ID is found.
    """
    db_report = get_ai_report_by_id(
        db, report_id
    )  # Reuse existing getter for validation

    # Ensure only PENDING reports can be updated to APPROVED/REJECTED
    if db_report.state != ProcessingStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"AI Report with ID {report_id} is already in state '{db_report.state.value}'. Only PENDING reports can be updated.",
        )

    db_report.state = report_update.state
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    logger.info(f"AI Report {report_id} updated to state {db_report.state.value}.")
    return db_report
