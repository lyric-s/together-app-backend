"""
Simple standalone script to test local AI model inference.
"""

import sys
import os

from loguru import logger

# It adds the project's root directory to Python's path.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.ai_loader import load_models
from app.services.ai_moderation_client import AIModerationClient
from app.utils.logger import setup_logging

# Configure logging using the project's setup
setup_logging()

# Load models
logger.info("---" + "-" * 30 + " AI Model Inference Test ---")
load_models()


def test_models():
    """
    Runs a simple inference test using the pre-loaded models.
    """
    client = AIModerationClient()

    if not client.models_loaded:
        logger.error("Models failed to load. Please check logs for errors.")
        return

    logger.info("Models loaded successfully.")
    logger.info("-" * 30)

    test_cases = [
        ("Gagnez 5000€ par mois sans effort, cliquez ici !", "Spam"),
        ("Tu es vraiment un imbécile, foutez le camp d'ici.", "Toxic"),
        ("Bonjour, je cherche des informations sur la mission.", "Clean"),
    ]

    for text, expected in test_cases:
        logger.info(f"Testing text: '{text}' (Expected: {expected})")
        result = client.analyze_text(text)

        if result:
            category, score = result
            # This is the fix for the SyntaxError
            logger.info(
                f"  -> Result: {category.value} (Score: {score if score is not None else 'N/A'})"
            )
        else:
            logger.info("  -> Result: Clean (No flag)")


if __name__ == "__main__":
    test_models()
