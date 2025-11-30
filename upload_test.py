#!/usr/bin/env python3
"""
Upload test package to verify RDS + S3 integration.
"""
import requests
import os

# API configuration
API_URL = "http://localhost:8000"
TOKEN = "l-C6LIgL1oWz8jTInsskmOGTv-9pWA_AXkdj5kLqJtg"

def upload_package():
    """Upload test package."""
    print("=" * 60)
    print("Uploading Test Package to API")
    print("=" * 60)

    # Package details
    package_file = "test_package.zip"
    package_name = "my-test-model"
    package_version = "1.0.0"

    # Check if file exists
    if not os.path.exists(package_file):
        print(f"[ERROR] File not found: {package_file}")
        return False

    print(f"\nPackage details:")
    print(f"  Name: {package_name}")
    print(f"  Version: {package_version}")
    print(f"  File: {package_file} ({os.path.getsize(package_file)} bytes)")

    # Prepare multipart form data
    files = {
        'file': (package_file, open(package_file, 'rb'), 'application/zip')
    }

    data = {
        'name': package_name,
        'version': package_version
    }

    headers = {
        'X-Authorization': TOKEN
    }

    print(f"\nUploading to {API_URL}/package...")

    try:
        response = requests.post(
            f"{API_URL}/package",
            files=files,
            data=data,
            headers=headers,
            timeout=60
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("[SUCCESS] Package uploaded successfully!")
            print(f"\nResponse:")
            print(response.json())
            return True
        else:
            print(f"[ERROR] Upload failed")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

def verify_in_s3():
    """Check if package exists in S3."""
    print("\n" + "=" * 60)
    print("Verifying Package in S3")
    print("=" * 60)

    from src.services.s3_service import s3_helper

    # Expected S3 path: {package_name}/{version}/package.zip
    s3_key = "my-test-model/1.0.0/package.zip"

    print(f"\nLooking for: s3://{s3_helper.bucket_name}/{s3_key}")

    if s3_helper.file_exists(s3_key):
        size = s3_helper.get_file_size(s3_key)
        print(f"[SUCCESS] Package found in S3!")
        print(f"  Size: {size} bytes")

        # Generate presigned URL
        url = s3_helper.generate_presigned_url(s3_key, expiration=300)
        if url:
            print(f"  Download URL (expires in 5 min):")
            print(f"  {url[:80]}...")

        return True
    else:
        print(f"[ERROR] Package not found in S3")
        return False

if __name__ == "__main__":
    if upload_package():
        verify_in_s3()

    print("\n" + "=" * 60)
