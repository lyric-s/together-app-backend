"""Performance benchmarks for category service operations."""

from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services import category as category_service


def test_category_creation_performance(
    benchmark: BenchmarkFixture, session: Session, category_create_data_factory, tracker
):
    """Benchmark category creation operation."""

    @benchmark
    def create_category():
        category = category_service.create_category(
            session=session, category_in=category_create_data_factory()
        )
        tracker.append(category)
        return category.id_categ


def test_get_all_categories_performance(
    benchmark: BenchmarkFixture, session: Session, category_create_data_factory
):
    """Benchmark retrieving all categories."""
    # Setup: Create some categories
    for _ in range(10):
        category_service.create_category(
            session=session, category_in=category_create_data_factory()
        )
    session.flush()

    @benchmark
    def get_all_categories():
        session.expire_all()
        return category_service.get_all_categories(session=session)
