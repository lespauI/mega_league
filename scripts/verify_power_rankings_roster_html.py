#!/usr/bin/env python3
"""Verify HTML report for roster-based power rankings (Phases 3–4).

Checks performed:
- HTML file exists and is non-trivial in size (> 10 KB).
- Presence of a team listing table/container.
- Embedded JS data blob representing team metrics.
- Existence of search/sort UI elements.
- Phase 4 enhancements:
  - Team-level cards or sections with radar-style visuals.
  - Per-team narrative text (strengths/weaknesses) matching CSV teams.
  - Visible methodology/config section.

Usage (from project root):
    python3 scripts/verify_power_rankings_roster_html.py \
        --html docs/power_rankings_roster.html \
        --csv output/power_rankings_roster.csv
"""
from __future__ import annotations

import argparse
import csv
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
    if "id=\"teams-data\"" not in text and '"teams"' not in text:
        print(
            "error: HTML is missing embedded JS data blob for teams "
            "(expected <script id=\"teams-data\"> or JSON key 'teams')",
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


def load_team_abbrevs_from_csv(path: str) -> list[str]:
    """Load team abbreviations from the power rankings CSV.

    Exits with an error if the CSV is missing or malformed.
    """

    if not os.path.exists(path):
        print(f"error: rankings CSV not found: {path}", file=sys.stderr)
        sys.exit(2)

    abbrs: list[str] = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                abbr = (row.get("team_abbrev") or row.get("abbrev") or "").strip()
                if not abbr:
                    continue
                if abbr not in abbrs:
                    abbrs.append(abbr)
    except Exception as exc:  # pragma: no cover - defensive path
        print(f"error: failed to read rankings CSV '{path}': {exc}", file=sys.stderr)
        sys.exit(2)

    if not abbrs:
        print(
            f"error: no team_abbrev values found in {path}; cannot verify team cards",
            file=sys.stderr,
        )
        sys.exit(1)

    return abbrs


def verify_phase4_enhancements(html_text: str, csv_path: str) -> None:
    """Verify Phase 4 specific HTML features (advanced visuals & narratives)."""

    lower = html_text.lower()

    # Methodology/config section.
    if "id=\"methodology\"" not in html_text and "methodology &amp; config" not in lower:
        print(
            "error: HTML is missing methodology/config section (expected element with id 'methodology')",
            file=sys.stderr,
        )
        sys.exit(1)

    # Radar / multi-metric visualization elements.
    if "radar-chart" not in lower:
        print(
            "error: HTML is missing radar-style unit visuals (expected elements with class 'radar-chart')",
            file=sys.stderr,
        )
        sys.exit(1)

    # Team cards and narratives per team.
    abbrs = load_team_abbrevs_from_csv(csv_path)

    card_count = html_text.count("class=\"team-card")
    if card_count < len(abbrs):
        print(
            f"error: expected at least {len(abbrs)} team cards but found {card_count} (class 'team-card')",
            file=sys.stderr,
        )
        sys.exit(1)

    for abbr in abbrs:
        card_marker = f'class="team-card"'
        if f'data-team-abbr="{abbr}"' not in html_text:
            print(
                f"error: no HTML section/card found for team '{abbr}' (missing data-team-abbr)",
                file=sys.stderr,
            )
            sys.exit(1)

        narrative_marker = f'class="team-narrative" data-team-abbr="{abbr}"'
        if narrative_marker not in html_text:
            print(
                f"error: team '{abbr}' is missing narrative block (class 'team-narrative')",
                file=sys.stderr,
            )
            sys.exit(1)

        idx = html_text.find(narrative_marker)
        window = html_text[idx : idx + 2000]
        # Require both strengths and weaknesses labels to appear near the narrative.
        if "Strengths" not in window or "Weaknesses" not in window:
            print(
                f"error: narrative for team '{abbr}' is missing strengths/weaknesses text",
                file=sys.stderr,
            )
            sys.exit(1)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify power rankings HTML report (Phases 3–4)",
    )
    parser.add_argument(
        "--html",
        default=os.path.join("docs", "power_rankings_roster.html"),
        help="Path to HTML report (default: docs/power_rankings_roster.html)",
    )
    parser.add_argument(
        "--csv",
        default=os.path.join("output", "power_rankings_roster.csv"),
        help="Path to power rankings CSV (default: output/power_rankings_roster.csv)",
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
    verify_phase4_enhancements(text, args.csv)

    print(
        f"ok: verified power rankings HTML report (Phases 3–4) at {args.html}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
