"""
AI Moderation Client Module.

This module provides the low-level HTTP client responsible for communicating with
external AI models hosted on Hugging Face. it handles request formatting,
authentication via service-to-service tokens, parallel model execution,
and response parsing.

Technological Context:
- Uses CamemBERT-based models for French language processing.
- Leverages HTTPX for asynchronous, non-blocking network calls.
- Integrates with Hugging Face Inference API.
"""

import httpx
import logging
import asyncio
from typing import Optional, Tuple, Dict

from app.core.config import get_settings
from app.models.enums import AIContentCategory

logger = logging.getLogger(__name__)


class AIModerationClient:
    """
    Client for interacting with CamemBERT models for content classification.

    This client orchestrates calls to multiple specialized models to detect
    non-compliant content such as spam and toxic language. It abstracts the
    complexity of API communication and provides a unified interface for
    the service layer.

    Attributes:
        spam_url (Optional[str]): The endpoint for the spam detection model.
        toxicity_url (Optional[str]): The endpoint for the toxicity classifier.
        auth_token (Optional[str]): Bearer token for API authentication.
        timeout (int): Network timeout in seconds for each request.
    """

    def __init__(self):
        """
        Initializes the AI moderation client with settings from the environment.

        Configurations are retrieved from the global settings object, specifically
        targeting URLs for specialized CamemBERT models.
        """
        settings = get_settings()
        self.spam_url = settings.AI_SPAM_MODEL_URL
        self.toxicity_url = settings.AI_TOXICITY_MODEL_URL
        self.auth_token = (
            settings.AI_MODERATION_SERVICE_TOKEN.get_secret_value()
            if settings.AI_MODERATION_SERVICE_TOKEN
            else None
        )
        self.timeout = settings.AI_MODERATION_TIMEOUT_SECONDS

    async def _call_model(
        self, client: httpx.AsyncClient, url: str, text: str
    ) -> Optional[Dict]:
        """
        Executes a POST request to a specific AI model endpoint.

        This internal method handles the standard Hugging Face 'inputs' payload
        format and parses the resulting JSON. It includes error logging for
        network failures and non-200 HTTP statuses.

        Args:
            client (httpx.AsyncClient): The shared HTTP client for efficiency.
            url (str): The specific model API URL.
            text (str): The raw text string to be analyzed.

        Returns:
            Optional[Dict]: The primary classification result (label and score)
                if successful, or None if the request failed or the response
                was malformed.
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
            # Handle different common Inference API response structures
            if isinstance(result, list) and len(result) > 0:
                # Format: [[{"label": "...", "score": ...}]] (Pipeline)
                if isinstance(result[0], list) and len(result[0]) > 0:
                    return result[0][0]
                # Format: [{"label": "...", "score": ...}]
                return result[0]
            return None
        except httpx.HTTPStatusError as e:
            logger.error(
                f"AI model API returned error {e.response.status_code} for {url}"
            )
            return None
        except Exception as e:
            logger.error(f"Unexpected error during AI model call at {url}: {e}")
            return None

    async def analyze_text(
        self, text: str
    ) -> Optional[Tuple[AIContentCategory, Optional[float]]]:
        """
        Analyzes raw text using all configured specialized models in parallel.

        This is the main entry point for text analysis. it executes calls to
        the spam detector and the toxicity classifier simultaneously to
        minimize latency.

        Priority Logic (Conflict Resolution):
        1. If the spam model flags the content, it returns SPAM_LIKE.
        2. If the toxicity model flags the content, it returns TOXIC_LANGUAGE.
        3. If neither flags the content (LABEL_0), it returns None.

        Args:
            text (str): The raw user-generated text content.

        Returns:
            Optional[Tuple[AIContentCategory, Optional[float]]]: A tuple of
                (Category, Score) if a violation is detected, otherwise None.
                The score might be None if the model provides binary labels only.
        """
        if not self.spam_url or not self.toxicity_url:
            logger.debug("AI model URLs missing in configuration. Skipping analysis.")
            return None

        async with httpx.AsyncClient() as client:
            # Use asyncio.gather for concurrent execution
            spam_task = self._call_model(client, str(self.spam_url), text)
            toxicity_task = self._call_model(client, str(self.toxicity_url), text)

            spam_res, tox_res = await asyncio.gather(spam_task, toxicity_task)

        # Extraction and Label Mapping
        # Note: We check for multiple label variations to ensure compatibility
        is_spam = spam_res and spam_res.get("label") in ["LABEL_1", "spam", "SPAM"]
        spam_score = spam_res.get("score") if spam_res else None

        is_toxic = tox_res and tox_res.get("label") in ["LABEL_1", "toxic", "TOXIC"]
        tox_score = tox_res.get("score") if tox_res else None

        if is_spam:
            return AIContentCategory.SPAM_LIKE, spam_score

        if is_toxic:
            return AIContentCategory.TOXIC_LANGUAGE, tox_score

        return None
