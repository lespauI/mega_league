#!/usr/bin/env python3
"""
Verify Round 1 recap and section intro blocks in the generated HTML.

Checks:
- Presence of id="round1" section with at least one entry (card).
- Round 1 entries sorted by Pick ascending.
- If any Round 1 photo <img> exists, src matches the EA portraits pattern.
- .section-intro blocks exist in KPIs, Elites Spotlight, Team Draft Quality, Positions sections.

Usage:
  python3 scripts/verify_draft_round1_recap.py 2026 \
    --players MEGA_players.csv --teams MEGA_teams.csv \
    --html docs/draft_class_2026.html
"""
from __future__ import annotations

import argparse
import os
import re
import sys


def read_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"error: failed to read file '{path}': {e}", file=sys.stderr)
        sys.exit(2)


def find_section(html: str, section_id: str) -> str | None:
    # Simple, liberal regex: match <section ... id="{section_id}" ...>...</section>
    pat = re.compile(rf"<section[^>]*id=\"{re.escape(section_id)}\"[^>]*>(.*?)</section>", re.S | re.I)
    m = pat.search(html)
    return m.group(1) if m else None


def verify_round1(html: str) -> list[str]:
    errs: list[str] = []
    block = find_section(html, 'round1')
    if not block:
        errs.append("missing <section id=\"round1\"> block")
        return errs

    # Count cards
    cards = re.findall(r"<div\s+class=\"r1-card\"", block, re.I)
    if len(cards) < 1:
        errs.append("round1: expected at least one r1-card entry")

    # Extract picks and ensure ascending order
    picks = [int(x) for x in re.findall(r"<div\s+class=\"pick\">\s*Pick\s+(\d+)\s*</div>", block, re.I)]
    if picks:
        if picks != sorted(picks):
            errs.append(f"round1: picks not sorted ascending: {picks}")

    # Validate portrait image URLs if any present
    photos = re.findall(r"<img[^>]*class=\"r1-photo\"[^>]*src=\"([^\"]+)\"", block, re.I)
    if photos:
        bad = [u for u in photos if not re.match(r"^https://ratings-images-prod\.pulse\.ea\.com/madden-nfl-26/portraits/\d+\.png$", u)]
        if bad:
            errs.append(f"round1: invalid portrait img src(s): {', '.join(bad[:3])}")
    return errs


def verify_intros(html: str) -> list[str]:
    errs: list[str] = []
    targets = [
        ('kpis', 'KPIs'),
        ('spotlight', 'Elites Spotlight'),
        ('teams', 'Team Draft Quality'),
        ('positions', 'Positions'),
    ]
    for sec_id, label in targets:
        block = find_section(html, sec_id)
        if not block:
            errs.append(f"missing section id='{sec_id}' for {label}")
            continue
        if 'class="section-intro"' not in block:
            errs.append(f"{label}: missing .section-intro block")
    return errs


def main():
    ap = argparse.ArgumentParser(description='Verify Round 1 recap and section intros in generated HTML')
    ap.add_argument('year', type=int, help='Draft class year (e.g., 2026)')
    ap.add_argument('--players', default='MEGA_players.csv', help='Players CSV (unused; for parity)')
    ap.add_argument('--teams', default='MEGA_teams.csv', help='Teams CSV (unused; for parity)')
    ap.add_argument('--html', default=None, help='Path to generated HTML (default: docs/draft_class_<year>.html)')
    args = ap.parse_args()

    html_path = args.html or os.path.join('docs', f'draft_class_{args.year}.html')
    if not os.path.exists(html_path):
        print(f"error: HTML not found: {html_path}", file=sys.stderr)
        sys.exit(2)

    html = read_file(html_path)

    errs: list[str] = []
    errs += verify_round1(html)
    errs += verify_intros(html)

    if errs:
        print("Verification failed:", file=sys.stderr)
        for e in errs:
            print(f" - {e}", file=sys.stderr)
        sys.exit(1)
    print("Verification passed: Round 1 recap and section intros look good.")


if __name__ == '__main__':
    main()

