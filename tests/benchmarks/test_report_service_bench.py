"""Benchmark tests for report service operations."""

import pytest
import uuid
from pytest_codspeed import BenchmarkFixture
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.report import ReportCreate
from app.models.enums import UserType, ReportType, ReportTarget
from app.services import user as user_service
from app.services import report as report_service


@pytest.fixture(name="reporter_user")
def reporter_user_fixture(session: Session):
    """Create reporter user for benchmarks."""
    return user_service.create_user(
        session,
        UserCreate(
            username="bench_reporter",
            email="bench_reporter@example.com",
            password="BenchPass123",
            user_type=UserType.VOLUNTEER,
        ),
    )


@pytest.fixture(name="reported_user")
def reported_user_fixture(session: Session):
    """Create user to be reported."""
    return user_service.create_user(
        session,
        UserCreate(
            username="bench_reported",
            email="bench_reported@example.com",
            password="BenchPass123",
            user_type=UserType.ASSOCIATION,
        ),
    )


class TestReportServiceBenchmarks:
    """Benchmark report service CRUD operations."""

    def test_create_report_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        reporter_user,
    ):
        """Benchmark creating a report."""

        @benchmark
        def create_report():
            # Need unique reported user for each iteration
            unique_user = user_service.create_user(
                session,
                UserCreate(
                    username=f"bench_reported_{uuid.uuid4().hex[:8]}",
                    email=f"bench_reported_{uuid.uuid4().hex[:8]}@example.com",
                    password="BenchPass123",
                    user_type=UserType.VOLUNTEER,
                ),
            )

            report_service.create_report(
                session,
                reporter_user.id_user,
                ReportCreate(
                    type=ReportType.HARASSMENT,
                    target=ReportTarget.PROFILE,
                    reason="Benchmark test report with sufficient detail.",
                    id_user_reported=unique_user.id_user,
                ),
            )

    def test_get_reports_by_reporter_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        reporter_user,
    ):
        """Benchmark retrieving reports by reporter."""
        # Create 10 reports first
        for i in range(10):
            unique_user = user_service.create_user(
                session,
                UserCreate(
                    username=f"bench_multi_{i}",
                    email=f"bench_multi_{i}@example.com",
                    password="BenchPass123",
                    user_type=UserType.VOLUNTEER,
                ),
            )
            report_service.create_report(
                session,
                reporter_user.id_user,
                ReportCreate(
                    type=ReportType.SPAM,
                    target=ReportTarget.MESSAGE,
                    reason=f"Benchmark report number {i} for retrieval.",
                    id_user_reported=unique_user.id_user,
                ),
            )

        @benchmark
        def get_reports():
            report_service.get_reports_by_reporter(session, reporter_user.id_user)

    def test_get_all_reports_benchmark(
        self,
        benchmark: BenchmarkFixture,
        session: Session,
        reporter_user,
    ):
        """Benchmark retrieving all reports (admin view)."""
        # Create 20 reports
        for i in range(20):
            unique_user = user_service.create_user(
                session,
                UserCreate(
                    username=f"bench_all_{i}",
                    email=f"bench_all_{i}@example.com",
                    password="BenchPass123",
                    user_type=UserType.VOLUNTEER,
                ),
            )
            report_service.create_report(
                session,
                reporter_user.id_user,
                ReportCreate(
                    type=ReportType.FRAUD,
                    target=ReportTarget.MISSION,
                    reason=f"Benchmark report {i} for get_all test.",
                    id_user_reported=unique_user.id_user,
                ),
            )

        @benchmark
        def get_all():
            report_service.get_all_reports(session, offset=0, limit=100)
