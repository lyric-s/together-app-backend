"""Report router module for user reporting endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.exceptions import InvalidTokenError
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
    The report will be created with PENDING state and reviewed by administrators.
    Only one PENDING report per user against the same target is allowed.

    ## Request Body

    The request must include:
    - `type` (string, required): Report type - `HARASSMENT`, `SPAM`, `FRAUD`, `INAPPROPRIATE_BEHAVIOR`, or `OTHER`
    - `target` (string, required): What is being reported - `PROFILE`, `MESSAGE`, `MISSION`, or `OTHER`
    - `reason` (string, required): Detailed explanation (minimum 10 characters)
    - `id_user_reported` (integer, required): ID of the user being reported

    ## Example Request

    ```json
    {
      "type": "HARASSMENT",
      "target": "PROFILE",
      "reason": "This user has been sending inappropriate messages repeatedly.",
      "id_user_reported": 456
    }
    ```

    ## Response

    Returns the created report with:
    - Generated `id_report` (integer)
    - All input fields
    - `state` field set to `PENDING`
    - Reporter and reported user names
    - `created_at` timestamp (ISO 8601 format)

    ## Example Response

    ```json
    {
      "id_report": 789,
      "type": "HARASSMENT",
      "target": "PROFILE",
      "reason": "This user has been sending inappropriate messages repeatedly.",
      "id_user_reported": 456,
      "reporter_name": "John Doe",
      "reported_name": "Jane Smith",
      "state": "PENDING",
      "created_at": "2026-01-14T10:30:00Z"
    }
    ```

    Args:
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).
        `report_in`: Report data including type, target, reason, and id_user_reported.

    Returns:
        `ReportPublic`: The created report with its unique ID and timestamp.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
        `422 ValidationError`: If attempting to report oneself.
        `404 NotFoundError`: If the reported user doesn't exist.
        `409 AlreadyExistsError`: If a PENDING report against this user already exists.
    """
    if current_user.id_user is None:
        raise InvalidTokenError("User ID not found in token")
    report = report_service.create_report(session, current_user.id_user, report_in)
    return ReportPublic.model_validate(report_service.to_report_public(report))


@router.get("/me", response_model=list[ReportPublic])
def get_my_reports(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ReportPublic]:
    """
    Retrieve all reports made by the authenticated user.

    Returns all reports submitted by the authenticated user, ordered by most recent first.
    Users can view their own report history to track the status of their submissions.

    ## Response

    Returns an array of reports, each containing:
    - `id_report` (integer): Unique report identifier
    - `type` (string): Report type (`HARASSMENT`, `SPAM`, etc.)
    - `target` (string): What was reported (`PROFILE`, `MESSAGE`, etc.)
    - `reason` (string): The submitted reason
    - `state` (string): Current status (`PENDING`, `RESOLVED`, `DISMISSED`)
    - `reporter_name` (string): Name of the person who reported
    - `reported_name` (string): Name of the reported user
    - `created_at` (string): Timestamp in ISO 8601 format

    ## Example Response

    ```json
    [
      {
        "id_report": 789,
        "type": "HARASSMENT",
        "target": "PROFILE",
        "reason": "This user has been sending inappropriate messages repeatedly.",
        "id_user_reported": 456,
        "reporter_name": "John Doe",
        "reported_name": "Jane Smith",
        "state": "PENDING",
        "created_at": "2026-01-14T10:30:00Z"
      },
      {
        "id_report": 654,
        "type": "SPAM",
        "target": "MESSAGE",
        "reason": "Received unsolicited promotional messages.",
        "id_user_reported": 123,
        "reporter_name": "John Doe",
        "reported_name": "Bob Johnson",
        "state": "RESOLVED",
        "created_at": "2026-01-10T14:20:00Z"
      }
    ]
    ```

    Args:
        `session`: Database session (automatically injected).
        `current_user`: Authenticated user (automatically injected from token).

    Returns:
        `list[ReportPublic]`: Reports submitted by the authenticated user, ordered by
            most recent first.

    Raises:
        `401 Unauthorized`: If no valid authentication token is provided.
    """
    if current_user.id_user is None:
        raise InvalidTokenError("User ID not found in token")
    reports = report_service.get_reports_by_reporter(session, current_user.id_user)
    return [
        ReportPublic.model_validate(report_service.to_report_public(r)) for r in reports
    ]
