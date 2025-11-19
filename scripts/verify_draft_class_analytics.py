#!/usr/bin/env python3
"""
Verify the generated Draft Class Analytics HTML against CSV data.

Checks:
- Recompute rookies for the given year from MEGA_players.csv
- Compute KPIs (total, avg OVR, dev counts, elite count and %)
- Parse HTML and assert KPI numbers match
- Assert no unresolved placeholders like __PLACEHOLDER__ remain
- Assert title/header includes the correct year

Usage:
  python3 scripts/verify_draft_class_analytics.py 2026 \
      --players MEGA_players.csv --teams MEGA_teams.csv \
      --html docs/draft_class_2026.html
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import statistics as st
import sys
from collections import Counter


DEV_VALID = {"3", "2", "1", "0"}


def read_csv(path: str) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except FileNotFoundError:
        print(f"verify: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"verify: failed to read CSV '{path}': {e}", file=sys.stderr)
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


def gather_rookies(players: list[dict], year: int) -> list[dict]:
    out = []
    for r in players:
        if str(r.get("rookieYear", "")).strip() != str(year):
            continue

        ovr = safe_int(r.get("playerBestOvr"), None)
        if ovr is None:
            ovr = safe_int(r.get("playerSchemeOvr"), 0)
        if ovr is None:
            ovr = 0

        dev_raw = r.get("devTrait", "0")
        dev = str(dev_raw).strip() if dev_raw is not None else "0"
        if dev not in DEV_VALID:
            dev = "0"

        out.append({
            "ovr": int(ovr),
            "dev": dev,
        })
    # sort not necessary for verification
    return out


def compute_kpis(rows: list[dict]) -> dict:
    total = len(rows)
    ovrs = [r["ovr"] for r in rows]
    avg_ovr = round(st.mean(ovrs), 2) if ovrs else 0.0
    dev_counts = Counter(r["dev"] for r in rows)
    xf = dev_counts.get("3", 0)
    ss = dev_counts.get("2", 0)
    star = dev_counts.get("1", 0)
    elite = xf + ss
    # mirror generator behavior (handles total==0 safely)
    denom = total or 1
    elite_pct = round(100.0 * elite / denom, 1)
    return {
        "total": total,
        "avg_ovr": avg_ovr,
        "xf": xf,
        "ss": ss,
        "star": star,
        "elite": elite,
        "elite_pct": elite_pct,
    }


def parse_html_kpis(html_text: str) -> dict:
    # Extract KPIs as rendered in the generator template
    def extract(label: str) -> str | None:
        # Pattern like: <b>Total rookies</b><span>123</span>
        m = re.search(rf"<b>{re.escape(label)}</b><span>([^<]+)</span>", html_text)
        return m.group(1).strip() if m else None

    k = {}
    k["total"] = extract("Total rookies")
    k["avg_ovr"] = extract("Avg overall")
    k["xf"] = extract("X-Factors")
    k["ss"] = extract("Superstars")
    k["star"] = extract("Stars")

    # Elites share: value is "<elite> (<pct>%)"
    m = re.search(r"<b>Elites share</b><span>([^<]+)</span>", html_text)
    if m:
        piece = m.group(1).strip()  # e.g., "17 (23.6%)"
        m2 = re.match(r"(\d+)\s*\(([-+]?[0-9]*\.?[0-9]+)%\)", piece)
        if m2:
            k["elite"] = m2.group(1)
            k["elite_pct"] = m2.group(2)
        else:
            k["elite"] = None
            k["elite_pct"] = None
    else:
        k["elite"] = None
        k["elite_pct"] = None
    return k


def main():
    ap = argparse.ArgumentParser(description="Verify Draft Class Analytics HTML against CSV data")
    # support positional year as per usage, and optional --year for flexibility
    ap.add_argument("year", nargs="?", type=int, help="Draft class year (e.g., 2026)")
    ap.add_argument("--year", dest="year_opt", type=int, help="Draft class year (e.g., 2026)")
    ap.add_argument("--players", default="MEGA_players.csv", help="Path to players CSV")
    ap.add_argument("--teams", default="MEGA_teams.csv", help="Path to teams CSV (unused, kept for CLI parity)")
    ap.add_argument("--html", required=True, help="Path to generated HTML to verify")
    args = ap.parse_args()

    year = args.year_opt if args.year_opt is not None else args.year
    if year is None:
        print("verify: error: year is required (positional or --year)", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(args.html):
        print(f"verify: error: HTML not found: {args.html}", file=sys.stderr)
        sys.exit(2)

    players = read_csv(args.players)
    rookies = gather_rookies(players, year)
    kpis = compute_kpis(rookies)

    with open(args.html, "r", encoding="utf-8") as fh:
        html_text = fh.read()

    # 1) Title/header check
    expected_hdr = f"Draft Class {year} — Analytics Report"
    if expected_hdr not in html_text:
        print(f"verify: mismatch: header missing or incorrect: '{expected_hdr}'", file=sys.stderr)
        sys.exit(1)

    # 2) No placeholders left
    if re.search(r"__[A-Z_]+__", html_text):
        print("verify: unresolved placeholders found in HTML (e.g., __FOO__)", file=sys.stderr)
        sys.exit(1)

    # 3) KPI extraction and comparison
    html_kpis = parse_html_kpis(html_text)

    mismatches = []
    def cmp_int(key: str, v: int):
        s = html_kpis.get(key)
        try:
            hv = int(s) if s is not None else None
        except Exception:
            hv = None
        if hv != v:
            mismatches.append(f"{key}: expected {v}, found {s}")

    def cmp_float_str(key: str, v: float):
        s = html_kpis.get(key)
        # generator prints avg_ovr as rounded float str
        if s is None or s != str(v):
            mismatches.append(f"{key}: expected {v}, found {s}")

    cmp_int("total", kpis["total"])  # Total rookies
    cmp_float_str("avg_ovr", kpis["avg_ovr"])  # Avg overall
    cmp_int("xf", kpis["xf"])  # X-Factors
    cmp_int("ss", kpis["ss"])  # Superstars
    cmp_int("star", kpis["star"])  # Stars
    cmp_int("elite", kpis["elite"])  # Elites count

    # Elite pct as string with 1 decimal, compare string form to avoid locale/format surprises
    elite_pct_str = f"{kpis['elite_pct']}"
    if html_kpis.get("elite_pct") != elite_pct_str:
        mismatches.append(f"elite_pct: expected {elite_pct_str}, found {html_kpis.get('elite_pct')}")

    if mismatches:
        print("verify: FAILED — mismatches detected:", file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)

    # Success
    print(
        f"verify: OK — year {year}, total {kpis['total']}, elites {kpis['elite']} ({kpis['elite_pct']}%), avg {kpis['avg_ovr']}"
    )


if __name__ == "__main__":
    main()

