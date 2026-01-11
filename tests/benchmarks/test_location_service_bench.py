"""Performance benchmarks for location service operations."""

from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services import location as location_service


def test_location_creation_performance(
    benchmark: BenchmarkFixture, session: Session, location_create_data_factory, tracker
):
    """Benchmark location creation operation."""

    @benchmark
    def create_location():
        location = location_service.create_location(
            session=session, location_in=location_create_data_factory()
        )
        tracker.append(location)
        return location.id_location


def test_location_retrieval_performance(
    benchmark: BenchmarkFixture, session: Session, location_create_data_factory
):
    """Benchmark location retrieval by ID operation."""
    location = location_service.create_location(
        session=session, location_in=location_create_data_factory()
    )
    session.flush()
    location_id = location.id_location

    @benchmark
    def get_location():
        session.expire_all()
        assert location_id is not None
        return location_service.get_location(session=session, location_id=location_id)
