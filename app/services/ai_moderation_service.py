import logging
import random
from datetime import datetime, time
from typing import Dict, Any, Tuple, List, cast

from sqlmodel import Session, select, func

from app.core.config import get_settings
from app.models.ai_report import AIReport
from app.models.report import Report
from app.models.user import User
from app.models.mission import Mission
from app.models.enums import ProcessingStatus, ReportTarget, AIContentCategory
from app.services.ai_moderation_client import AIModerationClient

logger = logging.getLogger(__name__)

class AIModerationService:
    """
    Orchestrates the AI-assisted content moderation process.

    This service manages:
    - Daily scan quotas based on database records.
    - Lifecycle rules to avoid redundant scans.
    - Batch processing of users and missions for daily maintenance.
    - Persistence of AI-generated reports in the database.
    """

    def __init__(self, ai_client: AIModerationClient):
        """
        Initializes the service with an AI client.
        """
        self.settings = get_settings()
        self.ai_client = ai_client

    def _check_quota(self, db: Session) -> bool:
        """
        Verifies if the daily AI moderation quota has been reached by counting
        reports created today.
        """
        today_start = datetime.combine(datetime.now().date(), time.min)
        statement = select(func.count()).select_from(AIReport).where(AIReport.created_at >= today_start)
        count = db.exec(statement).one()
        
        if count >= self.settings.AI_MODERATION_DAILY_QUOTA:
            logger.info(f"AI Quota reached for today ({count}/{self.settings.AI_MODERATION_DAILY_QUOTA}).")
            return False
        return True

    def _has_human_report(self, db: Session, target: ReportTarget, target_id: int) -> bool:
        """
        Checks if a human-generated report already exists for the given content.
        """
        if target == ReportTarget.PROFILE:
            statement = select(Report).where(
                Report.target == ReportTarget.PROFILE,
                Report.id_user_reported == target_id
            )
            return db.exec(statement).first() is not None
        
        if target == ReportTarget.MISSION:
            mission = db.get(Mission, target_id)
            if mission:
                statement = select(Report).where(
                    Report.target == ReportTarget.MISSION,
                    Report.id_user_reported == mission.id_asso
                )
                return db.exec(statement).first() is not None
                
        return False

    def _has_pending_ai_report(self, db: Session, target: ReportTarget, target_id: int) -> bool:
        """
        Checks if a PENDING AI report already exists for the given content.
        """
        statement = select(AIReport).where(
            AIReport.target == target,
            AIReport.target_id == target_id,
            AIReport.state == ProcessingStatus.PENDING
        )
        return db.exec(statement).first() is not None

    async def moderate_content(
        self,
        db: Session,
        target: ReportTarget,
        target_id: int,
        text_content: str,
    ) -> None:
        """
        Initiates an AI moderation scan for a specific piece of content.
        """
        if not self.ai_client.spam_url or not self.ai_client.toxicity_url:
            return

        if self._has_human_report(db, target, target_id):
            return

        if self._has_pending_ai_report(db, target, target_id):
            return

        if not self._check_quota(db):
            return

        try:
            classification_result = await self.ai_client.analyze_text(text_content)

            if classification_result:
                classification_label, confidence_score = classification_result
                
                ai_report = AIReport(
                    target=target,
                    target_id=target_id,
                    classification=classification_label,
                    confidence_score=confidence_score,
                    model_version=self.settings.AI_MODEL_VERSION,
                    state=ProcessingStatus.PENDING,
                )
                db.add(ai_report)
                db.commit()
                db.refresh(ai_report)
                logger.info(f"AI Report created for {target.value}:{target_id} - Label: {classification_label.value}")
        except Exception as e:
            logger.error(f"Failed to process AI moderation: {e}")

    async def run_batch_moderation(self, db: Session):
        """
        Executes a batch moderation scan using a randomized selection to avoid
        repetition and ensure gradual coverage of all content.
        """
        if not self.ai_client.spam_url or not self.ai_client.toxicity_url:
            logger.warning("AI Model URLs not configured. Skipping batch moderation.")
            return
        
        logger.info("Starting daily AI moderation batch scan...")
        
        # 1. Fetch random users who don't have a pending AI report
        user_subquery = select(AIReport.target_id).where(
            AIReport.target == ReportTarget.PROFILE, 
            AIReport.state == ProcessingStatus.PENDING
        )
        # Using column.in_(subquery) == False to avoid static analysis issues with .not_in()
        users_stmt = select(User).where(~User.id_user.in_(user_subquery)).order_by(func.random()).limit(500)
        users = db.exec(users_stmt).all()

        # 2. Fetch random missions who don't have a pending AI report
        mission_subquery = select(AIReport.target_id).where(
            AIReport.target == ReportTarget.MISSION, 
            AIReport.state == ProcessingStatus.PENDING
        )
        missions_stmt = select(Mission).where(~Mission.id_mission.in_(mission_subquery)).order_by(func.random()).limit(500)
        missions = db.exec(missions_stmt).all()
        
        candidates: List[Tuple[ReportTarget, int, str]] = []
        
        for user in users:
            text = ""
            if user.volunteer_profile:
                text = f"{user.volunteer_profile.bio or ''} {user.volunteer_profile.skills or ''}"
            elif user.association_profile:
                text = f"{user.association_profile.description or ''} {user.association_profile.name or ''}"
            
            if len(text.strip()) > 10 and user.id_user is not None:
                candidates.append((ReportTarget.PROFILE, cast(int, user.id_user), text))

        for mission in missions:
            text = f"{mission.name} {mission.description}"
            if len(text.strip()) > 10 and mission.id_mission is not None:
                candidates.append((ReportTarget.MISSION, cast(int, mission.id_mission), text))

        # Re-shuffle in Python to mix Users and Missions
        random.shuffle(candidates)

        processed = 0
        for target, target_id, text in candidates:
            if not self._check_quota(db):
                break
            await self.moderate_content(db, target, target_id, text)
            processed += 1
    
        logger.info(f"Daily AI batch scan completed. {processed} items analyzed.")
