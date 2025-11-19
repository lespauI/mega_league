#!/usr/bin/env python3
"""
Verify the generated Draft Class Analytics HTML against CSV data.

New verification scope (unmasked dev tiers):
- Recompute rookies for the given year from MEGA_players.csv
- Compute KPIs for dev tiers XF(3)/SS(2)/Star(1)/Norm(0)
- Validate HTML KPIs: X-Factors, Superstars, Stars (and Normal if present)
- Validate "Elites share" count and percentage ((XF+SS)/Total)
- Validate spotlight section title includes "Elites Spotlight"
- Validate team and position table headers include dev columns XF/SS/Star/Norm
- Optionally check grading badges (class="grade-(on|near|below)") when present
- Optionally check presence of dual rounds titles when present
- Assert no unresolved placeholders like __PLACEHOLDER__ remain
- Assert title/header includes the correct year

Usage:
  python3 scripts/verify_draft_class_analytics.py 2026 \
      --players MEGA_players.csv --teams MEGA_teams.csv \
      --html docs/draft_class_2026_test.html
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
    """Compute KPI metrics for verification with explicit dev tiers.

    Returns keys: total, avg_ovr, xf, ss, star, norm, elites, elites_pct
    """
    total = len(rows)
    ovrs = [r["ovr"] for r in rows]
    avg_ovr = round(st.mean(ovrs), 2) if ovrs else 0.0
    dev_counts = Counter(r["dev"] for r in rows)
    xf = int(dev_counts.get("3", 0))
    ss = int(dev_counts.get("2", 0))
    star = int(dev_counts.get("1", 0))
    norm = int(dev_counts.get("0", 0))
    elites = xf + ss
    elites_pct = round((100.0 * elites / (total or 1)), 1)
    return {
        "total": int(total),
        "avg_ovr": avg_ovr,
        "xf": xf,
        "ss": ss,
        "star": star,
        "norm": norm,
        "elites": elites,
        "elites_pct": elites_pct,
    }


def parse_html_kpis(html_text: str) -> dict:
    """Extract KPI values from HTML.

    Looks for labels rendered as <b>Label</b><span>VALUE</span>.
    Returns string values for robustness; caller compares appropriately.
    """
    def extract(label: str) -> str | None:
        # tolerate whitespace variations
        m = re.search(rf"<b>\s*{re.escape(label)}\s*</b>\s*<span>([^<]+)</span>", html_text)
        return m.group(1).strip() if m else None

    k: dict[str, str | None] = {}
    k["total"] = extract("Total rookies")
    k["avg_ovr"] = extract("Avg overall")
    # New explicit KPIs
    k["xf"] = extract("X-Factors")
    k["ss"] = extract("Superstars")
    k["star"] = extract("Stars")
    k["norm"] = extract("Normal")  # optional in newer layout

    # Elites share: "<count> (<pct>%)"
    m = re.search(r"<b>\s*Elites share\s*</b>\s*<span>([^<]+)</span>", html_text)
    if m:
        piece = m.group(1).strip()
        m2 = re.match(r"(\d+)\s*\(([-+]?[0-9]*\.?[0-9]+)%\)", piece)
        if m2:
            k["elites"] = m2.group(1)
            k["elites_pct"] = m2.group(2)
        else:
            k["elites"] = None
            k["elites_pct"] = None
    else:
        k["elites"] = None
        k["elites_pct"] = None
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

    # 1) Title/header check (h1 line should include year and 'Analytics Report')
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

    mismatches: list[str] = []
    soft_warnings: list[str] = []

    def cmp_int(key: str, v: int, label: str):
        s = html_kpis.get(key)
        if s is None:
            mismatches.append(f"missing KPI '{label}' in HTML")
            return
        try:
            hv = int(str(s).replace(",", "").strip())
        except Exception:
            hv = None
        if hv != v:
            mismatches.append(f"{label}: expected {v}, found {s}")

    def cmp_float_str(key: str, v: float, label: str):
        s = html_kpis.get(key)
        if s is None or s != str(v):
            mismatches.append(f"{label}: expected {v}, found {s}")

    # Required: total and avg
    cmp_int("total", kpis["total"], "Total rookies")
    cmp_float_str("avg_ovr", kpis["avg_ovr"], "Avg overall")

    # Required: dev KPIs for XF/SS/Star (Normal is optional depending on layout)
    cmp_int("xf", kpis["xf"], "X-Factors")
    cmp_int("ss", kpis["ss"], "Superstars")
    cmp_int("star", kpis["star"], "Stars")
    # Normal KPI: only compare if present in HTML (some layouts omit it from KPIs)
    if html_kpis.get("norm") is not None:
        try:
            hv = int(html_kpis.get("norm"))
        except Exception:
            hv = None
        if hv != kpis["norm"]:
            mismatches.append(f"Normal: expected {kpis['norm']}, found {html_kpis.get('norm')}")

    # Elites share (count and percent)
    elites_count_str = html_kpis.get("elites")
    elites_pct_str = html_kpis.get("elites_pct")
    if elites_count_str is None or elites_pct_str is None:
        mismatches.append("missing KPI 'Elites share' in HTML")
    else:
        # Compare as exact strings
        if elites_count_str != str(kpis["elites"]):
            mismatches.append(f"Elites share (count): expected {kpis['elites']}, found {elites_count_str}")
        if elites_pct_str != str(kpis["elites_pct"]):
            mismatches.append(f"Elites share (%): expected {kpis['elites_pct']}, found {elites_pct_str}")

    # Spotlight title check: allow extended subtitle, but must include key phrase
    if not re.search(r"<div\s+class=\"section-title\"[^>]*>[^<]*Elites Spotlight", html_text, re.IGNORECASE):
        mismatches.append("Spotlight title missing or not 'Elites Spotlight'")

    # Table header checks
    def thead_contains(block_regex: str, required_headers: list[str]) -> bool:
        ok = False
        for m in re.finditer(block_regex, html_text, re.IGNORECASE | re.DOTALL):
            thead_html = m.group(0)
            if all(re.search(rf"<th>\s*{re.escape(h)}\s*</th>", thead_html) for h in required_headers):
                ok = True
                break
        return ok

    # Teams table: requires dev columns present in a thead that has 'Team'
    teams_ok = thead_contains(r"<thead>.*?<th>\s*Team\s*</th>.*?</thead>", ["XF", "SS", "Star", "Norm"])
    if not teams_ok:
        mismatches.append("Teams table header missing dev columns XF/SS/Star/Norm")

    # Positions table: requires dev columns present in a thead that has 'Pos' or 'Position'
    pos_ok = (
        thead_contains(r"<thead>.*?<th>\s*Pos(ition)?\s*</th>.*?</thead>", ["XF", "SS", "Star", "Norm"])
    )
    if not pos_ok:
        mismatches.append("Positions table header missing dev columns XF/SS/Star/Norm")

    # Optional: grading badges presence (class="grade-on|near|below").
    if re.search(r"class=\"grade-(on|near|below)\"", html_text):
        # If any grade badge exists, ensure both XF and SS labels exist nearby
        # (best-effort heuristic; do not fail too aggressively)
        if not re.search(r"XF", html_text) or not re.search(r"SS", html_text):
            soft_warnings.append("grade badges present but XF/SS labels not found near KPIs")
    else:
        # Not present; only warn (layout may omit grades in test HTML)
        soft_warnings.append("grading badges not found; skipping grade checks")

    # Optional: dual rounds sections — only enforce if any rounds title text exists
    rounds_titles = re.findall(r"Hit\s*=\s*([^<]+)", html_text)
    if rounds_titles:
        has_non_norm = any("XF/SS/Star" in t for t in rounds_titles)
        has_elites = any("Elites (XF/SS)" in t for t in rounds_titles)
        if not (has_non_norm and has_elites):
            soft_warnings.append("rounds section present but missing one of the required titles")
    else:
        soft_warnings.append("rounds sections not found; skipping rounds checks")

    if mismatches:
        print("verify: FAILED — mismatches detected:", file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        # Print non-fatal warnings to aid debugging
        for w in soft_warnings:
            print(f"  (note) {w}", file=sys.stderr)
        sys.exit(1)

    # Success — include brief summary
    print(
        f"verify: OK — year {year}, total {kpis['total']}, XF {kpis['xf']}, SS {kpis['ss']}, Star {kpis['star']}, Elites {kpis['elites']} ({kpis['elites_pct']}%), avg {kpis['avg_ovr']}"
    )
    # Print any soft warnings to stdout for visibility (non-fatal)
    for w in soft_warnings:
        print(f"verify: note — {w}")


if __name__ == "__main__":
    main()
