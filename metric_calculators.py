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

# Try to import Anthropic for Claude API integration
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not available. Install with: pip install anthropic")


class LicenseMetric:
    """Evaluates license compatibility."""

    # Accepted licenses compatible with open source
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
                score_dict = {
                    device: round(min(max(0.0, 1.0 - size_gb / limit), 1.0), 2)
                    for device, limit in self.SIZE_THRESHOLDS_GB.items()
                }
            else:
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

    MIN_WORDS_THRESHOLD = 50

    def _analyze_with_claude(self, readme_text: str) -> float:
        """
        Use Claude AI to analyze README quality.
        Returns score 0.0-1.0 or None if unavailable.
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
        Fallback keyword-based analysis.
        Returns score 0.0-1.0.
        """
        section_scores = []

        for section in self.RAMP_UP_SECTIONS:
            if section in readme_text:
                idx = readme_text.index(section) + len(section)
                after_text = readme_text[idx:]

                # Find next section boundary
                next_idx = len(after_text)
                for next_section in self.RAMP_UP_SECTIONS:
                    ni = after_text.find(next_section)
                    if ni != -1 and ni < next_idx:
                        next_idx = ni

                section_content = after_text[:next_idx].split()
                # Filter out common filler words
                meaningful_words = [
                    w for w in section_content
                    if w not in ("more", "information", "see", "docs")
                ]
                score = min(len(meaningful_words) / self.MIN_WORDS_THRESHOLD, 1.0)
                section_scores.append(score)
            else:
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

            # Try Claude API first
            claude_score = self._analyze_with_claude(readme_text)

            if claude_score is not None:
                final_score = round(claude_score, 2)
                logger.debug(f"Ramp-up score (Claude): {final_score}")
            else:
                # Fallback to keyword analysis
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

            if num_contributors >= 10:
                score = 1.0
            elif num_contributors >= 7:
                score = 0.5
            elif num_contributors >= 5:
                score = 0.3
            else:
                score = 0.0

            logger.debug(f"Bus factor score: {score} ({num_contributors} contributors)")
        except Exception as e:
            logger.warning(f"Error calculating bus factor metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class PerformanceClaimsMetric:
    """Evaluates presence of performance benchmarks and claims."""

    PERFORMANCE_KEYWORDS = ["accuracy", "benchmark", "perplexity", "performance"]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate performance claims score based on keyword presence."""
        start_time = time.time()

        try:
            readme_text = fetcher.fetch_readme("code").lower()

            has_perf_keywords = any(kw in readme_text for kw in self.PERFORMANCE_KEYWORDS)
            score = 1.0 if has_perf_keywords else 0.0

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

            score = (float(has_code) + float(has_dataset)) / 2.0
            logger.debug(f"Dataset/Code score: {score} (code={has_code}, dataset={has_dataset})")
        except Exception as e:
            logger.warning(f"Error calculating dataset/code metric: {e}")
            score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return score, latency_ms


class DatasetQualityMetric:
    """Evaluates dataset quality based on documentation and popularity."""

    DATASET_KEYWORDS = ["license", "download", "split", "train", "test", "validation"]

    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """Calculate dataset quality score."""
        start_time = time.time()

        try:
            # README length component
            readme_length = len(fetcher.fetch_readme("dataset").split())
            readme_score = 0.3 if readme_length >= 820 else 0.0

            # Download count component
            downloads = fetcher.get_dataset_downloads()
            if downloads >= 100000:
                download_score = 0.2
            elif downloads >= 50000:
                download_score = 0.15
            else:
                download_score = 0.0

            # Keyword presence component
            dataset_readme = fetcher.fetch_readme("dataset").lower()
            has_keywords = any(kw in dataset_readme for kw in self.DATASET_KEYWORDS)
            keyword_score = 0.5 if has_keywords else 0.0

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
            # GitHub stats (stars/forks)
            stats = fetcher.get_github_stats()
            stars = stats.get("stars", 0)
            forks = stats.get("forks", 0)

            stats_score = 0.0
            if stars >= 10000:
                stats_score += 0.1
            if forks >= 5000:
                stats_score += 0.1

            # README quality
            readme_length = len(fetcher.fetch_readme("code").split())
            if readme_length >= 1700:
                readme_score = 0.3
            elif readme_length >= 1000:
                readme_score = 0.2
            else:
                readme_score = 0.0

            # Recent maintenance (within 180 days)
            is_maintained = fetcher.is_recently_modified("github", 180)
            maintenance_score = 0.2 if is_maintained else 0.0

            total_score = stats_score + readme_score + maintenance_score
            logger.debug(f"Code quality score: {total_score}")
        except Exception as e:
            logger.warning(f"Error calculating code quality metric: {e}")
            total_score = 0.0

        latency_ms = int((time.time() - start_time) * 1000)
        return total_score, latency_ms
