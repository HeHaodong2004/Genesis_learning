"""Run a synthetic paired comparison without importing gnav, Torch or Genesis."""

import argparse
import importlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", choices=("starter", "solution"), default="solution")
    parser.add_argument("--input", type=Path, default=Path(__file__).parent / "fixtures" / "synthetic.json")
    args = parser.parse_args()
    implementation = importlib.import_module(f"developer.labs.paired_comparison.{args.implementation}")
    try:
        fixture = json.loads(args.input.read_text(encoding="utf-8"))
        result = implementation.paired_comparison(fixture["a"], fixture["b"], fixture["keys"])
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        parser.exit(2, f"Comparison failed: {error}\n")


if __name__ == "__main__":
    main()
