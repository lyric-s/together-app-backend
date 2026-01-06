from sqlmodel import Session, select
from loguru import logger

from app.core.config import get_settings
from app.models.admin import Admin
from app.core.password import get_password_hash


def init_db(session: Session) -> None:
    """
    Ensure the configured first superuser exists in the database.

    Creates an Admin record from FIRST_SUPERUSER_EMAIL, FIRST_SUPERUSER_USERNAME, and
    FIRST_SUPERUSER_PASSWORD in application settings when a user with the configured
    username is not present. If required settings are missing, the function logs a
    warning and returns without making changes. On successful creation the new user
    is added and the transaction committed; if commit fails the transaction is
    rolled back and the original exception is propagated.

    Parameters:
        session (Session): SQLModel session used to query, add, and commit the Admin.

    Raises:
        Exception: If adding or committing the new Admin fails.
    """
    settings = get_settings()
    if (
        not settings.FIRST_SUPERUSER_EMAIL
        or not settings.FIRST_SUPERUSER_PASSWORD.get_secret_value()
        or not settings.FIRST_SUPERUSER_USERNAME
    ):
        logger.warning("First superuser not configured. Skipping creation.")
        return

    admin = session.exec(
        select(Admin).where(
            (Admin.username == settings.FIRST_SUPERUSER_USERNAME)
            | (Admin.email == settings.FIRST_SUPERUSER_EMAIL)
        )
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
