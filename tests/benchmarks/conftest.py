"""Shared fixtures for benchmark tests."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool


@pytest.fixture(name="session")
def session_fixture():
    """
    Provide a SQLModel Session connected to a fresh in-memory SQLite database.

    Returns:
        session (Session): A SQLModel Session bound to an in-memory SQLite database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
