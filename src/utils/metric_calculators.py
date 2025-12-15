"""
Individual metric calculator classes.
Each metric implements calculate() method returning (score, latency_ms).

Metrics follow proper scoring based on actual analysis:
- Score 0.0: Feature not present / cannot be evaluated
- Score 0.0-1.0: Proportional to actual quality
- No artificial inflation of scores
"""

import time
import logging
import os
import re
from typing import Dict, Tuple, Optional, List
from src.utils.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

# Try to import Anthropic for Claude API integration
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning(
        "Anthropic library not available. Install with: pip install anthropic"
    )


class LicenseMetric:
    """
    Evaluates license compatibility.

    Scoring:
    - 1.0: Has a recognized open source license
    - 0.0: No license or unrecognized license
    """

    ACCEPTED_LICENSES = [
        "mit",
        "apache",
        "apache-2.0",
        "bsd",
        "bsd-2-clause",
        "bsd-3-clause",
        "gpl",
        "gpl-2.0",
        "gpl-3.0",
        "lgpl",
        "lgpl-2.1",
        "lgpl-3.0",
        "cc0",
        "cc-by",
        "cc-by-4.0",
        "cc-by-sa",
        "cc-by-sa-4.0",
        "unlicense",
        "public domain",
        "openrail",
        "openrail++",
        "bigscience-bloom-rail-1.0",
        "creativeml-openrail-m",
    ]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate license compatibility score."""
        start_time = time.time()

        try:
            license_str = fetcher.get_license()
            if not license_str:
                logger.debug("License score: 0.0 (no license found)")
                score = 0.0
            else:
                license_lower = license_str.lower()
                score = (
                    1.0
                    if any(lic in license_lower for lic in self.ACCEPTED_LICENSES)
                    else 0.0
                )
                logger.debug(f"License score: {score} (license: {license_str})")
        except Exception as e:
            logger.warning(f"Error calculating license metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class SizeScoreMetric:
    """
    Evaluates model size compatibility across hardware platforms.

    Scoring per platform:
    - 1.0: Model fits comfortably within platform limits
    - 0.0-1.0: Proportional score based on size vs limit
    - 0.0: Model too large for platform or size unknown
    """

    SIZE_THRESHOLDS_GB = {
        "raspberry_pi": 0.5,
        "jetson_nano": 1.0,
        "desktop_pc": 6.0,
        "aws_server": 15.0,
    }

    def calculate(self, fetcher: DataFetcher) -> Tuple[Dict[str, float], int]:
        """Calculate size compatibility scores for different platforms."""
        start_time = time.time()

        try:
            size_gb = fetcher.get_model_size_gb()

            if size_gb > 0:
                score_dict = {}
                for device, limit in self.SIZE_THRESHOLDS_GB.items():
                    if size_gb <= limit:
                        # Model fits: score based on how much room is left
                        ratio = size_gb / limit
                        score = 1.0 - (ratio * 0.3)  # Up to 30% penalty at limit
                    else:
                        # Model doesn't fit: decay based on how much over
                        over_ratio = size_gb / limit
                        score = max(0.0, 1.0 - (over_ratio - 1.0) * 0.5)
                    score_dict[device] = round(min(max(0.0, score), 1.0), 2)
                logger.debug(f"Size scores: {score_dict} (size: {size_gb:.2f} GB)")
            else:
                # Size unknown - return 0 (we cannot evaluate)
                logger.debug("Size score: 0.0 for all platforms (size unknown)")
                score_dict = {device: 0.0 for device in self.SIZE_THRESHOLDS_GB.keys()}

        except Exception as e:
            logger.warning(f"Error calculating size metric: {e}")
            score_dict = {device: 0.0 for device in self.SIZE_THRESHOLDS_GB.keys()}

        latency_ms = int((time.time() - start_time) * 1000)
        return score_dict, latency_ms


class RampUpTimeMetric:
    """
    Evaluates ease of getting started based on documentation quality.

    Scoring:
    - 1.0: Excellent documentation with installation, usage, examples
    - 0.5-0.9: Good documentation with some sections
    - 0.1-0.4: Minimal documentation
    - 0.0: No README or empty documentation
    """

    RAMP_UP_SECTIONS = [
        "install",
        "installation",
        "setup",
        "usage",
        "example",
        "quickstart",
        "quick start",
        "getting started",
        "how to use",
        "tutorial",
    ]

    CODE_INDICATORS = [
        "```python",
        "```py",
        "```bash",
        "```shell",
        "pip install",
        "from transformers",
        "import torch",
    ]

    def _analyze_with_llm_service(self, readme_text: str) -> Optional[float]:
        """Use LLM service for comprehensive analysis."""
        try:
            from src.services.llm_readme_analyzer import get_llm_analyzer

            analyzer = get_llm_analyzer()
            result = analyzer.analyze_readme_quality(readme_text)

            if result.success and result.confidence > 0.5:
                logger.debug(
                    f"LLM analysis: score={result.score}, confidence={result.confidence}"
                )
                return result.score
            return None

        except Exception as e:
            logger.debug(f"LLM service unavailable: {e}")
            return None

    def _analyze_with_keywords(self, readme_text: str) -> float:
        """Keyword-based analysis of README quality."""
        readme_lower = readme_text.lower()

        # Count present sections
        sections_found = sum(
            1 for section in self.RAMP_UP_SECTIONS if section in readme_lower
        )

        # Check for code examples
        has_code = any(indicator in readme_lower for indicator in self.CODE_INDICATORS)

        # Calculate base score from sections (max 0.6 from sections)
        section_score = min(sections_found / 5, 0.6)

        # Bonus for code examples (up to 0.2)
        code_bonus = 0.2 if has_code else 0.0

        # Bonus for README length (up to 0.2)
        word_count = len(readme_text.split())
        if word_count >= 500:
            length_bonus = 0.2
        elif word_count >= 200:
            length_bonus = 0.15
        elif word_count >= 100:
            length_bonus = 0.1
        elif word_count >= 50:
            length_bonus = 0.05
        else:
            length_bonus = 0.0

        total_score = section_score + code_bonus + length_bonus
        return round(min(total_score, 1.0), 2)

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate ramp-up time score based on documentation."""
        start_time = time.time()

        try:
            # Try model README first (more common for HuggingFace models)
            readme_text = fetcher.fetch_readme("model")
            if not readme_text:
                logger.debug("No model README, trying code README")
                readme_text = fetcher.fetch_readme("code")

            if not readme_text or len(readme_text.strip()) < 20:
                logger.debug("No README found - ramp-up score: 0.0")
                return 0.0, int((time.time() - start_time) * 1000)

            # Try LLM service first
            llm_score = self._analyze_with_llm_service(readme_text)

            if llm_score is not None:
                final_score = round(llm_score, 2)
                logger.debug(f"Ramp-up score (LLM): {final_score}")
            else:
                # Fallback to keyword analysis
                final_score = self._analyze_with_keywords(readme_text)
                logger.debug(f"Ramp-up score (keywords): {final_score}")

        except Exception as e:
            logger.warning(f"Error calculating ramp-up metric: {e}")
            final_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return final_score, latency_ms


class BusFactorMetric:
    """
    Evaluates project sustainability through contributor diversity.

    Scoring (based on "bus factor" - risk if key people leave):
    - 1.0: 5+ contributors (low risk)
    - 0.8: 4 contributors
    - 0.6: 3 contributors
    - 0.4: 2 contributors
    - 0.2: 1 contributor (high risk)
    - 0.0: 0 contributors or unknown
    """

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate bus factor score based on contributor count."""
        start_time = time.time()

        try:
            num_contributors = fetcher.get_contributor_count()

            if num_contributors >= 5:
                score = 1.0
            elif num_contributors == 4:
                score = 0.8
            elif num_contributors == 3:
                score = 0.6
            elif num_contributors == 2:
                score = 0.4
            elif num_contributors == 1:
                score = 0.2
            else:
                score = 0.0

            logger.debug(f"Bus factor score: {score} ({num_contributors} contributors)")
        except Exception as e:
            logger.warning(f"Error calculating bus factor metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class PerformanceClaimsMetric:
    """
    Evaluates presence and quality of performance benchmarks and claims.

    Scoring:
    - 1.0: Has quantitative benchmarks with datasets mentioned
    - 0.7: Has performance keywords with some numbers
    - 0.4: Has performance keywords but no numbers
    - 0.0: No performance information found
    """

    PERFORMANCE_KEYWORDS = [
        "accuracy", "benchmark", "perplexity", "performance",
        "f1", "precision", "recall", "bleu", "rouge",
        "evaluation", "metrics", "results", "score"
    ]

    BENCHMARK_DATASETS = [
        "squad", "glue", "superglue", "imagenet", "coco",
        "wmt", "conll", "mnli", "sst", "qqp", "mrpc"
    ]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate performance claims score."""
        start_time = time.time()

        try:
            # Get README content
            model_readme = fetcher.fetch_readme("model") or ""
            code_readme = fetcher.fetch_readme("code") or ""
            combined_text = (model_readme + " " + code_readme).lower()

            if not combined_text.strip():
                logger.debug("Performance claims score: 0.0 (no README)")
                return 0.0, int((time.time() - start_time) * 1000)

            # Check for performance keywords
            perf_keywords_found = sum(
                1 for kw in self.PERFORMANCE_KEYWORDS if kw in combined_text
            )

            # Check for benchmark dataset mentions
            has_benchmark_dataset = any(
                ds in combined_text for ds in self.BENCHMARK_DATASETS
            )

            # Check for quantitative numbers (percentages, decimals)
            has_numbers = bool(re.search(r'\d+\.?\d*\s*%|\d+\.\d+', combined_text))

            # Calculate score
            if perf_keywords_found >= 3 and has_benchmark_dataset and has_numbers:
                score = 1.0
            elif perf_keywords_found >= 2 and has_numbers:
                score = 0.7
            elif perf_keywords_found >= 1:
                score = 0.4
            else:
                score = 0.0

            logger.debug(
                f"Performance claims score: {score} "
                f"(keywords={perf_keywords_found}, benchmarks={has_benchmark_dataset}, numbers={has_numbers})"
            )
        except Exception as e:
            logger.warning(f"Error calculating performance claims metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class DatasetCodeScoreMetric:
    """
    Evaluates availability of dataset and code resources.

    Scoring:
    - 1.0: Both dataset and code URLs provided
    - 0.5: Only code URL provided
    - 0.3: Only dataset URL provided
    - 0.0: Neither provided
    """

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate dataset and code availability score."""
        start_time = time.time()

        try:
            has_code = fetcher.has_code_url()
            has_dataset = fetcher.has_dataset_url()

            if has_code and has_dataset:
                score = 1.0
            elif has_code:
                score = 0.5  # Code is more valuable for reproducibility
            elif has_dataset:
                score = 0.3
            else:
                score = 0.0

            logger.debug(
                f"Dataset/Code score: {score} (code={has_code}, dataset={has_dataset})"
            )
        except Exception as e:
            logger.warning(f"Error calculating dataset/code metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class DatasetQualityMetric:
    """
    Evaluates dataset quality based on documentation and metadata.

    Scoring components:
    - README quality (0-0.4): Based on length and keywords
    - Download popularity (0-0.3): Based on download count
    - Metadata completeness (0-0.3): Based on key fields
    """

    QUALITY_KEYWORDS = [
        "license", "citation", "download", "split", "train",
        "test", "validation", "size", "samples", "examples",
        "format", "columns", "features"
    ]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate dataset quality score."""
        start_time = time.time()

        try:
            # Check if dataset exists
            if not fetcher.has_dataset_url():
                logger.debug("Dataset quality score: 0.0 (no dataset)")
                return 0.0, int((time.time() - start_time) * 1000)

            # README quality component (0-0.4)
            dataset_readme = fetcher.fetch_readme("dataset") or ""
            readme_words = len(dataset_readme.split())

            if readme_words >= 300:
                readme_score = 0.4
            elif readme_words >= 150:
                readme_score = 0.3
            elif readme_words >= 50:
                readme_score = 0.2
            elif readme_words >= 20:
                readme_score = 0.1
            else:
                readme_score = 0.0

            # Download count component (0-0.3)
            downloads = fetcher.get_dataset_downloads()
            if downloads >= 10000:
                download_score = 0.3
            elif downloads >= 1000:
                download_score = 0.25
            elif downloads >= 100:
                download_score = 0.15
            elif downloads >= 10:
                download_score = 0.1
            else:
                download_score = 0.0

            # Keyword/metadata component (0-0.3)
            readme_lower = dataset_readme.lower()
            keywords_found = sum(
                1 for kw in self.QUALITY_KEYWORDS if kw in readme_lower
            )
            keyword_score = min(keywords_found / 10, 0.3)

            total_score = round(readme_score + download_score + keyword_score, 2)
            logger.debug(
                f"Dataset quality score: {total_score} "
                f"(readme={readme_score}, downloads={download_score}, keywords={keyword_score})"
            )

        except Exception as e:
            logger.warning(f"Error calculating dataset quality metric: {e}")
            total_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return total_score, latency_ms


class CodeQualityMetric:
    """
    Evaluates code repository quality and maintenance.

    Scoring components:
    - GitHub engagement (0-0.35): Stars and forks
    - README quality (0-0.35): Documentation quality
    - Maintenance (0-0.3): Recent activity
    """

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate code quality score."""
        start_time = time.time()

        try:
            # Check if code repository exists
            if not fetcher.has_code_url():
                logger.debug("Code quality score: 0.0 (no code repository)")
                return 0.0, int((time.time() - start_time) * 1000)

            # GitHub engagement score (0-0.35)
            stats = fetcher.get_github_stats()
            stars = stats.get("stars", 0)
            forks = stats.get("forks", 0)

            if stars >= 1000:
                star_score = 0.2
            elif stars >= 100:
                star_score = 0.15
            elif stars >= 10:
                star_score = 0.1
            elif stars >= 1:
                star_score = 0.05
            else:
                star_score = 0.0

            if forks >= 100:
                fork_score = 0.15
            elif forks >= 10:
                fork_score = 0.1
            elif forks >= 1:
                fork_score = 0.05
            else:
                fork_score = 0.0

            engagement_score = star_score + fork_score

            # README quality (0-0.35)
            code_readme = fetcher.fetch_readme("code") or ""
            readme_words = len(code_readme.split())

            if readme_words >= 500:
                readme_score = 0.35
            elif readme_words >= 200:
                readme_score = 0.25
            elif readme_words >= 100:
                readme_score = 0.15
            elif readme_words >= 50:
                readme_score = 0.1
            else:
                readme_score = 0.0

            # Maintenance score (0-0.3)
            # Check for recent activity (within different timeframes)
            if fetcher.is_recently_modified("github", 90):  # 90 days
                maintenance_score = 0.3
            elif fetcher.is_recently_modified("github", 365):  # 1 year
                maintenance_score = 0.2
            elif fetcher.is_recently_modified("github", 730):  # 2 years
                maintenance_score = 0.1
            else:
                maintenance_score = 0.0

            total_score = round(engagement_score + readme_score + maintenance_score, 2)
            logger.debug(
                f"Code quality score: {total_score} "
                f"(engagement={engagement_score}, readme={readme_score}, maintenance={maintenance_score})"
            )

        except Exception as e:
            logger.warning(f"Error calculating code quality metric: {e}")
            total_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return total_score, latency_ms


class ReproducibilityMetric:
    """
    Evaluates whether the model can be run using only the demo code in the model card.

    Scoring:
    - 1.0: Demo code runs without errors
    - 0.5: Demo code has fixable errors (missing imports, etc.)
    - 0.2: Demo code exists but has unfixable errors
    - 0.0: No demo code provided
    """

    CODE_INDICATORS = [
        "```python",
        "```py",
        "from transformers",
        "import torch",
        "pipeline(",
        "AutoModel",
        "AutoTokenizer",
    ]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate reproducibility score based on model card demo code."""
        start_time = time.time()

        try:
            readme_text = fetcher.fetch_readme("model") or ""

            if not readme_text:
                logger.debug("Reproducibility score: 0.0 (no model card)")
                return 0.0, int((time.time() - start_time) * 1000)

            readme_lower = readme_text.lower()

            # Check for code indicators
            has_code = any(
                indicator.lower() in readme_lower
                for indicator in self.CODE_INDICATORS
            )

            if not has_code:
                logger.debug("Reproducibility score: 0.0 (no demo code found)")
                return 0.0, int((time.time() - start_time) * 1000)

            # Extract Python code blocks
            code_blocks = self._extract_code_blocks(readme_text)

            if not code_blocks:
                # Has indicators but no extractable code blocks
                logger.debug("Reproducibility score: 0.2 (code indicators but no blocks)")
                return 0.2, int((time.time() - start_time) * 1000)

            # Test code execution
            score = self._test_code_execution(code_blocks[0])
            logger.debug(f"Reproducibility score: {score} (code execution tested)")

        except Exception as e:
            logger.warning(f"Error calculating reproducibility metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms

    def _extract_code_blocks(self, readme_text: str) -> List[str]:
        """Extract Python code blocks from README markdown."""
        pattern = r"```(?:python|py)\s*\n(.*?)```"
        matches = re.findall(pattern, readme_text, re.DOTALL | re.IGNORECASE)

        # Filter for substantial code blocks (at least 2 lines)
        substantial_blocks = [
            block.strip() for block in matches
            if len(block.strip().split("\n")) >= 2
        ]

        return substantial_blocks

    def _test_code_execution(self, code: str) -> float:
        """
        Test if code executes successfully.

        Returns:
        - 1.0: Runs without errors
        - 0.5: Has fixable errors (missing modules, etc.)
        - 0.2: Has unfixable errors
        """
        import subprocess
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # Syntax is valid - try actual execution with short timeout
                    exec_result = subprocess.run(
                        ["python3", temp_file],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )

                    if exec_result.returncode == 0:
                        return 1.0

                    # Check for fixable errors
                    error_output = exec_result.stderr.lower()
                    fixable_patterns = [
                        "no module named",
                        "importerror",
                        "modulenotfounderror",
                    ]

                    if any(p in error_output for p in fixable_patterns):
                        return 0.5
                    return 0.2
                else:
                    # Syntax error
                    return 0.2

            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        except subprocess.TimeoutExpired:
            return 0.5  # Might work with more time
        except Exception as e:
            logger.debug(f"Code execution test error: {e}")
            return 0.2


class ReviewednessMetric:
    """
    Evaluates the fraction of code introduced through pull requests with code review.

    Scoring:
    - -1.0: No linked GitHub repository (excluded from net score)
    - 0.0-1.0: Fraction of commits from merged PRs
    """

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate reviewedness score from GitHub repository."""
        start_time = time.time()

        try:
            import requests

            if not fetcher.has_code_url():
                logger.debug("Reviewedness score: -1 (no GitHub repo)")
                return -1.0, int((time.time() - start_time) * 1000)

            owner, repo = fetcher.code_repo

            # Get GitHub token if available
            github_token = os.environ.get("GITHUB_TOKEN")
            headers = {}
            if github_token:
                headers["Authorization"] = f"token {github_token}"

            # Fetch commits
            commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=100"
            response = requests.get(commits_url, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Failed to fetch commits: {response.status_code}")
                return 0.0, int((time.time() - start_time) * 1000)

            commits = response.json()
            total_commits = len(commits)

            if total_commits == 0:
                return 0.0, int((time.time() - start_time) * 1000)

            # Count merge commits (from PRs)
            reviewed_commits = 0
            for commit in commits:
                message = commit.get("commit", {}).get("message", "").lower()
                parents = commit.get("parents", [])

                is_merge = (
                    "merge pull request" in message
                    or "merge pr" in message
                    or len(parents) > 1
                )

                if is_merge:
                    reviewed_commits += 1

            score = round(reviewed_commits / total_commits, 2)
            logger.debug(
                f"Reviewedness score: {score} ({reviewed_commits}/{total_commits} reviewed)"
            )

        except Exception as e:
            logger.warning(f"Error calculating reviewedness metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class TreescoreMetric:
    """
    Evaluates the average net_score of all parent models in the lineage graph.

    Scoring:
    - Average of parent models' net_scores
    - 0.0 if no parents exist
    """

    def __init__(self, db_session=None, package_id=None):
        """Initialize with database context for lineage queries."""
        self.db_session = db_session
        self.package_id = package_id

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate treescore based on parent model scores."""
        start_time = time.time()

        try:
            if not self.db_session or not self.package_id:
                logger.debug("Treescore: 0.0 (no database context)")
                return 0.0, int((time.time() - start_time) * 1000)

            from src.crud.package import get_package_lineage
            from src.core.models import Package
            from uuid import UUID

            lineage = get_package_lineage(self.db_session, self.package_id)
            parent_entries = [e for e in lineage if e.get("depth", 0) > 0]

            if not parent_entries:
                logger.debug("Treescore: 0.0 (no parent models)")
                return 0.0, int((time.time() - start_time) * 1000)

            parent_scores = []
            for entry in parent_entries:
                try:
                    parent_id = UUID(entry["id"])
                    parent = (
                        self.db_session.query(Package)
                        .filter(Package.id == parent_id)
                        .first()
                    )
                    if parent and parent.net_score is not None:
                        parent_scores.append(parent.net_score)
                except Exception as e:
                    logger.debug(f"Failed to get parent score: {e}")

            if parent_scores:
                score = round(sum(parent_scores) / len(parent_scores), 2)
                logger.debug(f"Treescore: {score} (avg of {len(parent_scores)} parents)")
            else:
                score = 0.0

        except Exception as e:
            logger.warning(f"Error calculating treescore: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms
