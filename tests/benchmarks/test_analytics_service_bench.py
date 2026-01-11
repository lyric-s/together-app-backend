"""Performance benchmarks for analytics service operations."""

from datetime import date, timedelta
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.services import analytics as analytics_service
from app.models.user import User
from app.models.mission import Mission
from app.models.enums import UserType


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
    # Add some data for realistic benchmark
    for i in range(10):
        u = User(
            username=f"user_{i}",
            email=f"user_{i}@example.com",
            hashed_password="hash",
            user_type=UserType.VOLUNTEER,
        )
        session.add(u)
    session.commit()

    @benchmark
    def get_volunteers_monthly():
        return analytics_service.get_volunteers_by_month(session=session)


def test_get_missions_by_month_performance(
    benchmark: BenchmarkFixture,
    session: Session,
):
    """Benchmark retrieving monthly mission statistics."""
    # Add some data for realistic benchmark
    today = date.today()
    for i in range(5):
        m = Mission(
            name=f"Mission {i}",
            id_location=1,  # Assuming location 1 exists or is not strictly validated for this bench
            id_asso=1,
            date_start=today - timedelta(days=10),
            date_end=today - timedelta(days=1),
            skills="None",
            description="None",
            capacity_min=1,
            capacity_max=10,
        )
        session.add(m)
    session.commit()

    @benchmark
    def get_missions_monthly():
        return analytics_service.get_missions_by_month(session=session)
