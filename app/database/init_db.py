from sqlmodel import Session, select
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.models.admin import Admin
from app.core.password import get_password_hash
from app.exceptions import AlreadyExistsError


def init_db(session: Session) -> None:
    """
    Ensure the configured initial superuser exists in the database.

    If FIRST_SUPERUSER_EMAIL, FIRST_SUPERUSER_USERNAME, or FIRST_SUPERUSER_PASSWORD is not set, the function logs a warning and makes no changes. If an Admin with the configured username or email already exists, no action is taken. Otherwise, an Admin is created from the configured settings (first_name set to "Initial", last_name set to "Admin") and persisted.

    Parameters:
        session (Session): Database session used to query for an existing Admin and to add/commit a new Admin.

    Raises:
        AlreadyExistsError: If a unique constraint prevents creating the admin (username or email already exists).
        Exception: Any other error encountered while creating or persisting the Admin is propagated.
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
        except IntegrityError:
            session.rollback()
            logger.error("First superuser already exists (constraint violation)")
            raise AlreadyExistsError(
                "Admin", "username or email", settings.FIRST_SUPERUSER_USERNAME
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create first superuser: {e}")
            raise
    else:
        logger.info("First superuser already exists")
