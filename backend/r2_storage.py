"""Module for managing Cloudflare R2 zero-egress object storage operations."""

import asyncio
import logging
import os
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception

logging.basicConfig(level=logging.INFO, format="%(asctime)s [R2 Storage] %(message)s")


class R2StorageManager:
    """Manager for S3-compatible uploads to Cloudflare R2."""

    def __init__(self):
        # Read credentials securely from environment variables
        self.bucket_name = "aibs-vault"
        # e.g., https://<ACCOUNT_ID>.r2.cloudflarestorage.com
        self.endpoint_url = os.getenv("R2_ENDPOINT_URL")
        self.access_key = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

        self.s3_client = None
        if self.endpoint_url and self.access_key and self.secret_key:
            try:
                # Initialize the S3-compatible client
                self.s3_client = boto3.client(
                    service_name="s3",
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name="auto",  # Geographic routing is automatic
                )
            except ClientError as e:
                logging.error("❌ Failed to initialize R2 client: %s", e)
        else:
            logging.warning(
                "⚠️ Cloudflare R2 credentials (R2_ENDPOINT_URL, "
                "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY) "
                "not set in environment."
            )

    def _sync_upload(self, file_path: str, object_name: str) -> bool:
        """Synchronous upload execution helper."""
        if not self.s3_client:
            logging.warning("⚠️ R2 Client not initialized. Skipping upload.")
            return False
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, object_name)
            return True
        except ClientError as e:
            logging.error("❌ R2 Upload Failed: %s", e)
            return False

    async def upload_file(
        self, local_path: str, object_name: Optional[str] = None
    ) -> bool:
        """Asynchronously uploads a local file to Cloudflare R2."""
        if not self.s3_client:
            return False

        if not object_name:
            object_name = os.path.basename(local_path)

        logging.info(
            "☁️ Uploading %s to R2 bucket '%s'...",
            local_path,
            self.bucket_name,
        )
        # Offload synchronous S3 upload to an async thread pool
        success = await asyncio.to_thread(self._sync_upload, local_path, object_name)

        if success:
            logging.info("✅ Successfully uploaded %s to R2.", object_name)
        return success
