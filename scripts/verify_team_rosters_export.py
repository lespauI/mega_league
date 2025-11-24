#!/usr/bin/env python3
"""Verify that per-team roster exports exist and have the expected schema.

Phase 1 verification helper for roster-based power rankings.

Checks performed:
- The number of base team roster CSVs in the output directory matches
  the number of teams defined in MEGA_teams.csv.
- Each roster CSV contains core columns required by later phases
  (team_abbrev, player_id, player_name, position, ovr, dev).

Usage (from project root):
    python3 scripts/verify_team_rosters_export.py \
        --teams MEGA_teams.csv --rosters-dir output/team_rosters
"""
from __future__ import annotations

import argparse
import csv
import os
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


def count_teams(teams_path: str) -> int:
    rows = read_csv(teams_path)
    if not rows:
        print("error: MEGA_teams.csv appears to be empty", file=sys.stderr)
        sys.exit(1)

    abbrevs: set[str] = set()
    for r in rows:
        abbrev = (r.get("abbrev") or r.get("abbrName") or "").strip()
        if not abbrev:
            # fallback to teamName/displayName if abbrev is missing
            abbrev = (r.get("teamName") or r.get("displayName") or "").strip()
        if abbrev:
            abbrevs.add(abbrev)

    if not abbrevs:
        print("error: could not determine any team abbreviations from MEGA_teams.csv", file=sys.stderr)
        sys.exit(1)

    return len(abbrevs)


def count_base_roster_files(rosters_dir: str) -> int:
    if not os.path.isdir(rosters_dir):
        print(f"error: rosters directory does not exist: {rosters_dir}", file=sys.stderr)
        sys.exit(1)

    count = 0
    for name in os.listdir(rosters_dir):
        if not name.lower().endswith(".csv"):
            continue
        stem = os.path.splitext(name)[0]
        # Only count base team files like BUF.csv, not BUF_O.csv, etc.
        if "_" in stem:
            continue
        count += 1
    return count


def verify_roster_schema(rosters_dir: str) -> None:
    required = {"team_abbrev", "player_id", "player_name", "position", "ovr", "dev"}
    if not os.path.isdir(rosters_dir):
        print(f"error: rosters directory does not exist: {rosters_dir}", file=sys.stderr)
        sys.exit(1)

    violations = 0
    for name in os.listdir(rosters_dir):
        if not name.lower().endswith(".csv"):
            continue
        stem = os.path.splitext(name)[0]
        if "_" in stem:
            # Skip future split-unit files like BUF_O.csv.
            continue
        path = os.path.join(rosters_dir, name)
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            headers = set(reader.fieldnames or [])
        missing = sorted(required - headers)
        if missing:
            print(
                f"error: roster file {path} is missing required columns: {', '.join(missing)}",
                file=sys.stderr,
            )
            violations += 1

    if violations:
        print(f"error: {violations} roster file(s) failed schema verification", file=sys.stderr)
        sys.exit(1)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify per-team roster CSV exports for Phase 1",
    )
    parser.add_argument(
        "--teams",
        default="MEGA_teams.csv",
        help="Path to MEGA_teams.csv (default: MEGA_teams.csv)",
    )
    parser.add_argument(
        "--rosters-dir",
        default=os.path.join("output", "team_rosters"),
        help="Directory containing per-team roster CSVs (default: output/team_rosters)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    expected_teams = count_teams(args.teams)
    actual_files = count_base_roster_files(args.rosters_dir)

    if expected_teams != actual_files:
        print(
            "error: team count mismatch: "
            f"MEGA_teams.csv has {expected_teams} teams, "
            f"but found {actual_files} base roster CSV(s) in {args.rosters_dir}",
            file=sys.stderr,
        )
        return 1

    verify_roster_schema(args.rosters_dir)

    print(
        f"ok: {actual_files} team roster CSVs verified against {expected_teams} teams",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())

