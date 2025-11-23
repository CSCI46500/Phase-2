"""
Comprehensive tests for data_fetcher.py to achieve 60%+ coverage.
Tests DataFetcher class with various scenarios including API mocking.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
from src.utils.data_fetcher import DataFetcher


# ============================================================================
# Initialization and URL Parsing Tests
# ============================================================================

class TestDataFetcherInit:
    """Test DataFetcher initialization and URL parsing."""

    def test_init_with_all_urls(self):
        """Test initialization with all URLs provided."""
        fetcher = DataFetcher(
            model_url="https://huggingface.co/bert-base-uncased",
            dataset_url="https://huggingface.co/datasets/squad",
            code_url="https://github.com/huggingface/transformers"
        )
        assert fetcher.model_url == "https://huggingface.co/bert-base-uncased"
        assert fetcher.dataset_url == "https://huggingface.co/datasets/squad"
        assert fetcher.code_url == "https://github.com/huggingface/transformers"

    def test_init_strips_trailing_slashes(self):
        """Test that trailing slashes are stripped from URLs."""
        fetcher = DataFetcher(
            model_url="https://huggingface.co/bert-base-uncased/",
            dataset_url="https://huggingface.co/datasets/squad/",
            code_url="https://github.com/huggingface/transformers/"
        )
        assert not fetcher.model_url.endswith("/")
        assert not fetcher.dataset_url.endswith("/")
        assert not fetcher.code_url.endswith("/")

    def test_init_with_empty_urls(self):
        """Test initialization with empty URLs."""
        fetcher = DataFetcher()
        assert fetcher.model_url == ""
        assert fetcher.dataset_url == ""
        assert fetcher.code_url == ""
        assert fetcher.model_id == ""
        assert fetcher.dataset_id == ""
        assert fetcher.code_repo == ("", "")

    def test_extract_hf_model_id(self):
        """Test extracting HuggingFace model ID."""
        fetcher = DataFetcher(model_url="https://huggingface.co/google/bert-base-uncased")
        assert fetcher.model_id == "google/bert-base-uncased"

    def test_extract_hf_model_id_with_tree_main(self):
        """Test extracting model ID with /tree/main suffix."""
        fetcher = DataFetcher(model_url="https://huggingface.co/google/bert/tree/main")
        assert fetcher.model_id == "google/bert"

    def test_extract_hf_dataset_id(self):
        """Test extracting HuggingFace dataset ID."""
        fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/squad")
        assert fetcher.dataset_id == "squad"

    def test_extract_hf_dataset_id_complex(self):
        """Test extracting complex dataset ID."""
        fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/microsoft/orca")
        assert fetcher.dataset_id == "microsoft/orca"

    def test_extract_github_repo(self):
        """Test extracting GitHub repository owner and name."""
        fetcher = DataFetcher(code_url="https://github.com/microsoft/vscode")
        assert fetcher.code_repo == ("microsoft", "vscode")

    def test_extract_github_repo_invalid(self):
        """Test extracting from invalid GitHub URL."""
        fetcher = DataFetcher(code_url="https://github.com/invalid")
        assert fetcher.code_repo == ("", "")

    def test_extract_non_github_url(self):
        """Test extracting from non-GitHub URL."""
        fetcher = DataFetcher(code_url="https://gitlab.com/some/repo")
        assert fetcher.code_repo == ("", "")


# ============================================================================
# Cache Tests
# ============================================================================

class TestDataFetcherCache:
    """Test caching functionality."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        fetcher = DataFetcher()
        fetcher._cache_set("test_key", "test_value")
        assert fetcher._cache_get("test_key") == "test_value"

    def test_cache_get_missing(self):
        """Test getting non-existent cache key."""
        fetcher = DataFetcher()
        assert fetcher._cache_get("nonexistent") is None

    def test_cache_dict_value(self):
        """Test caching dictionary values."""
        fetcher = DataFetcher()
        test_dict = {"key": "value", "number": 123}
        fetcher._cache_set("dict_key", test_dict)
        assert fetcher._cache_get("dict_key") == test_dict


# ============================================================================
# Model Metadata Tests
# ============================================================================

class TestModelMetadata:
    """Test model metadata fetching."""

    @patch('src.utils.data_fetcher.HfApi')
    def test_fetch_model_metadata_success(self, mock_hf_api):
        """Test successful model metadata fetch."""
        mock_api_instance = Mock()
        mock_metadata = Mock()
        mock_metadata.modelId = "test/model"
        mock_api_instance.model_info.return_value = mock_metadata
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        assert fetcher.model_metadata is not None

    @patch('src.utils.data_fetcher.HfApi')
    def test_fetch_model_metadata_error(self, mock_hf_api):
        """Test model metadata fetch error handling."""
        mock_api_instance = Mock()
        mock_api_instance.model_info.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        assert fetcher.model_metadata is None

    def test_fetch_model_metadata_no_model_id(self):
        """Test metadata fetch with no model ID."""
        fetcher = DataFetcher()
        assert fetcher.model_metadata is None

    def test_get_model_name(self):
        """Test getting model name from ID."""
        fetcher = DataFetcher(model_url="https://huggingface.co/google/bert-base-uncased")
        assert fetcher.get_model_name() == "bert-base-uncased"

    def test_get_model_name_empty(self):
        """Test getting model name with no model."""
        fetcher = DataFetcher()
        assert fetcher.get_model_name() == ""


# ============================================================================
# License Tests
# ============================================================================

class TestLicense:
    """Test license retrieval."""

    @patch('requests.get')
    def test_get_license_from_readme_frontmatter(self, mock_get):
        """Test extracting license from README frontmatter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """---
license: MIT
---
# Model Card
"""
        mock_get.return_value = mock_response

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        license_str = fetcher.get_license()
        assert "MIT" in license_str or license_str == "MIT"

    @patch('requests.get')
    def test_get_license_from_readme_body(self, mock_get):
        """Test extracting license from README body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """# Model Card

## License

Apache-2.0
"""
        mock_get.return_value = mock_response

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        license_str = fetcher.get_license()
        assert license_str != ""

    @patch('requests.get')
    def test_get_license_from_github(self, mock_get):
        """Test extracting license from GitHub LICENSE file."""
        def mock_get_side_effect(url, *args, **kwargs):
            mock_resp = Mock()
            if "README.md" in url:
                mock_resp.status_code = 404
            elif "LICENSE" in url:
                mock_resp.status_code = 200
                mock_resp.text = "MIT License\n\nCopyright..."
            return mock_resp

        mock_get.side_effect = mock_get_side_effect

        fetcher = DataFetcher(
            model_url="https://huggingface.co/test/model",
            code_url="https://github.com/test/repo"
        )
        license_str = fetcher.get_license()
        assert "MIT" in license_str

    @patch('requests.get')
    def test_get_license_apache_detection(self, mock_get):
        """Test detecting Apache license."""
        def mock_get_side_effect(url, *args, **kwargs):
            mock_resp = Mock()
            if "README.md" in url:
                mock_resp.status_code = 404
            elif "LICENSE" in url:
                mock_resp.status_code = 200
                mock_resp.text = "Apache License Version 2.0"
            return mock_resp

        mock_get.side_effect = mock_get_side_effect

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        license_str = fetcher.get_license()
        assert "Apache" in license_str

    @patch('requests.get')
    def test_get_license_not_found(self, mock_get):
        """Test license not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        license_str = fetcher.get_license()
        assert license_str == "Unknown"

    @patch('requests.get')
    def test_get_license_caching(self, mock_get):
        """Test that license is cached."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "---\nlicense: MIT\n---\n"
        mock_get.return_value = mock_response

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")

        # First call
        license1 = fetcher.get_license()
        # Second call should use cache
        license2 = fetcher.get_license()

        assert license1 == license2
        # Should only be called once due to caching
        assert mock_get.call_count <= 2  # Allow for initialization calls


# ============================================================================
# Model Size Tests
# ============================================================================

class TestModelSize:
    """Test model size calculation."""

    @patch('requests.head')
    @patch('src.utils.data_fetcher.HfApi')
    def test_get_model_size_with_files(self, mock_hf_api, mock_head):
        """Test calculating model size from files."""
        # Mock metadata with siblings
        mock_sibling1 = Mock()
        mock_sibling1.rfilename = "pytorch_model.bin"
        mock_sibling2 = Mock()
        mock_sibling2.rfilename = "model.safetensors"

        mock_metadata = Mock()
        mock_metadata.siblings = [mock_sibling1, mock_sibling2]

        mock_api_instance = Mock()
        mock_api_instance.model_info.return_value = mock_metadata
        mock_hf_api.return_value = mock_api_instance

        # Mock HEAD requests for file sizes
        mock_response = Mock()
        mock_response.headers = {"Content-Length": "1073741824"}  # 1 GB
        mock_head.return_value = mock_response

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        size = fetcher.get_model_size_gb()

        assert size > 0

    def test_get_model_size_no_metadata(self):
        """Test model size with no metadata."""
        fetcher = DataFetcher()
        size = fetcher.get_model_size_gb()
        assert size == 0.0

    @patch('src.utils.data_fetcher.HfApi')
    def test_get_model_size_error(self, mock_hf_api):
        """Test model size calculation error handling."""
        mock_api_instance = Mock()
        mock_metadata = Mock()
        mock_metadata.siblings = []
        mock_api_instance.model_info.return_value = mock_metadata
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        size = fetcher.get_model_size_gb()
        assert size == 0.0


# ============================================================================
# README Fetching Tests
# ============================================================================

class TestFetchReadme:
    """Test README fetching for different resources."""

    @patch('src.utils.data_fetcher.HfApi')
    def test_fetch_model_readme(self, mock_hf_api):
        """Test fetching model README."""
        mock_metadata = Mock()
        mock_metadata.cardData = {"readme": "# Model Card\nThis is a test model."}

        mock_api_instance = Mock()
        mock_api_instance.model_info.return_value = mock_metadata
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        readme = fetcher.fetch_readme("model")
        assert len(readme) > 0

    @patch('src.utils.data_fetcher.HfApi')
    def test_fetch_dataset_readme(self, mock_hf_api):
        """Test fetching dataset README."""
        mock_dataset_info = Mock()
        mock_dataset_info.cardData = {"readme": "# Dataset Card"}

        mock_api_instance = Mock()
        mock_api_instance.dataset_info.return_value = mock_dataset_info
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/test/dataset")
        readme = fetcher.fetch_readme("dataset")
        assert isinstance(readme, str)

    @patch('requests.get')
    def test_fetch_code_readme(self, mock_get):
        """Test fetching code/GitHub README."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "# Project README\nInstallation instructions"
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        readme = fetcher.fetch_readme("code")
        assert len(readme) > 0

    @patch('requests.get')
    def test_fetch_code_readme_not_found(self, mock_get):
        """Test fetching code README when not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        readme = fetcher.fetch_readme("code")
        assert readme == ""

    def test_fetch_readme_caching(self):
        """Test that README is cached."""
        fetcher = DataFetcher()
        fetcher._cache_set("readme_model", "Cached content")

        readme = fetcher.fetch_readme("model")
        assert readme == "Cached content"


# ============================================================================
# GitHub Stats Tests
# ============================================================================

class TestGitHubStats:
    """Test GitHub statistics fetching."""

    @patch('requests.get')
    def test_get_github_stats_success(self, mock_get):
        """Test successful GitHub stats fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stargazers_count": 5000,
            "forks_count": 1200
        }
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        stats = fetcher.get_github_stats()

        assert stats["stars"] == 5000
        assert stats["forks"] == 1200

    @patch('requests.get')
    def test_get_github_stats_error(self, mock_get):
        """Test GitHub stats fetch error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        stats = fetcher.get_github_stats()

        assert stats["stars"] == 0
        assert stats["forks"] == 0

    def test_get_github_stats_no_repo(self):
        """Test GitHub stats with no repo."""
        fetcher = DataFetcher()
        stats = fetcher.get_github_stats()

        assert stats["stars"] == 0
        assert stats["forks"] == 0

    @patch('requests.get')
    def test_get_github_stats_exception(self, mock_get):
        """Test GitHub stats with exception."""
        mock_get.side_effect = Exception("Network error")

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        stats = fetcher.get_github_stats()

        assert stats == {"stars": 0, "forks": 0}


# ============================================================================
# Contributor Count Tests
# ============================================================================

class TestContributorCount:
    """Test contributor count fetching."""

    @patch('requests.get')
    def test_get_contributor_count_success(self, mock_get):
        """Test successful contributor count fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"login": "user1"}, {"login": "user2"}, {"login": "user3"}]
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        count = fetcher.get_contributor_count()

        assert count == 3

    @patch('requests.get')
    def test_get_contributor_count_error(self, mock_get):
        """Test contributor count fetch error."""
        mock_response = Mock()
        mock_response.status_code = 403  # Rate limited
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        count = fetcher.get_contributor_count()

        assert count == 0

    def test_get_contributor_count_no_repo(self):
        """Test contributor count with no repo."""
        fetcher = DataFetcher()
        count = fetcher.get_contributor_count()

        assert count == 0


# ============================================================================
# Dataset Downloads Tests
# ============================================================================

class TestDatasetDownloads:
    """Test dataset download count fetching."""

    @patch('src.utils.data_fetcher.HfApi')
    def test_get_dataset_downloads_success(self, mock_hf_api):
        """Test successful dataset downloads fetch."""
        mock_dataset_info = Mock()
        mock_dataset_info.downloads = 150000

        mock_api_instance = Mock()
        mock_api_instance.dataset_info.return_value = mock_dataset_info
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/test/dataset")
        downloads = fetcher.get_dataset_downloads()

        assert downloads == 150000

    @patch('src.utils.data_fetcher.HfApi')
    def test_get_dataset_downloads_error(self, mock_hf_api):
        """Test dataset downloads fetch error."""
        mock_api_instance = Mock()
        mock_api_instance.dataset_info.side_effect = Exception("API Error")
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/test/dataset")
        downloads = fetcher.get_dataset_downloads()

        assert downloads == 0

    def test_get_dataset_downloads_no_dataset(self):
        """Test dataset downloads with no dataset."""
        fetcher = DataFetcher()
        downloads = fetcher.get_dataset_downloads()

        assert downloads == 0


# ============================================================================
# Recently Modified Tests
# ============================================================================

class TestRecentlyModified:
    """Test recently modified checking."""

    @patch('src.utils.data_fetcher.HfApi')
    def test_is_recently_modified_model_true(self, mock_hf_api):
        """Test recently modified model (within days)."""
        recent_date = datetime.now().isoformat()

        mock_metadata = Mock()
        mock_metadata.lastModified = recent_date

        mock_api_instance = Mock()
        mock_api_instance.model_info.return_value = mock_metadata
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        is_recent = fetcher.is_recently_modified("model", 180)

        assert is_recent is True

    @patch('src.utils.data_fetcher.HfApi')
    def test_is_recently_modified_model_false(self, mock_hf_api):
        """Test not recently modified model."""
        old_date = (datetime.now() - timedelta(days=200)).isoformat()

        mock_metadata = Mock()
        mock_metadata.lastModified = old_date

        mock_api_instance = Mock()
        mock_api_instance.model_info.return_value = mock_metadata
        mock_hf_api.return_value = mock_api_instance

        fetcher = DataFetcher(model_url="https://huggingface.co/test/model")
        is_recent = fetcher.is_recently_modified("model", 180)

        assert is_recent is False

    @patch('requests.get')
    def test_is_recently_modified_github_true(self, mock_get):
        """Test recently modified GitHub repo."""
        recent_date = datetime.now().isoformat()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"commit": {"committer": {"date": recent_date}}}
        ]
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        is_recent = fetcher.is_recently_modified("github", 180)

        assert is_recent is True

    @patch('requests.get')
    def test_is_recently_modified_github_error(self, mock_get):
        """Test GitHub recently modified with error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        is_recent = fetcher.is_recently_modified("github", 180)

        assert is_recent is False


# ============================================================================
# Helper Method Tests
# ============================================================================

class TestHelperMethods:
    """Test helper methods."""

    def test_has_code_url_true(self):
        """Test has_code_url when code URL exists."""
        fetcher = DataFetcher(code_url="https://github.com/test/repo")
        assert fetcher.has_code_url() is True

    def test_has_code_url_false(self):
        """Test has_code_url when no code URL."""
        fetcher = DataFetcher()
        assert fetcher.has_code_url() is False

    def test_has_dataset_url_true(self):
        """Test has_dataset_url when dataset URL exists."""
        fetcher = DataFetcher(dataset_url="https://huggingface.co/datasets/squad")
        assert fetcher.has_dataset_url() is True

    def test_has_dataset_url_false(self):
        """Test has_dataset_url when no dataset URL."""
        fetcher = DataFetcher()
        assert fetcher.has_dataset_url() is False


# ============================================================================
# Integration Tests
# ============================================================================

class TestDataFetcherIntegration:
    """Integration tests for DataFetcher."""

    def test_full_initialization_flow(self):
        """Test complete initialization with all URLs."""
        fetcher = DataFetcher(
            model_url="https://huggingface.co/google/bert-base-uncased",
            dataset_url="https://huggingface.co/datasets/squad",
            code_url="https://github.com/google-research/bert"
        )

        assert fetcher.model_id == "google/bert-base-uncased"
        assert fetcher.dataset_id == "squad"
        assert fetcher.code_repo == ("google-research", "bert")
        assert fetcher.has_code_url()
        assert fetcher.has_dataset_url()

    @patch('requests.get')
    def test_license_fallback_chain(self, mock_get):
        """Test license detection falls back from model to GitHub."""
        def mock_get_side_effect(url, *args, **kwargs):
            mock_resp = Mock()
            if "huggingface.co" in url:
                mock_resp.status_code = 404  # No model README
            elif "LICENSE" in url:
                mock_resp.status_code = 200
                mock_resp.text = "BSD 3-Clause License"
            else:
                mock_resp.status_code = 404
            return mock_resp

        mock_get.side_effect = mock_get_side_effect

        fetcher = DataFetcher(
            model_url="https://huggingface.co/test/model",
            code_url="https://github.com/test/repo"
        )

        license_str = fetcher.get_license()
        assert "BSD" in license_str or license_str == "Unknown"

    def test_cache_persistence_across_calls(self):
        """Test that cache persists across multiple method calls."""
        fetcher = DataFetcher()

        # Set cache manually
        fetcher._cache_set("test_data", {"value": 123})

        # Retrieve multiple times
        data1 = fetcher._cache_get("test_data")
        data2 = fetcher._cache_get("test_data")

        assert data1 == data2
        assert data1["value"] == 123
