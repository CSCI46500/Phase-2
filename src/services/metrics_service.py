"""
Metrics evaluation orchestrator with parallel execution support.
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
from collections import OrderedDict

from src.utils.data_fetcher import DataFetcher
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

logger = logging.getLogger(__name__)


class MetricsEvaluator:
    """
    Orchestrates parallel evaluation of all metrics.
    """

    # Phase 2 weights (11 metrics total, sum = 1.0)
    WEIGHTS = {
        "license": 0.15,           # Critical for legal compliance
        "code_quality": 0.11,      # High importance for maintainability
        "dataset_quality": 0.11,   # High importance for model quality
        "reproducibility": 0.10,   # Can the model actually run?
        "ramp": 0.09,              # Ease of getting started
        "bus": 0.09,               # Team maintainability risk
        "reviewedness": 0.09,      # Code review quality
        "ds_code": 0.09,           # Dataset and code availability
        "size": 0.07,              # Storage/deployment considerations
        "perf": 0.07,              # Performance claims validity
        "treescore": 0.03          # Supplementary (lineage quality)
    }

    def __init__(self, model_url: str, dataset_url: str, code_url: str):
        """Initialize evaluator with resource URLs."""
        self.fetcher = DataFetcher(model_url, dataset_url, code_url)

        # Initialize metric calculators
        self.metrics = {
            'license': LicenseMetric(),
            'size_score': SizeScoreMetric(),
            'ramp_up_time': RampUpTimeMetric(),
            'bus_factor': BusFactorMetric(),
            'performance_claims': PerformanceClaimsMetric(),
            'dataset_and_code_score': DatasetCodeScoreMetric(),
            'dataset_quality': DatasetQualityMetric(),
            'code_quality': CodeQualityMetric(),
            'reproducibility': ReproducibilityMetric(),
            'reviewedness': ReviewednessMetric(),
            'treescore': TreescoreMetric()
        }

    def _execute_metric(self, metric_name: str, metric_calculator) -> Dict[str, Any]:
        """Execute a single metric calculation."""
        logger.debug(f"Calculating metric: {metric_name}")
        score, latency = metric_calculator.calculate(self.fetcher)
        return {
            'name': metric_name,
            'score': score,
            'latency': latency,
            'success': True
        }

    def evaluate(self) -> Dict[str, Any]:
        """
        Execute all metrics in parallel and return results.
        """
        logger.info("Starting metrics evaluation")
        overall_start = time.time()

        # Execute metrics in parallel
        metric_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all metric calculations
            future_to_metric = {
                executor.submit(self._execute_metric, name, calculator): name
                for name, calculator in self.metrics.items()
            }

            # Collect results as they complete
            for future in as_completed(future_to_metric):
                result = future.result()
                metric_name = result['name']
                metric_results[metric_name] = result
                logger.debug(f"Completed {metric_name}: score={result['score']}, latency={result['latency']}ms")

        # Calculate net score
        net_score, net_latency = self._calculate_net_score(metric_results)

        # Format results in NDJSON-compatible structure
        output = self._format_results(metric_results, net_score, net_latency)

        overall_time = int((time.time() - overall_start) * 1000)
        logger.info(f"Metrics evaluation completed in {overall_time}ms")

        return output

    def _calculate_net_score(self, metric_results: Dict[str, Dict]) -> tuple[float, int]:
        """
        Calculate weighted net score from individual metric scores.
        Handles special cases:
        - reviewedness can be -1 (no GitHub repo) - excluded from calculation
        - size_score is a dict - use minimum value
        """
        start_time = time.time()

        # Extract scores
        license_score = metric_results['license']['score']
        size_score = metric_results['size_score']['score']
        ramp_score = metric_results['ramp_up_time']['score']
        bus_score = metric_results['bus_factor']['score']
        perf_score = metric_results['performance_claims']['score']
        ds_code_score = metric_results['dataset_and_code_score']['score']
        ds_quality = metric_results['dataset_quality']['score']
        code_quality = metric_results['code_quality']['score']
        reproducibility = metric_results['reproducibility']['score']
        reviewedness = metric_results['reviewedness']['score']
        treescore = metric_results['treescore']['score']

        # Handle size_score (it's a dictionary)
        if isinstance(size_score, dict):
            size_score = min(size_score.values()) if size_score else 0.0

        # Handle reviewedness = -1 (no GitHub repo)
        # If -1, exclude from calculation and redistribute its weight
        total_weight = 1.0
        reviewedness_weight = self.WEIGHTS["reviewedness"]

        if reviewedness < 0:
            # Exclude reviewedness, redistribute weight proportionally
            total_weight -= reviewedness_weight
            reviewedness = 0.0
            reviewedness_weight = 0.0

        # Calculate weighted sum (all 11 metrics)
        net_score = (
            license_score * self.WEIGHTS["license"] +
            size_score * self.WEIGHTS["size"] +
            ramp_score * self.WEIGHTS["ramp"] +
            bus_score * self.WEIGHTS["bus"] +
            perf_score * self.WEIGHTS["perf"] +
            ds_code_score * self.WEIGHTS["ds_code"] +
            ds_quality * self.WEIGHTS["ds_quality"] +
            code_quality * self.WEIGHTS["code_quality"] +
            reproducibility * self.WEIGHTS["reproducibility"] +
            reviewedness * reviewedness_weight +
            treescore * self.WEIGHTS["treescore"]
        )

        # Normalize if we excluded reviewedness
        if total_weight < 1.0:
            net_score = net_score / total_weight

        # Clamp to [0.0, 1.0] and round
        net_score = round(min(max(net_score, 0.0), 1.0), 2)
        logger.debug(f"Net score calculated: {net_score}")

        latency_ms = int((time.time() - start_time) * 1000)
        return net_score, latency_ms

    def _format_results(self, metric_results: Dict[str, Dict], net_score: float, net_latency: int) -> Dict[str, Any]:
        """Format results in NDJSON-compatible ordered structure."""
        model_name = self.fetcher.get_model_name()

        # Build ordered dictionary matching Phase 1 output format
        output = OrderedDict([
            ("name", model_name),
            ("category", "MODEL"),
            ("net_score", net_score),
            ("net_score_latency", net_latency),
            ("ramp_up_time", metric_results['ramp_up_time']['score']),
            ("ramp_up_time_latency", metric_results['ramp_up_time']['latency']),
            ("bus_factor", metric_results['bus_factor']['score']),
            ("bus_factor_latency", metric_results['bus_factor']['latency']),
            ("performance_claims", metric_results['performance_claims']['score']),
            ("performance_claims_latency", metric_results['performance_claims']['latency']),
            ("license", metric_results['license']['score']),
            ("license_latency", metric_results['license']['latency']),
            ("size_score", metric_results['size_score']['score']),
            ("size_score_latency", metric_results['size_score']['latency']),
            ("dataset_and_code_score", metric_results['dataset_and_code_score']['score']),
            ("dataset_and_code_score_latency", metric_results['dataset_and_code_score']['latency']),
            ("dataset_quality", metric_results['dataset_quality']['score']),
            ("dataset_quality_latency", metric_results['dataset_quality']['latency']),
            ("code_quality", metric_results['code_quality']['score']),
            ("code_quality_latency", metric_results['code_quality']['latency']),
            ("reproducibility", metric_results['reproducibility']['score']),
            ("reproducibility_latency", metric_results['reproducibility']['latency']),
            ("reviewedness", metric_results['reviewedness']['score']),
            ("reviewedness_latency", metric_results['reviewedness']['latency']),
            ("treescore", metric_results['treescore']['score']),
            ("treescore_latency", metric_results['treescore']['latency']),
        ])

        return output
