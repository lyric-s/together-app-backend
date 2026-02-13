"""
Local AI Moderation Client.

This module provides a client that performs inference directly using locally
loaded 'transformers' models. It accesses the singleton models loaded by 
'app.core.ai_loader' to avoid reloading them on every request.

This approach replaces the previous HTTP-based client.
"""

import logging
import torch
from typing import Optional, Tuple
from app.core import ai_loader
from app.models.enums import AIContentCategory

logger = logging.getLogger(__name__)

class AIModerationClient:
    """
    Client for performing local inference with CamemBERT models.
    
    This client uses the pre-loaded models to classify text for spam and toxicity.
    It is designed to be highly efficient by reusing the singleton model instances.
    """

    def __init__(self):
        """
        Initializes the client.
        """
        pass

    @property
    def models_loaded(self) -> bool:
        """
        Checks if all required models are loaded in the ai_loader module.
        """
        return (
            ai_loader.toxicity_pipeline is not None 
            and ai_loader.spam_tokenizer is not None 
            and ai_loader.spam_model is not None
        )
            
    def _predict_spam(self, text: str) -> Tuple[bool, Optional[float]]:
        """
        Performs spam detection on a text string using the local spam model.

        Args:
            text (str): The text to classify.

        Returns:
            A tuple containing a boolean (True if spam detected) and the confidence score (float).
            Returns False and 0.0 if prediction fails or models are not loaded.
        """
        if not self.models_loaded:
            logger.warning("Spam prediction skipped: Models not loaded.")
            return False, 0.0

        try:
            inputs = ai_loader.spam_tokenizer(text, return_tensors="pt", truncation=True, max_length=256, padding=True)
            with torch.no_grad():
                outputs = ai_loader.spam_model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
                pred = torch.argmax(probs, dim=1).item()
            is_spam = pred == 1
            score = probs[0][pred].item() if is_spam else None
            return is_spam, score
        except Exception as e:
            logger.error(f"Error during spam prediction: {e}", exc_info=True)
            return False, 0.0

    def _predict_toxicity(self, text: str) -> bool:
        """
        Performs toxicity detection on a text string using the local toxicity model.

        Args:
            text (str): The text to classify.

        Returns:
            A boolean indicating if the text is toxic.
            Returns False if prediction fails or models are not loaded.
        """
        if not self.models_loaded:
            logger.warning("Toxicity prediction skipped: Models not loaded.")
            return False

        try:
            result = ai_loader.toxicity_pipeline(text)
            # The pipeline returns [{'label': 'LABEL_1', 'score': ...}]
            if result and result[0]['label'] in ['LABEL_1', 'toxic', 'TOXIC']:
                return True
            return False
        except Exception as e:
            logger.error(f"Error during toxicity prediction: {e}", exc_info=True)
            return False

    def analyze_text(self, text: str) -> Optional[Tuple[AIContentCategory, Optional[float]]]:
        """
        Analyzes text using local spam and toxicity models.

        Priority Logic:
        1. SPAM: If the spam model flags the content, it returns SPAM_LIKE.
        2. TOXICITY: If the toxicity model flags the content, it returns TOXIC_LANGUAGE (only if not already flagged as spam).
        3. No Flag: If neither flags the content, it returns None.
        
        Args:
            text (str): The raw text to analyze.

        Returns:
            Optional[Tuple[AIContentCategory, Optional[float]]]: A tuple of 
                (Category, Score) if a violation is detected, otherwise None.
                The score might be None if the model provides binary labels only.
        """
        if not self.models_loaded:
            logger.warning("AI text analysis skipped: Models not loaded.")
            return None

        # Since inference is CPU-bound, run sequentially for simplicity.
        # For heavy loads, this should be offloaded to a background worker process.
        is_spam, spam_score = self._predict_spam(text)
        if is_spam:
            return AIContentCategory.SPAM_LIKE, spam_score

        is_toxic = self._predict_toxicity(text)
        if is_toxic:
            # The toxicity model doesn't provide a reliable confidence score by default
            return AIContentCategory.TOXIC_LANGUAGE, None
            
        return None