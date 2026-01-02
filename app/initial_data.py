from loguru import logger
from sqlmodel import Session

from app.database.database import engine, create_db_and_tables
from app.database.init_db import init_db


def init() -> None:
    with Session(engine) as session:
        create_db_and_tables()
        init_db(session)


def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
