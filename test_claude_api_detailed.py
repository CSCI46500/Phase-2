#!/usr/bin/env python3
"""
Detailed test to see the exact error from Claude API.
"""
import os
from anthropic import Anthropic

print("Testing direct Anthropic API call...")
print()

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: No API key set")
    exit(1)

print(f"API Key: {api_key[:10]}... (showing first 10 chars)")
print()

try:
    client = Anthropic(api_key=api_key)

    print("Sending test request to Claude API...")
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": "Rate this README from 0.0-1.0: Installation: pip install test"
        }]
    )

    print("✓ SUCCESS!")
    print(f"Response: {message.content[0].text}")

except Exception as e:
    print(f"✗ ERROR: {e}")
    print()
    print("This error might mean:")
    print("  - Invalid or expired API key")
    print("  - API key lacks necessary permissions")
    print("  - Rate limit exceeded")
    print("  - Model name is invalid")
