"""Performance benchmarks for storage service operations."""

import pytest
from pytest_codspeed import BenchmarkFixture
from unittest.mock import MagicMock

from app.services.storage import StorageService


@pytest.fixture(name="mock_storage_service")
def mock_storage_service_fixture():
    """Create a mock storage service for benchmarking."""
    service = StorageService()
    mock_client = MagicMock()
    mock_client.presigned_get_object.return_value = (
        "http://minio:9000/bucket/file.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&"
        "X-Amz-Credential=minioadmin/20260115/us-east-1/s3/aws4_request&"
        "X-Amz-Date=20260115T000000Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&"
        "X-Amz-Signature=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    service.client = mock_client
    service.bucket_name = "benchmark-bucket"
    return service


def test_presigned_url_download_performance(
    benchmark: BenchmarkFixture, mock_storage_service: StorageService
):
    """Benchmark presigned URL generation for download mode."""

    @benchmark
    def generate_download_url():
        return mock_storage_service.get_presigned_url(
            "user_123/document_456.pdf", inline=False
        )


def test_presigned_url_preview_performance(
    benchmark: BenchmarkFixture, mock_storage_service: StorageService
):
    """Benchmark presigned URL generation for preview mode."""

    @benchmark
    def generate_preview_url():
        return mock_storage_service.get_presigned_url(
            "user_123/document_456.pdf", inline=True
        )


def test_presigned_url_custom_expiry_performance(
    benchmark: BenchmarkFixture, mock_storage_service: StorageService
):
    """Benchmark presigned URL generation with custom expiry time."""

    @benchmark
    def generate_url_with_custom_expiry():
        return mock_storage_service.get_presigned_url(
            "user_123/document_456.pdf", expires_in_hours=24, inline=False
        )


def test_presigned_url_batch_generation_performance(
    benchmark: BenchmarkFixture, mock_storage_service: StorageService
):
    """Benchmark batch generation of presigned URLs (simulating multiple documents)."""
    object_names = [f"user_{i}/document_{i}.pdf" for i in range(10)]

    @benchmark
    def generate_batch_urls():
        urls = []
        for obj_name in object_names:
            url = mock_storage_service.get_presigned_url(obj_name, inline=False)
            urls.append(url)
        return urls


def test_presigned_url_mixed_modes_performance(
    benchmark: BenchmarkFixture, mock_storage_service: StorageService
):
    """Benchmark alternating between download and preview URL generation."""
    object_names = [f"user_{i}/document_{i}.pdf" for i in range(10)]

    @benchmark
    def generate_mixed_urls():
        urls = []
        for i, obj_name in enumerate(object_names):
            # Alternate between download (even) and preview (odd)
            inline = bool(i % 2)
            url = mock_storage_service.get_presigned_url(obj_name, inline=inline)
            urls.append(url)
        return urls


def test_presigned_url_error_handling_performance(
    benchmark: BenchmarkFixture, mock_storage_service: StorageService
):
    """Benchmark error handling for empty object names."""

    @benchmark
    def handle_empty_object_name():
        # This should return None without calling MinIO
        return mock_storage_service.get_presigned_url("", inline=False)
