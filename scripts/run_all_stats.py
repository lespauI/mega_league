#!/usr/bin/env python3
"""Stats-only runner selecting shared tasks from the pipeline graph."""

import argparse

from pipeline_tasks import pipeline_succeeded, run_pipeline
from run_utils import run_command


def main(*, staged: bool = True, publish: bool = True):
    results = run_pipeline("stats", executor=run_command, staged=staged, publish=publish)
    if not pipeline_succeeded(results):
        raise SystemExit(1)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the stats task selection")
    parser.add_argument("--validate-only", action="store_true",
                        help="Run a staged build and validation without publishing generated files")
    args = parser.parse_args()
    main(publish=not args.validate_only)
