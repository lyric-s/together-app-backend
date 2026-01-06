"""Shared fixtures for service tests."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool


@pytest.fixture(name="session")
def session_fixture():
    """
    Provide a SQLModel Session connected to a fresh in-memory SQLite database for a test.

    The database schema is created from SQLModel.metadata before yielding; the fixture yields a Session for use in the test and closes it when the test completes.

    Returns:
        session (Session): A SQLModel Session bound to the initialized in-memory SQLite database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
