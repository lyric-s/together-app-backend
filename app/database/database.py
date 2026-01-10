from app.core.config import get_settings
from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(
    get_settings().DATABASE_URL,
    pool_pre_ping=True,
)


def create_db_and_tables():
    """
    Create database tables defined in SQLModel metadata.

    Creates all tables in the configured database according to `SQLModel.metadata` using the module-level engine.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Provide a context-managed SQLModel session.

    Returns:
        session (Session): A SQLModel Session bound to the module-level engine. The session is yielded for use and is closed when the generator exits.
    """
    with Session(engine) as session:
        yield session
