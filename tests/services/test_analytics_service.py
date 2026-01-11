"""Tests for analytics service."""

from datetime import date, datetime
from unittest.mock import patch
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.association import Association
from app.models.report import Report
from app.models.enums import ProcessingStatus, UserType, ReportType, ReportTarget
from app.services import analytics as analytics_service
from app.services import user as user_service
from app.services import location as location_service
from app.models.location import LocationCreate


@pytest.fixture
def analytics_data(session: Session):
    # This fixture is currently unused by the tests below but good for reference/future
    # Update to match requirements
    pass


class TestAnalytics:
    def test_get_overview_statistics(self, session: Session):
        # 1. Validated Association
        u1 = user_service.create_user(
            session,
            UserCreate(
                username="u1",
                email="e1@e.com",
                password="password123",
                user_type=UserType.ASSOCIATION,
            ),
        )
        a1 = Association(
            id_user=u1.id_user,
            name="A1",
            rna_code="R1",
            company_name="C1",
            phone_number="P1",
            address="A1",
            zip_code="Z1",
            country="C1",
            verification_status=ProcessingStatus.APPROVED,
        )
        session.add(a1)

        # 2. Pending Association
        u2 = user_service.create_user(
            session,
            UserCreate(
                username="u2",
                email="e2@e.com",
                password="password123",
                user_type=UserType.ASSOCIATION,
            ),
        )
        a2 = Association(
            id_user=u2.id_user,
            name="A2",
            rna_code="R2",
            company_name="C2",
            phone_number="P2",
            address="A2",
            zip_code="Z2",
            country="C2",
            verification_status=ProcessingStatus.PENDING,
        )
        session.add(a2)

        # 3. Completed Mission (date_end < today)
        # Need location/category
        loc = location_service.create_location(
            session, LocationCreate(address="L", country="C", zip_code="Z")
        )

        session.commit()
        session.refresh(a1)

        from app.models.mission import Mission

        m1 = Mission(
            name="Past Mission",
            id_location=loc.id_location,
            id_asso=a1.id_asso,
            date_start=date(2020, 1, 1),
            date_end=date(2020, 1, 2),
            skills="S",
            description="D",
            capacity_min=1,
            capacity_max=5,
        )
        session.add(m1)

        # 4. Pending Report
        u3 = user_service.create_user(
            session,
            UserCreate(
                username="u3",
                email="e3@e.com",
                password="password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        r1 = Report(
            id_user_reporter=u3.id_user,
            id_user_reported=u1.id_user,
            reason="Reason is long enough",
            state=ProcessingStatus.PENDING,
            type=ReportType.OTHER,
            target=ReportTarget.PROFILE,
        )
        session.add(r1)

        session.commit()

        stats = analytics_service.get_overview_statistics(session)

        assert stats["total_validated_associations"] == 1
        assert stats["pending_associations_count"] == 1
        assert stats["total_completed_missions"] == 1
        assert stats["total_users"] == 3
        assert stats["pending_reports_count"] == 1

    def test_get_report_statistics(self, session: Session):
        u = user_service.create_user(
            session,
            UserCreate(
                username="u",
                email="e@e.com",
                password="password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        u_rep = user_service.create_user(
            session,
            UserCreate(
                username="ur",
                email="er@e.com",
                password="password123",
                user_type=UserType.VOLUNTEER,
            ),
        )

        session.add(
            Report(
                id_user_reporter=u.id_user,
                id_user_reported=u_rep.id_user,
                reason="Reason long enough 1",
                state=ProcessingStatus.PENDING,
                type=ReportType.OTHER,
                target=ReportTarget.PROFILE,
            )
        )
        session.add(
            Report(
                id_user_reporter=u.id_user,
                id_user_reported=u_rep.id_user,
                reason="Reason long enough 2",
                state=ProcessingStatus.APPROVED,
                type=ReportType.OTHER,
                target=ReportTarget.PROFILE,
            )
        )
        session.add(
            Report(
                id_user_reporter=u.id_user,
                id_user_reported=u_rep.id_user,
                reason="Reason long enough 3",
                state=ProcessingStatus.REJECTED,
                type=ReportType.OTHER,
                target=ReportTarget.PROFILE,
            )
        )
        session.commit()

        stats = analytics_service.get_report_statistics(session)
        assert stats["pending"] == 1
        assert stats["accepted"] == 1
        assert stats["rejected"] == 1

    def test_get_volunteers_by_month_mocked(self, session: Session):
        # Mocking the query result because sqlite doesn't support date_trunc
        mock_results = [(datetime(2023, 1, 1), 5), (datetime(2023, 2, 1), 10)]

        with patch.object(session, "exec") as mock_exec:
            mock_exec.return_value.all.return_value = mock_results

            # Let's mock 'date' to have a fixed 'today' so we can assert exact output.
            with patch("app.services.analytics.date") as mock_date:
                mock_date.today.return_value = date(2023, 3, 15)
                # months=3 means: Mar, Feb, Jan.
                # Start date = 2023-01-01.

                stats = analytics_service.get_volunteers_by_month(session, months=3)

                assert stats[0]["month"] == "2023-01"
                assert stats[0]["value"] == 5
                assert stats[1]["month"] == "2023-02"
                assert stats[1]["value"] == 10
                assert stats[2]["month"] == "2023-03"
                assert stats[2]["value"] == 0

    def test_get_missions_by_month_mocked(self, session: Session):
        mock_results = [
            (datetime(2023, 1, 1), 2),
        ]

        with patch.object(session, "exec") as mock_exec:
            mock_exec.return_value.all.return_value = mock_results

            with patch("app.services.analytics.date") as mock_date:
                mock_date.today.return_value = date(2023, 2, 15)
                # months=2: Feb, Jan.

                stats = analytics_service.get_missions_by_month(session, months=2)

                assert len(stats) == 2
                assert stats[0]["month"] == "2023-01"
                assert stats[0]["value"] == 2
                assert stats[1]["month"] == "2023-02"
                assert stats[1]["value"] == 0
