#!/usr/bin/env python3
"""
Demo script to showcase the new Phase 2 metrics.
"""
import json
from metrics_evaluator import MetricsEvaluator

def demo_new_metrics():
    """Demonstrate the three new Phase 2 metrics."""
    print("=" * 70)
    print("Phase 2 New Metrics Demo")
    print("=" * 70)
    print()

    # Example model with GitHub repository
    print("Testing with a real HuggingFace model...")
    print("-" * 70)

    evaluator = MetricsEvaluator(
        model_url="https://huggingface.co/bert-base-uncased",
        dataset_url="https://huggingface.co/datasets/squad",
        code_url="https://github.com/huggingface/transformers"
    )

    print("\nEvaluating metrics...")
    results = evaluator.evaluate()

    print("\n" + "=" * 70)
    print("NEW PHASE 2 METRICS")
    print("=" * 70)

    print(f"\n1. REVIEWEDNESS: {results.get('reviewedness', 'N/A')}")
    print(f"   Latency: {results.get('reviewedness_latency', 'N/A')} ms")
    print(f"   Description: Fraction of code introduced through reviewed PRs")
    if results.get('reviewedness') == -1:
        print(f"   Status: No GitHub repository linked")
    elif results.get('reviewedness') is not None:
        print(f"   Status: {results['reviewedness']*100:.1f}% of code was reviewed")

    print(f"\n2. REPRODUCIBILITY: {results.get('reproducibility', 'N/A')}")
    print(f"   Latency: {results.get('reproducibility_latency', 'N/A')} ms")
    print(f"   Description: Whether model can run using demo code from card")
    if results.get('reproducibility') == 1.0:
        print(f"   Status: Code runs without changes ✓")
    elif results.get('reproducibility') == 0.5:
        print(f"   Status: Code runs with debugging")
    else:
        print(f"   Status: No runnable code or doesn't run")

    print(f"\n3. TREESCORE: {results.get('treescore', 'N/A')}")
    print(f"   Latency: {results.get('treescore_latency', 'N/A')} ms")
    print(f"   Description: Average score of parent models (lineage)")
    if results.get('treescore') == 0:
        print(f"   Status: No parent models or registry not available")
    else:
        print(f"   Status: Average parent score: {results['treescore']}")

    print("\n" + "=" * 70)
    print("UPDATED NET SCORE")
    print("=" * 70)
    print(f"\nNet Score: {results.get('net_score', 'N/A')}")
    print(f"(Now includes all 11 metrics with adjusted weights)")

    print("\n" + "=" * 70)
    print("FULL RESULTS (JSON)")
    print("=" * 70)
    print(json.dumps(results, indent=2))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("""
The three new Phase 2 metrics have been successfully implemented:

1. **Reviewedness** - Analyzes GitHub PR review coverage
   - Returns -1 if no GitHub repo
   - Returns 0.0-1.0 based on % of code reviewed

2. **Reproducibility** - Tests if model card code can run
   - 0.0: No code or doesn't run
   - 0.5: Runs with debugging
   - 1.0: Runs without changes
   - Uses Claude AI when available, falls back to heuristics

3. **Treescore** - Calculates average score of parent models
   - Extracts lineage from config.json
   - Requires registry access to fetch parent scores
   - Returns 0.0 if no parents or no registry

All metrics include latency tracking and are integrated into the
weighted net score calculation.
    """)

if __name__ == "__main__":
    demo_new_metrics()
