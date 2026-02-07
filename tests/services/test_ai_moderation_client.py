import pytest
import respx
import httpx
from app.services.ai_moderation_client import AIModerationClient
from app.models.enums import AIContentCategory

@pytest.mark.asyncio
@respx.mock
async def test_analyze_text_full_flow():
    """
    Test the AIModerationClient with mocked HTTP responses for both models.
    """
    client = AIModerationClient()
    # Force URLs for test if not set in environment
    client.spam_url = "https://mock-spam-api"
    client.toxicity_url = "https://mock-tox-api"
    
    text = "Test content"
    
    # Mock Spam API response (Flags as spam)
    respx.post(str(client.spam_url)).mock(return_value=httpx.Response(200, json=[{"label": "LABEL_1", "score": 0.99}]))
    
    # Mock Toxicity API response (Flags as toxic)
    respx.post(str(client.toxicity_url)).mock(return_value=httpx.Response(200, json=[{"label": "LABEL_1", "score": 0.8}]))
    
    category, score = await client.analyze_text(text)
    
    # Spam has priority according to our logic
    assert category == AIContentCategory.SPAM_LIKE
    assert score == 0.99

@pytest.mark.asyncio
@respx.mock
async def test_analyze_text_only_toxic():
    """Test when only the toxicity model flags the content."""
    client = AIModerationClient()
    client.spam_url = "https://mock-spam-api"
    client.toxicity_url = "https://mock-tox-api"
    
    respx.post(str(client.spam_url)).mock(return_value=httpx.Response(200, json=[{"label": "LABEL_0", "score": 0.99}]))
    respx.post(str(client.toxicity_url)).mock(return_value=httpx.Response(200, json=[{"label": "LABEL_1", "score": 0.85}]))
    
    category, score = await client.analyze_text("Some text")
    
    assert category == AIContentCategory.TOXIC_LANGUAGE
    assert score == 0.85

@pytest.mark.asyncio
@respx.mock
async def test_analyze_text_no_flags():
    """Test when no model flags the content."""
    client = AIModerationClient()
    client.spam_url = "https://mock-spam-api"
    client.toxicity_url = "https://mock-tox-api"
    
    respx.post(str(client.spam_url)).mock(return_value=httpx.Response(200, json=[{"label": "LABEL_0", "score": 0.99}]))
    respx.post(str(client.toxicity_url)).mock(return_value=httpx.Response(200, json=[{"label": "LABEL_0", "score": 0.99}]))
    
    result = await client.analyze_text("Clean text")
    assert result is None
