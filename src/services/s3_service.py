"""
S3 helper module for package storage.
Implements S3 operations as per CRUD_IMPLEMENTATION_PLAN.md
"""
import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional
import os
from src.core.config import settings

logger = logging.getLogger(__name__)


class S3Helper:
    """Helper class for S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.bucket_name = settings.s3_bucket_name
        self.region = settings.s3_region

        # Initialize boto3 client
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        else:
            # Use default credentials (IAM role, env vars, etc.)
            self.s3_client = boto3.client('s3', region_name=self.region)

        logger.info(f"S3Helper initialized for bucket: {self.bucket_name}")

    def upload_file(self, file_path: str, s3_key: str) -> bool:
        """
        Upload file to S3.
        Args:
            file_path: Local file path
            s3_key: S3 object key (path in bucket)
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            logger.info(f"Uploaded file to S3: s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False

    def upload_fileobj(self, file_obj, s3_key: str) -> bool:
        """
        Upload file object to S3.
        Args:
            file_obj: File-like object
            s3_key: S3 object key
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.upload_fileobj(file_obj, self.bucket_name, s3_key)
            logger.info(f"Uploaded file object to S3: s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file object to S3: {e}")
            return False

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download file from S3.
        Args:
            s3_key: S3 object key
            local_path: Local destination path
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded from S3: s3://{self.bucket_name}/{s3_key} -> {local_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return False

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 300
    ) -> Optional[str]:
        """
        Generate presigned URL for downloading.
        As per plan: Expires in 5 minutes (300 seconds).
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for: s3://{self.bucket_name}/{s3_key}")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3.
        Args:
            s3_key: S3 object key
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted from S3: s3://{self.bucket_name}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3.
        Args:
            s3_key: S3 object key
        Returns:
            True if exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_file_size(self, s3_key: str) -> Optional[int]:
        """
        Get file size in bytes.
        Args:
            s3_key: S3 object key
        Returns:
            File size in bytes or None if not found
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return int(response['ContentLength'])
        except ClientError as e:
            logger.error(f"Failed to get file size: {e}")
            return None

    def build_s3_path(self, package_name: str, version: str, filename: str = "package.zip") -> str:
        """
        Build S3 path following the structure from CRUD plan.
        Structure: /{package_name}/{version}/{filename}
        Args:
            package_name: Package name
            version: Package version
            filename: File name (default: package.zip)
        Returns:
            S3 path string
        """
        return f"{package_name}/{version}/{filename}"

    def build_full_s3_url(self, s3_key: str) -> str:
        """
        Build full S3 URL.
        Args:
            s3_key: S3 object key
        Returns:
            Full S3 URL (s3://bucket/key)
        """
        return f"s3://{self.bucket_name}/{s3_key}"


# Global S3 helper instance
s3_helper = S3Helper()