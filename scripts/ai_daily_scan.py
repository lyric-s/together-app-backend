import asyncio
import logging
import sys
import os


# Add root directory to path to import the application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from app.database.database import get_session
from app.core.dependencies import get_ai_moderation_service


# Configure logging to see progress in Coolify logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("ai_daily_scan")


async def run_scan():
    """
    Daily maintenance script to run AI moderation scan.
    """
    logger.info("Starting daily AI moderation scan...")
    
    # Get a database session
    # Since we're outside a FastAPI request, we use the generator manually
    session_generator = get_session()
    db = next(session_generator)
    
    try:
        # Initialize the service
        ai_service = get_ai_moderation_service()
        
        # Run the batch
        await ai_service.run_batch_moderation(db)
        
        logger.info("AI moderation scan completed successfully.")
    except Exception as e:
        logger.error(f"Critical error during AI scan: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_scan())
