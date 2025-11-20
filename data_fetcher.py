"""
Data fetcher module for retrieving and caching API responses.
Handles HuggingFace and GitHub API interactions.
"""
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from huggingface_hub import HfApi, ModelInfo
from strip import strip_html, strip_markdown

logger = logging.getLogger(__name__)

# Check if Anthropic library is available for code testing
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class DataFetcher:
    """Unified data fetcher for all resource types with caching support."""

    def __init__(self, model_url: str = "", dataset_url: str = "", code_url: str = ""):
        self.model_url = model_url.rstrip("/")
        self.dataset_url = dataset_url.rstrip("/")
        self.code_url = code_url.rstrip("/")

        # API clients
        self.hf_api = HfApi()

        # Cache for API responses
        self._cache: Dict[str, Any] = {}

        # Extract identifiers
        self.model_id = self._extract_hf_id(model_url, "model")
        self.dataset_id = self._extract_hf_id(dataset_url, "dataset")
        self.code_repo = self._extract_github_repo(code_url)

        # Fetch metadata once
        self.model_metadata: Optional[ModelInfo] = self._fetch_model_metadata()

    def _extract_hf_id(self, url: str, resource_type: str) -> str:
        """Extract HuggingFace model or dataset ID from URL."""
        if not url or "huggingface.co" not in url:
            return ""

        if resource_type == "dataset":
            parts = url.split("huggingface.co/datasets/")
            return parts[1].replace("/tree/main", "").strip("/") if len(parts) > 1 else ""
        else:
            parts = url.split("huggingface.co/")
            return parts[1].replace("/tree/main", "").strip("/") if len(parts) > 1 else ""

    def _extract_github_repo(self, url: str) -> tuple[str, str]:
        """Extract GitHub owner and repo name from URL."""
        if not url or "github.com" not in url:
            return "", ""

        parts = url.rstrip("/").split("/")
        return (parts[-2], parts[-1]) if len(parts) >= 5 else ("", "")

    def _cache_get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        return self._cache.get(key)

    def _cache_set(self, key: str, value: Any) -> None:
        """Store value in cache."""
        self._cache[key] = value

    def _fetch_model_metadata(self) -> Optional[ModelInfo]:
        """Fetch HuggingFace model metadata with caching."""
        if not self.model_id:
            return None

        cache_key = f"model_metadata_{self.model_id}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            metadata = self.hf_api.model_info(self.model_id)
            self._cache_set(cache_key, metadata)
            logger.debug(f"Fetched model metadata for {self.model_id}")
            return metadata
        except Exception as e:
            logger.warning(f"Failed to fetch model metadata for {self.model_id}: {e}")
            return None

    def get_model_name(self) -> str:
        """Get model name from URL."""
        if self.model_id:
            return self.model_id.split("/")[-1]
        return ""

    def get_license(self) -> str:
        """
        Retrieve license information by downloading README locally.
        This satisfies the requirement to analyze files without using HuggingFace API.
        """
        cache_key = "license"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        license_name = ""

        # Download README.md from HuggingFace model directly (no API)
        if self.model_id:
            try:
                # Download raw README file (not using HuggingFace API)
                readme_url = f"https://huggingface.co/{self.model_id}/raw/main/README.md"
                response = requests.get(readme_url, timeout=10)

                if response.status_code == 200:
                    readme_content = response.text

                    # Parse license from YAML frontmatter
                    if readme_content.startswith("---"):
                        parts = readme_content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = parts[1]
                            # Look for license: line
                            for line in frontmatter.split("\n"):
                                if line.strip().startswith("license:"):
                                    license_name = line.split(":", 1)[1].strip()
                                    break

                    # If not found in frontmatter, search in README body
                    if not license_name:
                        lines = readme_content.lower().split("\n")
                        for i, line in enumerate(lines):
                            if "## license" in line or "# license" in line:
                                # Get next few lines after license heading
                                for j in range(i+1, min(i+5, len(lines))):
                                    if lines[j].strip():
                                        license_name = lines[j].strip()
                                        break
                                break

                    logger.debug(f"Downloaded and parsed license from README: {license_name}")
                else:
                    logger.debug(f"Could not download README for {self.model_id}")
            except Exception as e:
                logger.warning(f"Failed to download README for license parsing: {e}")

        # Fallback to GitHub if no model license found
        if not license_name and self.code_repo[0]:
            try:
                owner, repo = self.code_repo
                # Download LICENSE file directly (no API)
                license_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/LICENSE"
                response = requests.get(license_url, timeout=10)

                if response.status_code == 200:
                    license_content = response.text.lower()
                    # Detect license type from content
                    if "mit license" in license_content:
                        license_name = "MIT"
                    elif "apache license" in license_content:
                        license_name = "Apache-2.0"
                    elif "gnu general public license" in license_content:
                        if "version 3" in license_content:
                            license_name = "GPL-3.0"
                        else:
                            license_name = "GPL-2.0"
                    elif "bsd" in license_content:
                        license_name = "BSD"
                    logger.debug(f"Downloaded and parsed LICENSE file: {license_name}")
            except Exception as e:
                logger.warning(f"Failed to download LICENSE file: {e}")

        result = license_name if license_name else "Unknown"
        self._cache_set(cache_key, result)
        return result

    def get_model_size_gb(self) -> float:
        """Calculate total model size in GB from model files."""
        cache_key = "model_size"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not self.model_metadata:
            return 0.0

        total_bytes = 0
        file_extensions = (".bin", ".safetensors")

        try:
            for sibling in getattr(self.model_metadata, "siblings", []):
                filename = getattr(sibling, "rfilename", "")
                if filename.endswith(file_extensions):
                    file_url = f"{self.model_url}/resolve/main/{filename}"
                    try:
                        response = requests.head(file_url, timeout=15, allow_redirects=True)
                        size = int(response.headers.get("Content-Length", 0) or 0)
                        total_bytes += size
                    except Exception as e:
                        logger.debug(f"Could not fetch size for {filename}: {e}")

            size_gb = total_bytes / (1024**3)
            self._cache_set(cache_key, size_gb)
            logger.debug(f"Model size: {size_gb:.2f} GB")
            return size_gb
        except Exception as e:
            logger.warning(f"Error calculating model size: {e}")
            return 0.0

    def fetch_readme(self, resource_type: str) -> str:
        """Fetch and clean README content for specified resource type."""
        cache_key = f"readme_{resource_type}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        readme_text = ""

        try:
            if resource_type == "model" and self.model_metadata:
                card_data = getattr(self.model_metadata, "cardData", None)
                if card_data:
                    readme_text = card_data.get("readme", "")

            elif resource_type == "dataset" and self.dataset_id:
                try:
                    dataset_info = self.hf_api.dataset_info(self.dataset_id)
                    card_data = getattr(dataset_info, "cardData", None)
                    if card_data:
                        readme_text = card_data.get("readme", "")
                    logger.debug(f"Fetched dataset README for {self.dataset_id}")
                except Exception as e:
                    logger.debug(f"Could not fetch dataset README: {e}")

            elif resource_type == "code" and self.code_repo[0]:
                owner, repo = self.code_repo
                readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
                response = requests.get(readme_url, timeout=10)
                if response.status_code == 200:
                    readme_text = response.text
                logger.debug(f"Fetched code README for {owner}/{repo}")

            # Clean HTML and Markdown
            if readme_text:
                readme_text = strip_html(readme_text)
                readme_text = strip_markdown(readme_text)

        except Exception as e:
            logger.warning(f"Error fetching {resource_type} README: {e}")

        self._cache_set(cache_key, readme_text)
        return readme_text

    def get_github_stats(self) -> Dict[str, int]:
        """Get GitHub repository statistics (stars, forks)."""
        cache_key = "github_stats"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        default = {"stars": 0, "forks": 0}

        if not self.code_repo[0]:
            return default

        try:
            owner, repo = self.code_repo
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                result = {
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0)
                }
                self._cache_set(cache_key, result)
                logger.debug(f"Fetched GitHub stats for {owner}/{repo}")
                return result
            else:
                logger.warning(f"GitHub API returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"Error fetching GitHub stats: {e}")

        return default

    def get_contributor_count(self) -> int:
        """Get number of contributors from GitHub."""
        cache_key = "contributor_count"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not self.code_repo[0]:
            return 0

        try:
            owner, repo = self.code_repo
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                contributors = response.json()
                count = len(contributors)
                self._cache_set(cache_key, count)
                logger.debug(f"Fetched {count} contributors for {owner}/{repo}")
                return count
            else:
                logger.warning(f"GitHub contributors API returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"Error fetching contributors: {e}")

        return 0

    def get_dataset_downloads(self) -> int:
        """Get dataset download count from HuggingFace."""
        cache_key = "dataset_downloads"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not self.dataset_id:
            return 0

        try:
            dataset_info = self.hf_api.dataset_info(self.dataset_id)
            downloads = getattr(dataset_info, "downloads", 0)
            self._cache_set(cache_key, downloads)
            logger.debug(f"Fetched {downloads} downloads for dataset {self.dataset_id}")
            return downloads
        except Exception as e:
            logger.warning(f"Error fetching dataset downloads: {e}")
            return 0

    def is_recently_modified(self, resource_type: str, days: int) -> bool:
        """Check if resource was modified within specified days."""
        cache_key = f"recently_modified_{resource_type}_{days}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        result = False

        try:
            if resource_type == "model" and self.model_metadata:
                last_modified = getattr(self.model_metadata, "lastModified", None)
                if last_modified:
                    date = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                    result = datetime.now(date.tzinfo) - date < timedelta(days=days)

            elif resource_type == "github" and self.code_repo[0]:
                owner, repo = self.code_repo
                api_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    commits = response.json()
                    if commits:
                        commit_date_str = commits[0]["commit"]["committer"]["date"]
                        commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                        result = datetime.now(commit_date.tzinfo) - commit_date < timedelta(days=days)
                        logger.debug(f"GitHub repo last modified check: {result}")

        except Exception as e:
            logger.warning(f"Error checking if {resource_type} recently modified: {e}")

        self._cache_set(cache_key, result)
        return result

    def has_code_url(self) -> bool:
        """Check if code URL is available."""
        return bool(self.code_repo[0])

    def has_dataset_url(self) -> bool:
        """Check if dataset URL is available."""
        return bool(self.dataset_id)

    def get_pr_review_stats(self) -> tuple[int, int]:
        """
        Get pull request review statistics from GitHub repository.

        Returns:
            tuple: (reviewed_lines, total_lines) where reviewed_lines is the number
                   of lines added through reviewed PRs and total_lines is total lines
                   of code (excluding weights/model files).
        """
        cache_key = "pr_review_stats"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        if not self.code_repo[0]:
            return 0, 0

        try:
            owner, repo = self.code_repo
            reviewed_lines = 0
            total_lines = 0

            # Get all pull requests (merged)
            pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed&per_page=100"
            response = requests.get(pr_url, timeout=15)

            if response.status_code == 200:
                prs = response.json()

                # Count lines from reviewed PRs
                for pr in prs:
                    if pr.get("merged_at"):  # Only count merged PRs
                        additions = pr.get("additions", 0)
                        net_lines = additions  # Count additions as new code

                        total_lines += net_lines

                        # Check if PR had reviews
                        pr_number = pr.get("number")
                        review_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
                        review_response = requests.get(review_url, timeout=10)

                        if review_response.status_code == 200:
                            reviews = review_response.json()
                            if reviews:  # PR had at least one review
                                reviewed_lines += net_lines

                logger.debug(f"PR review stats: {reviewed_lines}/{total_lines} lines reviewed")

            # If no PRs found, estimate from direct commits
            if total_lines == 0:
                # Get total lines of code in repository (excluding binary/model files)
                total_lines = self._estimate_total_code_lines()

                # Assume no code review if no PRs
                reviewed_lines = 0

            result = (reviewed_lines, total_lines)
            self._cache_set(cache_key, result)
            return result

        except Exception as e:
            logger.warning(f"Error fetching PR review stats: {e}")
            return 0, 0

    def _estimate_total_code_lines(self) -> int:
        """
        Estimate total lines of code in repository using GitHub API.

        Returns:
            int: Estimated total lines of code
        """
        if not self.code_repo[0]:
            return 0

        try:
            owner, repo = self.code_repo
            # Use GitHub's languages endpoint to get code size estimates
            lang_url = f"https://api.github.com/repos/{owner}/{repo}/languages"
            response = requests.get(lang_url, timeout=10)

            if response.status_code == 200:
                languages = response.json()
                # Sum bytes of all languages, rough estimate: 50 chars per line average
                total_bytes = sum(languages.values())
                estimated_lines = total_bytes // 50
                logger.debug(f"Estimated {estimated_lines} lines of code")
                return estimated_lines

        except Exception as e:
            logger.warning(f"Error estimating code lines: {e}")

        return 0

    def extract_model_card_code(self) -> list[str]:
        """
        Extract code snippets from model card README.

        Returns:
            list[str]: List of code snippets found in markdown code blocks
        """
        cache_key = "model_card_code"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        code_snippets = []

        try:
            # Get raw README content (before stripping)
            if not self.model_id:
                return []

            readme_url = f"https://huggingface.co/{self.model_id}/raw/main/README.md"
            response = requests.get(readme_url, timeout=10)

            if response.status_code == 200:
                readme_content = response.text

                # Extract code blocks (```python ... ```)
                import re
                # Match code blocks with optional language specifier
                pattern = r'```(?:python|py)?\n(.*?)```'
                matches = re.findall(pattern, readme_content, re.DOTALL)

                code_snippets = [match.strip() for match in matches if match.strip()]
                logger.debug(f"Extracted {len(code_snippets)} code snippets from model card")

        except Exception as e:
            logger.warning(f"Error extracting model card code: {e}")

        self._cache_set(cache_key, code_snippets)
        return code_snippets

    def test_code_execution(self, code_snippets: list[str]) -> tuple[bool, bool]:
        """
        Test if code snippets can execute successfully.

        Args:
            code_snippets: List of code snippets to test

        Returns:
            tuple: (can_run, needs_debugging)
                   - can_run: True if code runs without critical errors
                   - needs_debugging: True if code needed fixes to run
        """
        if not code_snippets:
            return False, False

        try:
            # Use Claude API to analyze if code would run
            # This is a static analysis approach using AI
            import os
            api_key = os.environ.get("ANTHROPIC_API_KEY")

            if not api_key or not ANTHROPIC_AVAILABLE:
                # Fallback: simple heuristic check
                return self._heuristic_code_check(code_snippets)

            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)

            # Combine code snippets
            combined_code = "\n\n".join(code_snippets)

            prompt = f"""Analyze if this code from a model card would run successfully.
Rate it as one of:
- RUNS_CLEAN: Code will run without any modifications
- RUNS_WITH_DEBUG: Code will run but needs minor fixes (missing imports, typos, etc.)
- DOES_NOT_RUN: Code has critical errors or is incomplete

Code:
{combined_code[:2000]}

Respond with ONLY one of: RUNS_CLEAN, RUNS_WITH_DEBUG, DOES_NOT_RUN"""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}]
            )

            result = message.content[0].text.strip()

            if "RUNS_CLEAN" in result:
                return True, False
            elif "RUNS_WITH_DEBUG" in result:
                return True, True
            else:
                return False, False

        except Exception as e:
            logger.warning(f"Error testing code execution: {e}")
            # Fallback to heuristic
            return self._heuristic_code_check(code_snippets)

    def _heuristic_code_check(self, code_snippets: list[str]) -> tuple[bool, bool]:
        """
        Simple heuristic check for code quality when AI is unavailable.

        Args:
            code_snippets: List of code snippets

        Returns:
            tuple: (can_run, needs_debugging)
        """
        if not code_snippets:
            return False, False

        # Check for common issues
        combined_code = "\n".join(code_snippets)

        # Positive indicators
        has_imports = "import " in combined_code or "from " in combined_code
        has_function_calls = "(" in combined_code and ")" in combined_code

        # Negative indicators
        has_placeholder = "..." in combined_code or "TODO" in combined_code
        has_incomplete = combined_code.count("(") != combined_code.count(")")

        if has_placeholder or has_incomplete:
            return False, False  # Doesn't run
        elif has_imports and has_function_calls:
            return True, False  # Likely runs clean
        elif has_function_calls:
            return True, True  # Might run with debugging
        else:
            return False, False  # Doesn't run

    def get_parent_model_ids(self) -> list[str]:
        """
        Extract parent model IDs from config.json lineage information.

        Returns:
            list[str]: List of parent model IDs
        """
        cache_key = "parent_model_ids"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        parent_ids = []

        try:
            if not self.model_id:
                return []

            # Download config.json from HuggingFace
            config_url = f"https://huggingface.co/{self.model_id}/raw/main/config.json"
            response = requests.get(config_url, timeout=10)

            if response.status_code == 200:
                config = response.json()

                # Look for common parent/base model fields
                # Different model types use different field names
                potential_fields = [
                    "_name_or_path",
                    "base_model",
                    "parent_model",
                    "pretrained_model_name_or_path",
                    "model_name_or_path"
                ]

                for field in potential_fields:
                    value = config.get(field)
                    if value and isinstance(value, str):
                        # Check if it looks like a HuggingFace model ID
                        if "/" in value or value.startswith("bert") or value.startswith("gpt"):
                            if value not in parent_ids:
                                parent_ids.append(value)

                logger.debug(f"Found {len(parent_ids)} parent models: {parent_ids}")

        except Exception as e:
            logger.warning(f"Error extracting parent model IDs: {e}")

        self._cache_set(cache_key, parent_ids)
        return parent_ids
