import pytest
from typing import Any, cast
from unittest.mock import patch, AsyncMock
from app.services.ai_moderation_client import AIModerationClient
from app.models.enums import AIContentCategory


@pytest.mark.asyncio
async def test_analyze_text_full_flow():
    """
    Test the AIModerationClient priority logic (Spam over Toxicity).
    """
    client = AIModerationClient()
    # Force URLs for test if not set in environment
    client.spam_url = cast(Any, "https://mock-spam-api")
    client.toxicity_url = cast(Any, "https://mock-tox-api")

    text = "Test content"

    # Mocking internal _call_model to avoid respx dependency
    with patch.object(client, "_call_model", new_callable=AsyncMock) as mock_call:
        # First call returns Spam result, Second call returns Toxicity result
        mock_call.side_effect = [
            {"label": "LABEL_1", "score": 0.99},  # Spam
            {"label": "LABEL_1", "score": 0.8},  # Toxicity
        ]

        result = await client.analyze_text(text)
        assert result is not None
        category, score = result

        # Spam has priority according to our logic
        assert category == AIContentCategory.SPAM_LIKE
        assert score == 0.99


@pytest.mark.asyncio
async def test_analyze_text_only_toxic():
    """Test when only the toxicity model flags the content."""
    client = AIModerationClient()
    client.spam_url = cast(Any, "https://mock-spam-api")
    client.toxicity_url = cast(Any, "https://mock-tox-api")

    with patch.object(client, "_call_model", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [
            {"label": "LABEL_0", "score": 0.99},  # Not Spam
            {"label": "LABEL_1", "score": 0.85},  # Toxic
        ]

        result = await client.analyze_text("Some text")
        assert result is not None
        category, score = result

        assert category == AIContentCategory.TOXIC_LANGUAGE
        assert score == 0.85


@pytest.mark.asyncio
async def test_analyze_text_no_flags():
    """Test when no model flags the content."""
    client = AIModerationClient()
    client.spam_url = cast(Any, "https://mock-spam-api")
    client.toxicity_url = cast(Any, "https://mock-tox-api")

    with patch.object(client, "_call_model", new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [
            {"label": "LABEL_0", "score": 0.99},
            {"label": "LABEL_0", "score": 0.99},
        ]

        result = await client.analyze_text("Clean text")
        assert result is None
