"""
Individual metric calculator classes.
Each metric implements calculate() method returning (score, latency_ms).
"""
import time
import logging
import os
from typing import Dict, Tuple
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

# Attempt to import the Anthropic library for AI-powered README analysis
# If unavailable, the RampUpTimeMetric will fall back to keyword-based analysis
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Install with: pip install anthropic")


class LicenseMetric:
    """Evaluates license compatibility.""" 

    # List of open-source licenses considered compatible and acceptable
    # Score of 1.0 is assigned if the package uses any of these licenses
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
        "unlicense",
        "public domain"
    ]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate license compatibility score."""
        start_time = time.time()

        try:
            license_str = fetcher.get_license().lower()
            score = 1.0 if any(lic in license_str for lic in self.ACCEPTED_LICENSES) else 0.0
            logger.debug(f"License score: {score} (license: {license_str})")
        except Exception as e:
            logger.warning(f"Error calculating license metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class SizeScoreMetric:
    """Evaluates model size compatibility across hardware platforms."""

    # Maximum model size (in GB) each platform can reasonably handle
    # Score decreases linearly as model size approaches these thresholds
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
                # Calculate compatibility score for each device using linear decay formula:
                # score = 1.0 - (model_size / threshold), clamped between 0.0 and 1.0
                score_dict = {
                    device: round(min(max(0.0, 1.0 - size_gb / limit), 1.0), 2)
                    for device, limit in self.SIZE_THRESHOLDS_GB.items()
                }
            else:
                # If size is unknown or invalid, assign 0.0 to all devices
                score_dict = {device: 0.0 for device in self.SIZE_THRESHOLDS_GB.keys()}

            logger.debug(f"Size scores: {score_dict} (size: {size_gb:.2f} GB)")
        except Exception as e:
            logger.warning(f"Error calculating size metric: {e}")
            score_dict = {device: 0.0 for device in self.SIZE_THRESHOLDS_GB.keys()}

        latency_ms = int((time.time() - start_time) * 1000)
        return score_dict, latency_ms


class RampUpTimeMetric:
    """
    Evaluates ease of getting started based on documentation quality.
    Uses Claude AI to analyze README when API key is available.
    Falls back to keyword-based analysis otherwise.
    """

    # Keywords indicating sections that help developers get started quickly
    # Presence of these sections in README indicates better documentation
    RAMP_UP_SECTIONS = [
        "install",
        "installation",
        "usage",
        "example",
        "quickstart",
        "quick start",
        "download",
        "how to use"
    ]

    # Minimum number of meaningful words in a section to consider it substantial
    MIN_WORDS_THRESHOLD = 50

    def _analyze_with_claude(self, readme_text: str) -> float:
        """
        Use Claude AI to intelligently analyze README quality and documentation.

        Returns:
            float: Score between 0.0-1.0 indicating documentation quality
            None: If API key is not available or analysis fails
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or not ANTHROPIC_AVAILABLE:
            return None

        try:
            client = Anthropic(api_key=api_key)
            prompt = f"""Analyze this README for ease of onboarding. Rate 0.0-1.0 based on installation instructions, examples, and documentation quality.

README: {readme_text[:4000]}

Respond with ONLY a number 0.0-1.0."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )

            score = float(message.content[0].text.strip())
            return max(0.0, min(1.0, score))

        except Exception:
            return None

    def _analyze_with_keywords(self, readme_text: str) -> float:
        """
        Fallback keyword-based analysis when Claude AI is unavailable.
        Searches for important documentation sections and evaluates their content depth.

        Returns:
            float: Average score (0.0-1.0) across all expected documentation sections
        """
        section_scores = []

        for section in self.RAMP_UP_SECTIONS:
            if section in readme_text:
                # Extract the text starting from this section keyword
                idx = readme_text.index(section) + len(section)
                after_text = readme_text[idx:]

                # Find where the next section starts to isolate this section's content
                next_idx = len(after_text)
                for next_section in self.RAMP_UP_SECTIONS:
                    ni = after_text.find(next_section)
                    if ni != -1 and ni < next_idx:
                        next_idx = ni

                section_content = after_text[:next_idx].split()
                # Remove common filler words that don't contribute to documentation value
                meaningful_words = [
                    w for w in section_content
                    if w not in ("more", "information", "see", "docs")
                ]
                # Score based on content depth: reaches 1.0 at MIN_WORDS_THRESHOLD
                score = min(len(meaningful_words) / self.MIN_WORDS_THRESHOLD, 1.0)
                section_scores.append(score)
            else:
                # Section not found in README
                section_scores.append(0.0)

        return round(sum(section_scores) / len(section_scores), 2) if section_scores else 0.0

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate ramp-up time score based on documentation."""
        start_time = time.time()

        try:
            readme_text = fetcher.fetch_readme("code")

            if not readme_text:
                logger.debug("No code README found for ramp-up calculation")
                return 0.0, int((time.time() - start_time) * 1000)

            # Attempt AI-powered analysis first for more accurate evaluation
            claude_score = self._analyze_with_claude(readme_text)

            if claude_score is not None:
                final_score = round(claude_score, 2)
                logger.debug(f"Ramp-up score (Claude): {final_score}")
            else:
                # Fall back to simpler keyword-based analysis if AI is unavailable
                final_score = self._analyze_with_keywords(readme_text.lower())
                logger.debug(f"Ramp-up score (keywords): {final_score}")

        except Exception as e:
            logger.warning(f"Error calculating ramp-up metric: {e}")
            final_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return final_score, latency_ms


class BusFactorMetric:
    """Evaluates project sustainability through contributor diversity."""

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate bus factor score based on contributor count."""
        start_time = time.time()

        try:
            num_contributors = fetcher.get_contributor_count()

            # Assign scores based on contributor count thresholds
            # Higher contributor count = better project resilience and bus factor
            if num_contributors >= 10:
                score = 1.0  # Excellent: many contributors reduce dependency on individuals
            elif num_contributors >= 7:
                score = 0.5  # Good: moderate contributor base
            elif num_contributors >= 5:
                score = 0.3  # Fair: minimal viable contributor diversity
            else:
                score = 0.0  # Poor: high risk if key contributors leave

            logger.debug(f"Bus factor score: {score} ({num_contributors} contributors)")
        except Exception as e:
            logger.warning(f"Error calculating bus factor metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class PerformanceClaimsMetric:
    """Evaluates presence of performance benchmarks and claims."""

    # Keywords indicating that performance metrics or benchmarks are documented
    PERFORMANCE_KEYWORDS = ["accuracy", "benchmark", "perplexity", "performance"]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate performance claims score based on keyword presence."""
        start_time = time.time()

        try:
            readme_text = fetcher.fetch_readme("code").lower()

            # Check if any performance-related keywords appear in the README
            has_perf_keywords = any(kw in readme_text for kw in self.PERFORMANCE_KEYWORDS)
            score = 1.0 if has_perf_keywords else 0.0  # Binary: either documented or not

            logger.debug(f"Performance claims score: {score}")
        except Exception as e:
            logger.warning(f"Error calculating performance claims metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class DatasetCodeScoreMetric:
    """Evaluates availability of dataset and code resources."""

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate dataset and code availability score."""
        start_time = time.time()

        try:
            has_code = fetcher.has_code_url()
            has_dataset = fetcher.has_dataset_url()

            # Average of two binary checks: code availability and dataset availability
            # Score of 1.0 if both present, 0.5 if only one, 0.0 if neither
            score = (float(has_code) + float(has_dataset)) / 2.0
            logger.debug(f"Dataset/Code score: {score} (code={has_code}, dataset={has_dataset})")
        except Exception as e:
            logger.warning(f"Error calculating dataset/code metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class DatasetQualityMetric:
    """Evaluates dataset quality based on documentation and popularity."""

    # Keywords that indicate a well-documented dataset with proper structure
    DATASET_KEYWORDS = ["license", "download", "split", "train", "test", "validation"]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate dataset quality score."""
        start_time = time.time()

        try:
            # Component 1: README documentation completeness (30% weight)
            readme_length = len(fetcher.fetch_readme("dataset").split())
            readme_score = 0.3 if readme_length >= 820 else 0.0

            # Component 2: Dataset popularity/usage (20% weight)
            downloads = fetcher.get_dataset_downloads()
            if downloads >= 100000:
                download_score = 0.2  # Very popular dataset
            elif downloads >= 50000:
                download_score = 0.15  # Moderately popular dataset
            else:
                download_score = 0.0  # Less established dataset

            # Component 3: Documentation structure and key information (50% weight)
            dataset_readme = fetcher.fetch_readme("dataset").lower()
            has_keywords = any(kw in dataset_readme for kw in self.DATASET_KEYWORDS)
            keyword_score = 0.5 if has_keywords else 0.0

            # Final score is sum of all components (max 1.0)
            total_score = readme_score + download_score + keyword_score
            logger.debug(f"Dataset quality score: {total_score}")
        except Exception as e:
            logger.warning(f"Error calculating dataset quality metric: {e}")
            total_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return total_score, latency_ms


class CodeQualityMetric:
    """Evaluates code repository quality and maintenance."""

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate code quality score."""
        start_time = time.time()

        try:
            # Component 1: Repository popularity indicators (20% weight total)
            stats = fetcher.get_github_stats()
            stars = stats.get("stars", 0)
            forks = stats.get("forks", 0)

            stats_score = 0.0
            if stars >= 10000:
                stats_score += 0.1  # High community interest
            if forks >= 5000:
                stats_score += 0.1  # Strong development activity

            # Component 2: Documentation quality (30% weight)
            readme_length = len(fetcher.fetch_readme("code").split())
            if readme_length >= 1700:
                readme_score = 0.3  # Comprehensive documentation
            elif readme_length >= 1000:
                readme_score = 0.2  # Adequate documentation
            else:
                readme_score = 0.0  # Insufficient documentation

            # Component 3: Active maintenance status (20% weight)
            # Checks if repository was updated within the last 180 days
            is_maintained = fetcher.is_recently_modified("github", 180)
            maintenance_score = 0.2 if is_maintained else 0.0

            # Final score is sum of all components (max 0.6)
            total_score = stats_score + readme_score + maintenance_score
            logger.debug(f"Code quality score: {total_score}")
        except Exception as e:
            logger.warning(f"Error calculating code quality metric: {e}")
            total_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return total_score, latency_ms


class ReviewednessMetric:
    """
    Evaluates the fraction of code introduced through pull requests with code review.
    Returns -1 if no GitHub repository is linked.
    """

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate reviewedness score based on PR code review coverage."""
        start_time = time.time()

        try:
            # Check if GitHub repository exists
            if not fetcher.has_code_url():
                logger.debug("No GitHub repository linked, returning -1 for reviewedness")
                return -1.0, int((time.time() - start_time) * 1000)

            # Get PR statistics from GitHub
            reviewed_lines, total_lines = fetcher.get_pr_review_stats()

            if total_lines == 0:
                # No code in repository or unable to fetch
                score = 0.0
            else:
                # Calculate fraction of reviewed code
                score = round(reviewed_lines / total_lines, 2)

            logger.debug(f"Reviewedness score: {score} ({reviewed_lines}/{total_lines} lines reviewed)")
        except Exception as e:
            logger.warning(f"Error calculating reviewedness metric: {e}")
            score = -1.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class ReproducibilityMetric:
    """
    Evaluates whether model can be run using demonstration code from model card.
    Scores: 0 (no code/doesn't run), 0.5 (runs with debugging), 1 (runs without changes).
    """

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate reproducibility score based on code execution."""
        start_time = time.time()

        try:
            # Extract code from model card README
            code_snippets = fetcher.extract_model_card_code()

            if not code_snippets:
                logger.debug("No code found in model card, reproducibility = 0")
                return 0.0, int((time.time() - start_time) * 1000)

            # Test if code can run
            can_run, needs_debugging = fetcher.test_code_execution(code_snippets)

            if can_run and not needs_debugging:
                score = 1.0  # Runs with no changes
                logger.debug("Code runs without changes, reproducibility = 1.0")
            elif can_run and needs_debugging:
                score = 0.5  # Runs with debugging
                logger.debug("Code runs with debugging, reproducibility = 0.5")
            else:
                score = 0.0  # Doesn't run
                logger.debug("Code doesn't run, reproducibility = 0.0")

        except Exception as e:
            logger.warning(f"Error calculating reproducibility metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class TreescoreMetric:
    """
    Evaluates average score of all parent models according to lineage graph.
    Requires access to parent model scores from registry.
    """

    def __init__(self, registry=None):
        """
        Initialize with optional registry access.

        Args:
            registry: Optional registry object to fetch parent model scores
        """
        self.registry = registry

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate treescore based on parent model scores."""
        start_time = time.time()

        try:
            # Get parent model IDs from config.json
            parent_ids = fetcher.get_parent_model_ids()

            if not parent_ids:
                logger.debug("No parent models found, treescore = 0.0")
                return 0.0, int((time.time() - start_time) * 1000)

            # Fetch scores of parent models from registry
            parent_scores = []
            for parent_id in parent_ids:
                if self.registry:
                    # If registry is available, fetch actual scores
                    parent_score = self.registry.get_model_score(parent_id)
                    if parent_score is not None:
                        parent_scores.append(parent_score)
                else:
                    # Without registry, we cannot compute treescore
                    logger.debug("No registry provided, cannot fetch parent scores")
                    return 0.0, int((time.time() - start_time) * 1000)

            if not parent_scores:
                logger.debug("No parent scores available, treescore = 0.0")
                score = 0.0
            else:
                # Calculate average of parent scores
                score = round(sum(parent_scores) / len(parent_scores), 2)
                logger.debug(f"Treescore: {score} (average of {len(parent_scores)} parents)")

        except Exception as e:
            logger.warning(f"Error calculating treescore metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms
