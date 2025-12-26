import logging
from datetime import timedelta
from typing import Optional, BinaryIO

from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.ENVIRONMENT != "development",
        )
        self.bucket_name = settings.AVATARS_BUCKET

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
        self, file_data: BinaryIO, file_name: str, content_type: str, size: int = -1
    ) -> str:
        """
        Uploads a file and returns the Object Name (Key) to store in the DB.
        """
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_name,
                data=file_data,
                length=size,
                content_type=content_type,
                # Part size 10MB ensures better performance for larger files
                part_size=10 * 1024 * 1024,
            )
            logger.info(f"File '{file_name}' uploaded successfully.")
            return file_name
        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise

    def get_presigned_url(
        self, object_name: str, expires_in_hours: int = 1
    ) -> Optional[str]:
        """
        Generates a secure temporary link for the frontend to display the image.
        """
        if not object_name:
            return None
        try:
            url = self.client.get_presigned_url(
                "GET",
                self.bucket_name,
                object_name,
                expires=timedelta(hours=expires_in_hours),
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def delete_file(self, object_name: str):
        """
        Deletes a file. Useful when a user updates their avatar (cleanup old one).
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File '{object_name}' deleted.")
        except S3Error as e:
            logger.error(f"Failed to delete file: {e}")


# Singleton instance to be imported elsewhere
storage_service = StorageService()
