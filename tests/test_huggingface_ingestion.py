"""
Test script for HuggingFace model ingestion endpoint.

This demonstrates how to use the new POST /package/ingest-huggingface endpoint
to automatically download and ingest HuggingFace models.
"""
import requests
import json


def test_huggingface_ingestion():
    """
    Test the HuggingFace model ingestion endpoint.

    This test:
    1. Authenticates with the API
    2. Calls the /package/ingest-huggingface endpoint
    3. Verifies the model is ingested successfully
    """

    BASE_URL = "http://localhost:8000"

    # Step 1: Authenticate
    print("Step 1: Authenticating...")
    auth_response = requests.post(
        f"{BASE_URL}/authenticate",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.text}")
        return

    token = auth_response.json()["token"]
    print(f"✓ Authenticated successfully. Token: {token[:20]}...")

    # Step 2: Ingest a small HuggingFace model
    # Using a very small model for testing: distilbert-base-uncased-finetuned-sst-2-english
    # This is a small sentiment analysis model (about 250MB)
    print("\nStep 2: Ingesting HuggingFace model...")
    print("Model: distilbert-base-uncased-finetuned-sst-2-english")
    print("This may take a few minutes to download and process...")

    ingest_response = requests.post(
        f"{BASE_URL}/package/ingest-huggingface",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "model_id": "distilbert-base-uncased-finetuned-sst-2-english",
            "description": "DistilBERT model fine-tuned for sentiment analysis"
        }
    )

    print(f"Response status: {ingest_response.status_code}")

    if ingest_response.status_code == 200:
        result = ingest_response.json()
        print("\n✓ Model ingested successfully!")
        print(f"  Package ID: {result['package_id']}")
        print(f"  Name: {result['name']}")
        print(f"  Version: {result['version']}")
        print(f"  Net Score: {result['net_score']}")
        print(f"  Size: {result['size_bytes']:,} bytes")
        print(f"  S3 Path: {result['s3_path']}")
        print("\n  Metrics:")
        for metric, value in result['metrics'].items():
            print(f"    {metric}: {value}")

    elif ingest_response.status_code == 400:
        error = ingest_response.json()
        print(f"\n✗ Model failed validation: {error['detail']}")
        print("This means the model did not meet the minimum quality threshold (≥0.5 for all metrics)")

    else:
        print(f"\n✗ Ingestion failed: {ingest_response.text}")

    # Step 3: Verify the package was created
    print("\nStep 3: Verifying package was created...")
    search_response = requests.post(
        f"{BASE_URL}/packages",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "distilbert"}
    )

    if search_response.status_code == 200:
        packages = search_response.json()["packages"]
        print(f"✓ Found {len(packages)} package(s) matching 'distilbert'")
        for pkg in packages:
            print(f"  - {pkg['name']} v{pkg['version']} (score: {pkg['net_score']})")
    else:
        print(f"✗ Search failed: {search_response.text}")


def test_failed_ingestion():
    """
    Test ingesting a model that might fail quality checks.

    This demonstrates what happens when a model doesn't meet the ≥0.5 threshold.
    """
    BASE_URL = "http://localhost:8000"

    # Authenticate
    auth_response = requests.post(
        f"{BASE_URL}/authenticate",
        json={"username": "admin", "password": "admin123"}
    )

    if auth_response.status_code != 200:
        print(f"Authentication failed: {auth_response.text}")
        return

    token = auth_response.json()["token"]

    # Try to ingest a model (this might fail validation depending on the model)
    print("Testing model that might fail quality checks...")
    ingest_response = requests.post(
        f"{BASE_URL}/package/ingest-huggingface",
        headers={"Authorization": f"Bearer {token}"},
        json={"model_id": "gpt2"}  # Small model for testing
    )

    if ingest_response.status_code == 400:
        print(f"✓ Model correctly rejected: {ingest_response.json()['detail']}")
    elif ingest_response.status_code == 200:
        print("✓ Model passed quality checks and was ingested")
    else:
        print(f"Unexpected response: {ingest_response.text}")


def test_duplicate_ingestion():
    """
    Test that duplicate model ingestion is prevented.
    """
    BASE_URL = "http://localhost:8000"

    # Authenticate
    auth_response = requests.post(
        f"{BASE_URL}/authenticate",
        json={"username": "admin", "password": "admin123"}
    )

    token = auth_response.json()["token"]

    model_id = "distilbert-base-uncased-finetuned-sst-2-english"

    print(f"Attempting to ingest {model_id} twice...")

    # First ingestion
    response1 = requests.post(
        f"{BASE_URL}/package/ingest-huggingface",
        headers={"Authorization": f"Bearer {token}"},
        json={"model_id": model_id}
    )

    # Second ingestion (should fail)
    response2 = requests.post(
        f"{BASE_URL}/package/ingest-huggingface",
        headers={"Authorization": f"Bearer {token}"},
        json={"model_id": model_id}
    )

    if response2.status_code == 400 and "already exists" in response2.json().get("detail", ""):
        print("✓ Duplicate ingestion correctly prevented")
    else:
        print(f"Unexpected response: {response2.text}")


def print_curl_examples():
    """
    Print curl command examples for manual testing.
    """
    print("\n" + "="*80)
    print("CURL EXAMPLES FOR MANUAL TESTING")
    print("="*80)

    print("""
# 1. Authenticate
curl -X POST http://localhost:8000/authenticate \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "admin123"}'

# Save the token from the response
TOKEN="<your-token-here>"

# 2. Ingest a HuggingFace model
curl -X POST http://localhost:8000/package/ingest-huggingface \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model_id": "distilbert-base-uncased-finetuned-sst-2-english",
    "description": "Sentiment analysis model"
  }'

# 3. Ingest with custom version
curl -X POST http://localhost:8000/package/ingest-huggingface \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model_id": "gpt2",
    "version": "1.0.1",
    "description": "GPT-2 small model"
  }'

# 4. Search for ingested packages
curl -X POST http://localhost:8000/packages \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "distilbert"}'

# 5. Get package metadata
curl -X GET http://localhost:8000/package/{package_id}/metadata \\
  -H "Authorization: Bearer $TOKEN"
""")


if __name__ == "__main__":
    print("="*80)
    print("HUGGINGFACE MODEL INGESTION TEST")
    print("="*80)
    print("\nNOTE: Make sure the API server is running on http://localhost:8000")
    print("      and that you have AWS S3 credentials configured.\n")

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--curl":
        print_curl_examples()
    else:
        try:
            test_huggingface_ingestion()
        except requests.exceptions.ConnectionError:
            print("\n✗ Error: Could not connect to API server at http://localhost:8000")
            print("   Make sure the server is running with: ./run_api_new.sh")
        except Exception as e:
            print(f"\n✗ Error: {e}")

        print("\n" + "="*80)
        print("Run with --curl flag to see curl command examples")
        print("="*80)
