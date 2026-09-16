"""Test script to verify Cloudflare R2 S3-compatible upload functionality."""

import asyncio
import os
import sys
from r2_storage import R2StorageManager


async def main():
    print("==================================================")
    print("Cloudflare R2 S3-Compatible Upload Test")
    print("==================================================")

    # 1. Check environment variables
    endpoint = os.getenv("R2_ENDPOINT_URL")
    key_id = os.getenv("R2_ACCESS_KEY_ID")
    secret = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all([endpoint, key_id, secret]):
        print("❌ Error: Missing R2 environment variables.")
        print("Please set the following in your shell before running:")
        print(
            '  $env:R2_ENDPOINT_URL = "https://<account-id>.r2.cloudflarestorage.com"'
        )
        print('  $env:R2_ACCESS_KEY_ID = "your-access-key-id"')
        print('  $env:R2_SECRET_ACCESS_KEY = "your-secret-access-key"')
        sys.exit(1)

    print(f"Endpoint: {endpoint}")
    print(f"Access Key ID: {key_id[:8]}...")
    print(f"Secret Access Key: [REDACTED]")
    print("--------------------------------------------------")

    # 2. Initialize Storage Manager
    print("[Test] Initializing R2StorageManager...")
    r2 = R2StorageManager()

    # 3. Create a dummy file
    temp_file = "temp_r2_test_file.txt"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("This is a test file to verify Cloudflare R2 S3-compatible upload.")
    print(f"[Test] Created local test file: {temp_file}")

    # 4. Upload file
    object_name = "tests/temp_r2_test_file.txt"
    print(f"[Test] Uploading to R2 as '{object_name}'...")
    success = await r2.upload_file(temp_file, object_name)

    # 5. Clean up local file
    if os.path.exists(temp_file):
        os.remove(temp_file)
        print("[Test] Cleaned up local test file.")

    if success:
        print("==================================================")
        print("🎉 SUCCESS: R2 S3-compatible upload verified!")
        print("==================================================")
    else:
        print("==================================================")
        print("❌ FAILURE: R2 S3-compatible upload failed.")
        print("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
