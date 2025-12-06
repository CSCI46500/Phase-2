"""
S3 helper module for package storage.
Implements S3 operations as per CRUD_IMPLEMENTATION_PLAN.md
"""
import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional, List
import os
import zipfile
import tempfile
import io
import fnmatch
from src.core.config import settings

logger = logging.getLogger(__name__)


class S3Helper:
    """Helper class for S3 operations."""

    def __init__(self):
        """Initialize S3 client with support for MinIO/LocalStack."""
        self.bucket_name = settings.s3_bucket_name
        self.region = settings.s3_region
        self.endpoint_url = settings.s3_endpoint_url

        # Build client configuration
        client_kwargs = {
            'service_name': 's3',
            'region_name': self.region,
        }

        # Add endpoint URL if specified (for MinIO, LocalStack, etc.)
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url
            logger.info(f"Using custom S3 endpoint: {self.endpoint_url}")

        # Add credentials if provided
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs['aws_access_key_id'] = settings.aws_access_key_id
            client_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key

        # Initialize boto3 client
        self.s3_client = boto3.client(**client_kwargs)

        logger.info(f"S3Helper initialized for bucket: {self.bucket_name} (environment: {settings.environment})")

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

    def download_file_to_string(self, s3_key: str) -> str:
        """
        Download file from S3 and return as string.
        Args:
            s3_key: S3 object key
        Returns:
            File contents as string
        Raises:
            ClientError: If download fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Downloaded text content from S3: s3://{self.bucket_name}/{s3_key}")
            return content
        except ClientError as e:
            logger.error(f"Failed to download text from S3: {e}")
            raise

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

    def delete_all_objects(self) -> int:
        """
        Delete all objects in the bucket with pagination.
        Used for system reset functionality.

        Returns:
            Number of objects deleted
        """
        deleted_count = 0

        try:
            # Use pagination to handle large number of objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)

            for page in pages:
                if 'Contents' not in page:
                    continue

                # Build list of objects to delete (max 1000 per batch)
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]

                if objects_to_delete:
                    # Delete batch of objects
                    response = self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )

                    # Count successful deletions
                    if 'Deleted' in response:
                        batch_count = len(response['Deleted'])
                        deleted_count += batch_count
                        logger.info(f"Deleted batch of {batch_count} objects from S3")

                    # Log any errors
                    if 'Errors' in response:
                        for error in response['Errors']:
                            logger.error(f"Error deleting {error['Key']}: {error['Message']}")

            logger.info(f"Total S3 objects deleted: {deleted_count}")
            return deleted_count

        except ClientError as e:
            logger.error(f"Failed to delete all objects: {e}")
            return deleted_count

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

    def _get_component_file_patterns(self, component: str) -> List[str]:
        """
        Get file patterns for each component type.
        Returns list of patterns to match files in the zip.
        """
        patterns = {
            "weights": [
                "*.pth", "*.pt", "*.bin", "*.safetensors", "*.ckpt",
                "*.h5", "*.pb", "*.onnx", "*.tflite",
                "pytorch_model.bin", "model.safetensors",
                "**/pytorch_model*.bin", "**/model*.safetensors"
            ],
            "datasets": [
                "*.csv", "*.json", "*.jsonl", "*.parquet", "*.arrow",
                "*.txt", "data/*", "dataset/*", "datasets/*",
                "**/data/**", "**/dataset/**", "**/datasets/**"
            ],
            "code": [
                "*.py", "*.ipynb", "*.sh", "*.yaml", "*.yml",
                "*.md", "README*", "requirements.txt", "setup.py",
                "*.cfg", "*.ini", "*.toml"
            ]
        }
        return patterns.get(component, [])

    def _matches_component_pattern(self, filename: str, component: str) -> bool:
        """Check if filename matches component patterns."""
        patterns = self._get_component_file_patterns(component)

        for pattern in patterns:
            if fnmatch.fnmatch(filename.lower(), pattern.lower()):
                return True
            # Also check just the basename
            if fnmatch.fnmatch(os.path.basename(filename).lower(), pattern.lower()):
                return True
        return False

    def generate_component_download_url(
        self,
        s3_key: str,
        component: str,
        package_name: str,
        version: str,
        expiration: int = 300
    ) -> Optional[str]:
        """
        Generate presigned URL for component-specific download.
        Downloads the full zip, extracts matching files, creates new zip, uploads temporarily.

        Args:
            s3_key: S3 object key for full package
            component: Component type ("weights", "datasets", "code")
            package_name: Package name for temp file naming
            version: Package version
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL or None if failed
        """
        try:
            # Download the full package to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_download:
                self.s3_client.download_fileobj(
                    self.bucket_name,
                    s3_key,
                    temp_download
                )
                temp_download_path = temp_download.name

            # Create filtered zip with only component files
            temp_component_path = tempfile.mktemp(suffix=f"_{component}.zip")

            with zipfile.ZipFile(temp_download_path, 'r') as source_zip:
                with zipfile.ZipFile(temp_component_path, 'w', zipfile.ZIP_DEFLATED) as target_zip:
                    # Filter and copy matching files
                    matched_files = []
                    for file_info in source_zip.filelist:
                        if self._matches_component_pattern(file_info.filename, component):
                            data = source_zip.read(file_info.filename)
                            target_zip.writestr(file_info, data)
                            matched_files.append(file_info.filename)

                    logger.info(f"Component '{component}': matched {len(matched_files)} files")

                    if not matched_files:
                        logger.warning(f"No files matched component '{component}'")
                        # Still create zip with a note
                        target_zip.writestr(
                            "README.txt",
                            f"No {component} files found in this package.\n"
                        )

            # Upload component zip to temporary S3 location
            component_s3_key = f"temp/{package_name}/{version}/{component}.zip"

            with open(temp_component_path, 'rb') as f:
                self.s3_client.upload_fileobj(f, self.bucket_name, component_s3_key)

            # Clean up temp files
            os.unlink(temp_download_path)
            os.unlink(temp_component_path)

            # Generate presigned URL for component zip
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': component_s3_key},
                ExpiresIn=expiration
            )

            logger.info(f"Generated component download URL for: {component_s3_key}")
            return url

        except Exception as e:
            logger.error(f"Failed to generate component download URL: {e}")
            return None


# Global S3 helper instance
s3_helper = S3Helper()