"""Tests for report router endpoints."""

import pytest
from sqlmodel import Session
from fastapi.testclient import TestClient

from app.models.user import UserCreate
from app.models.report import ReportCreate
from app.models.enums import UserType, ReportType, ReportTarget, ProcessingStatus
from app.services import user as user_service
from app.core.security import create_access_token


@pytest.fixture(name="auth_user1")
def auth_user1_fixture(session: Session):
    """Create authenticated user (reporter)."""
    user_create = UserCreate(
        username="auth_reporter",
        email="auth_reporter@example.com",
        password="Password123",
        user_type=UserType.VOLUNTEER,
    )
    user = user_service.create_user(session, user_create)
    return user


@pytest.fixture(name="auth_user2")
def auth_user2_fixture(session: Session):
    """Create authenticated user (to be reported)."""
    user_create = UserCreate(
        username="auth_reported",
        email="auth_reported@example.com",
        password="Password123",
        user_type=UserType.ASSOCIATION,
    )
    user = user_service.create_user(session, user_create)
    return user


@pytest.fixture(name="auth_token")
def auth_token_fixture(auth_user1):
    """Generate valid JWT token for auth_user1."""
    return create_access_token(data={"sub": auth_user1.username})


class TestCreateReportEndpoint:
    """Test POST /reports/ endpoint."""

    def test_create_report_success(
        self, session: Session, client: TestClient, auth_user1, auth_user2, auth_token
    ):
        """Successfully create report with valid authentication."""
        payload = {
            "type": ReportType.HARASSMENT.value,
            "target": ReportTarget.PROFILE.value,
            "reason": "This user has been harassing me repeatedly.",
            "id_user_reported": auth_user2.id_user,
        }

        response = client.post(
            "/reports/", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == ReportType.HARASSMENT.value
        assert data["id_user_reported"] == auth_user2.id_user
        assert data["state"] == ProcessingStatus.PENDING.value
        assert "id_report" in data

    def test_create_report_unauthorized(self, client: TestClient, auth_user2):
        """Reject report creation without authentication."""
        payload = {
            "type": ReportType.SPAM.value,
            "target": ReportTarget.MESSAGE.value,
            "reason": "Spam message from this user.",
            "id_user_reported": auth_user2.id_user,
        }

        response = client.post("/reports/", json=payload)
        assert response.status_code == 401

    def test_create_report_invalid_token(self, client: TestClient, auth_user2):
        """Reject report creation with invalid token."""
        payload = {
            "type": ReportType.SPAM.value,
            "target": ReportTarget.MESSAGE.value,
            "reason": "Spam message from this user.",
            "id_user_reported": auth_user2.id_user,
        }

        response = client.post(
            "/reports/",
            json=payload,
            headers={"Authorization": "Bearer invalid_token_12345"},
        )
        assert response.status_code == 401

    def test_create_report_self_report(
        self, client: TestClient, auth_user1, auth_token
    ):
        """Cannot report yourself."""
        payload = {
            "type": ReportType.HARASSMENT.value,
            "target": ReportTarget.PROFILE.value,
            "reason": "Trying to report myself for testing.",
            "id_user_reported": auth_user1.id_user,
        }

        response = client.post(
            "/reports/", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 422  # ValidationError returns 422

    def test_create_report_duplicate_pending(
        self, client: TestClient, auth_user1, auth_user2, auth_token
    ):
        """Cannot create duplicate PENDING report."""
        payload = {
            "type": ReportType.HARASSMENT.value,
            "target": ReportTarget.PROFILE.value,
            "reason": "First report against this user with sufficient detail.",
            "id_user_reported": auth_user2.id_user,
        }

        # First report succeeds
        response1 = client.post(
            "/reports/", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response1.status_code == 201

        # Second report fails
        response2 = client.post(
            "/reports/", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response2.status_code == 409  # AlreadyExistsError returns 409 (Conflict)

    def test_create_report_nonexistent_user(self, client: TestClient, auth_token):
        """Cannot report non-existent user."""
        payload = {
            "type": ReportType.FRAUD.value,
            "target": ReportTarget.MISSION.value,
            "reason": "Reporting a non-existent user for fraud.",
            "id_user_reported": 99999,
        }

        response = client.post(
            "/reports/", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404

    def test_create_report_invalid_payload(self, client: TestClient, auth_token):
        """Reject report with invalid payload (missing required fields)."""
        payload = {
            "type": ReportType.SPAM.value,
            # Missing 'target', 'reason', 'id_user_reported'
        }

        response = client.post(
            "/reports/", json=payload, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 422  # Validation error

    def test_create_report_all_types(
        self, session: Session, client: TestClient, auth_user1, auth_token
    ):
        """Create reports with different types and targets."""
        test_cases = [
            (ReportType.SPAM, ReportTarget.MESSAGE),
            (ReportType.FRAUD, ReportTarget.MISSION),
            (ReportType.INAPPROPRIATE_BEHAVIOR, ReportTarget.OTHER),
        ]

        for report_type, report_target in test_cases:
            # Create new user for each report to avoid duplicates
            new_user = user_service.create_user(
                session,
                UserCreate(
                    username=f"user_{report_type.value}_{report_target.value}",
                    email=f"{report_type.value}_{report_target.value}@example.com",
                    password="Password123",
                    user_type=UserType.VOLUNTEER,
                ),
            )

            payload = {
                "type": report_type.value,
                "target": report_target.value,
                "reason": "Valid reason with minimum 10 characters for testing.",
                "id_user_reported": new_user.id_user,
            }

            response = client.post(
                "/reports/",
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["type"] == report_type.value
            assert data["target"] == report_target.value


class TestGetMyReportsEndpoint:
    """Test GET /reports/me endpoint."""

    def test_get_my_reports_success(
        self, session: Session, client: TestClient, auth_user1, auth_user2, auth_token
    ):
        """Retrieve all reports made by authenticated user."""
        # Create 2 reports by auth_user1
        from app.services import report as report_service

        report_service.create_report(
            session,
            auth_user1.id_user,
            ReportCreate(
                type=ReportType.HARASSMENT,
                target=ReportTarget.PROFILE,
                reason="First report by authenticated user.",
                id_user_reported=auth_user2.id_user,
            ),
        )

        # Create another user to report
        user3 = user_service.create_user(
            session,
            UserCreate(
                username="third_user",
                email="third@example.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )

        report_service.create_report(
            session,
            auth_user1.id_user,
            ReportCreate(
                type=ReportType.SPAM,
                target=ReportTarget.MESSAGE,
                reason="Second report by authenticated user.",
                id_user_reported=user3.id_user,
            ),
        )

        response = client.get(
            "/reports/me", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Reports should have correct state and target information
        assert all("id_report" in r for r in data)
        assert all(r["state"] == ProcessingStatus.PENDING.value for r in data)

    def test_get_my_reports_empty(self, client: TestClient, auth_token):
        """User with no reports returns empty list."""
        response = client.get(
            "/reports/me", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_my_reports_unauthorized(self, client: TestClient):
        """Reject request without authentication."""
        response = client.get("/reports/me")
        assert response.status_code == 401

    def test_get_my_reports_invalid_token(self, client: TestClient):
        """Reject request with invalid token."""
        response = client.get(
            "/reports/me", headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401

    def test_get_my_reports_only_own_reports(
        self, session: Session, client: TestClient, auth_user1, auth_user2, auth_token
    ):
        """User only sees their own reports, not others'."""
        from app.services import report as report_service

        # User3 to be reported by both users
        user3 = user_service.create_user(
            session,
            UserCreate(
                username="reported_by_both",
                email="reportedbyboth@example.com",
                password="Password123",
                user_type=UserType.VOLUNTEER,
            ),
        )

        # auth_user1 reports user3
        report_service.create_report(
            session,
            auth_user1.id_user,
            ReportCreate(
                type=ReportType.HARASSMENT,
                target=ReportTarget.PROFILE,
                reason="Report by auth_user1.",
                id_user_reported=user3.id_user,
            ),
        )

        # auth_user2 reports user3 (should NOT appear in auth_user1's list)
        report_service.create_report(
            session,
            auth_user2.id_user,
            ReportCreate(
                type=ReportType.SPAM,
                target=ReportTarget.MESSAGE,
                reason="Report by auth_user2, should not appear.",
                id_user_reported=user3.id_user,
            ),
        )

        response = client.get(
            "/reports/me", headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # User should only see their own report
        assert data[0]["type"] == ReportType.HARASSMENT.value
