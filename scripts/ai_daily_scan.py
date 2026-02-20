"""
Synchronous daily scan script for AI moderation.
"""

import logging
import sys
import os
import asyncio

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import get_session
from app.core.dependencies import get_ai_moderation_service
from app.core.ai_loader import load_models

# Configure logging to see output in Coolify logs or terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ai_daily_scan")


def run_scan():
    """
    Daily maintenance script to run the AI moderation scan.
    """
    logger.info("Starting daily AI moderation scan...")

    # Manually load models since this script runs outside the FastAPI app lifespan
    load_models()

    # Get a database session manually
    session_generator = get_session()
    db = next(session_generator)

    try:
        # Initialize the AI service
        ai_service = get_ai_moderation_service()

        # Run the asynchronous batch moderation
        asyncio.run(ai_service.run_batch_moderation(db))
        db.commit()
        logger.info("AI moderation scan completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(
            f"A critical error occurred during the AI scan: {e}", exc_info=True
        )
        sys.exit(1)
    finally:
        session_generator.close()


if __name__ == "__main__":
    run_scan()
