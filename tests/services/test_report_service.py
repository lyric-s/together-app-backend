"""Tests for report service CRUD operations."""

import pytest
from sqlmodel import Session

from app.models.user import UserCreate
from app.models.report import ReportCreate, ReportUpdate
from app.models.enums import UserType, ReportType, ReportTarget, ProcessingStatus
from app.services import report as report_service
from app.services import user as user_service
from app.exceptions import NotFoundError, AlreadyExistsError, ValidationError

# Test data constants
NONEXISTENT_ID = 99999


@pytest.fixture(name="user1")
def user1_fixture(session: Session):
    """Create a test user (reporter)."""
    user_create = UserCreate(
        username="reporter_user",
        email="reporter@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    return user_service.create_user(session, user_create)


@pytest.fixture(name="user2")
def user2_fixture(session: Session):
    """Create a test user (reported)."""
    user_create = UserCreate(
        username="reported_user",
        email="reported@example.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    return user_service.create_user(session, user_create)


@pytest.fixture(name="user3")
def user3_fixture(session: Session):
    """Create a third test user."""
    user_create = UserCreate(
        username="another_user",
        email="another@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    return user_service.create_user(session, user_create)


class TestCreateReport:
    def test_create_report_success(self, session: Session, user1, user2):
        """Successfully create a report from user1 about user2."""
        report_create = ReportCreate(
            type=ReportType.HARASSMENT,
            target=ReportTarget.PROFILE,
            reason="This user has been harassing me repeatedly.",
            id_user_reported=user2.id_user,
        )

        report = report_service.create_report(session, user1.id_user, report_create)

        assert report.id_report is not None
        assert report.id_user_reporter == user1.id_user
        assert report.id_user_reported == user2.id_user
        assert report.type == ReportType.HARASSMENT
        assert report.target == ReportTarget.PROFILE
        assert report.reason == "This user has been harassing me repeatedly."
        assert report.state == ProcessingStatus.PENDING
        assert report.date_reporting is not None

    def test_create_report_all_types(self, session: Session, user1, user2):
        """Test creating reports with different types and targets."""
        test_cases = [
            (ReportType.SPAM, ReportTarget.MESSAGE),
            (ReportType.FRAUD, ReportTarget.MISSION),
            (ReportType.INAPPROPRIATE_BEHAVIOR, ReportTarget.OTHER),
            (ReportType.OTHER, ReportTarget.PROFILE),
        ]

        for report_type, report_target in test_cases:
            # Create a new user for each report to avoid duplicate errors
            new_user = user_service.create_user(
                session,
                UserCreate(
                    username=f"user_{report_type.value}",
                    email=f"{report_type.value}@example.com",
                    password="Password123",
                    user_type=UserType.VOLUNTEER,
                ),
            )
            report_create = ReportCreate(
                type=report_type,
                target=report_target,
                reason="Valid reason with minimum 10 characters",
                id_user_reported=new_user.id_user,
            )
            report = report_service.create_report(session, user1.id_user, report_create)
            assert report.type == report_type
            assert report.target == report_target

    def test_create_report_self_report(self, session: Session, user1):
        """Cannot report yourself."""
        report_create = ReportCreate(
            type=ReportType.HARASSMENT,
            target=ReportTarget.PROFILE,
            reason="Trying to report myself for testing.",
            id_user_reported=user1.id_user,
        )

        with pytest.raises(ValidationError) as exc_info:
            report_service.create_report(session, user1.id_user, report_create)
        assert "cannot report yourself" in str(exc_info.value).lower()

    def test_create_report_user_not_found(self, session: Session, user1):
        """Cannot report non-existent user."""
        report_create = ReportCreate(
            type=ReportType.HARASSMENT,
            target=ReportTarget.PROFILE,
            reason="Reporting a non-existent user.",
            id_user_reported=NONEXISTENT_ID,
        )

        with pytest.raises(NotFoundError) as exc_info:
            report_service.create_report(session, user1.id_user, report_create)
        assert exc_info.value.resource == "User"

    def test_create_report_duplicate_pending(self, session: Session, user1, user2):
        """Cannot create duplicate PENDING report against same user."""
        report_create = ReportCreate(
            type=ReportType.HARASSMENT,
            target=ReportTarget.PROFILE,
            reason="First report against this user.",
            id_user_reported=user2.id_user,
        )

        # First report succeeds
        report_service.create_report(session, user1.id_user, report_create)

        # Second report fails
        with pytest.raises(AlreadyExistsError):
            report_service.create_report(session, user1.id_user, report_create)

    def test_create_report_after_resolved(self, session: Session, user1, user2):
        """Can create new report after previous one is resolved."""
        report_create = ReportCreate(
            type=ReportType.HARASSMENT,
            target=ReportTarget.PROFILE,
            reason="First report against this user.",
            id_user_reported=user2.id_user,
        )

        # First report
        report1 = report_service.create_report(session, user1.id_user, report_create)
        assert report1.id_report is not None

        # Mark as APPROVED (resolved)
        report_service.update_report(
            session, report1.id_report, ReportUpdate(state=ProcessingStatus.APPROVED)
        )

        # Second report should succeed since first is not PENDING
        report_create2 = ReportCreate(
            type=ReportType.SPAM,
            target=ReportTarget.MESSAGE,
            reason="Another issue with the same user.",
            id_user_reported=user2.id_user,
        )
        report2 = report_service.create_report(session, user1.id_user, report_create2)
        assert report2.id_report != report1.id_report


class TestGetReport:
    def test_get_report_by_id(self, session: Session, user1, user2):
        """Get a report by ID."""
        report_create = ReportCreate(
            type=ReportType.HARASSMENT,
            target=ReportTarget.PROFILE,
            reason="Test report for retrieval.",
            id_user_reported=user2.id_user,
        )
        created = report_service.create_report(session, user1.id_user, report_create)
        assert created.id_report is not None

        retrieved = report_service.get_report(session, created.id_report)
        assert retrieved is not None
        assert retrieved.id_report == created.id_report

    def test_get_report_not_found(self, session: Session):
        """Get non-existent report returns None."""
        report = report_service.get_report(session, NONEXISTENT_ID)
        assert report is None


class TestGetReportsByReporter:
    def test_get_reports_by_reporter(self, session: Session, user1, user2, user3):
        """Get all reports made by a user."""
        # User1 reports User2
        report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.HARASSMENT,
                target=ReportTarget.PROFILE,
                reason="First report by user1.",
                id_user_reported=user2.id_user,
            ),
        )

        # User1 reports User3
        report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.SPAM,
                target=ReportTarget.MESSAGE,
                reason="Second report by user1.",
                id_user_reported=user3.id_user,
            ),
        )

        # User2 reports User3 (different reporter)
        report_service.create_report(
            session,
            user2.id_user,
            ReportCreate(
                type=ReportType.FRAUD,
                target=ReportTarget.MISSION,
                reason="Report by user2, should not appear in user1's list.",
                id_user_reported=user3.id_user,
            ),
        )

        reports = report_service.get_reports_by_reporter(session, user1.id_user)
        assert len(reports) == 2
        assert all(r.id_user_reporter == user1.id_user for r in reports)

    def test_get_reports_by_reporter_empty(self, session: Session, user1):
        """User with no reports returns empty list."""
        reports = report_service.get_reports_by_reporter(session, user1.id_user)
        assert reports == []


class TestGetReportsByReportedUser:
    def test_get_reports_by_reported_user(self, session: Session, user1, user2, user3):
        """Get all reports against a specific user."""
        # User1 reports User3
        report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.HARASSMENT,
                target=ReportTarget.PROFILE,
                reason="User1 reports User3.",
                id_user_reported=user3.id_user,
            ),
        )

        # User2 reports User3
        report_service.create_report(
            session,
            user2.id_user,
            ReportCreate(
                type=ReportType.SPAM,
                target=ReportTarget.MESSAGE,
                reason="User2 reports User3.",
                id_user_reported=user3.id_user,
            ),
        )

        # User1 reports User2 (different target)
        report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.FRAUD,
                target=ReportTarget.MISSION,
                reason="User1 reports User2, should not appear.",
                id_user_reported=user2.id_user,
            ),
        )

        reports = report_service.get_reports_by_reported_user(session, user3.id_user)
        assert len(reports) == 2
        assert all(r.id_user_reported == user3.id_user for r in reports)

    def test_get_reports_by_reported_user_empty(self, session: Session, user1):
        """User with no reports against them returns empty list."""
        reports = report_service.get_reports_by_reported_user(session, user1.id_user)
        assert reports == []


class TestGetAllReports:
    def test_get_all_reports(self, session: Session, user1, user2, user3):
        """Get all reports in the system."""
        # Create multiple reports
        report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.HARASSMENT,
                target=ReportTarget.PROFILE,
                reason="Report 1 for admin view.",
                id_user_reported=user2.id_user,
            ),
        )
        report_service.create_report(
            session,
            user2.id_user,
            ReportCreate(
                type=ReportType.SPAM,
                target=ReportTarget.MESSAGE,
                reason="Report 2 for admin view.",
                id_user_reported=user3.id_user,
            ),
        )

        reports = report_service.get_all_reports(session)
        assert len(reports) >= 2

    def test_get_all_reports_pagination(self, session: Session, user1, user2):
        """Test pagination for get_all_reports."""
        # Create 5 reports
        for i in range(5):
            new_user = user_service.create_user(
                session,
                UserCreate(
                    username=f"paginated_user_{i}",
                    email=f"paginated{i}@example.com",
                    password="Password123",
                    user_type=UserType.VOLUNTEER,
                ),
            )
            report_service.create_report(
                session,
                user1.id_user,
                ReportCreate(
                    type=ReportType.HARASSMENT,
                    target=ReportTarget.PROFILE,
                    reason=f"Report number {i} for pagination test.",
                    id_user_reported=new_user.id_user,
                ),
            )

        # Get first 3
        page1 = report_service.get_all_reports(session, offset=0, limit=3)
        assert len(page1) == 3

        # Get next 2
        page2 = report_service.get_all_reports(session, offset=3, limit=3)
        assert len(page2) >= 2


class TestUpdateReport:
    def test_update_report_state(self, session: Session, user1, user2):
        """Update report state from PENDING to APPROVED."""
        report = report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.HARASSMENT,
                target=ReportTarget.PROFILE,
                reason="Report to be approved.",
                id_user_reported=user2.id_user,
            ),
        )
        assert report.id_report is not None

        updated = report_service.update_report(
            session, report.id_report, ReportUpdate(state=ProcessingStatus.APPROVED)
        )

        assert updated.state == ProcessingStatus.APPROVED
        assert updated.id_report == report.id_report

    def test_update_report_not_found(self, session: Session):
        """Update non-existent report raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            report_service.update_report(
                session, NONEXISTENT_ID, ReportUpdate(state=ProcessingStatus.APPROVED)
            )
        assert exc_info.value.resource == "Report"


class TestDeleteReport:
    def test_delete_report_success(self, session: Session, user1, user2):
        """Successfully delete a report."""
        report = report_service.create_report(
            session,
            user1.id_user,
            ReportCreate(
                type=ReportType.SPAM,
                target=ReportTarget.MESSAGE,
                reason="Report to be deleted.",
                id_user_reported=user2.id_user,
            ),
        )
        assert report.id_report is not None

        report_service.delete_report(session, report.id_report)

        # Verify deletion
        deleted = report_service.get_report(session, report.id_report)
        assert deleted is None

    def test_delete_report_not_found(self, session: Session):
        """Delete non-existent report raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            report_service.delete_report(session, NONEXISTENT_ID)
        assert exc_info.value.resource == "Report"
