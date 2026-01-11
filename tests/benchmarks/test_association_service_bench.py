"""Performance benchmarks for association service operations."""

from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services import association as association_service


def test_association_creation_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data_factory,
    association_create_data_factory,
    tracker,
):
    """Benchmark association creation operation."""

    @benchmark
    def create_association():
        association = association_service.create_association(
            session=session,
            user_in=user_create_data_factory(),
            association_in=association_create_data_factory(),
        )
        tracker.append(association)
        tracker.append(association.user)
        return association.id_asso


def test_association_retrieval_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data_factory,
    association_create_data_factory,
):
    """Benchmark association retrieval by ID operation."""
    association = association_service.create_association(
        session=session,
        user_in=user_create_data_factory(),
        association_in=association_create_data_factory(),
    )
    session.flush()
    association_id = association.id_asso

    @benchmark
    def get_association():
        session.expire_all()
        assert association_id is not None
        return association_service.get_association(
            session=session, association_id=association_id
        )


def test_get_associations_list_performance(
    benchmark: BenchmarkFixture,
    session: Session,
    user_create_data_factory,
    association_create_data_factory,
):
    """Benchmark retrieving a paginated list of associations."""
    # Setup: Create some associations
    for _ in range(10):
        association_service.create_association(
            session=session,
            user_in=user_create_data_factory(),
            association_in=association_create_data_factory(),
        )
    session.flush()

    @benchmark
    def get_associations():
        session.expire_all()
        return association_service.get_associations(session=session, limit=10)
