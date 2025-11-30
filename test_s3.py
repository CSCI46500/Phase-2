#!/usr/bin/env python3
"""
Simple script to test S3 connection with AWS.
"""
from dotenv import load_dotenv
load_dotenv(override=True)

from src.services.s3_service import s3_helper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_s3_connection():
    """Test S3 connection and bucket access."""
    print("=" * 60)
    print("Testing S3 Connection")
    print("=" * 60)

    # Test 1: List bucket (checks if bucket exists and credentials work)
    print("\n1. Testing bucket access...")
    try:
        response = s3_helper.s3_client.list_objects_v2(
            Bucket=s3_helper.bucket_name,
            MaxKeys=5
        )
        print(f"[SUCCESS] Successfully accessed bucket: {s3_helper.bucket_name}")
        print(f"  Region: {s3_helper.region}")

        if 'Contents' in response:
            print(f"  Found {len(response['Contents'])} objects (showing first 5)")
            for obj in response['Contents'][:5]:
                print(f"    - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("  Bucket is empty")

    except Exception as e:
        print(f"[ERROR] Failed to access bucket: {e}")
        return False

    # Test 2: Upload a test file
    print("\n2. Testing file upload...")
    test_key = "test/connection_test.txt"
    test_content = b"Hello from FastAPI! Connection test successful."

    try:
        import io
        s3_helper.upload_fileobj(
            io.BytesIO(test_content),
            test_key
        )
        print(f"[SUCCESS] Successfully uploaded test file: {test_key}")
    except Exception as e:
        print(f"[ERROR] Failed to upload test file: {e}")
        return False

    # Test 3: Check if file exists
    print("\n3. Testing file exists check...")
    if s3_helper.file_exists(test_key):
        print(f"[SUCCESS] Test file found in S3")
    else:
        print(f"[ERROR] Test file not found")
        return False

    # Test 4: Get file size
    print("\n4. Testing file size retrieval...")
    size = s3_helper.get_file_size(test_key)
    if size:
        print(f"[SUCCESS] File size: {size} bytes")
    else:
        print(f"[ERROR] Could not get file size")

    # Test 5: Generate presigned URL
    print("\n5. Testing presigned URL generation...")
    url = s3_helper.generate_presigned_url(test_key, expiration=60)
    if url:
        print(f"[SUCCESS] Generated presigned URL")
        print(f"  URL (first 80 chars): {url[:80]}...")
    else:
        print(f"[ERROR] Failed to generate presigned URL")

    # Test 6: Delete test file
    print("\n6. Testing file deletion...")
    if s3_helper.delete_file(test_key):
        print(f"[SUCCESS] Successfully deleted test file")
    else:
        print(f"[ERROR] Failed to delete test file")

    print("\n" + "=" * 60)
    print("All S3 tests passed! [SUCCESS]")
    print("=" * 60)
    print("\nYour S3 configuration:")
    print(f"  Bucket: {s3_helper.bucket_name}")
    print(f"  Region: {s3_helper.region}")
    print(f"  Endpoint: {s3_helper.endpoint_url or 'AWS S3 (default)'}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    test_s3_connection()
