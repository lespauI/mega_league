#!/usr/bin/env python3
"""Verify power rankings roster CSV for Phase 2 unit scoring.

Checks performed:
- Expected header columns exist.
- Score columns are numeric and in the 0–100 range.
- Rank columns contain unique integers in 1..N with no gaps.

Usage (from project root):
    python3 scripts/verify_power_rankings_roster_csv.py \
        --csv output/power_rankings_roster.csv
"""
from __future__ import annotations

import argparse
import csv
import sys


def read_csv(path: str) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"error: failed to read CSV '{path}': {exc}", file=sys.stderr)
        sys.exit(2)


def safe_float(value, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if s == "":
            return default
        return float(s)
    except Exception:
        return default


def safe_int(value, default: int | None = None) -> int | None:
    try:
        if value is None:
            return default
        if isinstance(value, int):
            return value
        s = str(value).strip()
        if s == "":
            return default
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return default


def verify_headers(fieldnames: list[str]) -> None:
    required = {
        "team_abbrev",
        "team_name",
        "overall_score",
        "overall_rank",
        "off_pass_score",
        "off_pass_rank",
        "off_run_score",
        "off_run_rank",
        "def_cover_score",
        "def_cover_rank",
        "def_pass_rush_score",
        "def_pass_rush_rank",
        "def_run_score",
        "def_run_rank",
    }
    missing = sorted(required - set(fieldnames or []))
    if missing:
        print(
            "error: CSV is missing required column(s): " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)


def verify_scores_and_ranks(rows: list[dict]) -> None:
    if not rows:
        print("error: CSV appears to be empty (no data rows)", file=sys.stderr)
        sys.exit(1)

    n = len(rows)

    score_cols = [
        "overall_score",
        "off_pass_score",
        "off_run_score",
        "def_cover_score",
        "def_pass_rush_score",
        "def_run_score",
    ]
    # ST columns are optional but, if present, should also satisfy checks.
    optional_score_cols = ["st_score"]

    rank_cols = [
        "overall_rank",
        "off_pass_rank",
        "off_run_rank",
        "def_cover_rank",
        "def_pass_rush_rank",
        "def_run_rank",
    ]
    optional_rank_cols = ["st_rank"]

    present_score_cols = [c for c in score_cols if c in rows[0].keys()]
    present_optional_scores = [c for c in optional_score_cols if c in rows[0].keys()]

    present_rank_cols = [c for c in rank_cols if c in rows[0].keys()]
    present_optional_ranks = [c for c in optional_rank_cols if c in rows[0].keys()]

    # Score columns: numeric and in [0, 100].
    for col in present_score_cols + present_optional_scores:
        for i, row in enumerate(rows, start=1):
            raw = row.get(col, "")
            if raw == "" and col in optional_score_cols:
                continue
            val = safe_float(raw, None)
            if val is None:
                print(
                    f"error: row {i}: column {col!r} is not numeric: {raw!r}",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not (0.0 <= val <= 100.0):
                print(
                    f"error: row {i}: column {col!r} out of range 0–100: {val}",
                    file=sys.stderr,
                )
                sys.exit(1)

    # Rank columns: unique integers 1..N with no gaps.
    for col in present_rank_cols + present_optional_ranks:
        ranks: list[int] = []
        for i, row in enumerate(rows, start=1):
            raw = row.get(col, "")
            if raw == "" and col in optional_rank_cols:
                continue
            val = safe_int(raw, None)
            if val is None:
                print(
                    f"error: row {i}: column {col!r} is not an integer: {raw!r}",
                    file=sys.stderr,
                )
                sys.exit(1)
            ranks.append(val)

        if not ranks:
            # e.g., ST ranks omitted for all rows; that's acceptable.
            continue

        expected = set(range(1, n + 1))
        actual = set(ranks)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            msg_parts = []
            if missing:
                msg_parts.append(f"missing ranks: {missing}")
            if extra:
                msg_parts.append(f"unexpected ranks: {extra}")
            detail = "; ".join(msg_parts) or "ranks do not form 1..N"
            print(
                f"error: column {col!r} ranks invalid: {detail}",
                file=sys.stderr,
            )
            sys.exit(1)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify power rankings roster CSV for Phase 2 unit scoring",
    )
    parser.add_argument(
        "--csv",
        default="output/power_rankings_roster.csv",
        help="Path to power rankings CSV (default: output/power_rankings_roster.csv)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    rows = read_csv(args.csv)
    if not rows:
        print(f"error: no rows found in {args.csv}", file=sys.stderr)
        return 1

    verify_headers(list(rows[0].keys()))
    verify_scores_and_ranks(rows)

    print(
        f"ok: verified power rankings CSV with {len(rows)} team row(s) at {args.csv}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())

