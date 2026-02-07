import pytest
from sqlmodel import Session
from fastapi.testclient import TestClient
from app.models.admin import AdminCreate
from app.services import admin as admin_service
from app.core.security import create_access_token
from app.models.ai_report import AIReport
from app.models.enums import AIContentCategory, ReportTarget, ProcessingStatus

@pytest.fixture(name="admin_token")
def admin_token_fixture(session: Session) -> str:
    """Fixture to provide a valid admin token."""
    admin_in = AdminCreate(
        username="admin_tester_ai",
        email="admin_tester_ai@example.com",
        password="password",
        first_name="Admin",
        last_name="Tester",
    )
    existing = admin_service.get_admin_by_username(session, "admin_tester_ai")
    if not existing:
        admin = admin_service.create_admin(session, admin_in)
        session.commit()
    else:
        admin = existing

    return create_access_token(data={"sub": admin.username, "mode": "admin"})

@pytest.fixture(name="sample_ai_report")
def sample_ai_report_fixture(session: Session) -> AIReport:
    """Fixture to create a sample AI report."""
    report = AIReport(
        target=ReportTarget.PROFILE,
        target_id=10,
        classification=AIContentCategory.SPAM_LIKE,
        confidence_score=0.95,
        model_version="CamemBERT-v1",
        state=ProcessingStatus.PENDING
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report

def test_get_all_ai_reports(client: TestClient, admin_token: str, sample_ai_report: AIReport):
    """Test that an admin can retrieve all AI reports."""
    response = client.get(
        "/internal/admin/ai-reports",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["id_report"] == sample_ai_report.id_report
    assert data[0]["classification"] == "SPAM_LIKE"

def test_get_all_ai_reports_unauthorized(client: TestClient):
    """Test that non-admins cannot access AI reports."""
    response = client.get("/internal/admin/ai-reports")
    assert response.status_code == 401

def test_update_ai_report_state(client: TestClient, session: Session, admin_token: str, sample_ai_report: AIReport):
    """Test that an admin can update an AI report state."""
    response = client.patch(
        f"/internal/admin/ai-reports/{sample_ai_report.id_report}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"state": "APPROVED"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "APPROVED"
    
    # Verify in DB using the session fixture
    session.expire_all() # Ensure we get fresh data
    db_report = session.get(AIReport, sample_ai_report.id_report)
    assert db_report is not None
    assert db_report.state == ProcessingStatus.APPROVED

def test_update_ai_report_state_not_found(client: TestClient, admin_token: str):
    """Test updating a non-existent AI report returns 404."""
    response = client.patch(
        "/internal/admin/ai-reports/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"state": "REJECTED"}
    )
    assert response.status_code == 404
