#!/usr/bin/env python3
"""
Direct S3 upload test - bypasses API to test S3 integration.
"""
from dotenv import load_dotenv
load_dotenv(override=True)

from src.services.s3_service import s3_helper
import os

def upload_test_package():
    """Upload test package directly to S3."""
    print("=" * 60)
    print("Direct S3 Upload Test")
    print("=" * 60)

    package_file = "test_package.zip"
    package_name = "my-test-model"
    package_version = "1.0.0"

    # Build S3 path using the helper's method
    s3_key = s3_helper.build_s3_path(package_name, package_version, "package.zip")

    print(f"\nPackage details:")
    print(f"  Local file: {package_file}")
    print(f"  File size: {os.path.getsize(package_file)} bytes")
    print(f"  S3 bucket: {s3_helper.bucket_name}")
    print(f"  S3 key: {s3_key}")
    print(f"  Full S3 URL: {s3_helper.build_full_s3_url(s3_key)}")

    # Upload to S3
    print(f"\nUploading to S3...")
    if s3_helper.upload_file(package_file, s3_key):
        print("[SUCCESS] Package uploaded to S3!")

        # Verify it exists
        print("\nVerifying upload...")
        if s3_helper.file_exists(s3_key):
            size = s3_helper.get_file_size(s3_key)
            print(f"[SUCCESS] Package verified in S3")
            print(f"  Size: {size} bytes")

            # Generate download URL
            print("\nGenerating presigned download URL...")
            url = s3_helper.generate_presigned_url(s3_key, expiration=300)
            if url:
                print(f"[SUCCESS] Download URL generated (expires in 5 min)")
                print(f"\nYou can download the package from:")
                print(f"{url[:80]}...")
                print(f"\n(Full URL is {len(url)} characters)")

            print("\n" + "=" * 60)
            print("S3 Integration Test: PASSED!")
            print("=" * 60)
            print("\nYour package is now stored in:")
            print(f"  AWS S3 Bucket: {s3_helper.bucket_name}")
            print(f"  Region: {s3_helper.region}")
            print(f"  Path: {s3_key}")
            print("=" * 60)

            return True
        else:
            print("[ERROR] Package not found after upload")
            return False
    else:
        print("[ERROR] Upload failed")
        return False

if __name__ == "__main__":
    upload_test_package()
