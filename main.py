#!/usr/bin/env python3
import sys
import subprocess
import json
import pytest
from metrics import Metrics
from typing import Dict, Any


def parse_input(path: str):
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
    print(json.dumps(obj, ensure_ascii=False))


def run_tests():
    exit_code = pytest.main([
        "tests",       
        "--cov=.",
        "--cov-report=term-missing",
        "--disable-warnings",
        "-q"
    ])
    sys.exit(exit_code)


def main(argv: list[str]) -> None:
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
                metrics = Metrics(input_dict)
                result = metrics.run()
                print_ndjson(result)
            sys.exit(0)
        except Exception as e:
            print(f"Error processing URL file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
