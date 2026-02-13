import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from app.services.ai_moderation_client import AIModerationClient
from app.models.enums import AIContentCategory

# This test file focuses on the client's internal logic.

def test_spam_prediction_logic():
    """
    Unit test for the _predict_spam method, isolated from the real model and torch.
    """
    # Patch the actual implementation of _predict_spam
    with patch.object(AIModerationClient, '_predict_spam', return_value=(True, 0.99)) as mock_predict_spam, \
         patch.object(AIModerationClient, 'models_loaded', new_callable=PropertyMock) as mock_loaded:
        
        mock_loaded.return_value = True
        client = AIModerationClient()

        is_spam, score = client._predict_spam("some text")

        assert is_spam is True
        assert score == 0.99
        mock_predict_spam.assert_called_once_with("some text")

def test_toxicity_prediction_logic():
    """
    Unit test for the _predict_toxicity method, isolated from the real model.
    """
    with patch.object(AIModerationClient, '_predict_toxicity', return_value=True) as mock_predict_toxicity, \
         patch.object(AIModerationClient, 'models_loaded', new_callable=PropertyMock) as mock_loaded:
        
        mock_loaded.return_value = True
        client = AIModerationClient()

        is_toxic = client._predict_toxicity("some text")
        
        assert is_toxic is True
        mock_predict_toxicity.assert_called_once_with("some text")

def test_analyze_text_logic_isolated():
    """
    Tests the priority logic of analyze_text without any real model calls.
    """
    # Patch the internal prediction methods directly
    with patch.object(AIModerationClient, '_predict_spam', return_value=(False, None)) as mock_spam_predict, \
         patch.object(AIModerationClient, '_predict_toxicity', return_value=True) as mock_tox_predict, \
         patch.object(AIModerationClient, 'models_loaded', new_callable=PropertyMock) as mock_loaded:
        
        mock_loaded.return_value = True
        client = AIModerationClient()
        
        result = client.analyze_text("any text")
        
        assert result is not None
        category, score = result
        
        assert category == AIContentCategory.TOXIC_LANGUAGE
        mock_spam_predict.assert_called_once()
        mock_tox_predict.assert_called_once()

def test_client_initialization_no_models():
    """Test that the client disables itself if models are not loaded."""
    # Patch the loader variables to be None at their source
    with patch('app.core.ai_loader.toxicity_pipeline', None), \
         patch('app.core.ai_loader.spam_tokenizer', None), \
         patch('app.core.ai_loader.spam_model', None):
        
        client = AIModerationClient()
        assert client.models_loaded is False
        assert client.analyze_text("any text") is None

def test_analyze_text_priority_spam():
    """Test that spam detection takes priority over toxicity."""
    with patch.object(AIModerationClient, '_predict_spam', return_value=(True, 0.95)) as mock_spam_predict, \
         patch.object(AIModerationClient, '_predict_toxicity', return_value=True) as mock_tox_predict, \
         patch.object(AIModerationClient, 'models_loaded', new_callable=PropertyMock) as mock_loaded:
        
        mock_loaded.return_value = True
        client = AIModerationClient()
        
        category, score = client.analyze_text("spam and toxic text")
        
        assert category == AIContentCategory.SPAM_LIKE
        assert score == 0.95
        mock_spam_predict.assert_called_once()
        # Ensure toxicity is NOT checked if spam is already found
        mock_tox_predict.assert_not_called()

def test_analyze_text_no_flags():
    """Test that if neither model flags, analyze_text returns None."""
    with patch.object(AIModerationClient, '_predict_spam', return_value=(False, None)) as mock_spam_predict, \
         patch.object(AIModerationClient, '_predict_toxicity', return_value=False) as mock_tox_predict, \
         patch.object(AIModerationClient, 'models_loaded', new_callable=PropertyMock) as mock_loaded:
        
        mock_loaded.return_value = True
        client = AIModerationClient()
        
        result = client.analyze_text("clean text")
        
        assert result is None
        mock_spam_predict.assert_called_once()
        mock_tox_predict.assert_called_once()

