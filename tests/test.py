# tests/test.py
import pytest
from unittest.mock import patch, MagicMock
from metrics import Metrics

# --- Helper function to create a mocked Metrics instance ---
def create_mock_metrics(mock_values):
    with patch("metrics.Model") as MockModel:
        instance = MockModel.return_value

        # Patch all the Model methods used in Metrics
        instance.model_dict = {
            "name": mock_values.get("name", "bert-base-uncased"),
            "category": mock_values.get("category", "MODEL")
        }
        instance.fetch_readme.return_value = mock_values.get("readme", "")
        instance.get_contrib.return_value = mock_values.get("contrib", 10)
        instance.get_license.return_value = mock_values.get("license", "mit")
        instance.get_size.return_value = mock_values.get("size", 1.0)
        instance.code_dict = mock_values.get("code_dict", {"file.py": "content"})
        instance.dataset_dict = mock_values.get("dataset_dict", {"data.csv": "content"})
        instance.len_readme.side_effect = lambda which: mock_values.get(f"{which}_readme_len", 1000)
        instance.get_downloads.return_value = mock_values.get("downloads", 100000)
        instance.kw_check.return_value = mock_values.get("kw_check", True)
        instance.get_git_stats.return_value = mock_values.get("git_stats", {"stars": 10000, "forks": 5000})
        instance.last_modified.return_value = mock_values.get("last_modified", True)

        return Metrics({"code_url": "dummy", "dataset_url": "dummy", "model_url": "dummy"})

# --- Tests ---
def test_name_and_category():
    metrics = create_mock_metrics({})
    results = metrics.run()
    assert results["name"] == "bert-base-uncased"
    assert results["category"] == "MODEL"

def test_ramp_up_score():
    metrics = create_mock_metrics({"readme": "installation usage example quickstart"})
    results = metrics.run()
    assert 0 <= results["ramp_up_time"] <= 1

def test_bus_factor_score():
    metrics = create_mock_metrics({"contrib": 10})
    results = metrics.run()
    assert results["bus_factor"] == 1.0

def test_perf_claims_score():
    metrics = create_mock_metrics({"readme": "benchmark accuracy"})
    results = metrics.run()
    assert results["performance_claims"] == 1.0

def test_license_score():
    metrics = create_mock_metrics({"license": "MIT"})
    results = metrics.run()
    assert results["license"] == 1.0

def test_size_score():
    metrics = create_mock_metrics({"size": 1.0})
    results = metrics.run()
    for score in results["size_score"].values():
        assert 0 <= score <= 1

def test_dataset_and_code_score():
    metrics = create_mock_metrics({"code_dict": {"a.py": "x"}, "dataset_dict": {"data.csv": "y"}})
    results = metrics.run()
    assert results["dataset_and_code_score"] == 1.0

def test_dataset_quality_score():
    metrics = create_mock_metrics({
        "dataset_readme_len": 1000,
        "downloads": 100000,
        "kw_check": True
    })
    results = metrics.run()
    assert 0 <= results["dataset_quality"] <= 1.0

def test_code_quality_score():
    metrics = create_mock_metrics({
        "git_stats": {"stars": 10000, "forks": 5000},
        "code_readme_len": 1700,
        "last_modified": True
    })
    results = metrics.run()
    assert 0 <= results["code_quality"] <= 1.0

def test_net_score():
    metrics = create_mock_metrics({})
    results = metrics.run()
    assert 0 <= results["net_score"] <= 1.0
