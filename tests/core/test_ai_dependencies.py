from app.core.dependencies import get_ai_moderation_service
from app.services.ai_moderation_service import AIModerationService
from app.services.ai_moderation_client import AIModerationClient


def test_get_ai_moderation_service():
    """
    Test that the AI moderation service dependency is correctly initialized.

    Verifies that:
    - The returned object is an instance of AIModerationService.
    - It contains an initialized AIModerationClient.
    """
    service = get_ai_moderation_service()

    assert isinstance(service, AIModerationService)
    assert isinstance(service.ai_client, AIModerationClient)
    assert service.settings is not None
