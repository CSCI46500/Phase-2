"""
Metrics evaluation orchestrator with parallel execution support.
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
from collections import OrderedDict

from data_fetcher import DataFetcher
from metric_calculators import (
    LicenseMetric,
    SizeScoreMetric,
    RampUpTimeMetric,
    BusFactorMetric,
    PerformanceClaimsMetric,
    DatasetCodeScoreMetric,
    DatasetQualityMetric,
    CodeQualityMetric,
    ReviewednessMetric,
    ReproducibilityMetric,
    TreescoreMetric
)

logger = logging.getLogger(__name__)


class MetricsEvaluator:
    """
    Orchestrates parallel evaluation of all metrics.
    """

    # Phase 2 weights (adjusted to include new metrics)
    WEIGHTS = {
        "license": 0.18,
        "size": 0.09,
        "ramp": 0.11,
        "bus": 0.11,
        "perf": 0.09,
        "ds_code": 0.09,
        "ds_quality": 0.12,
        "code_quality": 0.12,
        "reviewedness": 0.03,
        "reproducibility": 0.03,
        "treescore": 0.03
    }

    def __init__(self, model_url: str, dataset_url: str, code_url: str, registry=None):
        """
        Initialize evaluator with resource URLs.

        Args:
            model_url: URL to HuggingFace model
            dataset_url: URL to HuggingFace dataset
            code_url: URL to GitHub repository
            registry: Optional registry object for treescore calculation
        """
        self.fetcher = DataFetcher(model_url, dataset_url, code_url)
        self.registry = registry

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
            'reviewedness': ReviewednessMetric(),
            'reproducibility': ReproducibilityMetric(),
            'treescore': TreescoreMetric(registry=registry)
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
        """Calculate weighted net score from individual metric scores."""
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
        reviewedness_score = metric_results['reviewedness']['score']
        reproducibility_score = metric_results['reproducibility']['score']
        treescore_score = metric_results['treescore']['score']

        # Handle size_score (it's a dictionary)
        if isinstance(size_score, dict):
            size_score = min(size_score.values()) if size_score else 0.0

        # Handle reviewedness (can be -1 if no GitHub repo)
        # Treat -1 as neutral (0.5) for scoring purposes
        if reviewedness_score == -1:
            reviewedness_score = 0.5

        # Calculate weighted sum
        net_score = (
            license_score * self.WEIGHTS["license"] +
            size_score * self.WEIGHTS["size"] +
            ramp_score * self.WEIGHTS["ramp"] +
            bus_score * self.WEIGHTS["bus"] +
            perf_score * self.WEIGHTS["perf"] +
            ds_code_score * self.WEIGHTS["ds_code"] +
            ds_quality * self.WEIGHTS["ds_quality"] +
            code_quality * self.WEIGHTS["code_quality"] +
            reviewedness_score * self.WEIGHTS["reviewedness"] +
            reproducibility_score * self.WEIGHTS["reproducibility"] +
            treescore_score * self.WEIGHTS["treescore"]
        )

        # Clamp to [0.0, 1.0] and round
        net_score = round(min(max(net_score, 0.0), 1.0), 2)
        logger.debug(f"Net score calculated: {net_score}")

        latency_ms = int((time.time() - start_time) * 1000)
        return net_score, latency_ms

    def _format_results(self, metric_results: Dict[str, Dict], net_score: float, net_latency: int) -> Dict[str, Any]:
        """Format results in NDJSON-compatible ordered structure."""
        model_name = self.fetcher.get_model_name()

        # Build ordered dictionary matching Phase 2 output format
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
            # Phase 2 new metrics
            ("reviewedness", metric_results['reviewedness']['score']),
            ("reviewedness_latency", metric_results['reviewedness']['latency']),
            ("reproducibility", metric_results['reproducibility']['score']),
            ("reproducibility_latency", metric_results['reproducibility']['latency']),
            ("treescore", metric_results['treescore']['score']),
            ("treescore_latency", metric_results['treescore']['latency']),
        ])

        return output
