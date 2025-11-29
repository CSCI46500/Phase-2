#!/usr/bin/env python3
"""
Test script to verify metric validation logic.
Tests the validate_metric_threshold function with various scenarios.
"""

from src.utils.validation import validate_metric_threshold

def test_all_metrics_pass():
    """Test case: All metrics meet threshold of 0.5"""
    print("\n=== Test 1: All metrics pass (≥ 0.5) ===")
    metrics = {
        "license": 1.0,
        "size_score": 0.8,
        "ramp_up_time": 0.7,
        "bus_factor": 0.6,
        "performance_claims": 0.9,
        "dataset_and_code_score": 0.8,
        "dataset_quality": 0.7,
        "code_quality": 0.6,
        "reproducibility": 0.9,
        "reviewedness": 0.5,
        "net_score": 0.75
    }
    is_valid, msg = validate_metric_threshold(metrics, threshold=0.5)
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid, "Expected validation to pass"
    print("✓ PASSED")


def test_one_metric_fails():
    """Test case: One metric below threshold"""
    print("\n=== Test 2: One metric fails (bus_factor = 0.3) ===")
    metrics = {
        "license": 1.0,
        "size_score": 0.8,
        "ramp_up_time": 0.7,
        "bus_factor": 0.3,  # Below threshold
        "performance_claims": 0.9,
        "dataset_and_code_score": 0.8,
        "dataset_quality": 0.7,
        "code_quality": 0.6,
        "reproducibility": 0.9,
        "reviewedness": 0.5,
        "net_score": 0.75
    }
    is_valid, msg = validate_metric_threshold(metrics, threshold=0.5)
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    assert not is_valid, "Expected validation to fail"
    assert "Bus Factor" in msg, "Expected Bus Factor to be mentioned"
    print("✓ PASSED")


def test_reviewedness_minus_one():
    """Test case: reviewedness = -1 (no GitHub repo) should be skipped"""
    print("\n=== Test 3: reviewedness = -1 (should skip validation) ===")
    metrics = {
        "license": 1.0,
        "size_score": 0.8,
        "ramp_up_time": 0.7,
        "bus_factor": 0.6,
        "performance_claims": 0.9,
        "dataset_and_code_score": 0.8,
        "dataset_quality": 0.7,
        "code_quality": 0.6,
        "reproducibility": 0.9,
        "reviewedness": -1,  # No GitHub repo
        "net_score": 0.75
    }
    is_valid, msg = validate_metric_threshold(metrics, threshold=0.5)
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid, "Expected validation to pass (reviewedness -1 should be skipped)"
    print("✓ PASSED")


def test_multiple_metrics_fail():
    """Test case: Multiple metrics below threshold"""
    print("\n=== Test 4: Multiple metrics fail ===")
    metrics = {
        "license": 0.2,  # Below
        "size_score": 0.8,
        "ramp_up_time": 0.1,  # Below
        "bus_factor": 0.3,  # Below
        "performance_claims": 0.9,
        "dataset_and_code_score": 0.8,
        "dataset_quality": 0.7,
        "code_quality": 0.6,
        "reproducibility": 0.9,
        "reviewedness": 0.5,
        "net_score": 0.75
    }
    is_valid, msg = validate_metric_threshold(metrics, threshold=0.5)
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    assert not is_valid, "Expected validation to fail"
    assert "License" in msg, "Expected License to be mentioned"
    assert "Ramp-Up Time" in msg, "Expected Ramp-Up Time to be mentioned"
    assert "Bus Factor" in msg, "Expected Bus Factor to be mentioned"
    print("✓ PASSED")


def test_size_score_as_dict():
    """Test case: size_score as dictionary (should take minimum)"""
    print("\n=== Test 5: size_score as dict (min value used) ===")
    metrics = {
        "license": 1.0,
        "size_score": {"model": 0.9, "dataset": 0.6, "code": 0.7},  # min = 0.6
        "ramp_up_time": 0.7,
        "bus_factor": 0.6,
        "performance_claims": 0.9,
        "dataset_and_code_score": 0.8,
        "dataset_quality": 0.7,
        "code_quality": 0.6,
        "reproducibility": 0.9,
        "reviewedness": 0.5,
        "net_score": 0.75
    }
    is_valid, msg = validate_metric_threshold(metrics, threshold=0.5)
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid, "Expected validation to pass (min size_score = 0.6 >= 0.5)"
    print("✓ PASSED")


def test_size_score_dict_fails():
    """Test case: size_score as dict with min < threshold"""
    print("\n=== Test 6: size_score dict with min < threshold ===")
    metrics = {
        "license": 1.0,
        "size_score": {"model": 0.9, "dataset": 0.3, "code": 0.7},  # min = 0.3
        "ramp_up_time": 0.7,
        "bus_factor": 0.6,
        "performance_claims": 0.9,
        "dataset_and_code_score": 0.8,
        "dataset_quality": 0.7,
        "code_quality": 0.6,
        "reproducibility": 0.9,
        "reviewedness": 0.5,
        "net_score": 0.75
    }
    is_valid, msg = validate_metric_threshold(metrics, threshold=0.5)
    print(f"Valid: {is_valid}")
    print(f"Message: {msg}")
    assert not is_valid, "Expected validation to fail (min size_score = 0.3 < 0.5)"
    assert "Size Score" in msg, "Expected Size Score to be mentioned"
    print("✓ PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Metric Validation Logic")
    print("=" * 60)

    try:
        test_all_metrics_pass()
        test_one_metric_fails()
        test_reviewedness_minus_one()
        test_multiple_metrics_fail()
        test_size_score_as_dict()
        test_size_score_dict_fails()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
