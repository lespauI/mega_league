#!/usr/bin/env python3
"""Verify basic HTML report for roster-based power rankings (Phase 3).

Checks performed:
- HTML file exists and is non-trivial in size (> 10 KB).
- Presence of a team listing table/container.
- Embedded JS data blob representing team metrics.
- Existence of search/sort UI elements.

Usage (from project root):
    python3 scripts/verify_power_rankings_roster_html.py \
        --html docs/power_rankings_roster.html
"""
from __future__ import annotations

import argparse
import os
import sys


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        print(f"error: HTML file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"error: failed to read HTML '{path}': {exc}", file=sys.stderr)
        sys.exit(2)


def verify_html_structure(path: str, text: str) -> None:
    # File size check: ensure report is non-trivial.
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0
    if size < 10 * 1024:
        print(
            f"error: HTML report at {path} is too small (size={size} bytes); "
            "expected a richer report (> 10 KB)",
            file=sys.stderr,
        )
        sys.exit(1)

    lower = text.lower()

    # Team listing: look for table with the expected id or class.
    if "teams-table" not in lower and "roster power" not in lower and "team" not in lower:
        print(
            "error: HTML does not appear to contain the team listing table "
            "(missing 'teams-table' marker)",
            file=sys.stderr,
        )
        sys.exit(1)

    if "<table" not in lower:
        print("error: HTML does not contain any <table> element", file=sys.stderr)
        sys.exit(1)

    # Embedded JS data: check for JSON blob with team metrics.
    if "id=\"teams-data\"" not in text and "\"teams\"" not in text:
        print(
            "error: HTML is missing embedded JS data blob for teams "
            "(expected <script id=\"teams-data\"> or '"teams"' JSON)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Search UI element.
    if "team-search" not in text and "search" not in lower:
        print(
            "error: HTML is missing search/filter UI (expected element with "
            "id 'team-search' or similar)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Sort controls: expect sortable table class or the sorter script.
    if "sortable" not in lower and "table sorter" not in lower:
        print(
            "error: HTML is missing sortable table markers (class 'sortable')",
            file=sys.stderr,
        )
        sys.exit(1)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify basic power rankings HTML report for Phase 3",
    )
    parser.add_argument(
        "--html",
        default=os.path.join("docs", "power_rankings_roster.html"),
        help="Path to HTML report (default: docs/power_rankings_roster.html)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not os.path.exists(args.html):
        print(f"error: HTML report does not exist: {args.html}", file=sys.stderr)
        return 1

    text = read_text(args.html)
    if not text.strip():
        print(f"error: HTML report at {args.html} is empty", file=sys.stderr)
        return 1

    verify_html_structure(args.html, text)

    print(
        f"ok: verified power rankings HTML report at {args.html}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())

