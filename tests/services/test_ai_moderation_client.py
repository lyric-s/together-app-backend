import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.ai_moderation_client import AIModerationClient
from app.models.enums import AIContentCategory

@pytest.fixture
def mock_settings():
    """Provides a mock Settings object for tests to avoid env dependency."""
    settings = MagicMock()
    settings.AI_SPAM_MODEL_URL = "https://mock-spam-api"
    settings.AI_TOXICITY_MODEL_URL = "https://mock-tox-api"
    # Mock the SecretStr behavior
    settings.AI_MODERATION_SERVICE_TOKEN.get_secret_value.return_value = "mock-token"
    settings.AI_MODERATION_TIMEOUT_SECONDS = 5
    return settings

@pytest.mark.asyncio
async def test_analyze_text_full_flow(mock_settings):
    """
    Test the AIModerationClient priority logic (Spam over Toxicity)
    with get_settings properly stubbed.
    """
    with patch('app.services.ai_moderation_client.get_settings', return_value=mock_settings):
        client = AIModerationClient()
        text = "Test content"
    
        # Mocking the internal _call_model method to isolate the client's logic
        with patch.object(client, '_call_model', new_callable=AsyncMock) as mock_call:
            # First call is spam, second is toxicity
            mock_call.side_effect = [
                {"label": "LABEL_1", "score": 0.99}, # Spam result
                {"label": "LABEL_1", "score": 0.8}   # Toxicity result
            ]
            
            result = await client.analyze_text(text)
            assert result is not None
            category, score = result
            
            # Verify that Spam has priority
            assert category == AIContentCategory.SPAM_LIKE
            assert score == 0.99
            # Verify both models were called
            assert mock_call.call_count == 2

@pytest.mark.asyncio
async def test_analyze_text_only_toxic(mock_settings):
    """Test when only the toxicity model flags the content."""
    with patch('app.services.ai_moderation_client.get_settings', return_value=mock_settings):
        client = AIModerationClient()
        
        with patch.object(client, '_call_model', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                {"label": "LABEL_0", "score": 0.99}, # Not Spam
                {"label": "LABEL_1", "score": 0.85}  # Toxic
            ]
            
            result = await client.analyze_text("Some text")
            assert result is not None
            category, score = result
            
            assert category == AIContentCategory.TOXIC_LANGUAGE
            assert score == 0.85

@pytest.mark.asyncio
async def test_analyze_text_no_flags(mock_settings):
    """Test when no model flags the content."""
    with patch('app.services.ai_moderation_client.get_settings', return_value=mock_settings):
        client = AIModerationClient()
        
        with patch.object(client, '_call_model', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                {"label": "LABEL_0", "score": 0.99},
                {"label": "LABEL_0", "score": 0.99}
            ]
            
            result = await client.analyze_text("Clean text")
            assert result is None