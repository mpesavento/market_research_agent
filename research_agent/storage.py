from abc import ABC, abstractmethod
import os
from typing import Optional, Union
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    @abstractmethod
    def save_file(self, content: str, filename: str) -> str:
        """
        Save content and return access path/URL

        Args:
            content: Content to save
            filename: Name of file to save

        Returns:
            str: Path or URL to saved file
        """
        pass

    @abstractmethod
    def get_file_url(self, filename: str, expires_in: int = 3600) -> str:
        """
        Get a URL or path for file access

        Args:
            filename: Name of file to access
            expires_in: Seconds until URL expires (for S3)

        Returns:
            str: URL or path to access file
        """
        pass

    @abstractmethod
    def file_exists(self, filename: str) -> bool:
        """Check if file exists in storage"""
        pass

class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation"""
    def __init__(self, base_dir: str = "reports"):
        # Get the repository root directory (where research_agent package is)
        repo_root = Path(__file__).parent.parent

        # Create absolute path for reports directory
        self.base_dir = repo_root / base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: str, filename: str) -> str:
        """Save file to local filesystem"""
        filepath = self.base_dir / filename
        filepath.write_text(content, encoding='utf-8')
        return str(filepath)

    def get_file_url(self, filename: str, expires_in: int = 3600) -> str:
        """Get local filesystem path"""
        return str(self.base_dir / filename)

    def file_exists(self, filename: str) -> bool:
        """Check if file exists locally"""
        return (self.base_dir / filename).exists()

    def get_file_content(self, filename: str) -> Optional[str]:
        """Read file content from local storage"""
        filepath = self.base_dir / filename
        if filepath.exists():
            return filepath.read_text(encoding='utf-8')
        return None

class S3StorageBackend(StorageBackend):
    """AWS S3 storage implementation"""
    def __init__(
        self,
        bucket_name: str,
        prefix: str = "reports/",
        region: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize S3 storage backend

        Args:
            bucket_name: Name of S3 bucket
            prefix: Prefix for all stored files (default: "reports/")
            region: AWS region (optional)
            **kwargs: Additional arguments passed to boto3.client
        """
        self.bucket = bucket_name
        self.prefix = prefix.rstrip('/') + '/'

        # Initialize S3 client
        self.s3 = boto3.client(
            's3',
            region_name=region or os.getenv('AWS_DEFAULT_REGION'),
            **kwargs
        )

    def save_file(self, content: str, filename: str) -> str:
        """Save file to S3"""
        key = f"{self.prefix}{filename}"
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/plain'
            )
            return self.get_file_url(filename)
        except ClientError as e:
            logger.error(f"Error saving to S3: {e}")
            raise

    def get_file_url(self, filename: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for S3 file access"""
        key = f"{self.prefix}{filename}"
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    def file_exists(self, filename: str) -> bool:
        """Check if file exists in S3"""
        key = f"{self.prefix}{filename}"
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking S3 file existence: {e}")
            raise

    def get_file_content(self, filename: str) -> Optional[str]:
        """Read file content from S3"""
        key = f"{self.prefix}{filename}"
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return response['Body'].read().decode('utf-8')
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logger.error(f"Error reading from S3: {e}")
            raise

def create_storage_backend(
    storage_type: str = "local",
    **kwargs
) -> StorageBackend:
    """
    Factory function to create storage backend

    Args:
        storage_type: Type of storage ("local" or "s3")
        **kwargs: Arguments passed to storage backend constructor

    Returns:
        StorageBackend: Configured storage backend

    Examples:
        # Local storage
        storage = create_storage_backend("local", base_dir="reports")

        # S3 storage
        storage = create_storage_backend(
            "s3",
            bucket_name="my-bucket",
            prefix="reports/",
            region="us-west-2"
        )
    """
    if storage_type == "local":
        return LocalStorageBackend(**kwargs)
    elif storage_type == "s3":
        return S3StorageBackend(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
