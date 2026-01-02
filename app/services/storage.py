import logging
from datetime import timedelta
from typing import Optional, BinaryIO
import os
import uuid
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.client = Minio(
            str(settings.MINIO_ENDPOINT),
            access_key=str(settings.MINIO_ACCESS_KEY.get_secret_value()),
            secret_key=str(settings.MINIO_SECRET_KEY.get_secret_value()),
            secure=settings.MINIO_SECURE,
        )
        self.bucket_name = settings.DOCUMENTS_BUCKET

    def ensure_bucket_exists(self):
        """
        Checks if the bucket exists; creates it if not.
        Run this on app startup.
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created successfully.")
            else:
                logger.debug(f"Bucket '{self.bucket_name}' already exists.")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        file_name: str,
        content_type: str,
        size: int = -1,
        overwrite: bool = False,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Uploads a file and returns the Object Name (Key) to store in the DB.

        Args:
            file_data: Binary file data to upload
            file_name: Original filename
            content_type: MIME type of the file
            size: File size in bytes (-1 for unknown)
            overwrite: If False (default), generates unique name to prevent overwrites.
                      If True, uses sanitized filename directly (may overwrite).
            user_id: Optional user ID for organizing files in user-specific paths

        Returns:
            The object name (key) stored in MinIO

        Note:
            For atomic overwrite prevention at the server level, MinIO supports
            conditional writes via If-None-Match headers, but requires using
            presigned URLs + requests library. The UUID approach here is simpler
            and provides collision-safe storage without extra dependencies.
        """
        if not file_data:
            raise ValueError("file_data cannot be None")
        if not file_name or not file_name.strip():
            raise ValueError("file_name cannot be empty")
        # Enforce maximum file size
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if size > max_size_bytes:
            raise ValueError(
                f"File size {size} bytes exceeds maximum allowed size of {max_size_bytes} bytes"
            )
        # Sanitize file_name to prevent path traversal
        sanitized_name = os.path.basename(file_name)
        if (
            not sanitized_name
            or sanitized_name != file_name
            or sanitized_name in (".", "..")
            or any(c in sanitized_name for c in ("\0", "\n", "\r"))
        ):
            raise ValueError(f"Invalid file_name: {file_name}")

        # Validate user_id if provided
        if user_id is not None:
            user_id = user_id.strip()
            if (
                not user_id
                or "/" in user_id
                or "\\" in user_id
                or user_id in (".", "..")
                or ".." in user_id
            ):
                raise ValueError(f"Invalid user_id: {user_id}")

        # Generate final object name
        if overwrite:
            # Use sanitized name directly (may overwrite existing file)
            object_name = sanitized_name
            if user_id:
                object_name = f"{user_id}/{object_name}"
        else:
            # Generate unique name to prevent collisions
            unique_id = str(uuid.uuid4())
            if user_id:
                # User-scoped path: user_id/uuid_filename
                object_name = f"{user_id}/{unique_id}_{sanitized_name}"
            else:
                # Global unique name: uuid_filename
                object_name = f"{unique_id}_{sanitized_name}"

        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=size,
                content_type=content_type,
                # Part size 10MB ensures better performance for larger files
                part_size=10 * 1024 * 1024,
            )
            logger.info(f"File uploaded successfully as '{object_name}'")
            return object_name
        except S3Error as e:
            logger.error(f"Failed to upload file '{object_name}' to MinIO: {e}")
            raise

    def get_presigned_url(
        self, object_name: str, expires_in_hours: int = 1
    ) -> Optional[str]:
        """
        Generates a presigned GET URL for temporary access to a file.
        """
        if not object_name or not object_name.strip():
            logger.warning("object_name is empty; cannot generate presigned URL.")
            return None

        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=expires_in_hours),
            )
            logger.debug(f"Generated presigned URL for '{object_name}'")
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for '{object_name}': {e}")
            return None

    def delete_file(self, object_name: str) -> None:
        """
        Deletes a file from the bucket.
        """
        if not object_name or not object_name.strip():
            raise ValueError("object_name cannot be empty")

        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            logger.info(f"File '{object_name}' deleted successfully.")
        except S3Error as e:
            logger.error(f"Failed to delete file '{object_name}' from MinIO: {e}")
            raise


storage_service = StorageService()
