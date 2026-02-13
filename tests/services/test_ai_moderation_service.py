import pytest
from unittest.mock import MagicMock
from sqlmodel import Session, select
from typing import Any

from app.services.ai_moderation_service import AIModerationService
from app.models.enums import AIContentCategory, ReportTarget, ProcessingStatus
from app.models.ai_report import AIReport
from app.models.report import Report
from app.services.ai_moderation_client import AIModerationClient


class MockAIModerationClient(AIModerationClient):
    """
    Mock client that simulates the behavior of the local AI models
    by overriding the analyze_text method.
    """

    def __init__(self):
        # We don't need to call the parent __init__
        pass

    @property
    def models_loaded(self) -> bool:
        return True

    def analyze_text(self, text: str):
        """
        Returns a deterministic result based on the text content,
        simulating the local inference logic.
        """
        if "spam" in text.lower():
            return AIContentCategory.SPAM_LIKE, 0.99
        if "toxic" in text.lower():
            return AIContentCategory.TOXIC_LANGUAGE, None
        return None


@pytest.fixture
def mock_ai_client():
    return MockAIModerationClient()


@pytest.fixture
def ai_service(mock_ai_client: MockAIModerationClient):
    """
    Provides a synchronous AIModerationService instance with a mocked client.
    """
    # Mock settings to avoid dependency on environment
    mock_settings = MagicMock()
    mock_settings.AI_MODERATION_DAILY_QUOTA = 100
    mock_settings.AI_MODEL_VERSION = "test-local-v1.0"
    
    # We don't need to patch get_settings if the service already uses it
    # and the test is isolated. The main thing is the mock client.
    service = AIModerationService(mock_ai_client)
    service.settings = mock_settings # Manually inject mock settings
    return service


@pytest.mark.asyncio
async def test_moderate_content_spam(session: Session, ai_service: AIModerationService):
    """Test that spam content creates an AIReport with SPAM_LIKE label."""
    text = "This is a spam message."
    target_id = 1
    reported_user_id = 100

    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, reported_user_id, text)

    report = session.exec(
        select(AIReport).where(AIReport.target_id == target_id)
    ).first()
    assert report is not None
    assert report.classification == AIContentCategory.SPAM_LIKE
    assert report.confidence_score == 0.99
    assert report.id_user_reported == reported_user_id


@pytest.mark.asyncio
async def test_moderate_content_toxic(session: Session, ai_service: AIModerationService):
    """Test that toxic content creates an AIReport with TOXIC_LANGUAGE label."""
    text = "This is a very toxic message."
    target_id = 2
    reported_user_id = 101

    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, reported_user_id, text)

    report = session.exec(
        select(AIReport).where(AIReport.target_id == target_id)
    ).first()
    assert report is not None
    assert report.classification == AIContentCategory.TOXIC_LANGUAGE
    assert report.confidence_score is None
    assert report.id_user_reported == reported_user_id


@pytest.mark.asyncio
async def test_skip_if_human_report_exists(session: Session, ai_service: AIModerationService):
    """Test that AI scan is skipped if a human report already exists."""
    target_id = 3
    reported_user_id = 102
    from app.models.enums import ReportType
    human_report = Report(
        type=ReportType.OTHER,
        target=ReportTarget.PROFILE,
        reason="A human saw this first.",
        id_user_reported=reported_user_id,
        id_user_reporter=999,
    )
    session.add(human_report)
    session.commit()

    await ai_service.moderate_content(session, ReportTarget.PROFILE, target_id, reported_user_id, "spam text")

    ai_report = session.exec(
        select(AIReport).where(AIReport.target_id == target_id)
    ).first()
    assert ai_report is None


@pytest.mark.asyncio
async def test_batch_moderation_logic(session: Session, ai_service: AIModerationService, volunteer_user):
    """Test the synchronous batch moderation candidate selection."""
    # Setup: Give the user a bio that will be flagged
    volunteer_user.volunteer_profile.bio = "Some toxic content here"
    session.add(volunteer_user)
    session.commit()

    # Run the synchronous batch moderation
    await ai_service.run_batch_moderation(session)

    # Check that a report was created for the user
    report = session.exec(
        select(AIReport).where(
            AIReport.target == ReportTarget.PROFILE,
            AIReport.target_id == volunteer_user.id_user,
        )
    ).first()
    assert report is not None
    assert report.classification == AIContentCategory.TOXIC_LANGUAGE
    assert report.id_user_reported == volunteer_user.id_user