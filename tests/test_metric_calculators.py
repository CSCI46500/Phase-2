"""
Comprehensive tests for metric_calculators.py to achieve 60%+ coverage.
Tests all metric classes with various scenarios including edge cases and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import os
from src.utils.metric_calculators import (
    LicenseMetric,
    SizeScoreMetric,
    RampUpTimeMetric,
    BusFactorMetric,
    PerformanceClaimsMetric,
    DatasetCodeScoreMetric,
    DatasetQualityMetric,
    CodeQualityMetric,
    ReproducibilityMetric,
    ReviewednessMetric,
    TreescoreMetric
)
from src.utils.data_fetcher import DataFetcher


# ============================================================================
# LicenseMetric Tests
# ============================================================================

class TestLicenseMetric:
    """Test LicenseMetric class."""

    def test_accepted_license_mit(self):
        """Test MIT license is accepted."""
        metric = LicenseMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.return_value = "MIT"

        score, latency = metric.calculate(fetcher)
        assert score == 1.0
        assert latency >= 0

    def test_accepted_license_apache(self):
        """Test Apache license is accepted."""
        metric = LicenseMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.return_value = "Apache-2.0"

        score, latency = metric.calculate(fetcher)
        assert score == 1.0
        assert latency >= 0

    def test_accepted_license_bsd(self):
        """Test BSD license is accepted."""
        metric = LicenseMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.return_value = "BSD-3-Clause"

        score, latency = metric.calculate(fetcher)
        assert score == 1.0

    def test_rejected_license_proprietary(self):
        """Test proprietary license is rejected."""
        metric = LicenseMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.return_value = "Proprietary"

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_license_case_insensitive(self):
        """Test license matching is case insensitive."""
        metric = LicenseMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.return_value = "MIT License"  # Mixed case

        score, latency = metric.calculate(fetcher)
        assert score == 1.0

    def test_license_error_handling(self):
        """Test error handling in license metric."""
        metric = LicenseMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.side_effect = Exception("API Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0
        assert latency >= 0


# ============================================================================
# SizeScoreMetric Tests
# ============================================================================

class TestSizeScoreMetric:
    """Test SizeScoreMetric class."""

    def test_zero_size_model(self):
        """Test zero-sized model returns all zeros."""
        metric = SizeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_model_size_gb.return_value = 0.0

        scores, latency = metric.calculate(fetcher)
        assert all(v == 0.0 for v in scores.values())
        assert latency >= 0

    def test_tiny_model_0_1gb(self):
        """Test tiny model (0.1 GB) scores high on all platforms."""
        metric = SizeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_model_size_gb.return_value = 0.1

        scores, latency = metric.calculate(fetcher)
        assert scores["raspberry_pi"] > 0.5
        assert scores["jetson_nano"] > 0.5
        assert scores["desktop_pc"] > 0.9
        assert scores["aws_server"] > 0.9

    def test_large_model_10gb(self):
        """Test large model (10 GB) scores vary by platform."""
        metric = SizeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_model_size_gb.return_value = 10.0

        scores, latency = metric.calculate(fetcher)
        assert scores["raspberry_pi"] == 0.0  # Too large
        assert scores["jetson_nano"] == 0.0   # Too large
        assert scores["desktop_pc"] == 0.0    # Too large
        assert scores["aws_server"] > 0.0     # Can handle it

    def test_size_error_handling(self):
        """Test error handling in size metric."""
        metric = SizeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_model_size_gb.side_effect = Exception("Size fetch error")

        scores, latency = metric.calculate(fetcher)
        assert all(v == 0.0 for v in scores.values())


# ============================================================================
# RampUpTimeMetric Tests
# ============================================================================

class TestRampUpTimeMetric:
    """Test RampUpTimeMetric class."""

    def test_ramp_up_with_keywords(self):
        """Test ramp-up score with installation keywords."""
        metric = RampUpTimeMetric()
        fetcher = Mock(spec=DataFetcher)
        readme = "installation " + " ".join(["word"] * 60) + " usage examples"
        fetcher.fetch_readme.return_value = readme

        with patch.dict(os.environ, {}, clear=True):  # No API key
            score, latency = metric.calculate(fetcher)
            assert 0.0 <= score <= 1.0
            assert latency >= 0

    def test_ramp_up_no_readme(self):
        """Test ramp-up score with no README."""
        metric = RampUpTimeMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.return_value = ""

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_ramp_up_keyword_analysis(self):
        """Test keyword-based analysis directly."""
        metric = RampUpTimeMetric()
        readme = "quickstart installation usage example"

        score = metric._analyze_with_keywords(readme.lower())
        assert 0.0 <= score <= 1.0

    def test_ramp_up_error_handling(self):
        """Test error handling in ramp-up metric."""
        metric = RampUpTimeMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.side_effect = Exception("Fetch error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# BusFactorMetric Tests
# ============================================================================

class TestBusFactorMetric:
    """Test BusFactorMetric class."""

    def test_bus_factor_high(self):
        """Test high contributor count (>=10)."""
        metric = BusFactorMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_contributor_count.return_value = 15

        score, latency = metric.calculate(fetcher)
        assert score == 1.0

    def test_bus_factor_medium(self):
        """Test medium contributor count (7-9)."""
        metric = BusFactorMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_contributor_count.return_value = 8

        score, latency = metric.calculate(fetcher)
        assert score == 0.5

    def test_bus_factor_low(self):
        """Test low contributor count (5-6)."""
        metric = BusFactorMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_contributor_count.return_value = 5

        score, latency = metric.calculate(fetcher)
        assert score == 0.3

    def test_bus_factor_very_low(self):
        """Test very low contributor count (<5)."""
        metric = BusFactorMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_contributor_count.return_value = 3

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_bus_factor_error(self):
        """Test error handling."""
        metric = BusFactorMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_contributor_count.side_effect = Exception("API Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# PerformanceClaimsMetric Tests
# ============================================================================

class TestPerformanceClaimsMetric:
    """Test PerformanceClaimsMetric class."""

    def test_performance_claims_with_accuracy(self):
        """Test detection of 'accuracy' keyword."""
        metric = PerformanceClaimsMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.return_value = "This model achieves 95% accuracy"

        score, latency = metric.calculate(fetcher)
        assert score == 1.0

    def test_performance_claims_with_benchmark(self):
        """Test detection of 'benchmark' keyword."""
        metric = PerformanceClaimsMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.return_value = "Benchmark results show great performance"

        score, latency = metric.calculate(fetcher)
        assert score == 1.0

    def test_performance_claims_no_keywords(self):
        """Test no performance keywords found."""
        metric = PerformanceClaimsMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.return_value = "This is a basic model"

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_performance_claims_error(self):
        """Test error handling."""
        metric = PerformanceClaimsMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.side_effect = Exception("Fetch error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# DatasetCodeScoreMetric Tests
# ============================================================================

class TestDatasetCodeScoreMetric:
    """Test DatasetCodeScoreMetric class."""

    def test_both_dataset_and_code(self):
        """Test when both dataset and code are available."""
        metric = DatasetCodeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = True
        fetcher.has_dataset_url.return_value = True

        score, latency = metric.calculate(fetcher)
        assert score == 1.0

    def test_only_code(self):
        """Test when only code is available."""
        metric = DatasetCodeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = True
        fetcher.has_dataset_url.return_value = False

        score, latency = metric.calculate(fetcher)
        assert score == 0.5

    def test_only_dataset(self):
        """Test when only dataset is available."""
        metric = DatasetCodeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = False
        fetcher.has_dataset_url.return_value = True

        score, latency = metric.calculate(fetcher)
        assert score == 0.5

    def test_neither_dataset_nor_code(self):
        """Test when neither is available."""
        metric = DatasetCodeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = False
        fetcher.has_dataset_url.return_value = False

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_dataset_code_error(self):
        """Test error handling."""
        metric = DatasetCodeScoreMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.side_effect = Exception("Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# DatasetQualityMetric Tests
# ============================================================================

class TestDatasetQualityMetric:
    """Test DatasetQualityMetric class."""

    def test_high_quality_dataset(self):
        """Test high quality dataset with long README, downloads, and keywords."""
        metric = DatasetQualityMetric()
        fetcher = Mock(spec=DataFetcher)
        long_readme = " ".join(["word"] * 900) + " license download split train test"
        fetcher.fetch_readme.return_value = long_readme
        fetcher.get_dataset_downloads.return_value = 150000

        score, latency = metric.calculate(fetcher)
        assert score > 0.5

    def test_low_quality_dataset(self):
        """Test low quality dataset."""
        metric = DatasetQualityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.return_value = "short readme"
        fetcher.get_dataset_downloads.return_value = 100

        score, latency = metric.calculate(fetcher)
        assert score < 0.5

    def test_dataset_quality_error(self):
        """Test error handling."""
        metric = DatasetQualityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.side_effect = Exception("Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# CodeQualityMetric Tests
# ============================================================================

class TestCodeQualityMetric:
    """Test CodeQualityMetric class."""

    def test_high_quality_code(self):
        """Test high quality code with stars, forks, long README, and recent updates."""
        metric = CodeQualityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_github_stats.return_value = {"stars": 15000, "forks": 6000}
        fetcher.fetch_readme.return_value = " ".join(["word"] * 2000)
        fetcher.is_recently_modified.return_value = True

        score, latency = metric.calculate(fetcher)
        assert score >= 0.4

    def test_low_quality_code(self):
        """Test low quality code."""
        metric = CodeQualityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_github_stats.return_value = {"stars": 5, "forks": 1}
        fetcher.fetch_readme.return_value = "short"
        fetcher.is_recently_modified.return_value = False

        score, latency = metric.calculate(fetcher)
        assert score < 0.3

    def test_code_quality_error(self):
        """Test error handling."""
        metric = CodeQualityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_github_stats.side_effect = Exception("Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# ReproducibilityMetric Tests (Phase 2)
# ============================================================================

class TestReproducibilityMetric:
    """Test ReproducibilityMetric class."""

    def test_reproducibility_with_code(self):
        """Test when demo code is present in model card."""
        metric = ReproducibilityMetric()
        fetcher = Mock(spec=DataFetcher)
        readme = """
        # Model Card

        ## Usage
        ```python
        from transformers import pipeline
        model = pipeline('text-generation', model='test/model')
        ```
        """
        fetcher.fetch_readme.return_value = readme

        score, latency = metric.calculate(fetcher)
        assert score == 0.5  # Found code but not tested
        assert latency >= 0

    def test_reproducibility_no_code(self):
        """Test when no demo code is present."""
        metric = ReproducibilityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.return_value = "This is a model without code examples"

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_reproducibility_error(self):
        """Test error handling."""
        metric = ReproducibilityMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.fetch_readme.side_effect = Exception("Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# ReviewednessMetric Tests (Phase 2)
# ============================================================================

class TestReviewednessMetric:
    """Test ReviewednessMetric class."""

    def test_reviewedness_no_repo(self):
        """Test when no GitHub repo is linked."""
        metric = ReviewednessMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = False

        score, latency = metric.calculate(fetcher)
        assert score == -1.0

    @patch('requests.get')
    def test_reviewedness_with_reviews(self, mock_get):
        """Test when commits have code reviews."""
        metric = ReviewednessMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = True
        fetcher.code_repo = ("owner", "repo")

        # Mock response with merge commits
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"commit": {"message": "Merge pull request #1"}, "parents": [{"sha": "a"}, {"sha": "b"}]},
            {"commit": {"message": "Regular commit"}, "parents": [{"sha": "c"}]},
            {"commit": {"message": "Merge PR #2"}, "parents": [{"sha": "d"}, {"sha": "e"}]},
        ]
        mock_get.return_value = mock_response

        score, latency = metric.calculate(fetcher)
        assert score > 0.0
        assert latency >= 0

    @patch('requests.get')
    def test_reviewedness_api_error(self, mock_get):
        """Test when GitHub API returns error."""
        metric = ReviewednessMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.return_value = True
        fetcher.code_repo = ("owner", "repo")

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_reviewedness_error(self):
        """Test error handling."""
        metric = ReviewednessMetric()
        fetcher = Mock(spec=DataFetcher)
        fetcher.has_code_url.side_effect = Exception("Error")

        score, latency = metric.calculate(fetcher)
        assert score == 0.0


# ============================================================================
# TreescoreMetric Tests (Phase 2)
# ============================================================================

class TestTreescoreMetric:
    """Test TreescoreMetric class."""

    def test_treescore_no_db(self):
        """Test when no database session is provided."""
        metric = TreescoreMetric()
        fetcher = Mock(spec=DataFetcher)

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_treescore_with_db_no_package_id(self):
        """Test when db session exists but no package ID."""
        db_session = Mock()
        metric = TreescoreMetric(db_session=db_session)
        fetcher = Mock(spec=DataFetcher)

        score, latency = metric.calculate(fetcher)
        assert score == 0.0

    def test_treescore_error(self):
        """Test error handling."""
        db_session = Mock()
        metric = TreescoreMetric(db_session=db_session, package_id="test-id")
        fetcher = Mock(spec=DataFetcher)

        # Simulate error in lineage query
        with patch('src.crud.package.get_package_lineage', side_effect=Exception("DB Error")):
            score, latency = metric.calculate(fetcher)
            assert score == 0.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestMetricIntegration:
    """Integration tests for all metrics."""

    def test_all_metrics_return_valid_scores(self):
        """Test that all metrics return scores in valid range."""
        fetcher = Mock(spec=DataFetcher)
        fetcher.get_license.return_value = "MIT"
        fetcher.get_model_size_gb.return_value = 1.0
        fetcher.fetch_readme.return_value = "test readme installation usage"
        fetcher.get_contributor_count.return_value = 10
        fetcher.has_code_url.return_value = True
        fetcher.has_dataset_url.return_value = True
        fetcher.get_dataset_downloads.return_value = 100000
        fetcher.get_github_stats.return_value = {"stars": 1000, "forks": 500}
        fetcher.is_recently_modified.return_value = True
        fetcher.code_repo = ("owner", "repo")

        metrics = [
            LicenseMetric(),
            SizeScoreMetric(),
            RampUpTimeMetric(),
            BusFactorMetric(),
            PerformanceClaimsMetric(),
            DatasetCodeScoreMetric(),
            DatasetQualityMetric(),
            CodeQualityMetric(),
            ReproducibilityMetric(),
            ReviewednessMetric(),
            TreescoreMetric()
        ]

        for metric in metrics:
            result, latency = metric.calculate(fetcher)
            # Size metric returns dict, others return float
            if isinstance(result, dict):
                assert all(0.0 <= v <= 1.0 for v in result.values())
            else:
                assert -1.0 <= result <= 1.0  # -1 is valid for Reviewedness
            assert latency >= 0

    def test_all_metrics_handle_errors_gracefully(self):
        """Test that all metrics handle errors without crashing."""
        fetcher = Mock(spec=DataFetcher)
        # Make all methods raise exceptions
        for attr in dir(fetcher):
            if not attr.startswith('_'):
                setattr(fetcher, attr, Mock(side_effect=Exception("Test error")))

        metrics = [
            LicenseMetric(),
            SizeScoreMetric(),
            RampUpTimeMetric(),
            BusFactorMetric(),
            PerformanceClaimsMetric(),
            DatasetCodeScoreMetric(),
            DatasetQualityMetric(),
            CodeQualityMetric(),
            ReproducibilityMetric(),
            ReviewednessMetric(),
            TreescoreMetric()
        ]

        for metric in metrics:
            # Should not raise exception
            result, latency = metric.calculate(fetcher)
            assert latency >= 0
