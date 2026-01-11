"""Tests for analytics service."""

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.association import Association
from app.models.mission import Mission
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

    def test_get_volunteers_by_month(self, session: Session):
        # Create some volunteers in different months
        today = date.today()

        # This month
        u1 = user_service.create_user(
            session,
            UserCreate(
                username="v1",
                email="v1@e.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        u1.date_creation = datetime(today.year, today.month, 1)
        session.add(u1)

        # Last month
        last_month_date = today - relativedelta(months=1)
        assert isinstance(last_month_date, date)
        u2 = user_service.create_user(
            session,
            UserCreate(
                username="v2",
                email="v2@e.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )
        u2.date_creation = datetime(last_month_date.year, last_month_date.month, 1)
        session.add(u2)

        session.commit()

        stats = analytics_service.get_volunteers_by_month(session, months=2)

        # Sort just in case although the service should return them in order
        assert len(stats) == 2
        assert stats[0]["month"] == last_month_date.strftime("%Y-%m")
        assert stats[0]["value"] == 1
        assert stats[1]["month"] == today.strftime("%Y-%m")
        assert stats[1]["value"] == 1

    def test_get_missions_by_month(self, session: Session):
        # Setup for mission creation
        u1 = user_service.create_user(
            session,
            UserCreate(
                username="asso_m",
                email="asso_m@e.com",
                password="Password123",
                user_type=UserType.ASSOCIATION,
            ),
        )
        a1 = Association(
            id_user=u1.id_user,
            name="A1",
            rna_code="W1",
            company_name="C1",
            phone_number="P1",
            address="A1",
            zip_code="Z1",
            country="C1",
        )
        session.add(a1)
        loc = location_service.create_location(
            session, LocationCreate(address="L", country="C", zip_code="Z")
        )
        session.commit()
        session.refresh(a1)

        today = date.today()
        last_month_date = today - relativedelta(months=1)
        assert isinstance(last_month_date, date)

        # Mission ending last month
        m1 = Mission(
            name="M1",
            id_location=loc.id_location,
            id_asso=a1.id_asso,
            date_start=last_month_date - relativedelta(days=5),
            date_end=date(last_month_date.year, last_month_date.month, 1),
            skills="S",
            description="D",
            capacity_min=1,
            capacity_max=5,
        )
        session.add(m1)

        # Mission ending this month (but before today)
        if today.day > 1:
            m2 = Mission(
                name="M2",
                id_location=loc.id_location,
                id_asso=a1.id_asso,
                date_start=today - relativedelta(days=5),
                date_end=date(today.year, today.month, 1),
                skills="S",
                description="D",
                capacity_min=1,
                capacity_max=5,
            )
            session.add(m2)
            expected_this_month = 1
        else:
            expected_this_month = 0

        session.commit()

        stats = analytics_service.get_missions_by_month(session, months=2)

        assert len(stats) == 2
        assert stats[0]["month"] == last_month_date.strftime("%Y-%m")
        assert stats[0]["value"] == 1
        assert stats[1]["month"] == today.strftime("%Y-%m")
        assert stats[1]["value"] == expected_this_month
