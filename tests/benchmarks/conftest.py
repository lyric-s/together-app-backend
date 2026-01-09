"""Shared fixtures for benchmark tests."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool


@pytest.fixture(name="session")
def session_fixture():
    """
    Create and yield a SQLModel Session bound to a fresh in-memory SQLite database.

    Yields:
        Session: A SQLModel Session connected to the created in-memory SQLite database; the session is closed when the fixture tears down.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
