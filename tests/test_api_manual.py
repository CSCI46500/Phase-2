#!/usr/bin/env python3
"""
Manual API testing script.
Tests all major CRUD endpoints.
"""
import requests
import json
import sys
import time
from typing import Optional
import tempfile
import zipfile
import os

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


class APITester:
    """API testing helper class."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.test_package_id: Optional[str] = None
        self.test_user_id: Optional[str] = None

    def log(self, message: str, status: str = "INFO"):
        """Print colored log message."""
        colors = {
            "INFO": "\033[94m",  # Blue
            "SUCCESS": "\033[92m",  # Green
            "ERROR": "\033[91m",  # Red
            "WARNING": "\033[93m",  # Yellow
        }
        reset = "\033[0m"
        print(f"{colors.get(status, '')}{status}: {message}{reset}")

    def test_health(self) -> bool:
        """Test health check endpoint."""
        self.log("Testing health check...", "INFO")
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                self.log(f"Health: {data['status']}", "SUCCESS")
                return True
            else:
                self.log(f"Health check failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Health check error: {e}", "ERROR")
            return False

    def test_authenticate(self, username: str, password: str) -> bool:
        """Test authentication."""
        self.log(f"Authenticating as {username}...", "INFO")
        try:
            response = requests.post(
                f"{self.base_url}/authenticate",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["token"]
                self.log(f"Authenticated! Token: {self.token[:20]}...", "SUCCESS")
                return True
            else:
                self.log(f"Authentication failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Authentication error: {e}", "ERROR")
            return False

    def test_register_user(self) -> bool:
        """Test user registration."""
        self.log("Registering test user...", "INFO")
        try:
            response = requests.post(
                f"{self.base_url}/user/register",
                headers={"X-Authorization": self.token},
                json={
                    "username": f"testuser_{int(time.time())}",
                    "password": "test123",
                    "permissions": ["upload", "download", "search"]
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.test_user_id = data["user_id"]
                self.log(f"User registered! ID: {self.test_user_id}", "SUCCESS")
                return True
            else:
                self.log(f"User registration failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"User registration error: {e}", "ERROR")
            return False

    def create_test_package_file(self) -> str:
        """Create a test zip file."""
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "test_package.zip")

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Create test files
            zipf.writestr("README.md", "# Test Model\nThis is a test model package.")
            zipf.writestr("model.txt", "Test model weights data")
            zipf.writestr("config.json", '{"model_type": "test", "version": "1.0"}')

        return zip_path

    def test_upload_package(self) -> bool:
        """Test package upload."""
        self.log("Uploading test package...", "INFO")

        # Create test zip file
        zip_path = self.create_test_package_file()

        try:
            with open(zip_path, 'rb') as f:
                files = {'file': ('test_package.zip', f, 'application/zip')}
                data = {
                    'name': f'test-model-{int(time.time())}',
                    'version': '1.0.0',
                    'description': 'Test model for API testing',
                    'model_url': 'https://huggingface.co/bert-base-uncased',
                    'code_url': 'https://github.com/huggingface/transformers',
                    'dataset_url': ''
                }

                response = requests.post(
                    f"{self.base_url}/package",
                    headers={"X-Authorization": self.token},
                    files=files,
                    data=data
                )

            if response.status_code == 200:
                data = response.json()
                self.test_package_id = data["package_id"]
                self.log(f"Package uploaded! ID: {self.test_package_id}", "SUCCESS")
                self.log(f"Net score: {data.get('net_score')}", "INFO")
                return True
            else:
                self.log(f"Package upload failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Package upload error: {e}", "ERROR")
            return False
        finally:
            # Cleanup
            if os.path.exists(zip_path):
                os.remove(zip_path)

    def test_search_packages(self) -> bool:
        """Test package search."""
        self.log("Searching packages...", "INFO")
        try:
            response = requests.post(
                f"{self.base_url}/packages",
                headers={"X-Authorization": self.token},
                json={"name": "test"}
            )
            if response.status_code == 200:
                data = response.json()
                self.log(f"Found {data['total']} packages", "SUCCESS")
                if data['packages']:
                    self.log(f"First package: {data['packages'][0]['name']}", "INFO")
                return True
            else:
                self.log(f"Package search failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Package search error: {e}", "ERROR")
            return False

    def test_get_metadata(self) -> bool:
        """Test getting package metadata."""
        if not self.test_package_id:
            self.log("No package ID available for metadata test", "WARNING")
            return False

        self.log("Getting package metadata...", "INFO")
        try:
            response = requests.get(
                f"{self.base_url}/package/{self.test_package_id}/metadata",
                headers={"X-Authorization": self.token}
            )
            if response.status_code == 200:
                data = response.json()
                self.log(f"Package: {data['name']} v{data['version']}", "SUCCESS")
                self.log(f"Metrics: {data.get('metrics')}", "INFO")
                return True
            else:
                self.log(f"Get metadata failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Get metadata error: {e}", "ERROR")
            return False

    def test_rate_package(self) -> bool:
        """Test rating a package."""
        if not self.test_package_id:
            self.log("No package ID available for rating test", "WARNING")
            return False

        self.log("Rating package...", "INFO")
        try:
            response = requests.put(
                f"{self.base_url}/package/{self.test_package_id}/rate",
                headers={"X-Authorization": self.token},
                json={"score": 5}
            )
            if response.status_code == 200:
                data = response.json()
                self.log(f"Rating submitted! Average: {data['average_rating']}", "SUCCESS")
                return True
            else:
                self.log(f"Rating failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Rating error: {e}", "ERROR")
            return False

    def test_get_download_url(self) -> bool:
        """Test getting download URL."""
        if not self.test_package_id:
            self.log("No package ID available for download test", "WARNING")
            return False

        self.log("Getting download URL...", "INFO")
        try:
            response = requests.get(
                f"{self.base_url}/package/{self.test_package_id}",
                headers={"X-Authorization": self.token}
            )
            if response.status_code == 200:
                data = response.json()
                self.log(f"Download URL generated (expires in {data['expires_in_seconds']}s)", "SUCCESS")
                return True
            else:
                self.log(f"Get download URL failed: {response.status_code} - {response.text}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Get download URL error: {e}", "ERROR")
            return False

    def test_lineage(self) -> bool:
        """Test getting package lineage."""
        if not self.test_package_id:
            self.log("No package ID available for lineage test", "WARNING")
            return False

        self.log("Getting package lineage...", "INFO")
        try:
            response = requests.get(
                f"{self.base_url}/package/{self.test_package_id}/lineage",
                headers={"X-Authorization": self.token}
            )
            if response.status_code == 200:
                data = response.json()
                self.log(f"Lineage depth: {len(data['lineage'])}", "SUCCESS")
                return True
            else:
                self.log(f"Get lineage failed: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Get lineage error: {e}", "ERROR")
            return False

    def run_all_tests(self):
        """Run all tests in sequence."""
        self.log("=" * 60, "INFO")
        self.log("Starting API Tests", "INFO")
        self.log("=" * 60, "INFO")

        results = {
            "Health Check": self.test_health(),
            "Authentication": self.test_authenticate(ADMIN_USERNAME, ADMIN_PASSWORD),
        }

        if results["Authentication"]:
            results["Register User"] = self.test_register_user()
            results["Upload Package"] = self.test_upload_package()
            results["Search Packages"] = self.test_search_packages()
            results["Get Metadata"] = self.test_get_metadata()
            results["Rate Package"] = self.test_rate_package()
            results["Get Download URL"] = self.test_get_download_url()
            results["Get Lineage"] = self.test_lineage()

        # Summary
        self.log("=" * 60, "INFO")
        self.log("Test Summary", "INFO")
        self.log("=" * 60, "INFO")

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "SUCCESS" if result else "ERROR"
            symbol = "✓" if result else "✗"
            self.log(f"{symbol} {test_name}", status)

        self.log("=" * 60, "INFO")
        self.log(f"Results: {passed}/{total} tests passed",
                "SUCCESS" if passed == total else "WARNING")
        self.log("=" * 60, "INFO")

        return passed == total


def main():
    """Main entry point."""
    print("\n🚀 Model Registry API Test Suite\n")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: API server is not running!")
        print(f"   Please start the server first: ./run_api.sh")
        print(f"   Or: python3 -m uvicorn api:app --port 8000")
        return 1

    # Run tests
    tester = APITester(BASE_URL)
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())