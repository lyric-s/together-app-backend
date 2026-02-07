import logging
import random
from datetime import datetime, time
from typing import Dict, Any, Tuple, List

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
    Orchestre le processus de modération assistée par IA.
    Responsable de la vérification des quotas, du respect du cycle de vie des rapports
    et de l'appel aux modèles de classification.
    """

    def __init__(self, ai_client: AIModerationClient):
        self.settings = get_settings()
        self.ai_client = ai_client

    def _check_quota(self, db: Session) -> bool:
        """
        Vérifie le quota quotidien en comptant les rapports créés en DB depuis minuit.
        Cela garantit que le quota est partagé entre tous les processus (API, Scripts, Workers).
        """
        today_start = datetime.combine(datetime.now().date(), time.min)
        
        # Compte le nombre de signalements IA créés aujourd'hui
        statement = select(func.count(AIReport.id_report)).where(AIReport.created_at >= today_start)
        count = db.exec(statement).one()
        
        if count >= self.settings.AI_MODERATION_DAILY_QUOTA:
            logger.info(f"Quota IA atteint pour aujourd'hui ({count}/{self.settings.AI_MODERATION_DAILY_QUOTA}).")
            return False
        return True

    def _has_human_report(self, db: Session, target: ReportTarget, target_id: int) -> bool:
        """
        Checks if a HUMAN report already exists for this content.

        - For a PROFILE: target_id is the user ID.
        - For a MISSION: target_id is the mission ID.
        Since the Human Report table only stores id_user_reported,
        we check if the mission's owner association has been reported.
        """
        if target == ReportTarget.PROFILE:
            statement = select(Report).where(
                Report.target == ReportTarget.PROFILE,
                Report.id_user_reported == target_id
            )
            return db.exec(statement).first() is not None
        
        if target == ReportTarget.MISSION:
            # First, we try to find out who owns the mission.
            mission = db.get(Mission, target_id)
            if mission:
                # We check if a human has reported a MISSION for this association
                statement = select(Report).where(
                    Report.target == ReportTarget.MISSION,
                    Report.id_user_reported == mission.id_asso
                )
                return db.exec(statement).first() is not None
                
        return False

    def _has_pending_ai_report(self, db: Session, target: ReportTarget, target_id: int) -> bool:
        """Check if a pending AI report already exists for this content."""
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
        """Initiates content analysis if business rules allow it."""
        if not self.ai_client.spam_url or not self.ai_client.toxicity_url:
            return

        # 1. Business rules (Do not rescan what has already been scanned)
        if self._has_human_report(db, target, target_id):
            return

        if self._has_pending_ai_report(db, target, target_id):
            return

        # 2. Persistent Quota Verification
        if not self._check_quota(db):
            return

        # 3. AI analysis
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
                logger.info(f"Signalement IA créé pour {target.value}:{target_id} - Label: {classification_label.value}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement de modération IA : {e}")

    async def run_batch_moderation(self, db: Session):
        """Performs the daily mass scan."""
        if not self.ai_client.spam_url or not self.ai_client.toxicity_url:
            logger.warning("URLs des modèles IA non configurées. Abandon du scan batch.")
            return
        
        logger.info("Démarrage du scan de modération IA quotidien...")
        
        # We collect the candidates (limited to 500 for performance)
        users = db.exec(select(User).limit(500)).all()
        missions = db.exec(select(Mission).limit(500)).all()
        
        candidates = []
        for user in users:
            text = ""
            if user.volunteer_profile:
                text = f"{user.volunteer_profile.bio or ''} {user.volunteer_profile.skills or ''}"
            elif user.association_profile:
                text = f"{user.association_profile.description or ''} {user.association_profile.name or ''}"
            
            if len(text.strip()) > 10:
                candidates.append((ReportTarget.PROFILE, user.id_user, text))

        for mission in missions:
            text = f"{mission.name} {mission.description}"
            if len(text.strip()) > 10:
                candidates.append((ReportTarget.MISSION, mission.id_mission, text))

        # On mélange pour varier les contenus scannés chaque jour
        random.shuffle(candidates)

        processed = 0
        for target, target_id, text in candidates:
             if not self._check_quota(db):
                 break
             await self.moderate_content(db, target, target_id, text)
             processed += 1
        
        logger.info(f"Scan batch terminé. {processed} contenus analysés.")