#!/usr/bin/env python3
"""
Test script to verify Claude API is being used for README analysis.
"""
import os
import logging
from metric_calculators import RampUpTimeMetric
from unittest.mock import Mock

# Enable debug logging to see what's happening
logging.basicConfig(level=logging.DEBUG)

# Create a mock DataFetcher
mock_fetcher = Mock()
mock_fetcher.fetch_readme.return_value = """
# Example Model

## Installation
To install this model, run: pip install example-model

## Usage
Here's how to use the model with detailed examples and code snippets.

## Quick Start Guide
Get started in under 5 minutes with our comprehensive tutorial.
"""

print("=" * 60)
print("Testing RampUpTimeMetric with Claude API")
print("=" * 60)

# Check API key
if os.environ.get("ANTHROPIC_API_KEY"):
    print("✓ ANTHROPIC_API_KEY is set")
else:
    print("✗ ANTHROPIC_API_KEY is NOT set")
    print("  Claude API will NOT be used (falling back to keywords)")

print()

# Test the metric
metric = RampUpTimeMetric()

print("Calling RampUpTimeMetric.calculate()...")
print()

try:
    score, latency = metric.calculate(mock_fetcher)

    print("-" * 60)
    print(f"Result: score={score}, latency={latency}ms")
    print("-" * 60)

    # The presence of latency > 100ms often indicates an API call was made
    # (keyword analysis is usually much faster)
    if latency > 100:
        print("\n✓ High latency suggests Claude API was called")
        print(f"  (Latency: {latency}ms)")
    else:
        print("\n⚠ Low latency suggests keyword fallback was used")
        print(f"  (Latency: {latency}ms)")

    print("\nTo confirm Claude API usage, check the logs above for:")
    print("  - 'Ramp-up score (Claude)' = API was used")
    print("  - 'Ramp-up score (keywords)' = Fallback was used")

except Exception as e:
    print(f"\n✗ Error occurred: {e}")
    print("\nThis might indicate:")
    print("  - Invalid API key")
    print("  - Network issues")
    print("  - API quota exceeded")
