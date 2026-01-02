from sqlmodel import Session, select
from loguru import logger

from app.core.config import get_settings
from app.models.admin import Admin
from app.core.security import get_password_hash


def init_db(session: Session) -> None:
    settings = get_settings()
    if not settings.FIRST_SUPERUSER_EMAIL or not settings.FIRST_SUPERUSER_PASSWORD:
        logger.warning("First superuser not configured. Skipping creation.")
        return

    admin = session.exec(
        select(Admin).where(Admin.username == settings.FIRST_SUPERUSER_USERNAME)
    ).first()

    if not admin:
        admin = Admin(
            email=settings.FIRST_SUPERUSER_EMAIL,
            username=settings.FIRST_SUPERUSER_USERNAME,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            first_name="Initial",
            last_name="Admin",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        logger.info(f"First superuser created: {admin.email}")
    else:
        logger.info(
            f"First superuser already exists: {settings.FIRST_SUPERUSER_USERNAME}"
        )
