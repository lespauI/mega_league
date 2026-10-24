#!/usr/bin/env python3
"""Playoff-analysis runner selecting shared tasks from the pipeline graph."""

import argparse

from pipeline_tasks import pipeline_succeeded, run_pipeline
from run_utils import run_command


def main(season_index: int = 0, *, staged: bool = True, publish: bool = True):
    results = run_pipeline("playoff", season_index, executor=run_command, staged=staged, publish=publish)
    if not pipeline_succeeded(results):
        raise SystemExit(1)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run playoff analysis for one CSV season")
    parser.add_argument("--season-index", type=int, default=0,
                        help="Zero-based CSV season index (default: 0)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Run a staged build and validation without publishing generated files")
    args = parser.parse_args()
    main(season_index=args.season_index, publish=not args.validate_only)
