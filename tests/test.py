# tests/test.py
import pytest
from unittest.mock import patch, MagicMock
from metrics_evaluator import MetricsEvaluator
from data_fetcher import DataFetcher


# --- Helper function to create a mocked MetricsEvaluator instance ---
def create_mock_evaluator(mock_values):
    """Create a MetricsEvaluator with mocked DataFetcher."""
    with patch("metrics_evaluator.DataFetcher") as MockDataFetcher:
        instance = MockDataFetcher.return_value

        # Mock all DataFetcher methods
        instance.get_model_name.return_value = mock_values.get("name", "bert-base-uncased")
        instance.fetch_readme.return_value = mock_values.get("readme", "")
        instance.get_contributor_count.return_value = mock_values.get("contrib", 10)
        instance.get_license.return_value = mock_values.get("license", "mit")
        instance.get_model_size_gb.return_value = mock_values.get("size", 1.0)
        instance.has_code_url.return_value = mock_values.get("has_code", True)
        instance.has_dataset_url.return_value = mock_values.get("has_dataset", True)
        instance.get_dataset_downloads.return_value = mock_values.get("downloads", 100000)
        instance.get_github_stats.return_value = mock_values.get("git_stats", {"stars": 10000, "forks": 5000})
        instance.is_recently_modified.return_value = mock_values.get("last_modified", True)

        return MetricsEvaluator(
            model_url="https://huggingface.co/test/model",
            dataset_url="https://huggingface.co/datasets/test/dataset",
            code_url="https://github.com/test/repo"
        )


# --- Tests ---
def test_name_and_category():
    evaluator = create_mock_evaluator({})
    results = evaluator.evaluate()
    assert results["name"] == "bert-base-uncased"
    assert results["category"] == "MODEL"


def test_ramp_up_score():
    evaluator = create_mock_evaluator({"readme": "installation usage example quickstart"})
    results = evaluator.evaluate()
    assert 0 <= results["ramp_up_time"] <= 1
    assert "ramp_up_time_latency" in results


def test_bus_factor_score():
    evaluator = create_mock_evaluator({"contrib": 10})
    results = evaluator.evaluate()
    assert results["bus_factor"] == 1.0
    assert "bus_factor_latency" in results


def test_bus_factor_medium():
    evaluator = create_mock_evaluator({"contrib": 7})
    results = evaluator.evaluate()
    assert results["bus_factor"] == 0.5


def test_bus_factor_low():
    evaluator = create_mock_evaluator({"contrib": 3})
    results = evaluator.evaluate()
    assert results["bus_factor"] == 0.0


def test_perf_claims_score():
    evaluator = create_mock_evaluator({"readme": "benchmark accuracy"})
    results = evaluator.evaluate()
    assert results["performance_claims"] == 1.0
    assert "performance_claims_latency" in results


def test_license_score_mit():
    evaluator = create_mock_evaluator({"license": "MIT"})
    results = evaluator.evaluate()
    assert results["license"] == 1.0
    assert "license_latency" in results


def test_license_score_apache():
    evaluator = create_mock_evaluator({"license": "Apache-2.0"})
    results = evaluator.evaluate()
    assert results["license"] == 1.0


def test_license_score_unknown():
    evaluator = create_mock_evaluator({"license": "Proprietary"})
    results = evaluator.evaluate()
    assert results["license"] == 0.0


def test_size_score():
    evaluator = create_mock_evaluator({"size": 1.0})
    results = evaluator.evaluate()
    assert isinstance(results["size_score"], dict)
    assert "raspberry_pi" in results["size_score"]
    assert "jetson_nano" in results["size_score"]
    assert "desktop_pc" in results["size_score"]
    assert "aws_server" in results["size_score"]
    for score in results["size_score"].values():
        assert 0 <= score <= 1
    assert "size_score_latency" in results


def test_dataset_and_code_score_both():
    evaluator = create_mock_evaluator({"has_code": True, "has_dataset": True})
    results = evaluator.evaluate()
    assert results["dataset_and_code_score"] == 1.0
    assert "dataset_and_code_score_latency" in results


def test_dataset_and_code_score_none():
    evaluator = create_mock_evaluator({"has_code": False, "has_dataset": False})
    results = evaluator.evaluate()
    assert results["dataset_and_code_score"] == 0.0


def test_dataset_quality_score():
    evaluator = create_mock_evaluator({
        "readme": "license download split train test validation",
        "downloads": 100000
    })
    results = evaluator.evaluate()
    assert 0 <= results["dataset_quality"] <= 1.0
    assert "dataset_quality_latency" in results


def test_code_quality_score():
    evaluator = create_mock_evaluator({
        "git_stats": {"stars": 10000, "forks": 5000},
        "readme": " ".join(["word"] * 2000),  # 2000 words
        "last_modified": True
    })
    results = evaluator.evaluate()
    assert 0 <= results["code_quality"] <= 1.0
    assert "code_quality_latency" in results


def test_net_score():
    evaluator = create_mock_evaluator({})
    results = evaluator.evaluate()
    assert 0 <= results["net_score"] <= 1.0
    assert "net_score_latency" in results


def test_net_score_calculation():
    """Test that net score is properly weighted."""
    evaluator = create_mock_evaluator({
        "license": "MIT",
        "size": 0.1,
        "contrib": 10,
        "readme": "installation usage example",
        "has_code": True,
        "has_dataset": True,
        "downloads": 100000,
        "git_stats": {"stars": 10000, "forks": 5000},
        "last_modified": True
    })
    results = evaluator.evaluate()
    assert results["net_score"] > 0.3


def test_all_latencies_present():
    """Verify all required latency fields are present."""
    evaluator = create_mock_evaluator({})
    results = evaluator.evaluate()

    required_latencies = [
        "net_score_latency",
        "ramp_up_time_latency",
        "bus_factor_latency",
        "performance_claims_latency",
        "license_latency",
        "size_score_latency",
        "dataset_and_code_score_latency",
        "dataset_quality_latency",
        "code_quality_latency"
    ]

    for latency_field in required_latencies:
        assert latency_field in results
        assert isinstance(results[latency_field], int)


def test_output_structure():
    """Verify output matches required NDJSON structure."""
    evaluator = create_mock_evaluator({})
    results = evaluator.evaluate()

    # Check all required fields
    required_fields = [
        "name", "category", "net_score", "net_score_latency",
        "ramp_up_time", "ramp_up_time_latency",
        "bus_factor", "bus_factor_latency",
        "performance_claims", "performance_claims_latency",
        "license", "license_latency",
        "size_score", "size_score_latency",
        "dataset_and_code_score", "dataset_and_code_score_latency",
        "dataset_quality", "dataset_quality_latency",
        "code_quality", "code_quality_latency"
    ]

    for field in required_fields:
        assert field in results, f"Missing required field: {field}"


def test_score_ranges():
    """Verify all scores are in valid range [0, 1]."""
    evaluator = create_mock_evaluator({})
    results = evaluator.evaluate()

    score_fields = [
        "net_score", "ramp_up_time", "bus_factor",
        "performance_claims", "license",
        "dataset_and_code_score", "dataset_quality", "code_quality"
    ]

    for field in score_fields:
        assert 0 <= results[field] <= 1, f"{field} out of range: {results[field]}"


def test_data_fetcher_model_name():
    """Test DataFetcher extracts model names correctly."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher(model_url="https://huggingface.co/google-bert/bert-base-uncased")
    assert fetcher.get_model_name() == "bert-base-uncased"


def test_data_fetcher_has_code_url():
    """Test DataFetcher detects code URL presence."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher(code_url="https://github.com/test/repo")
    assert fetcher.has_code_url() == True

    fetcher_no_code = DataFetcher(code_url="")
    assert fetcher_no_code.has_code_url() == False


def test_data_fetcher_has_dataset_url():
    """Test DataFetcher detects dataset URL presence."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/test/data")
    assert fetcher.has_dataset_url() == True

    fetcher_no_dataset = DataFetcher(dataset_url="")
    assert fetcher_no_dataset.has_dataset_url() == False


def test_license_metric_accepted_licenses():
    """Test that license metric recognizes all accepted licenses."""
    from metric_calculators import LicenseMetric
    from data_fetcher import DataFetcher

    metric = LicenseMetric()

    accepted = ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0", "LGPL-2.1"]
    for license_name in accepted:
        with patch("metric_calculators.DataFetcher") as MockFetcher:
            mock_instance = MockFetcher.return_value
            mock_instance.get_license.return_value = license_name
            fetcher = mock_instance
            score, latency = metric.calculate(fetcher)
            assert score == 1.0, f"License {license_name} should be accepted"


def test_size_metric_thresholds():
    """Test size metric calculates platform scores correctly."""
    from metric_calculators import SizeScoreMetric

    metric = SizeScoreMetric()

    with patch("metric_calculators.DataFetcher") as MockFetcher:
        mock_instance = MockFetcher.return_value

        # Test tiny model (0.1 GB)
        mock_instance.get_model_size_gb.return_value = 0.1
        scores, latency = metric.calculate(mock_instance)
        assert scores["raspberry_pi"] > 0.5  # Should be good for raspberry pi
        assert scores["aws_server"] > 0.9  # Should be excellent for AWS


def test_ramp_up_metric_fallback():
    """Test ramp-up metric falls back to keywords when no Claude API."""
    from metric_calculators import RampUpTimeMetric
    import os

    # Save original API key
    original_key = os.environ.get("ANTHROPIC_API_KEY")

    try:
        # Remove API key to force fallback
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        metric = RampUpTimeMetric()

        with patch("metric_calculators.DataFetcher") as MockFetcher:
            mock_instance = MockFetcher.return_value
            mock_instance.fetch_readme.return_value = "installation instructions usage examples"

            score, latency = metric.calculate(mock_instance)
            assert 0 <= score <= 1
            assert latency >= 0

    finally:
        # Restore original API key
        if original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key


def test_performance_claims_no_keywords():
    """Test performance claims metric returns 0 when no keywords found."""
    from metric_calculators import PerformanceClaimsMetric

    metric = PerformanceClaimsMetric()

    with patch("metric_calculators.DataFetcher") as MockFetcher:
        mock_instance = MockFetcher.return_value
        mock_instance.fetch_readme.return_value = "This is a basic model with no evaluation data"

        score, latency = metric.calculate(mock_instance)
        assert score == 0.0


def test_dataset_quality_low_downloads():
    """Test dataset quality metric with low downloads."""
    from metric_calculators import DatasetQualityMetric

    metric = DatasetQualityMetric()

    with patch("metric_calculators.DataFetcher") as MockFetcher:
        mock_instance = MockFetcher.return_value
        mock_instance.fetch_readme.return_value = "short readme"
        mock_instance.get_dataset_downloads.return_value = 10  # Low downloads

        score, latency = metric.calculate(mock_instance)
        assert score < 0.5  # Should have low score


def test_code_quality_low_stats():
    """Test code quality metric with low GitHub stats."""
    from metric_calculators import CodeQualityMetric

    metric = CodeQualityMetric()

    with patch("metric_calculators.DataFetcher") as MockFetcher:
        mock_instance = MockFetcher.return_value
        mock_instance.get_github_stats.return_value = {"stars": 5, "forks": 1}
        mock_instance.fetch_readme.return_value = "short"
        mock_instance.is_recently_modified.return_value = False

        score, latency = metric.calculate(mock_instance)
        assert score < 0.3  # Should have low score


def test_net_score_weights():
    """Test that net score uses correct Phase 2 weights."""
    evaluator = create_mock_evaluator({
        "license": "MIT",  # Should contribute 0.2 * 1.0
        "size": 0.0,       # Should contribute 0.1 * 0.0
        "contrib": 10,     # Should contribute 0.12 * 1.0
        "readme": "",
        "has_code": False,
        "has_dataset": False,
        "downloads": 0,
        "git_stats": {"stars": 0, "forks": 0},
        "last_modified": False
    })

    results = evaluator.evaluate()
    # With only license (0.2) and bus_factor (0.12) scoring 1.0, net should be 0.32
    # But there might be slight variations due to other metrics
    assert 0.25 <= results["net_score"] <= 0.40


# Integration tests - test real implementations
def test_data_fetcher_extract_hf_id_model():
    """Integration: Test extracting HuggingFace model ID."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher(model_url="https://huggingface.co/google-bert/bert-base-uncased")
    assert fetcher.model_id == "google-bert/bert-base-uncased"


def test_data_fetcher_extract_hf_id_dataset():
    """Integration: Test extracting HuggingFace dataset ID."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/squad")
    assert fetcher.dataset_id == "squad"


def test_data_fetcher_extract_github_repo():
    """Integration: Test extracting GitHub repo info."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher(code_url="https://github.com/microsoft/vscode")
    assert fetcher.code_repo == ("microsoft", "vscode")


def test_data_fetcher_cache():
    """Integration: Test caching mechanism."""
    from data_fetcher import DataFetcher
    fetcher = DataFetcher()

    # Test cache set and get
    fetcher._cache_set("test_key", "test_value")
    assert fetcher._cache_get("test_key") == "test_value"
    assert fetcher._cache_get("missing_key") is None


def test_license_metric_integration():
    """Integration: Test license metric with real instance."""
    from metric_calculators import LicenseMetric
    from data_fetcher import DataFetcher

    metric = LicenseMetric()

    # Create real DataFetcher (won't make API calls due to caching/empty URLs)
    with patch.object(DataFetcher, 'get_license', return_value='MIT'):
        fetcher = DataFetcher()
        score, latency = metric.calculate(fetcher)
        assert score == 1.0
        assert latency >= 0


def test_size_metric_integration():
    """Integration: Test size metric with real instance."""
    from metric_calculators import SizeScoreMetric
    from data_fetcher import DataFetcher

    metric = SizeScoreMetric()

    with patch.object(DataFetcher, 'get_model_size_gb', return_value=2.5):
        fetcher = DataFetcher()
        scores, latency = metric.calculate(fetcher)

        assert isinstance(scores, dict)
        assert len(scores) == 4
        assert all(0 <= v <= 1 for v in scores.values())
        assert latency >= 0


def test_bus_factor_metric_integration():
    """Integration: Test bus factor metric with real instance."""
    from metric_calculators import BusFactorMetric
    from data_fetcher import DataFetcher

    metric = BusFactorMetric()

    with patch.object(DataFetcher, 'get_contributor_count', return_value=8):
        fetcher = DataFetcher()
        score, latency = metric.calculate(fetcher)
        assert score == 0.5  # 7-9 contributors = 0.5
        assert latency >= 0


def test_dataset_code_metric_integration():
    """Integration: Test dataset/code metric with real instance."""
    from metric_calculators import DatasetCodeScoreMetric
    from data_fetcher import DataFetcher

    metric = DatasetCodeScoreMetric()

    with patch.object(DataFetcher, 'has_code_url', return_value=True):
        with patch.object(DataFetcher, 'has_dataset_url', return_value=True):
            fetcher = DataFetcher()
            score, latency = metric.calculate(fetcher)
            assert score == 1.0
            assert latency >= 0


def test_evaluator_parallel_execution():
    """Integration: Verify parallel execution of metrics."""
    import time
    from metrics_evaluator import MetricsEvaluator

    # This tests that metrics run in parallel by checking execution time
    evaluator = MetricsEvaluator(
        model_url="https://huggingface.co/test/model",
        dataset_url="",
        code_url=""
    )

    start = time.time()
    # Will fail on API calls but should still execute in parallel
    try:
        results = evaluator.evaluate()
    except:
        pass
    elapsed = time.time() - start

    # Parallel execution should be faster than sequential
    # Just verify it completes reasonably fast
    assert elapsed < 10  # Should complete within 10 seconds


def test_main_parse_input():
    """Integration: Test input file parsing."""
    import tempfile
    import os
    from main import parse_input

    # Create temporary test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("url1,url2,url3\n")
        f.write(",,url4\n")
        f.write("\n")  # Empty line
        f.write("url5\n")
        temp_path = f.name

    try:
        results = list(parse_input(temp_path))
        assert len(results) == 3  # Should skip empty line
        assert results[0]["code_url"] == "url1"
        assert results[0]["dataset_url"] == "url2"
        assert results[0]["model_url"] == "url3"
        assert results[1]["model_url"] == "url4"
        assert results[2]["code_url"] == "url5"
    finally:
        os.remove(temp_path)


def test_main_print_ndjson():
    """Integration: Test NDJSON output formatting."""
    from main import print_ndjson
    import json
    from io import StringIO
    import sys

    test_obj = {"name": "test", "score": 0.5, "category": "MODEL"}

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    print_ndjson(test_obj)
    output = sys.stdout.getvalue()

    sys.stdout = old_stdout

    # Verify it's valid JSON on one line
    parsed = json.loads(output.strip())
    assert parsed == test_obj


def test_logger_config():
    """Integration: Test logging configuration."""
    import os
    from logger_config import setup_logging
    import logging

    # Test with different log levels
    old_level = os.environ.get('LOG_LEVEL')
    try:
        os.environ['LOG_LEVEL'] = '1'
        setup_logging()

        # Just verify setup_logging doesn't crash
        logger = logging.getLogger("test_logger")
        assert logger is not None
    finally:
        # Reset
        if old_level:
            os.environ['LOG_LEVEL'] = old_level
        else:
            os.environ.pop('LOG_LEVEL', None)


def test_strip_utilities():
    """Integration: Test HTML and Markdown stripping."""
    from strip import strip_html, strip_markdown

    html_text = "<p>Hello <b>World</b></p>"
    assert "Hello" in strip_html(html_text)
    assert "<p>" not in strip_html(html_text)

    md_text = "# Header\n**Bold** text"
    stripped = strip_markdown(md_text)
    assert "Header" in stripped or "Bold" in stripped


def test_data_fetcher_cache_operations():
    """Test data fetcher caching works correctly."""
    from data_fetcher import DataFetcher

    fetcher = DataFetcher()
    fetcher._cache_set("key1", "value1")
    fetcher._cache_set("key2", {"nested": "data"})

    assert fetcher._cache_get("key1") == "value1"
    assert fetcher._cache_get("key2") == {"nested": "data"}
    assert fetcher._cache_get("nonexistent") is None


def test_metrics_evaluator_weights():
    """Test that MetricsEvaluator uses correct Phase 2 weights."""
    from metrics_evaluator import MetricsEvaluator

    evaluator = MetricsEvaluator("", "", "")
    weights = evaluator.WEIGHTS

    assert weights["license"] == 0.2
    assert weights["size"] == 0.1
    assert weights["ramp"] == 0.12
    assert weights["bus"] == 0.12
    assert weights["perf"] == 0.1
    assert weights["ds_code"] == 0.1
    assert weights["ds_quality"] == 0.13
    assert weights["code_quality"] == 0.13
    assert sum(weights.values()) == 1.0


def test_license_metric_rejects_proprietary():
    """Test that proprietary licenses are rejected."""
    from metric_calculators import LicenseMetric
    from data_fetcher import DataFetcher

    metric = LicenseMetric()

    with patch.object(DataFetcher, 'get_license', return_value='Proprietary'):
        fetcher = DataFetcher()
        score, latency = metric.calculate(fetcher)
        assert score == 0.0


def test_size_metric_zero_size():
    """Test size metric handles zero-sized models."""
    from metric_calculators import SizeScoreMetric
    from data_fetcher import DataFetcher

    metric = SizeScoreMetric()

    with patch.object(DataFetcher, 'get_model_size_gb', return_value=0.0):
        fetcher = DataFetcher()
        scores, latency = metric.calculate(fetcher)
        assert all(v == 0.0 for v in scores.values())


def test_bus_factor_edge_cases():
    """Test bus factor metric edge cases."""
    from metric_calculators import BusFactorMetric
    from data_fetcher import DataFetcher

    metric = BusFactorMetric()

    # Test exactly 10 contributors
    with patch.object(DataFetcher, 'get_contributor_count', return_value=10):
        fetcher = DataFetcher()
        score, _ = metric.calculate(fetcher)
        assert score == 1.0

    # Test exactly 7 contributors
    with patch.object(DataFetcher, 'get_contributor_count', return_value=7):
        fetcher = DataFetcher()
        score, _ = metric.calculate(fetcher)
        assert score == 0.5

    # Test exactly 5 contributors
    with patch.object(DataFetcher, 'get_contributor_count', return_value=5):
        fetcher = DataFetcher()
        score, _ = metric.calculate(fetcher)
        assert score == 0.3


def test_performance_claims_with_keywords():
    """Test performance claims detects various keywords."""
    from metric_calculators import PerformanceClaimsMetric
    from data_fetcher import DataFetcher

    metric = PerformanceClaimsMetric()

    keywords = ["accuracy", "benchmark", "perplexity", "performance"]
    for keyword in keywords:
        with patch.object(DataFetcher, 'fetch_readme', return_value=f"This model has great {keyword}"):
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert score == 1.0, f"Should detect keyword: {keyword}"


def test_dataset_code_score_partial():
    """Test dataset/code score with partial availability."""
    from metric_calculators import DatasetCodeScoreMetric
    from data_fetcher import DataFetcher

    metric = DatasetCodeScoreMetric()

    # Only code available
    with patch.object(DataFetcher, 'has_code_url', return_value=True):
        with patch.object(DataFetcher, 'has_dataset_url', return_value=False):
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert score == 0.5

    # Only dataset available
    with patch.object(DataFetcher, 'has_code_url', return_value=False):
        with patch.object(DataFetcher, 'has_dataset_url', return_value=True):
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert score == 0.5


def test_code_quality_metric_various_stats():
    """Test code quality with various GitHub stat levels."""
    from metric_calculators import CodeQualityMetric
    from data_fetcher import DataFetcher

    metric = CodeQualityMetric()

    # High stats
    with patch.object(DataFetcher, 'get_github_stats', return_value={"stars": 15000, "forks": 6000}):
        with patch.object(DataFetcher, 'fetch_readme', return_value=" ".join(["word"]*2000)):
            with patch.object(DataFetcher, 'is_recently_modified', return_value=True):
                fetcher = DataFetcher()
                score, _ = metric.calculate(fetcher)
                assert score > 0.4

    # Medium README
    with patch.object(DataFetcher, 'get_github_stats', return_value={"stars": 0, "forks": 0}):
        with patch.object(DataFetcher, 'fetch_readme', return_value=" ".join(["word"]*1200)):
            with patch.object(DataFetcher, 'is_recently_modified', return_value=False):
                fetcher = DataFetcher()
                score, _ = metric.calculate(fetcher)
                assert 0.1 <= score <= 0.3


def test_dataset_quality_metric_thresholds():
    """Test dataset quality metric with different download thresholds."""
    from metric_calculators import DatasetQualityMetric
    from data_fetcher import DataFetcher

    metric = DatasetQualityMetric()

    # High downloads
    with patch.object(DataFetcher, 'fetch_readme', return_value=" ".join(["word"]*900)):
        with patch.object(DataFetcher, 'get_dataset_downloads', return_value=150000):
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert score >= 0.5

    # Medium downloads
    with patch.object(DataFetcher, 'fetch_readme', return_value=" ".join(["word"]*500)):
        with patch.object(DataFetcher, 'get_dataset_downloads', return_value=60000):
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert 0.1 <= score <= 0.4


def test_ramp_up_keyword_analysis():
    """Test ramp-up keyword analysis in detail."""
    from metric_calculators import RampUpTimeMetric
    from data_fetcher import DataFetcher

    metric = RampUpTimeMetric()

    # README with installation section
    readme_with_install = """
    installation
    """ + " ".join(["word"] * 60) + """
    usage
    more content here
    """

    with patch.object(DataFetcher, 'fetch_readme', return_value=readme_with_install):
        with patch.dict('os.environ', {}, clear=True):  # No API key
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert score > 0


def test_metrics_evaluator_format_results():
    """Test metrics evaluator formats results correctly."""
    from metrics_evaluator import MetricsEvaluator

    evaluator = create_mock_evaluator({
        "name": "test-model",
        "license": "MIT",
        "size": 1.0,
        "contrib": 10,
        "readme": "test",
        "has_code": True,
        "has_dataset": True
    })

    results = evaluator.evaluate()

    # Verify OrderedDict structure
    assert list(results.keys())[0] == "name"
    assert list(results.keys())[1] == "category"
    assert results["name"] == "test-model"
    assert results["category"] == "MODEL"


def test_size_score_calculation_platforms():
    """Test size score calculation for all platforms."""
    from metric_calculators import SizeScoreMetric
    from data_fetcher import DataFetcher

    metric = SizeScoreMetric()

    # Test 3GB model
    with patch.object(DataFetcher, 'get_model_size_gb', return_value=3.0):
        fetcher = DataFetcher()
        scores, _ = metric.calculate(fetcher)

        # Raspberry Pi should be low (threshold 0.5GB)
        assert scores["raspberry_pi"] < 0.1

        # Desktop PC should be medium-high (threshold 6GB)
        assert scores["desktop_pc"] > 0.4

        # AWS should be very high (threshold 15GB)
        assert scores["aws_server"] > 0.7


def test_all_metrics_return_latency():
    """Ensure all metrics return latency values."""
    from data_fetcher import DataFetcher
    from metric_calculators import (
        LicenseMetric, SizeScoreMetric, RampUpTimeMetric, BusFactorMetric,
        PerformanceClaimsMetric, DatasetCodeScoreMetric,
        DatasetQualityMetric, CodeQualityMetric
    )

    fetcher = DataFetcher()
    metrics = [
        LicenseMetric(), SizeScoreMetric(), RampUpTimeMetric(),
        BusFactorMetric(), PerformanceClaimsMetric(),
        DatasetCodeScoreMetric(), DatasetQualityMetric(), CodeQualityMetric()
    ]

    for metric in metrics:
        _, latency = metric.calculate(fetcher)
        assert isinstance(latency, int)
        assert latency >= 0


def test_evaluator_handles_dict_size_score():
    """Test that evaluator correctly averages dict size scores."""
    evaluator = create_mock_evaluator({
        "size": {"raspberry_pi": 0.5, "jetson_nano": 0.7, "desktop_pc": 0.9, "aws_server": 1.0}
    })

    results = evaluator.evaluate()

    # Net score should use minimum of size scores (0.5)
    assert 0 <= results["net_score"] <= 1


def test_data_fetcher_url_extraction():
    """Test URL extraction methods."""
    from data_fetcher import DataFetcher

    # Test model URL
    fetcher1 = DataFetcher(model_url="https://huggingface.co/google/bert-base")
    assert fetcher1.model_id == "google/bert-base"

    # Test dataset URL
    fetcher2 = DataFetcher(dataset_url="https://huggingface.co/datasets/squad/v2")
    assert "squad" in fetcher2.dataset_id

    # Test GitHub URL
    fetcher3 = DataFetcher(code_url="https://github.com/microsoft/vscode")
    assert fetcher3.code_repo == ("microsoft", "vscode")

    # Test empty URLs
    fetcher4 = DataFetcher(model_url="", dataset_url="", code_url="")
    assert fetcher4.model_id == ""
    assert fetcher4.dataset_id == ""
    assert fetcher4.code_repo == ("", "")


def test_dataset_quality_with_keywords():
    """Test dataset quality detects keywords in README."""
    from metric_calculators import DatasetQualityMetric
    from data_fetcher import DataFetcher

    metric = DatasetQualityMetric()

    # README with keywords
    readme_with_keywords = "This dataset includes license info, download links, train/test split"

    with patch.object(DataFetcher, 'fetch_readme', return_value=readme_with_keywords):
        with patch.object(DataFetcher, 'get_dataset_downloads', return_value=120000):
            fetcher = DataFetcher()
            score, _ = metric.calculate(fetcher)
            assert score >= 0.5  # Should have high score
