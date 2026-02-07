import httpx
import logging
import asyncio
from typing import Optional, Tuple, Dict

from app.core.config import get_settings
from app.models.enums import AIContentCategory

logger = logging.getLogger(__name__)


class AIModerationClient:
    """
    Client for interacting with CamemBERT models hosted on Hugging Face.

    This client manages communication with two distinct models:
    - A spam detector (e.g., nellaw/camembert-spam-detector-fr)
    - A toxicity classifier (e.g., EIStakovskii/french_toxicity_classifier_plus_v2)
    """

    def __init__(self):
        """
        Initializes the AI moderation client with settings from the environment.
        """
        settings = get_settings()
        self.spam_url = settings.AI_SPAM_MODEL_URL
        self.toxicity_url = settings.AI_TOXICITY_MODEL_URL
        self.auth_token = settings.AI_MODERATION_SERVICE_TOKEN.get_secret_value() if settings.AI_MODERATION_SERVICE_TOKEN else None
        self.timeout = settings.AI_MODERATION_TIMEOUT_SECONDS

    async def _call_model(self, client: httpx.AsyncClient, url: str, text: str) -> Optional[Dict]:
        """
        Calls a specific AI model API endpoint.

        Args:
            client (httpx.AsyncClient): The HTTP client to use for the request.
            url (str): The endpoint URL of the model.
            text (str): The raw text content to analyze.

        Returns:
            Optional[Dict]: The raw JSON response from the model if successful, None otherwise.
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
                # Support for standard Hugging Face pipeline output formats
                if isinstance(result[0], list) and len(result[0]) > 0:
                    return result[0][0]
                return result[0]
            return None
        except Exception as e:
            logger.error(f"Error calling AI model at {url}: {e}")
            return None

    async def analyze_text(self, text: str) -> Optional[Tuple[AIContentCategory, Optional[float]]]:
        """
        Analyzes text using both spam and toxicity models and merges the results.

        Priority logic:
        1. If the spam model flags the content (LABEL_1), it returns SPAM_LIKE.
        2. If the toxicity model flags the content (LABEL_1), it returns TOXIC_LANGUAGE.
        3. Otherwise, returns None.

        Args:
            text (str): The raw text to analyze.

        Returns:
            Optional[Tuple[AIContentCategory, Optional[float]]]: A tuple containing the 
                classification category and the confidence score (if available).
        """
        if not self.spam_url or not self.toxicity_url:
            return None

        async with httpx.AsyncClient() as client:
            # Execute both model calls in parallel for better performance
            spam_task = self._call_model(client, str(self.spam_url), text)
            toxicity_task = self._call_model(client, str(self.toxicity_url), text)
            
            spam_res, tox_res = await asyncio.gather(spam_task, toxicity_task)

        # Handle different label formats (some models use 'LABEL_1', others 'spam'/'toxic')
        is_spam = spam_res and spam_res.get("label") in ["LABEL_1", "spam", "SPAM"]
        spam_score = spam_res.get("score") if spam_res else None

        is_toxic = tox_res and tox_res.get("label") in ["LABEL_1", "toxic", "TOXIC"]
        tox_score = tox_res.get("score") if tox_res else None

        if is_spam:
            return AIContentCategory.SPAM_LIKE, spam_score
        
        if is_toxic:
            return AIContentCategory.TOXIC_LANGUAGE, tox_score

        return None