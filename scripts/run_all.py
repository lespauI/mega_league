#!/usr/bin/env python3
"""Full analysis runner; task definitions live in pipeline_tasks.py."""

import argparse

from pipeline_tasks import pipeline_succeeded, run_pipeline
from run_utils import run_command


def main(season_index: int = 0, *, staged: bool = True, publish: bool = True):
    results = run_pipeline("full", season_index, executor=run_command, staged=staged, publish=publish)
    if not pipeline_succeeded(results):
        raise SystemExit(1)
    if publish:
        print(f"Season {season_index + 1} analysis complete (CSV seasonIndex={season_index}).")
        print("Results: output/; browser data: docs/data/; open index.html at the repository root.")
    else:
        print(f"Season {season_index + 1} staged validation passed; generated files were not published.")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run analysis for one CSV season")
    parser.add_argument("--season-index", type=int, default=0,
                        help="Zero-based CSV season index (default: 0)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Run a staged build and validation without publishing generated files")
    args = parser.parse_args()
    main(season_index=args.season_index, publish=not args.validate_only)
