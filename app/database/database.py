from app.core.config import get_settings
from sqlmodel import Session, SQLModel, create_engine

connect_args = {"check_same_thread": False}
engine = create_engine(get_settings().DATABASE_URL, echo=False, pool_pre_ping=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
