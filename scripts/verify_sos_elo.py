#!/usr/bin/env python3
"""
Verification helper for SoS via ELO — parameterized for any season.

Interface:
  python3 scripts/verify_sos_elo.py --season-index N --check schedules|sos
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
    ap = argparse.ArgumentParser(description="Verify SoS via ELO artifacts (parameterized by season)")
    ap.add_argument("--season-index", type=int, required=True, help="Season index to verify (e.g. 2 or 3)")
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

    logging.info("Verifying Season %d SoS ELO — check=%s", args.season_index, args.check)

    if args.check == "schedules":
        return check_schedules()
    elif args.check == "sos":
        return check_sos()
    else:
        logging.error("Unknown check: %s", args.check)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
