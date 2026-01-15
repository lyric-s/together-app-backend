from app.core.config import get_settings
from loguru import logger
from sqlmodel import Session

from app.database.database import engine, create_db_and_tables
from app.database.init_db import init_db
from app.database.init_sample_data import init_sample_data


def init() -> None:
    """
    Create the database schema and populate initial data within a session.

    Sets up required tables and inserts the application's initial dataset using a session bound to the configured database engine.
    """
    with Session(engine) as session:
        create_db_and_tables()
        init_db(session)
        # Lowering just in case
        if get_settings().ENVIRONMENT.lower() != "production":
            init_sample_data(session)


def main() -> None:
    """
    Create the database schema and seed initial data while logging progress.

    Logs start and completion messages and performs the initialization that sets up tables and inserts initial records.
    """
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
