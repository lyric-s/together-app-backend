from fastapi import APIRouter, Depends, BackgroundTasks, status, Query
from loguru import logger
from sqlmodel import Session
from typing import List, Optional

from app.core.dependencies import (
    get_current_admin,
    get_session,
    get_ai_moderation_service,
)
from app.services.ai_moderation_service import AIModerationService
from app.services import (
    ai_report as ai_report_service,
)  # Import the new AI report service
from app.models.ai_report import AIReportPublic, AIReportUpdate
from app.models.enums import ProcessingStatus


router = APIRouter(prefix="/ai_reports", tags=["AI Reports"])


@router.post(
    "/scan",
    summary="Manually trigger AI daily moderation scan",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ai_scan_manually(
    background_tasks: BackgroundTasks,
    current_admin: dict = Depends(get_current_admin),  # Ensure admin access
    db: Session = Depends(get_session),
    ai_service: AIModerationService = Depends(get_ai_moderation_service),
):
    """
    Manually triggers the AI daily moderation scan.

    This endpoint initiates the same batch moderation process that runs daily,
    allowing administrators to trigger it on demand. The scan runs in the background.

    Requires: Admin authentication.
    """
    logger.info(
        f"Admin {current_admin['email']} manually triggered AI daily moderation scan."
    )

    # We use a background task to immediately return a response
    # while the potentially long-running scan proceeds.
    async def run_scan_in_background(
        db_session: Session, moderation_service: AIModerationService
    ):
        try:
            await moderation_service.run_batch_moderation(db_session)
            db_session.commit()
            logger.info("AI daily moderation scan completed successfully.")
        except Exception as e:
            db_session.rollback()
            logger.error(f"AI daily moderation scan failed: {e}", exc_info=True)
            # Re-raise to ensure background task reports failure (if configured to do so)
            raise

    background_tasks.add_task(run_scan_in_background, db, ai_service)

    return {"message": "AI daily moderation scan has been triggered in the background."}


@router.get(
    "",
    response_model=List[AIReportPublic],
    summary="Get all AI reports",
    status_code=status.HTTP_200_OK,
)
def get_all_reports(
    db: Session = Depends(get_session),
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    status_filter: Optional[ProcessingStatus] = Query(
        None, description="Filter reports by processing status"
    ),
):
    """
    Retrieve a list of all AI reports.

    Allows filtering by processing status. Accessible only by administrators.
    """
    return ai_report_service.get_all_ai_reports(
        db, offset=offset, limit=limit, status=status_filter
    )


@router.get(
    "/{report_id}",
    response_model=AIReportPublic,
    summary="Get an AI report by ID",
    status_code=status.HTTP_200_OK,
)
def get_report_by_id(
    report_id: int,
    db: Session = Depends(get_session),
):
    """
    Retrieve a single AI report by its unique ID.

    Accessible only by administrators.
    """
    return ai_report_service.get_ai_report_by_id(db, report_id)


@router.patch(
    "/{report_id}/state",
    response_model=AIReportPublic,
    summary="Update AI report state",
    status_code=status.HTTP_200_OK,
)
def update_report_state(
    report_id: int,
    report_update: AIReportUpdate,
    db: Session = Depends(get_session),
):
    """
    Update the processing state of an AI report (e.g., from PENDING to APPROVED or REJECTED).

    Only PENDING reports can be updated. Accessible only by administrators.
    """
    return ai_report_service.update_ai_report_state(db, report_id, report_update)
