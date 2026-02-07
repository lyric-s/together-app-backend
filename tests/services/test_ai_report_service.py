import pytest
from sqlmodel import Session
from app.services import ai_report as ai_report_service
from app.models.ai_report import AIReport, AIReportUpdate
from app.models.enums import AIContentCategory, ReportTarget, ProcessingStatus
from app.exceptions import NotFoundError

@pytest.fixture
def sample_ai_report(session: Session) -> AIReport:
    """Fixture to create a sample AI report in the database."""
    report = AIReport(
        target=ReportTarget.PROFILE,
        target_id=1,
        classification=AIContentCategory.SPAM_LIKE,
        confidence_score=0.9,
        model_version="test-v1",
        state=ProcessingStatus.PENDING
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report

def test_get_ai_report(session: Session, sample_ai_report: AIReport):
    """Test retrieving an AI report by ID."""
    assert sample_ai_report.id_report is not None
    retrieved = ai_report_service.get_ai_report(session, sample_ai_report.id_report)
    assert retrieved is not None
    assert retrieved.id_report == sample_ai_report.id_report
    assert retrieved.classification == AIContentCategory.SPAM_LIKE

def test_get_ai_report_not_found(session: Session):
    """Test retrieving a non-existent AI report returns None."""
    assert ai_report_service.get_ai_report(session, 9999) is None

def test_get_ai_reports(session: Session, sample_ai_report: AIReport):
    """Test retrieving a list of AI reports."""
    reports = ai_report_service.get_ai_reports(session)
    assert len(reports) >= 1
    assert reports[0].id_report == sample_ai_report.id_report

def test_update_ai_report_state(session: Session, sample_ai_report: AIReport):
    """Test updating an AI report's state."""
    assert sample_ai_report.id_report is not None
    update_data = AIReportUpdate(state=ProcessingStatus.APPROVED)
    updated = ai_report_service.update_ai_report_state(session, sample_ai_report.id_report, update_data)
    
    # Check that change is flushed but not necessarily committed by service
    assert updated.state == ProcessingStatus.APPROVED
    
    # Verify in DB
    session.commit()
    db_report = session.get(AIReport, sample_ai_report.id_report)
    assert db_report is not None
    assert db_report.state == ProcessingStatus.APPROVED

def test_update_ai_report_state_not_found(session: Session):
    """Test updating a non-existent AI report raises NotFoundError."""
    with pytest.raises(NotFoundError):
        ai_report_service.update_ai_report_state(session, 9999, AIReportUpdate(state=ProcessingStatus.REJECTED))