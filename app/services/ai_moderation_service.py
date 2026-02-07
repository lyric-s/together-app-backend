import logging
import random
from datetime import datetime
from typing import Dict, Any, Tuple, List

from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.ai_report import AIReport
from app.models.report import Report
from app.models.user import User
from app.models.mission import Mission
from app.models.enums import ProcessingStatus, ReportTarget, AIContentCategory
from app.services.ai_moderation_client import AIModerationClient

logger = logging.getLogger(__name__)

# In-memory store for daily quota.
_daily_ai_calls: Dict[str, Any] = {"count": 0, "last_reset_date": datetime.now().date()}


class AIModerationService:
    """
    Orchestrates the AI-assisted content moderation process.

    This service is responsible for determining if and when to send content
    to the AI moderation client, enforcing quotas and probabilistic selection,
    and persisting the AI's findings in the database.
    """

    def __init__(self, ai_client: AIModerationClient):
        self.settings = get_settings()
        self.ai_client = ai_client

    def _reset_daily_quota_if_needed(self):
        """
        Resets the daily AI call quota if a new day has started.
        """
        current_date = datetime.now().date()
        if current_date > _daily_ai_calls["last_reset_date"]:
            _daily_ai_calls["count"] = 0
            _daily_ai_calls["last_reset_date"] = current_date
            logger.info("Daily AI moderation quota reset.")

    def _check_quota(self) -> bool:
        """
        Checks if the daily quota allows for more AI calls.
        """
        self._reset_daily_quota_if_needed()
        if _daily_ai_calls["count"] >= self.settings.AI_MODERATION_DAILY_QUOTA:
            return False
        return True

    def _increment_quota(self):
        """Increments the daily AI call count."""
        _daily_ai_calls["count"] += 1

    def _has_human_report(self, db: Session, target: ReportTarget, target_id: int) -> bool:
        """
        Checks if there is already a HUMAN report for this content.
        """
        if target == ReportTarget.PROFILE:
             statement = select(Report).where(
                Report.target == ReportTarget.PROFILE,
                Report.id_user_reported == target_id
            )
             return db.exec(statement).first() is not None
        return False

    def _has_pending_ai_report(self, db: Session, target: ReportTarget, target_id: int) -> bool:
        """
        Checks if there is already a PENDING AI report for this content.
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
        Initiates an asynchronous AI moderation analysis for given content.
        """
        if not self.ai_client.spam_url or not self.ai_client.toxicity_url:
            return

        # 1. Check Lifecycle Rules
        if self._has_human_report(db, target, target_id):
            logger.info(f"Skipping AI scan for {target.value}:{target_id} - Human report exists.")
            return

        if self._has_pending_ai_report(db, target, target_id):
            logger.info(f"Skipping AI scan for {target.value}:{target_id} - Pending AI report exists.")
            return

        # 2. Check Quota
        if not self._check_quota():
            logger.info(f"Skipping AI scan for {target.value}:{target_id} - Daily quota reached.")
            return

        # 3. Call AI
        logger.info(
            "Calling AI moderation service for %s:%s. Current daily count: %d",
            target.value,
            target_id,
            _daily_ai_calls["count"],
        )

        try:
            classification_result = await self.ai_client.analyze_text(text_content)
            self._increment_quota()

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
                logger.info(
                    "AI report created for %s:%s - Label: %s, Score: %s",
                    target.value,
                    target_id,
                    classification_label.value,
                    str(confidence_score),
                )
            else:
                logger.debug(
                    "AI moderation client returned no classification for %s:%s.",
                    target.value,
                    target_id,
                )
        except Exception as e:
            logger.error(
                "Failed to process AI moderation for %s:%s: %s",
                target.value,
                target_id,
                e,
                exc_info=True,
            )

    async def run_batch_moderation(self, db: Session):
        """
        Runs the daily batch moderation job.
        """
        if not self.ai_client.spam_url or not self.ai_client.toxicity_url:
            logger.info("AI Models URLs not configured. Skipping batch moderation.")
            return
        
        if not self._check_quota():
            logger.info("Daily quota reached. Skipping batch moderation.")
            return

        logger.info("Starting daily AI moderation batch job.")
        
        users = db.exec(select(User).limit(500)).all()
        missions = db.exec(select(Mission).limit(500)).all()
        
        candidates: List[Tuple[ReportTarget, int, str]] = []
        
        for user in users:
            text = ""
            if user.volunteer_profile:
                text = f"{user.volunteer_profile.bio or ''} {user.volunteer_profile.skills or ''} {user.volunteer_profile.address or ''}"
            elif user.association_profile:
                text = f"{user.association_profile.description or ''} {user.association_profile.name or ''} {user.association_profile.company_name or ''}"
            
            if len(text.strip()) > 10:
                candidates.append((ReportTarget.PROFILE, user.id_user, text)) # type: ignore

        for mission in missions:
            text = f"{mission.name} {mission.description} {mission.skills or ''}"
            if len(text.strip()) > 10:
                candidates.append((ReportTarget.MISSION, mission.id_mission, text)) # type: ignore

        random.shuffle(candidates)

        processed_count = 0
        for target, target_id, text in candidates:
             if not self._check_quota():
                 break
             
             await self.moderate_content(db, target, target_id, text)
             processed_count += 1
        
        logger.info(f"Daily AI batch job completed. Processed {processed_count} items.")
