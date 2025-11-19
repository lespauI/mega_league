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
    """Extract KPI values from HTML (new layout, tolerant of nested spans)."""
    def extract_first_number_after_label(label: str) -> str | None:
        pat = rf"<div[^>]*class=\"kpi\"[^>]*>.*?<b>\s*{re.escape(label)}\s*</b>(?P<tail>.*?)</div>"
        m = re.search(pat, html_text, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        tail = m.group('tail')
        m2 = re.search(r"(\d+)", tail)
        return m2.group(1) if m2 else None

    def extract_text_after_label(label: str) -> str | None:
        pat = rf"<div[^>]*class=\"kpi\"[^>]*>.*?<b>\s*{re.escape(label)}\s*</b>(?P<tail>.*?)</div>"
        m = re.search(pat, html_text, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        tail = m.group('tail')
        # first text-like number token (may include dot)
        m2 = re.search(r"([-+]?[0-9]*\.?[0-9]+)", tail)
        return m2.group(1) if m2 else None

    k: dict[str, str | None] = {}
    k["total"] = extract_first_number_after_label("Total rookies")
    k["avg_ovr"] = extract_text_after_label("Avg overall")
    # New explicit KPIs (support both long and short labels)
    k["xf"] = extract_first_number_after_label("X-Factors") or extract_first_number_after_label("XF")
    k["ss"] = extract_first_number_after_label("Superstars") or extract_first_number_after_label("SS")
    k["star"] = extract_first_number_after_label("Stars") or extract_first_number_after_label("Star")
    k["norm"] = extract_first_number_after_label("Normal")  # optional in newer layout

    # Elites share: "<count> (<pct>%)" OR just "<pct>%"
    # Extract elites share from the same KPI block
    share_tail_pat = r"<div[^>]*class=\"kpi\"[^>]*>.*?<b>\s*Elites share\s*</b>(?P<tail>.*?)</div>"
    m = re.search(share_tail_pat, html_text, re.IGNORECASE | re.DOTALL)
    k["elites"] = None
    k["elites_pct"] = None
    if m:
        tail = m.group('tail')
        m2 = re.search(r"(\d+)\s*\(([-+]?[0-9]*\.?[0-9]+)%\)", tail)
        if m2:
            k["elites"] = m2.group(1)
            k["elites_pct"] = m2.group(2)
        else:
            m3 = re.search(r"([-+]?[0-9]*\.?[0-9]+)%", tail)
            if m3:
                k["elites_pct"] = m3.group(1)
    return k


def parse_html_kpis_legacy(html_text: str) -> dict:
    """Extract legacy KPI values (Non‑Normal/Normal and share)."""
    def extract(label: str) -> str | None:
        m = re.search(rf"<b>\s*{re.escape(label)}\s*</b>\s*<span>([^<]+)</span>", html_text)
        return m.group(1).strip() if m else None

    k: dict[str, str | None] = {}
    k["total"] = extract("Total rookies")
    k["avg_ovr"] = extract("Avg overall")
    k["hidden"] = extract("Non‑Normal")
    k["normal"] = extract("Normal")
    m = re.search(r"<b>\s*Non‑Normal share\s*</b>\s*<span>([^<]+)</span>", html_text)
    if m:
        piece = m.group(1).strip()
        m2 = re.match(r"(\d+)\s*\(([-+]?[0-9]*\.?[0-9]+)%\)", piece)
        if m2:
            k["hidden"] = m2.group(1)
            k["hidden_pct"] = m2.group(2)
        else:
            k["hidden_pct"] = None
    else:
        k["hidden_pct"] = None
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
    # Try parsing new KPIs first; if none found, fallback to legacy
    html_kpis_try = parse_html_kpis(html_text)
    has_new_kpis = any(html_kpis_try.get(k) is not None for k in ("xf", "ss", "star"))
    is_new_layout = has_new_kpis
    mismatches: list[str] = []
    soft_warnings: list[str] = []
    html_kpis = html_kpis_try if is_new_layout else parse_html_kpis_legacy(html_text)

    def cmp_int(key: str, v: int, label: str):
        s = html_kpis.get(key)
        if s is None:
            mismatches.append(f"missing KPI '{label}' in HTML")
            return
        # Accept plain ints or values like "123 (45.6%) ..."
        m = re.match(r"\s*(\d+)", str(s))
        hv = int(m.group(1)) if m else None
        if hv != v:
            mismatches.append(f"{label}: expected {v}, found {s}")

    def cmp_float_str(key: str, v: float, label: str):
        s = html_kpis.get(key)
        if s is None or s != str(v):
            mismatches.append(f"{label}: expected {v}, found {s}")

    # Required: total and avg
    cmp_int("total", kpis["total"], "Total rookies")
    cmp_float_str("avg_ovr", kpis["avg_ovr"], "Avg overall")

    if is_new_layout:
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
        if elites_pct_str is None:
            mismatches.append("missing KPI 'Elites share' in HTML")
        else:
            # Compare as exact strings
            if elites_count_str is not None and elites_count_str != str(kpis["elites"]):
                mismatches.append(f"Elites share (count): expected {kpis['elites']}, found {elites_count_str}")
            if elites_pct_str != str(kpis["elites_pct"]):
                mismatches.append(f"Elites share (%): expected {kpis['elites_pct']}, found {elites_pct_str}")
    else:
        # Legacy: Non‑Normal/Normal counts and share
        # Non‑Normal = XF+SS+Star
        hidden_expected = kpis["xf"] + kpis["ss"] + kpis["star"]
        cmp_int("hidden", hidden_expected, "Non‑Normal")
        cmp_int("normal", kpis["norm"], "Normal")
        # Non‑Normal share percent if present
        hidden_pct_str = html_kpis.get("hidden_pct")
        if hidden_pct_str is not None:
            expected_hidden_pct = round(100.0 * hidden_expected / (kpis["total"] or 1), 1)
            if hidden_pct_str != str(expected_hidden_pct):
                mismatches.append(f"Non‑Normal share (%): expected {expected_hidden_pct}, found {hidden_pct_str}")
        # Spotlight title should reference Elites (legacy accepted if present)
        if not re.search(r"<div\s+class=\"section-title\"[^>]*>[^<]*Elites Spotlight", html_text, re.IGNORECASE):
            mismatches.append("Spotlight title missing ('Elites Spotlight' not found)")

    # Table header checks
    def thead_contains(block_regex: str, required_headers: list[str]) -> bool:
        ok = False
        for m in re.finditer(block_regex, html_text, re.IGNORECASE | re.DOTALL):
            thead_html = m.group(0)
            if all(re.search(rf"<th>\s*{re.escape(h)}\s*</th>", thead_html) for h in required_headers):
                ok = True
                break
        return ok

    if is_new_layout:
        # Teams table: requires dev columns present in a thead that has 'Team'
        teams_ok_new = thead_contains(r"<thead>.*?<th>\s*Team\s*</th>.*?</thead>", ["XF", "SS", "Star", "Normal"])
        teams_ok_legacy = thead_contains(r"<thead>.*?<th>\s*Team\s*</th>.*?</thead>", ["Non‑Normal", "Normal"])
        if not (teams_ok_new or teams_ok_legacy):
            mismatches.append("Teams table header missing expected columns (either dev columns or Non‑Normal/Normal)")
        # Positions table: requires dev columns present in a thead that has 'Pos' or 'Position'
        pos_ok = thead_contains(r"<thead>.*?<th>\s*Pos(ition)?\s*</th>.*?</thead>", ["XF", "SS", "Star", "Normal"])
        if not pos_ok:
            mismatches.append("Positions table header missing dev columns XF/SS/Star/Norm")
    else:
        # Legacy teams header requires Non‑Normal/Normal
        teams_ok_legacy = thead_contains(r"<thead>.*?<th>\s*Team\s*</th>.*?</thead>", ["Non‑Normal", "Normal"])
        if not teams_ok_legacy:
            mismatches.append("Legacy teams table header missing Non‑Normal/Normal columns")
        # Positions header may already have dev columns in some legacy files — allow either form
        pos_ok_new = thead_contains(r"<thead>.*?<th>\s*Pos(ition)?\s*</th>.*?</thead>", ["XF", "SS", "Star", "Normal"])
        pos_ok_legacy = thead_contains(r"<thead>.*?<th>\s*Pos(ition)?\s*</th>.*?</thead>", ["Non‑Normal", "Normal"]) or thead_contains(r"<thead>.*?<th>\s*Position\s*</th>.*?</thead>", ["Non‑Normal", "Normal"])
        if not (pos_ok_new or pos_ok_legacy):
            mismatches.append("Positions table header missing expected columns (either dev columns or Non‑Normal/Normal)")

    # Optional: grading badges presence (class="grade-on|near|below").
    if re.search(r"class=\"[^\"]*grade-(on|near|below)[^\"]*\"", html_text):
        # If any grade badge exists, ensure both XF and SS labels exist nearby (best-effort)
        if not re.search(r"XF", html_text) or not re.search(r"SS", html_text):
            soft_warnings.append("grade badges present but XF/SS labels not found near KPIs")
    else:
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
