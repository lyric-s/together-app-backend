"""
AI Moderation Service Module.

This service acts as the central orchestrator for the AI-assisted moderation system.
It implements the business logic for content selection, quota management, 
and automated report generation.
"""

import logging
import random
from datetime import datetime, time
from typing import Any, List, cast

from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.ai_report import AIReport
from app.models.report import Report
from app.models.user import User
from app.models.mission import Mission
from app.models.enums import ProcessingStatus, ReportTarget
from app.services.ai_moderation_client import AIModerationClient

logger = logging.getLogger(__name__)

class AIModerationService:
    """
    Service layer for coordinating AI-assisted content moderation.

    This class provides the high-level logic to decide which content should be 
    analyzed and how the results should be stored. It ensures that AI analysis 
    complements human moderation without causing redundancy or data overhead.

    Attributes:
        settings (Settings): Global application configuration.
        ai_client (AIModerationClient): Low-level client for model communication.
    """

    def __init__(self, ai_client: AIModerationClient):
        """
        Initializes the moderation service.

        Args:
            ai_client (AIModerationClient): An instance of the AI moderation client.
        """
        self.settings = get_settings()
        self.ai_client = ai_client

    def _check_quota(self, db: Session) -> bool:
        """
        Validates the current daily AI scan quota.

        This method counts total AIReports created today (since midnight UTC) 
        in the database. This approach is distributed-safe, allowing multiple 
        concurrent processes to respect the same global limit.

        Args:
            db (Session): The active database session.

        Returns:
            bool: True if the current count is below the configured daily limit.
        """
        today_start = datetime.combine(datetime.now().date(), time.min)
        
        # Use select(func.count()) for an efficient SQL COUNT query
        statement = select(func.count()).select_from(AIReport).where(AIReport.created_at >= today_start)
        count = db.exec(statement).one()
        
        if count >= self.settings.AI_MODERATION_DAILY_QUOTA:
            logger.info(f"AI Quota reached for today ({count}/{self.settings.AI_MODERATION_DAILY_QUOTA}).")
            return False
        return True

    def _has_human_report(
        self, db: Session, target: ReportTarget, target_id: int, id_user_reported: int
    ) -> bool:
        """
        Determines if a human moderator has already flagged the content.

        According to lifecycle rules, AI analysis is skipped if a human report 
        exists to avoid interfering with manual investigation or creating 
        noise for administrators.

        Args:
            db (Session): Database session.
            target (ReportTarget): Type of target (PROFILE or MISSION).
            target_id (int): ID of the specific target.
            id_user_reported (int): ID of the user responsible for the content.

        Returns:
            bool: True if a human report is already registered for this content.
        """
        # We now use id_user_reported directly as it's the source of truth for who is reported
        statement = select(Report).where(
            Report.target == target,
            Report.id_user_reported == id_user_reported,
        )
        return db.exec(statement).first() is not None

    def _has_pending_ai_report(
        self, db: Session, target: ReportTarget, target_id: int
    ) -> bool:
        """
        Checks for an existing PENDING AI-generated report.

        Prevents redundant AI calls if an item has already been flagged and 
        is currently awaiting administrative review.

        Args:
            db (Session): Database session.
            target (ReportTarget): Type of target.
            target_id (int): ID of the target.

        Returns:
            bool: True if a pending report exists.
        """
        statement = select(AIReport).where(
            AIReport.target == target,
            AIReport.target_id == target_id,
            AIReport.state == ProcessingStatus.PENDING,
        )
        return db.exec(statement).first() is not None

    async def moderate_content(
        self,
        db: Session,
        target: ReportTarget,
        target_id: int,
        id_user_reported: int,
        text_content: str,
    ) -> None:
        """
        Triggers a moderation analysis for a specific content string.

        This method performs all safety and business checks (quota, human reports, 
        existing AI reports) before invoking the AI client. If the content is 
        found non-compliant, it persists a new AIReport record.

        Args:
            db (Session): Database session.
            target (ReportTarget): The type of the content (PROFILE/MISSION).
            target_id (int): The primary key of the content in its respective table.
            id_user_reported (int): The ID of the user responsible for the content.
            text_content (str): The raw text extracted from the profile or mission.
        """
        if not self.ai_client.models_loaded:
            return

        # Core Lifecycle Guardrails
        if self._has_human_report(db, target, target_id, id_user_reported):
            return

        if self._has_pending_ai_report(db, target, target_id):
            return

        if not self._check_quota(db):
            return

        try:
            classification_result = self.ai_client.analyze_text(text_content)

            if classification_result:
                classification_label, confidence_score = classification_result
                
                # Persistence of findings
                ai_report = AIReport(
                    target=target,
                    target_id=target_id,
                    id_user_reported=id_user_reported,
                    classification=classification_label,
                    confidence_score=confidence_score,
                    model_version=self.settings.AI_MODEL_VERSION,
                    state=ProcessingStatus.PENDING,
                )
                db.add(ai_report)
                db.commit()
                db.refresh(ai_report)
                logger.info(
                    f"AI Report created for {target.value}:{target_id} - Label: {classification_label.value}"
                )
        except Exception as e:
            # Failure in the AI layer should never crash core business operations
            logger.error(f"Graceful failure in AI moderation processing: {e}")

    async def run_batch_moderation(self, db: Session):
        """
        Runs a mass moderation scan, typically called by a midnight maintenance job.

        Selection Strategy:
        - Fetches users and missions not currently under review.
        - Shuffles candidates to ensure randomized probabilistic coverage over time.
        - Processes exactly 100 random items (if available) to respect resources.

        Args:
            db (Session): Database session.
        """
        if not self.ai_client.models_loaded:
            logger.warning("AI Models not loaded. Skipping maintenance scan.")
            return
        
        logger.info("Initiating daily AI moderation maintenance scan...")
        
        # Select candidates not currently under review
        user_subquery = select(AIReport.target_id).where(
            AIReport.target == ReportTarget.PROFILE, 
            AIReport.state == ProcessingStatus.PENDING
        )
        users_stmt = (
            select(User)
            .where(~cast(Any, User.id_user).in_(user_subquery))
            .options(
                selectinload(cast(Any, User.volunteer_profile)),
                selectinload(cast(Any, User.association_profile)),
            )
        )
        users = db.exec(users_stmt).all()

        mission_subquery = select(AIReport.target_id).where(
            AIReport.target == ReportTarget.MISSION, 
            AIReport.state == ProcessingStatus.PENDING
        )
        missions_stmt = (
            select(Mission)
            .where(~cast(Any, Mission.id_mission).in_(mission_subquery))
            .options(selectinload(cast(Any, Mission.association)))
        )
        missions = db.exec(missions_stmt).all()
        
        candidates: List[Any] = []
        
        # Prepare data for processing
        for user in users:
            text = ""
            if user.volunteer_profile:
                text = f"{user.volunteer_profile.bio or ''} {user.volunteer_profile.skills or ''}"
            elif user.association_profile:
                text = f"{user.association_profile.description or ''} {user.association_profile.name or ''}"
            
            if len(text.strip()) > 10 and user.id_user is not None:
                candidates.append((ReportTarget.PROFILE, user.id_user, user.id_user, text))

        for mission in missions:
            text = f"{mission.name} {mission.description}"
            if len(text.strip()) > 10 and mission.id_mission is not None:
                # For missions, the reported user is the owner of the association
                reported_user_id = mission.association.id_user if mission.association else None
                if reported_user_id:
                    candidates.append((ReportTarget.MISSION, mission.id_mission, reported_user_id, text))

        # Randomize order and take exactly 100
        random.shuffle(candidates)
        candidates = candidates[:100]

        processed = 0

        for target, target_id, reported_user_id, text in candidates:
            await self.moderate_content(db, target, target_id, reported_user_id, text)
            processed += 1
    
        logger.info(f"Daily maintenance scan completed. {processed} records analyzed.")
