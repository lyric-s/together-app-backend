from unittest.mock import patch, MagicMock, PropertyMock
import torch
from app.services.ai_moderation_client import AIModerationClient
from app.models.enums import AIContentCategory

# This test file focuses on the client's internal logic.


def test_spam_prediction_logic():
    """
    Unit test for the _predict_spam method using mocked models.
    """
    mock_tokenizer = MagicMock()
    mock_model = MagicMock()

    # Mocking torch.softmax and torch.argmax is complex, easier to mock model output
    mock_output = MagicMock()
    # pred == 1 means spam. probs[0][1] is the score.
    mock_output.logits = torch.tensor([[0.1, 0.9]])
    mock_model.return_value = mock_output

    with (
        patch("app.core.ai_loader.spam_tokenizer", mock_tokenizer),
        patch("app.core.ai_loader.spam_model", mock_model),
        patch("app.core.ai_loader.toxicity_pipeline", MagicMock()),
    ):
        client = AIModerationClient()
        assert client.models_loaded is True

        is_spam, score = client._predict_spam("some spam text")

        assert is_spam is True
        assert score is not None
        assert score > 0.5
        mock_tokenizer.assert_called_once()
        mock_model.assert_called_once()


def test_toxicity_prediction_logic():
    """
    Unit test for the _predict_toxicity method using mocked pipeline.
    """
    mock_pipeline = MagicMock(return_value=[{"label": "toxic", "score": 0.99}])

    with (
        patch("app.core.ai_loader.toxicity_pipeline", mock_pipeline),
        patch("app.core.ai_loader.spam_tokenizer", MagicMock()),
        patch("app.core.ai_loader.spam_model", MagicMock()),
    ):
        client = AIModerationClient()
        assert client.models_loaded is True

        is_toxic = client._predict_toxicity("some toxic text")

        assert is_toxic is True
        mock_pipeline.assert_called_once_with("some toxic text")


def test_analyze_text_logic_isolated():
    """
    Tests the priority logic of analyze_text by mocking prediction results.
    """
    # We still use patch.object here because we want to test the orchestration logic
    # of analyze_text (Spam priority over Toxicity)
    with (
        patch.object(
            AIModerationClient, "_predict_spam", return_value=(False, None)
        ) as mock_spam_predict,
        patch.object(
            AIModerationClient, "_predict_toxicity", return_value=True
        ) as mock_tox_predict,
        patch.object(
            AIModerationClient, "models_loaded", new_callable=PropertyMock
        ) as mock_loaded,
    ):
        mock_loaded.return_value = True
        client = AIModerationClient()

        result = client.analyze_text("any text")

        assert result is not None
        category, _ = result

        assert category == AIContentCategory.TOXIC_LANGUAGE
        mock_spam_predict.assert_called_once()
        mock_tox_predict.assert_called_once()


def test_client_initialization_no_models():
    """Test that the client disables itself if models are not loaded."""
    with (
        patch("app.core.ai_loader.toxicity_pipeline", None),
        patch("app.core.ai_loader.spam_tokenizer", None),
        patch("app.core.ai_loader.spam_model", None),
    ):
        client = AIModerationClient()
        assert client.models_loaded is False
        assert client.analyze_text("any text") is None


def test_analyze_text_priority_spam():
    """Test that spam detection takes priority over toxicity."""
    with (
        patch.object(
            AIModerationClient, "_predict_spam", return_value=(True, 0.95)
        ) as mock_spam_predict,
        patch.object(
            AIModerationClient, "_predict_toxicity", return_value=True
        ) as mock_tox_predict,
        patch.object(
            AIModerationClient, "models_loaded", new_callable=PropertyMock
        ) as mock_loaded,
    ):
        mock_loaded.return_value = True
        client = AIModerationClient()

        result = client.analyze_text("spam and toxic text")

        assert result is not None
        category, score = result
        assert category == AIContentCategory.SPAM_LIKE
        assert score == 0.95
        mock_spam_predict.assert_called_once()
        mock_tox_predict.assert_not_called()


def test_analyze_text_no_flags():
    """Test that if neither model flags, analyze_text returns None."""
    with (
        patch.object(
            AIModerationClient, "_predict_spam", return_value=(False, None)
        ) as mock_spam_predict,
        patch.object(
            AIModerationClient, "_predict_toxicity", return_value=False
        ) as mock_tox_predict,
        patch.object(
            AIModerationClient, "models_loaded", new_callable=PropertyMock
        ) as mock_loaded,
    ):
        mock_loaded.return_value = True
        client = AIModerationClient()

        result = client.analyze_text("clean text")

        assert result is None
        mock_spam_predict.assert_called_once()
        mock_tox_predict.assert_called_once()
