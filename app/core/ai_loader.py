"""
AI Model Loader Module.

This module is responsible for loading the heavyweight AI models from Hugging Face
into memory ONCE at application startup. It implements a singleton pattern
to ensure that the models are not reloaded on every request, which would be
prohibitively slow and memory-intensive.

The loaded models are stored in global variables and are accessed by the
AIModerationClient.
"""

# import logging
from typing import Optional, Any
from transformers import (
    pipeline,
    CamembertTokenizer,
    CamembertForSequenceClassification,
    Pipeline,
)
from loguru import logger

# logger = logging.getLogger(__name__)

# Global variables to hold the singleton instances of the models
# These will be populated by the load_models function.
toxicity_pipeline: Optional[Pipeline] = None
spam_tokenizer: Optional[CamembertTokenizer] = None
spam_model: Optional[CamembertForSequenceClassification] = None


def load_models():
    """
    Loads both the toxicity and spam detection models into memory.

    This function should be called only once when the FastAPI application starts.
    It downloads the models from Hugging Face hub and initializes them for inference.

    If models are already loaded, it does nothing.
    """
    global toxicity_pipeline, spam_tokenizer, spam_model

    # Check if models are already loaded to ensure this is a singleton operation
    if toxicity_pipeline and spam_tokenizer and spam_model:
        logger.info("AI models are already loaded.")
        return

    logger.info("Loading AI models into memory. This may take a moment...")
    try:
        # Load the toxicity model using the simple pipeline API
        toxicity_pipeline = pipeline(
            "text-classification",
            model="EIStakovskii/french_toxicity_classifier_plus_v2",
        )

        # Load the spam model using the more detailed class-based API
        spam_model_name = "nellaw/camembert-spam-detector-fr"
        # Using Any to avoid static analysis issues with complex transformers types
        temp_tokenizer: Any = CamembertTokenizer.from_pretrained(spam_model_name)
        spam_tokenizer = temp_tokenizer

        temp_model: Any = CamembertForSequenceClassification.from_pretrained(
            spam_model_name
        )
        spam_model = temp_model

        logger.info("AI models loaded successfully.")
    except Exception:
        logger.exception("Failed to load AI models. AI moderation will be disabled.")
        # Ensure partial loads don't leave the system in an inconsistent state
        toxicity_pipeline = None
        spam_tokenizer = None
        spam_model = None
