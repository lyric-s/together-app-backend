from sqlmodel import Session, select
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.models.admin import Admin
from app.models.category import Category
from app.core.password import get_password_hash
from app.exceptions import AlreadyExistsError
from app.database.init_sample_data import init_sample_data


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

    # Initialize categories
    init_categories(session)

    # Initialize sample data for non-production environments
    if settings.ENVIRONMENT in ("development", "staging"):
        init_sample_data(session)


def init_categories(session: Session) -> None:
    """
    Ensure initial categories exist in the database.

    Creates the standard set of mission categories if they don't already exist.
    This function is idempotent and safe to run multiple times.

    Categories are already seeded by migration, but this ensures they exist
    even if running from a fresh database without migrations.

    Parameters:
        session (Session): Database session used to query and create categories.
    """
    categories = [
        "Aide alimentaire",
        "Accompagnement seniors",
        "Soutien handicap",
        "Aide administrative",
        "Mentorat",
        "Sensibilisation citoyenne",
        "Informatique",
        "Création graphique",
        "Photo & vidéo",
        "Animaux",
        "Biodiversité",
        "Jardinage solidaire",
        "Animation",
        "Arts & loisirs",
        "Organisation événement",
        "Patrimoine culturel",
        "Sport & loisirs",
        "Bien-être",
        "Prévention santé",
        "Logistique terrain",
        "Accueil public",
        "Transport",
        "Bricolage",
        "Collecte dons",
        "Communication",
        "Gestion associative",
        "Recherche financements",
        "Humanitaire",
        "Aide urgence",
    ]

    created_count = 0
    for label in categories:
        existing = session.exec(select(Category).where(Category.label == label)).first()
        if not existing:
            session.add(Category(label=label))
            created_count += 1

    if created_count > 0:
        session.commit()
        logger.info(f"Created {created_count} new categories")
    else:
        logger.info("All categories already exist")
