"""Tests for storage service presigned URL generation."""

from unittest.mock import MagicMock
from datetime import timedelta

from app.services.storage import StorageService
from minio.error import S3Error


class TestGetPresignedUrl:
    """Test cases for storage_service.get_presigned_url()."""

    def test_get_presigned_url_download_mode(self):
        """Test presigned URL generation in download mode (inline=False)."""
        mock_client = MagicMock()
        mock_client.presigned_get_object.return_value = (
            "http://minio:9000/bucket/file.pdf?signature=abc123"
        )

        service = StorageService()
        service.client = mock_client
        service.bucket_name = "test-bucket"

        # Test download mode (inline=False, default)
        url = service.get_presigned_url("user_5/document.pdf", inline=False)

        assert url is not None
        assert "http://minio:9000/bucket/file.pdf" in url
        mock_client.presigned_get_object.assert_called_once_with(
            bucket_name="test-bucket",
            object_name="user_5/document.pdf",
            expires=timedelta(hours=1),
            response_headers=None,
        )

    def test_get_presigned_url_preview_mode(self):
        """Test presigned URL generation in preview mode (inline=True)."""
        mock_client = MagicMock()
        mock_client.presigned_get_object.return_value = "http://minio:9000/bucket/file.pdf?response-content-disposition=inline&sig=xyz"

        service = StorageService()
        service.client = mock_client
        service.bucket_name = "test-bucket"

        # Test preview mode (inline=True)
        url = service.get_presigned_url("user_5/document.pdf", inline=True)

        assert url is not None
        assert "http://minio:9000/bucket/file.pdf" in url
        mock_client.presigned_get_object.assert_called_once_with(
            bucket_name="test-bucket",
            object_name="user_5/document.pdf",
            expires=timedelta(hours=1),
            response_headers={"response-content-disposition": "inline"},
        )

    def test_get_presigned_url_custom_expiry(self):
        """Test presigned URL generation with custom expiration time."""
        mock_client = MagicMock()
        mock_client.presigned_get_object.return_value = (
            "http://minio:9000/bucket/file.pdf?signature=custom"
        )

        service = StorageService()
        service.client = mock_client
        service.bucket_name = "test-bucket"

        # Test custom expiry (2 hours)
        url = service.get_presigned_url(
            "user_5/document.pdf", expires_in_hours=2, inline=False
        )

        assert url is not None
        mock_client.presigned_get_object.assert_called_once_with(
            bucket_name="test-bucket",
            object_name="user_5/document.pdf",
            expires=timedelta(hours=2),
            response_headers=None,
        )

    def test_get_presigned_url_empty_object_name(self):
        """Test presigned URL generation returns None for empty object name."""
        service = StorageService()

        # Test empty string
        url = service.get_presigned_url("", inline=False)
        assert url is None

        # Test whitespace-only string
        url = service.get_presigned_url("   ", inline=False)
        assert url is None

        # Test None (would fail type check but test defensive programming)
        url = service.get_presigned_url(None, inline=False)  # type: ignore
        assert url is None

    def test_get_presigned_url_s3_error(self):
        """Test presigned URL generation returns None on S3Error."""
        mock_client = MagicMock()
        # Create a mock response object
        mock_response = MagicMock()
        mock_response.status = 404
        mock_client.presigned_get_object.side_effect = S3Error(
            code="NoSuchKey",
            message="The specified key does not exist.",
            resource="/bucket/missing.pdf",
            request_id="abc123",
            host_id="host123",
            response=mock_response,  # type: ignore
        )

        service = StorageService()
        service.client = mock_client
        service.bucket_name = "test-bucket"

        # Test S3Error handling
        url = service.get_presigned_url("missing/file.pdf", inline=False)

        assert url is None
        mock_client.presigned_get_object.assert_called_once()

    def test_get_presigned_url_both_modes_different_headers(self):
        """Test that download and preview modes use different response headers."""
        mock_client = MagicMock()
        mock_client.presigned_get_object.return_value = (
            "http://minio:9000/bucket/file.pdf"
        )

        service = StorageService()
        service.client = mock_client
        service.bucket_name = "test-bucket"

        # Download mode (inline=False)
        service.get_presigned_url("document.pdf", inline=False)
        download_call = mock_client.presigned_get_object.call_args

        # Preview mode (inline=True)
        mock_client.reset_mock()
        service.get_presigned_url("document.pdf", inline=True)
        preview_call = mock_client.presigned_get_object.call_args

        # Verify different headers
        assert download_call.kwargs["response_headers"] is None
        assert preview_call.kwargs["response_headers"] == {
            "response-content-disposition": "inline"
        }
