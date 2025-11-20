#!/usr/bin/env python3
"""
Verification helper for Season 2 SoS via ELO — scaffolding.

Interface:
  python3 scripts/verify_sos_season2_elo.py --check schedules|sos

This file currently wires CLI and logging. The actual checks will be
implemented in subsequent steps alongside the calculation script.
"""

from __future__ import annotations

import argparse
import logging
from typing import List


def check_schedules() -> int:
    logging.info("[stub] verify schedules: will validate per-team schedule counts and schema")
    return 0


def check_sos() -> int:
    logging.info("[stub] verify sos: will validate ranking, league averages, and schema")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Verify Season 2 SoS via ELO artifacts (scaffold)")
    ap.add_argument(
        "--check",
        choices=["schedules", "sos"],
        required=True,
        help="Which verification to run",
    )
    return ap


def main(argv: List[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    if args.check == "schedules":
        return check_schedules()
    elif args.check == "sos":
        return check_sos()
    else:
        logging.error("Unknown check: %s", args.check)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

