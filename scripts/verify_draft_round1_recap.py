#!/usr/bin/env python3
"""
Verify Round 1 recap section and presence of section intro blocks in the
generated Draft Class Analytics HTML.

Checks (per spec):
- Presence of section id="round1" with at least one entry
- Round 1 entries sorted by Pick 1..N (ascending, starting at 1)
- If any Round 1 players in CSV have a portraitId, ensure at least one
  <img src> in #round1 matches:
  https://ratings-images-prod.pulse.ea.com/madden-nfl-26/portraits/\d+\.png
- Presence of a .section-intro block inside sections: #kpis, #spotlight,
  #teams, #positions

Usage:
  python3 scripts/verify_draft_round1_recap.py 2026 \
    --players MEGA_players.csv \
    --teams MEGA_teams.csv \
    --html docs/draft_class_2026.html

Notes:
- Standard library only (regex-based HTML inspection), aligned with
  scripts/verify_draft_class_analytics.py style and conventions.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys


def read_csv(path: str) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except FileNotFoundError:
        print(f"verify_r1: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"verify_r1: failed to read CSV '{path}': {e}", file=sys.stderr)
        sys.exit(2)


def safe_int(v, default=None):
    try:
        if v is None:
            return default
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if s == "":
            return default
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return default


def gather_round1_with_portraits(players: list[dict], year: int) -> list[dict]:
    out = []
    for r in players:
        if str(r.get("rookieYear", "")).strip() != str(year):
            continue
        rd = safe_int(r.get("draftRound"), None)
        if rd != 1:
            continue
        pid = (r.get("portraitId") or "").strip()
        out.append({
            "name": (r.get("fullName") or r.get("cleanName") or "").strip(),
            "portraitId": pid,
            "draftPick": safe_int(r.get("draftPick"), None),
        })
    return out


def extract_section(html_text: str, section_id: str) -> str | None:
    """Best-effort extraction of a <section id="...">...</section> block.

    Uses a simple regex to locate the opening <section ... id="section_id" ...>
    and returns content up to the next </section>. Assumes sections are not
    nested.
    """
    m = re.search(rf"<section[^>]*\bid=\"{re.escape(section_id)}\"[^>]*>", html_text, re.IGNORECASE)
    if not m:
        return None
    start = m.start()
    # Find the first closing </section> after start
    m_end = re.search(r"</section>", html_text[start:], re.IGNORECASE)
    if not m_end:
        # Return tail if no close tag found (tolerant)
        return html_text[start:]
    end = start + m_end.end()
    return html_text[start:end]


def extract_ordered_picks(round1_html: str) -> list[int]:
    """Extract pick numbers from #round1 content in document order.

    Supports multiple hints:
    - data-pick="N" attributes
    - visible text like "Pick N"
    - <span class="pick-badge">1.N</span> (takes N)
    Returns ordered pick integers (duplicates removed by first occurrence).
    """
    matches: list[tuple[int, int]] = []  # (pos, pick)

    # data-pick="N"
    for m in re.finditer(r"data-pick\s*=\s*\"(\d{1,2})\"", round1_html, re.IGNORECASE):
        matches.append((m.start(), int(m.group(1))))

    # text: Pick N
    for m in re.finditer(r"\bPick\s+(\d{1,2})\b", round1_html, re.IGNORECASE):
        matches.append((m.start(), int(m.group(1))))

    # pick-badge showing e.g., 1.7 -> we want 7
    for m in re.finditer(r"class=\"[^\"]*pick-badge[^\"]*\"[^>]*>\s*([0-9]+)\.([0-9]+)\s*<", round1_html, re.IGNORECASE):
        try:
            rd = int(m.group(1))
            pk = int(m.group(2))
            if rd == 1:
                matches.append((m.start(), pk))
        except Exception:
            pass

    # Sort by document position and dedupe by first occurrence
    matches.sort(key=lambda x: x[0])
    seen: set[int] = set()
    ordered: list[int] = []
    for _, p in matches:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def has_section_intro(html_text: str, section_id: str) -> bool:
    block = extract_section(html_text, section_id)
    if not block:
        return False
    return re.search(r"<div[^>]*class=\"[^\"]*section-intro[^\"]*\"", block, re.IGNORECASE) is not None


def main():
    ap = argparse.ArgumentParser(description="Verify Round 1 recap and section intros in Draft Class Analytics HTML")
    ap.add_argument("year", nargs="?", type=int, help="Draft class year (e.g., 2026)")
    ap.add_argument("--year", dest="year_opt", type=int, help="Draft class year (e.g., 2026)")
    ap.add_argument("--players", default="MEGA_players.csv", help="Path to players CSV")
    ap.add_argument("--teams", default="MEGA_teams.csv", help="Path to teams CSV (unused, kept for CLI parity)")
    ap.add_argument("--html", required=True, help="Path to generated HTML to verify")
    args = ap.parse_args()

    year = args.year_opt if args.year_opt is not None else args.year
    if year is None:
        print("verify_r1: error: year is required (positional or --year)", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(args.html):
        print(f"verify_r1: error: HTML not found: {args.html}", file=sys.stderr)
        sys.exit(2)

    # Load CSV to detect if any Round 1 players have portraitId
    players = read_csv(args.players)
    r1_players = gather_round1_with_portraits(players, year)
    any_portrait_in_csv = any((p.get("portraitId") or "").strip() for p in r1_players)

    with open(args.html, "r", encoding="utf-8") as fh:
        html_text = fh.read()

    # 1) Round 1 section exists
    round1_block = extract_section(html_text, "round1")
    if not round1_block:
        print("verify_r1: missing section id=\"round1\"", file=sys.stderr)
        sys.exit(1)

    # 2) At least one entry in #round1 (by detecting any pick marker)
    picks = extract_ordered_picks(round1_block)
    if not picks:
        print("verify_r1: no entries or pick markers found in #round1", file=sys.stderr)
        sys.exit(1)

    # 3) Sorted check: Pick 1..N (ascending, contiguous)
    expected = list(range(1, len(picks) + 1))
    if picks != expected:
        print(f"verify_r1: picks not sorted 1..N — found: {picks}", file=sys.stderr)
        sys.exit(1)

    # 4) Portrait image URL pattern if any portraitId exists for Round 1 in CSV
    if any_portrait_in_csv:
        pat = r"<img[^>]+src=\"https://ratings-images-prod\.pulse\.ea\.com/madden-nfl-26/portraits/\d+\.png\""
        if not re.search(pat, round1_block, re.IGNORECASE):
            print(
                "verify_r1: expected Round 1 portrait image with src '.../portraits/\\d+.png' not found",
                file=sys.stderr,
            )
            sys.exit(1)

    # 5) Section intro blocks in key sections
    missing_intros = []
    for sec_id, label in (("kpis", "KPIs"), ("spotlight", "Elites Spotlight"), ("teams", "Team Draft Quality"), ("positions", "Positions")):
        if not has_section_intro(html_text, sec_id):
            missing_intros.append(label)
    if missing_intros:
        print(
            "verify_r1: missing .section-intro in sections: " + ", ".join(missing_intros),
            file=sys.stderr,
        )
        sys.exit(1)

    # Success
    print(f"verify_r1: OK — Round 1 picks {len(picks)}; section intros present; year {year}")


if __name__ == "__main__":
    main()

