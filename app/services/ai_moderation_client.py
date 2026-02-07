import httpx
import logging
import asyncio
from typing import Optional, Tuple, Dict

from app.core.config import get_settings
from app.models.enums import AIContentCategory

logger = logging.getLogger(__name__)


class AIModerationClient:
    """
    Client pour interagir avec les modèles CamemBERT de Hugging Face.
    Gère le modèle de détection de Spam et le modèle de détection de Toxicité.
    """

    def __init__(self):
        settings = get_settings()
        self.spam_url = settings.AI_SPAM_MODEL_URL
        self.toxicity_url = settings.AI_TOXICITY_MODEL_URL
        self.auth_token = settings.AI_MODERATION_SERVICE_TOKEN.get_secret_value() if settings.AI_MODERATION_SERVICE_TOKEN else None
        self.timeout = settings.AI_MODERATION_TIMEOUT_SECONDS

    async def _call_model(self, client: httpx.AsyncClient, url: str, text: str) -> Optional[Dict]:
        """
        Call a specific model on Hugging Face
        """
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = await client.post(
                str(url),
                json={"inputs": text},
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                # Pipeline format [[{"label": "LABEL_1", "score": 0.98}]]
                if isinstance(result[0], list) and len(result[0]) > 0:
                    return result[0][0]
                # Simple format [{"label": "LABEL_1", "score": 0.98}]
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Erreur lors de l'appel au modèle {url}: {e}")
            return None

    async def analyze_text(self, text: str) -> Optional[Tuple[AIContentCategory, Optional[float]]]:
        """
        Analyze text with spam-detector and toxic-detector models and merge in a one response
        
        Priority:
        1. If Spam=1 -> SPAM_LIKE
        2. If Toxic=1 -> TOXIC_LANGUAGE
        """
        if not self.spam_url or not self.toxicity_url:
            return None

        async with httpx.AsyncClient() as client:
            spam_task = self._call_model(client, str(self.spam_url), text)
            toxicity_task = self._call_model(client, str(self.toxicity_url), text)
            
            spam_res, tox_res = await asyncio.gather(spam_task, toxicity_task)

        # Extracting the results (The label depends on the model, often LABEL_1 or toxic/spam)
        # nelaw/camembert-spam-detector-fr use LABEL_1 for spam
        is_spam = spam_res and spam_res.get("label") in ["LABEL_1", "spam", "SPAM"]
        spam_score = spam_res.get("score") if spam_res else None

        # french_toxicity_classifier_plus_v2 use LABEL_1 for toxic
        is_toxic = tox_res and tox_res.get("label") in ["LABEL_1", "toxic", "TOXIC"]
        tox_score = tox_res.get("score") if tox_res else None

        if is_spam:
            return AIContentCategory.SPAM_LIKE, spam_score
        
        if is_toxic:
            return AIContentCategory.TOXIC_LANGUAGE, tox_score

        return None
