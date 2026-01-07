"""Report router module for user reporting endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.report import ReportCreate, ReportPublic
from app.services import report as report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/", response_model=ReportPublic, status_code=201)
def create_report(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    report_in: ReportCreate,
) -> ReportPublic:
    """
    Create a report against another user.

    Any authenticated user can report another user (volunteer or association).
    The report will be created with PENDING state and reviewed by admins.

    Parameters:
        report_in: Report data (type, target, reason, id_user_reported).

    Returns:
        ReportPublic: The created report.

    Raises:
        ValidationError: If trying to report yourself.
        NotFoundError: If the reported user doesn't exist.
        AlreadyExistsError: If you already have a PENDING report against this user.
    """
    assert current_user.id_user is not None
    report = report_service.create_report(session, current_user.id_user, report_in)
    return ReportPublic.model_validate(report)


@router.get("/me", response_model=list[ReportPublic])
def get_my_reports(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ReportPublic]:
    """
    Get all reports made by the authenticated user.

    Returns:
        list[ReportPublic]: Reports made by this user, ordered by most recent first.
    """
    assert current_user.id_user is not None
    reports = report_service.get_reports_by_reporter(session, current_user.id_user)
    return [ReportPublic.model_validate(r) for r in reports]
