from sqlmodel import Session, select
from loguru import logger

from app.core.config import get_settings
from app.models.admin import Admin
from app.core.security import get_password_hash


def init_db(session: Session) -> None:
    settings = get_settings()
    if (
        not settings.FIRST_SUPERUSER_EMAIL
        or not settings.FIRST_SUPERUSER_PASSWORD.get_secret_value()
        or not settings.FIRST_SUPERUSER_USERNAME
    ):
        logger.warning("First superuser not configured. Skipping creation.")
        return

    admin = session.exec(
        select(Admin).where(Admin.username == settings.FIRST_SUPERUSER_USERNAME)
    ).first()

    if not admin:
        admin = Admin(
            email=settings.FIRST_SUPERUSER_EMAIL,
            username=settings.FIRST_SUPERUSER_USERNAME,
            hashed_password=get_password_hash(
                settings.FIRST_SUPERUSER_PASSWORD.get_secret_value()
            ),
            first_name="Initial",
            last_name="Admin",
        )
        try:
            session.add(admin)
            session.commit()
            logger.info("First superuser created successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create first superuser: {e}")
            raise
    else:
        logger.info("First superuser already exists")
