"""Performance benchmarks for analytics service operations."""

from datetime import datetime
from unittest.mock import patch
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services import analytics as analytics_service


def test_get_overview_statistics_performance(
    benchmark: BenchmarkFixture,
    session: Session,
):
    """Benchmark retrieving overview statistics."""

    # Setup is minimal as it's mostly counts
    @benchmark
    def get_overview():
        session.expire_all()
        return analytics_service.get_overview_statistics(session=session)


def test_get_volunteers_by_month_performance(
    benchmark: BenchmarkFixture,
    session: Session,
):
    """Benchmark retrieving monthly volunteer registration statistics."""
    # Mocking the query result because sqlite doesn't support date_trunc
    mock_results = [(datetime(2023, 1, 1), 5), (datetime(2023, 2, 1), 10)]

    with patch.object(session, "exec") as mock_exec:
        mock_exec.return_value.all.return_value = mock_results

        @benchmark
        def get_volunteers_monthly():
            return analytics_service.get_volunteers_by_month(session=session)


def test_get_missions_by_month_performance(
    benchmark: BenchmarkFixture,
    session: Session,
):
    """Benchmark retrieving monthly mission statistics."""
    mock_results = [
        (datetime(2023, 1, 1), 2),
    ]

    with patch.object(session, "exec") as mock_exec:
        mock_exec.return_value.all.return_value = mock_results

        @benchmark
        def get_missions_monthly():
            return analytics_service.get_missions_by_month(session=session)
