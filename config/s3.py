import logging
import mimetypes
from typing import TypedDict
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class UploadResult(TypedDict):
    url: str
    key: str
    content_type: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_TYPES: set[str] = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_DOCUMENT_TYPES: set[str] = ALLOWED_IMAGE_TYPES | {'application/pdf'}

MAX_FILE_SIZE: int = 25 * 1024 * 1024      # 25 MB
MIN_FILE_SIZE: int = 5 * 1024 * 1024       # 5 MB

EXTENSION_MAP: dict[str, str] = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'application/pdf': '.pdf',
}


# ---------------------------------------------------------------------------
# S3 Service
# ---------------------------------------------------------------------------

class S3Service:
    """Singleton-style S3 client wrapper. Reuse ``s3_service`` module instance."""

    def __init__(self) -> None:
        self._client: boto3.client | None = None

    @property
    def client(self) -> boto3.client:
        if self._client is None:
            self._client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._client

    @property
    def bucket(self) -> str:
        return settings.AWS_S3_BUCKET_NAME

    @property
    def url_prefix(self) -> str:
        """Base URL prefix for all S3 objects in this bucket."""
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/"

    def get_key_from_url(self, url: str) -> str | None:
        """Extract the S3 object key from a full URL. Returns None if URL doesn't match."""
        if url.startswith(self.url_prefix):
            return url[len(self.url_prefix):]
        return None

    def delete_file_by_url(self, url: str) -> bool:
        """Delete an S3 object by its full URL. Returns True on success."""
        key = self.get_key_from_url(url)
        if key:
            return self.delete_file(key)
        return False

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def upload_file(
        self,
        file: UploadedFile,
        folder: str,
        allowed_types: set[str],
        max_size: int = MAX_FILE_SIZE,
        min_size: int = MIN_FILE_SIZE,
    ) -> UploadResult:
        """
        Upload a file to S3 after validating type and size.

        Raises ``ValueError`` for validation failures and
        ``ClientError`` for S3 transport errors.
        """
        content_type = file.content_type or ''
        if content_type not in allowed_types:
            allowed = ', '.join(sorted(allowed_types))
            raise ValueError(f'File type "{content_type}" not allowed. Accepted: {allowed}')

        if file.size and file.size < min_size:
            min_mb = min_size / (1024 * 1024)
            raise ValueError(f'File size must be at least {min_mb:.0f} MB.')

        if file.size and file.size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(f'File size exceeds {max_mb:.0f} MB limit.')

        ext = EXTENSION_MAP.get(content_type, mimetypes.guess_extension(content_type) or '')
        key = f"{folder}/{uuid4().hex}{ext}"

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=file.read(),
            ContentType=content_type,
        )

        url = f"{self.url_prefix}{key}"
        logger.info("Uploaded %s (%s, %s bytes)", key, content_type, file.size)

        return UploadResult(url=url, key=key, content_type=content_type)

    def delete_file(self, key: str) -> bool:
        """Delete a single object from S3. Returns True on success."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("Deleted S3 object: %s", key)
            return True
        except ClientError:
            logger.exception("Failed to delete S3 object: %s", key)
            return False

    # ------------------------------------------------------------------
    # Convenience methods (delegate to upload_file with preset constraints)
    # ------------------------------------------------------------------

    def upload_image(self, file: UploadedFile, folder: str) -> UploadResult:
        """Upload an image (JPEG, PNG, WebP). 5–25 MB."""
        return self.upload_file(file, folder, ALLOWED_IMAGE_TYPES)

    def upload_document(self, file: UploadedFile, folder: str) -> UploadResult:
        """Upload a document (image or PDF). 5–25 MB."""
        return self.upload_file(file, folder, ALLOWED_DOCUMENT_TYPES)


# Module-level singleton — import this everywhere
s3_service = S3Service()
