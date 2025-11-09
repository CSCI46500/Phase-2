#!/usr/bin/env python3
import sys
import subprocess
import json
import pytest
from typing import Dict, Any
from dotenv import load_dotenv

from logger_config import setup_logging
from metrics_evaluator import MetricsEvaluator

# Load environment variables from .env file
load_dotenv()


def parse_input(path: str):
    """Parse input file containing URLs."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            yield {
                "code_url": parts[0] if len(parts) > 0 else "",
                "dataset_url": parts[1] if len(parts) > 1 else "",
                "model_url": parts[2] if len(parts) > 2 else ""
            }


def print_ndjson(obj: Dict[str, Any]) -> None:
    """Print object as NDJSON (newline-delimited JSON)."""
    print(json.dumps(obj, ensure_ascii=False))


def run_tests():
    """Run test suite with coverage and format output as required."""
    import subprocess
    import re
    import os

    try:
        # Run pytest with coverage in quiet mode
        result = subprocess.run(
            [
                "python3", "-m", "pytest", "tests/test.py",
                "--cov=.",
                "--cov-report=term",
                "--disable-warnings",
                "-q"
            ],
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr

        # Parse test results
        test_pattern = r"(\d+) passed"
        test_match = re.search(test_pattern, output)
        passed_tests = int(test_match.group(1)) if test_match else 0

        failed_pattern = r"(\d+) failed"
        failed_match = re.search(failed_pattern, output)
        failed_tests = int(failed_match.group(1)) if failed_match else 0

        total_tests = passed_tests + failed_tests if (passed_tests + failed_tests) > 0 else passed_tests

        # Parse coverage percentage from output
        coverage_pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
        coverage_match = re.search(coverage_pattern, output)
        coverage_percent = int(coverage_match.group(1)) if coverage_match else 0

        # Print formatted output (only this line should appear)
        print(f"{passed_tests}/{total_tests} test cases passed. {coverage_percent}% line coverage achieved.")

        # Exit with appropriate code
        if result.returncode != 0 or failed_tests > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


def main(argv: list[str]) -> None:
    """Main entry point."""
    # Setup logging configuration
    setup_logging()

    if len(argv) != 2:
        print("Usage: ./run <install|test|URL_FILE>", file=sys.stderr)
        sys.exit(2)

    cmd = argv[1]

    if cmd == "install":
        try:
            subprocess.run(["python3", "-m", "pip", "install", "-r", "dependencies.txt"], check=True)
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"Install failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "test":
        run_tests()

    else:
        try:
            for input_dict in parse_input(cmd):
                evaluator = MetricsEvaluator(
                    model_url=input_dict["model_url"],
                    dataset_url=input_dict["dataset_url"],
                    code_url=input_dict["code_url"]
                )
                result = evaluator.evaluate()
                print_ndjson(result)
            sys.exit(0)
        except Exception as e:
            print(f"Error processing URL file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
