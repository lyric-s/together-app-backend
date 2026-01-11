"""Performance benchmarks for admin service operations."""

from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services import admin as admin_service


def test_admin_creation_performance(
    benchmark: BenchmarkFixture, session: Session, admin_create_data_factory, tracker
):
    """Benchmark admin creation operation."""

    @benchmark
    def create_admin():
        admin = admin_service.create_admin(
            session=session, admin_in=admin_create_data_factory()
        )
        tracker.append(admin)
        return admin.id_admin


def test_admin_retrieval_performance(
    benchmark: BenchmarkFixture, session: Session, admin_create_data_factory
):
    """Benchmark admin retrieval by ID operation."""
    admin = admin_service.create_admin(
        session=session, admin_in=admin_create_data_factory()
    )
    session.flush()
    admin_id = admin.id_admin

    @benchmark
    def get_admin():
        session.expire_all()
        assert admin_id is not None
        return admin_service.get_admin(session=session, admin_id=admin_id)
