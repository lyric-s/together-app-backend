import pytest
from unittest.mock import MagicMock
from sqlmodel import Session, select

from app.services.ai_moderation_service import AIModerationService
from app.models.enums import AIContentCategory, ReportTarget, ProcessingStatus
from app.models.ai_report import AIReport
from app.models.report import Report
from app.models.mission import Mission
from app.models.user import User
from app.services.ai_moderation_client import AIModerationClient

class MockAIModerationClient(AIModerationClient):
    """
    Mock client for AI moderation that returns deterministic results without HTTP calls.
    """
    def __init__(self):
        self.spam_url = "http://mock-spam"
        self.toxicity_url = "http://mock-tox"
        self.auth_token = "mock-token"
        self.timeout = 5
        # Deterministic logic based on text content for testing
        if "spam" in text.lower():
            return AIContentCategory.SPAM_LIKE, 0.99
        if "toxic" in text.lower():
            # Test case for toxicity without score
            return AIContentCategory.TOXIC_LANGUAGE, None
        return None

@pytest.fixture
def mock_ai_client():
    return MockAIModerationClient()

@pytest.fixture
def ai_service(mock_ai_client):
    return AIModerationService(mock_ai_client)

@pytest.mark.asyncio
async def test_moderate_content_spam(session: Session, ai_service):
    """Test that spam content creates an AIReport with SPAM_LIKE label."""
    text = "This is a spam message with fraud links."
    target_id = 1
    
    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, text)
    
    # Verify AIReport was created
    report = session.exec(select(AIReport).where(AIReport.target_id == target_id)).first()
    assert report is not None
    assert report.classification == AIContentCategory.SPAM_LIKE
    assert report.confidence_score == 0.99
    assert report.state == ProcessingStatus.PENDING

@pytest.mark.asyncio
async def test_moderate_content_toxic_no_score(session: Session, ai_service):
    """Test that toxic content creates an AIReport even without confidence score."""
    text = "This is a very toxic and mean message."
    target_id = 2
    
    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, text)
    
    report = session.exec(select(AIReport).where(AIReport.target_id == target_id)).first()
    assert report is not None
    assert report.classification == AIContentCategory.TOXIC_LANGUAGE
    assert report.confidence_score is None

@pytest.mark.asyncio
async def test_skip_if_human_report_exists(session: Session, ai_service):
    """Test that AI scan is skipped if a human report already exists."""
    target_id = 3
    # Create a human report
    from app.models.enums import ReportType
    human_report = Report(
        type=ReportType.OTHER,
        target=ReportTarget.PROFILE,
        reason="Human already reported this",
        id_user_reported=target_id,
        id_user_reporter=999 
    )
    session.add(human_report)
    session.commit()
    
    text = "This is spam content"
    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, text)
    
    # Verify NO AIReport was created
    ai_report = session.exec(select(AIReport).where(AIReport.target_id == target_id)).first()
    assert ai_report is None

@pytest.mark.asyncio
async def test_skip_if_pending_ai_report_exists(session: Session, ai_service):
    """Test that AI scan is skipped if a pending AI report already exists."""
    target_id = 4
    # Create existing pending AI report
    existing_report = AIReport(
        target=ReportTarget.PROFILE,
        target_id=target_id,
        classification=AIContentCategory.SPAM_LIKE,
        confidence_score=0.5,
        model_version="old-v1",
        state=ProcessingStatus.PENDING
    )
    session.add(existing_report)
    session.commit()
    
    text = "This is spam content"
    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, text)
    
    # Verify no NEW report was created (only the old one exists)
    reports = session.exec(select(AIReport).where(AIReport.target_id == target_id)).all()
    assert len(reports) == 1
    assert reports[0].model_version == "old-v1"

@pytest.mark.asyncio
async def test_batch_moderation_logic(session: Session, ai_service, volunteer_user, association_user):
    """Test the batch moderation candidate selection and processing."""
    volunteer_user.volunteer_profile.bio = "Some spam content here"
    session.add(volunteer_user)
    session.commit()
    
    await ai_service.run_batch_moderation(session)
    
    # Check if a report was created for the volunteer user
    report = session.exec(select(AIReport).where(
        AIReport.target == ReportTarget.PROFILE,
        AIReport.target_id == volunteer_user.id_user
    )).first()
    
    assert report is not None
    assert report.classification == AIContentCategory.SPAM_LIKE