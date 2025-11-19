#!/usr/bin/env python3
"""
Generate an analytics-focused HTML page for a given draft class.

Focus:
- Show explicit dev trait tiers in UI (XF/SS/Star/Normal)
- Team draft analytics (who picked best OVR, how many rookies, counts by dev)
- Position strength analytics (counts by Non‑Normal/Normal, avg OVR)

Usage:
  python3 scripts/generate_draft_class_analytics.py --year 2026 \
      --players MEGA_players.csv --teams MEGA_teams.csv \
      --out docs/draft_class_2026.html
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import sys
import statistics as st
from collections import Counter


# Internal dev labels (raw).
DEV_LABELS = {"3": "X-Factor", "2": "Superstar", "1": "Star", "0": "Normal"}


def grade_badge(tier: str, pct: float, target: float) -> tuple[str, str]:
    """Return (label, css_class) for KPI grading badges.

    - css_class in {'grade-on','grade-near','grade-below'}
    - On-target: pct >= target
    - Near-target: pct >= 0.75 * target
    - Below-target: otherwise
    """
    try:
        p = float(pct)
        tgt = float(target)
    except Exception:
        p = 0.0
        tgt = 0.0
    if tgt <= 0:
        return ("On-target", "grade-on")
    if p >= tgt:
        return ("On-target", "grade-on")
    if p >= 0.75 * tgt:
        return ("Near-target", "grade-near")
    return ("Below-target", "grade-below")


def read_csv(path: str) -> list[dict]:
    """Read a CSV file returning a list of dict rows.

    - Uses utf-8-sig to tolerate BOMs
    - Raises a clear error message on failure
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            return list(reader)
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"error: failed to read CSV '{path}': {e}", file=sys.stderr)
        sys.exit(2)


def warn_missing_columns(rows: list[dict], required: list[str], context: str) -> None:
    """Warn about missing columns but do not fail.

    Gathers headers from first few rows to detect likely schema issues.
    """
    try:
        headers: set[str] = set()
        for r in rows[:5]:
            headers.update(r.keys())
        missing = [c for c in required if c not in headers]
        if missing:
            print(
                f"warn: {context}: missing column(s): {', '.join(missing)} — using safe fallbacks",
                file=sys.stderr,
            )
    except Exception:
        # Best-effort only; never crash on warnings path
        pass


def safe_int(v, default=None):
    """Best-effort parse of an int value.

    Accepts strings and numeric types; returns default on failure.
    """
    try:
        if v is None:
            return default
        if isinstance(v, int):
            return v
        s = str(v).strip()
        if s == "":
            return default
        # handle floats encoded as strings like "69.0"
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return default


def build_team_logo_map(teams_rows: list[dict]) -> dict:
    """Build a mapping of team names to logoId.

    Maps any of displayName, nickName, or teamName to the team's logoId.
    - Trims whitespace, skips empty/zero logoIds
    - Adds case-insensitive variants to increase match likelihood
    """
    mapping: dict[str, str] = {}
    if not teams_rows:
        return mapping

    for r in teams_rows:
        lid = str(r.get('logoId') or '').strip()
        # Allow '0' as a valid logoId (e.g., Bears => 0.png)
        if lid == '':
            continue

        for key in ('displayName', 'nickName', 'teamName'):
            name = (r.get(key) or '').strip()
            if not name:
                continue
            # Store several variants to be resilient to case/spacing differences
            for variant in {name, name.lower(), name.upper()}:
                mapping[variant] = lid

    return mapping


def gather_rookies(players: list[dict], year: int) -> list[dict]:
    """Filter rookies by year and normalize core fields for analytics.

    Normalization rules:
    - name: fullName > cleanName > firstName + lastName; trimmed
    - team: trimmed; default 'FA' when missing/blank
    - position: trimmed; default '?' when missing/blank
    - ovr: prefer playerBestOvr, then playerSchemeOvr; default 0
    - dev: keep as string in {'3','2','1','0'}; map unknowns to '0'
    - draftRound/draftPick: parsed to ints when available (used in Elites Spotlight)
    - college: if present, used in the meta line instead of current team
    """
    out = []
    for r in players:
        if str(r.get('rookieYear', '')).strip() != str(year):
            continue

        # Overall rating with fallback
        ovr = safe_int(r.get('playerBestOvr'), None)
        if ovr is None:
            ovr = safe_int(r.get('playerSchemeOvr'), 0)
        if ovr is None:
            ovr = 0

        # Dev trait mapping (unknown -> '0')
        dev_raw = r.get('devTrait', '0')
        dev = str(dev_raw).strip() if dev_raw is not None else '0'
        if dev not in DEV_LABELS:
            dev = '0'

        # Name derivation and trimming
        fn = (r.get('fullName') or '').strip()
        cn = (r.get('cleanName') or '').strip()
        first = (r.get('firstName') or '').strip()
        last = (r.get('lastName') or '').strip()
        name = fn or cn or (f"{first} {last}".strip())

        # Team, college, and position normalization
        team = (r.get('team') or '').strip() or 'FA'
        college = (r.get('college') or '').strip()
        pos = (r.get('position') or '').strip() or '?'

        out.append({
            'id': r.get('id'),
            'name': name,
            'team': team,
            'position': pos,
            'ovr': int(ovr),
            'dev': dev,
            'draft_round': safe_int(r.get('draftRound'), None),
            'draft_pick': safe_int(r.get('draftPick'), None),
            'college': college,
        })
    # Deterministic sorting: OVR desc, then name asc
    out.sort(key=lambda x: (-x['ovr'], x['name']))
    return out


def compute_analytics(rows: list[dict]):
    """Compute draft class analytics aggregates.

    KPIs:
    - total rookies
    - avg overall (2 decimals)
    - dev distribution (keys '3','2','1','0')
    - elites (XF+SS) absolute and share percentage

    Aggregates:
    - per team: count, avg_ovr, best_ovr, dev distribution
    - per position: count, avg_ovr, dev distribution

    Sorting rules are applied downstream during rendering, but we also return
    pre-sorted helper lists to make consumption straightforward if needed.
    """
    total = len(rows)

    # Dev distribution normalized to expected keys
    raw_dev_counts = Counter(r['dev'] for r in rows)
    dev_counts = {k: raw_dev_counts.get(k, 0) for k in ('3', '2', '1', '0')}

    ovrs = [r['ovr'] for r in rows]
    avg_ovr = round(st.mean(ovrs), 2) if ovrs else 0.0

    # Team aggregates
    teams: dict[str, dict] = {}
    for r in rows:
        team = r['team']
        t = teams.setdefault(team, {'count': 0, 'sum_ovr': 0, 'best_ovr': 0, 'dev': Counter()})
        t['count'] += 1
        t['sum_ovr'] += r['ovr']
        if r['ovr'] > t['best_ovr']:
            t['best_ovr'] = r['ovr']
        t['dev'][r['dev']] += 1
    for team, t in teams.items():
        t['avg_ovr'] = round((t['sum_ovr'] / t['count']) if t['count'] else 0.0, 2)
        # normalize dev dict to all expected keys
        t['dev'] = {k: t['dev'].get(k, 0) for k in ('3', '2', '1', '0')}
        # drop helper
        del t['sum_ovr']

    # Position aggregates
    positions: dict[str, dict] = {}
    for r in rows:
        pos = r['position']
        p = positions.setdefault(pos, {'count': 0, 'sum_ovr': 0, 'dev': Counter()})
        p['count'] += 1
        p['sum_ovr'] += r['ovr']
        p['dev'][r['dev']] += 1
    for pos, p in positions.items():
        p['avg_ovr'] = round((p['sum_ovr'] / p['count']) if p['count'] else 0.0, 2)
        p['dev'] = {k: p['dev'].get(k, 0) for k in ('3', '2', '1', '0')}
        del p['sum_ovr']

    # Elites spotlight (data only; HTML cards built in renderer)
    elites = sorted(
        (r for r in rows if r['dev'] in ('3', '2')),
        key=lambda r: (-int(r['dev']), -int(r['ovr']), r['name'])
    )
    elites_count = dev_counts['3'] + dev_counts['2']
    elite_share_pct = round((100.0 * elites_count / total), 1) if total else 0.0

    # Percentages by tier
    def pct(v: int, denom: int) -> float:
        return round(100.0 * v / denom, 1) if denom else 0.0

    xf_pct = pct(dev_counts['3'], total)
    ss_pct = pct(dev_counts['2'], total)
    star_pct = pct(dev_counts['1'], total)
    norm_pct = pct(dev_counts['0'], total)

    # Grading (targets: XF ≥10%, SS ≥15%)
    xf_grade_label, xf_grade_class = grade_badge('xf', xf_pct, 10.0)
    ss_grade_label, ss_grade_class = grade_badge('ss', ss_pct, 15.0)

    # Pre-sorted helper views (not strictly required by renderer)
    teams_sorted = sorted(teams.items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0]))
    positions_sorted = sorted(positions.items(), key=lambda kv: (-kv[1]['avg_ovr'], -kv[1]['count'], kv[0]))

    # Per-team per-round hits/misses
    # Only include rows with a known draft_round
    rounds_present: set[int] = set()
    team_rounds: dict[str, dict[int, dict[str, int]]] = {}
    team_rounds_elites: dict[str, dict[int, dict[str, int]]] = {}
    for r in rows:
        rd = r.get('draft_round')
        if rd is None:
            continue
        try:
            rdv = int(rd)
        except Exception:
            continue
        rounds_present.add(rdv)
        team = r['team']
        cell = team_rounds.setdefault(team, {}).setdefault(rdv, {'hit': 0, 'total': 0})
        cell['total'] += 1
        if r['dev'] in ('3', '2', '1'):
            cell['hit'] += 1
        # elites-only aggregation mirrors totals, counts hits for XF/SS only
        cell_e = team_rounds_elites.setdefault(team, {}).setdefault(rdv, {'hit': 0, 'total': 0})
        cell_e['total'] += 1
        if r['dev'] in ('3', '2'):
            cell_e['hit'] += 1
    rounds_sorted = sorted(rounds_present)

    return {
        'total': total,
        'avg_ovr': avg_ovr,
        'dev_counts': raw_dev_counts,  # keep Counter for compatibility in renderer
        'dev_counts_norm': dev_counts,  # normalized dict if needed elsewhere
        'elite_count': elites_count,
        'elite_share_pct': elite_share_pct,
        'elites': elites,
        # KPI percentages
        'xf_pct': xf_pct,
        'ss_pct': ss_pct,
        'star_pct': star_pct,
        'norm_pct': norm_pct,
        # Grades
        'xf_grade': 'on' if xf_grade_class.endswith('on') else ('near' if xf_grade_class.endswith('near') else 'below'),
        'ss_grade': 'on' if ss_grade_class.endswith('on') else ('near' if ss_grade_class.endswith('near') else 'below'),
        'xf_grade_label': xf_grade_label,
        'ss_grade_label': ss_grade_label,
        'xf_grade_class': xf_grade_class,
        'ss_grade_class': ss_grade_class,
        'teams': teams,
        'teams_sorted': teams_sorted,
        'positions': positions,
        'positions_sorted': positions_sorted,
        'team_rounds': team_rounds,
        'team_rounds_elites': team_rounds_elites,
        'rounds_sorted': rounds_sorted,
    }


def badge_for_dev(dev: str) -> str:
    # Render explicit dev tiers
    mapping = {
        '3': ('X-Factor', 'dev-xf'),
        '2': ('Superstar', 'dev-ss'),
        '1': ('Star', 'dev-star'),
        '0': ('Normal', 'dev-norm'),
    }
    label, cls = mapping.get(str(dev), ('Normal', 'dev-norm'))
    return f'<span class="dev-badge {cls}">{html.escape(label)}</span>'


def generate_html(year: int, rows: list[dict], analytics: dict, team_logo_map: dict, *, title_suffix: str | None = None, title_override: str | None = None) -> str:
    elites = [r for r in rows if r['dev'] in ('3','2')]
    # Order cards by draft pick: round asc, pick asc; missing picks last
    def elite_sort_key(r: dict):
        rd = r.get('draft_round')
        pk = r.get('draft_pick')
        missing = 0 if (rd is not None and pk is not None) else 1
        rdv = int(rd) if rd is not None else 999
        pkv = int(pk) if pk is not None else 999
        return (missing, rdv, pkv, -int(r['ovr']), r['name'])
    elites.sort(key=elite_sort_key)

    def logo_img(team: str) -> str:
        # Try exact then case-insensitive lookup
        lid = team_logo_map.get(team) or team_logo_map.get(team.lower()) or team_logo_map.get(team.upper())
        if not lid:
            return ''
        return f'<img class="logo" src="https://cdn.neonsportz.com/teamlogos/256/{lid}.png" alt="{html.escape(team)}" />'

    # Small, colorful position chip
    def pos_chip(pos: str) -> str:
        p = (pos or '?').upper()
        # Group common positions into color families for consistent styling
        if p in {'LT','LG','RT','RG','T','G','C','OL'}:
            cls = 'OL'
        elif p in {'DE','DT','RE','LE','DL'}:
            cls = 'DL'
        elif p in {'MLB','LOLB','ROLB','OLB','LB'}:
            cls = 'LB'
        elif p in {'CB','FS','SS','DB'}:
            cls = 'DB'
        elif p in {'HB','RB','FB','WR','TE'}:
            cls = p  # direct mapping available in CSS rules
        elif p in {'QB','K','P'}:
            cls = p
        elif p == '?':
            cls = '?'
        else:
            cls = 'UNK'
        return f'<span class="pos-chip pos-{html.escape(cls)}">{html.escape(p)}</span>'

    elite_cards = []
    for r in elites:
        # Round.pick badge when both are present (e.g., 1.7)
        rd = r.get('draft_round')
        pk = r.get('draft_pick')
        pick_badge = f"<span class=\"pick-badge\">{int(rd)}.{int(pk)}</span>" if (rd is not None and pk is not None) else ""
        ovr_badge = f"<span class=\"ovr-badge\">OVR {int(r['ovr'])}</span>"
        school = (r.get('college') or '').strip() or r['team']

        elite_cards.append(
            (
                '<div class="player">'
                f"<div class=\"hdr\">{logo_img(r['team'])}<div class=\"tags\">{ovr_badge}{pick_badge}</div></div>"
                f"<div class=\"nm\">{html.escape(r['name'])}</div>"
                f"<div class=\"dev\">{badge_for_dev(r['dev'])}</div>"
                f"<div class=\"meta\">{pos_chip(r['position'])}<span class=\"dot\">·</span>{html.escape(school)}</div>"
                '</div>'
            )
        )
    elite_cards_html = '\n'.join(elite_cards) if elite_cards else "<div class='muted'>No X-Factor or Superstar rookies.</div>"

    # Teams tables
    team_rows = []
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        dev = stats['dev']
        xf = dev.get('3', 0)
        ss = dev.get('2', 0)
        star = dev.get('1', 0)
        normal = dev.get('0', 0)
        team_rows.append(
            (
                '<tr>'
                f"<td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>"
                f"<td class='num'>{xf}</td>"
                f"<td class='num'>{ss}</td>"
                f"<td class='num'>{star}</td>"
                f"<td class='num'>{normal}</td>"
                f"<td class='num'>{stats['count']}</td>"
                f"<td class='num'>{stats['avg_ovr']:.2f}</td>"
                f"<td class='num'>{stats['best_ovr']}</td>"
                '</tr>'
            )
        )
    team_table_html = '\n'.join(team_rows)

    # Most elites: XF + SS
    team_hidden_rows = []
    for team, stats in sorted(
        analytics['teams'].items(),
        key=lambda kv: (-(kv[1]['dev'].get('3', 0) + kv[1]['dev'].get('2', 0)), kv[0])
    ):
        elites = stats['dev'].get('3', 0) + stats['dev'].get('2', 0)
        team_hidden_rows.append(
            f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td><td class='num'>{elites}</td><td class='num'>{stats['count']}</td><td class='num'>{stats['avg_ovr']:.2f}</td></tr>"
        )
    team_hiddens_html = '\n'.join(team_hidden_rows)

    # Positions table
    pos_rows = []
    for pos, stats in sorted(analytics['positions'].items(), key=lambda kv: (-kv[1]['avg_ovr'], -kv[1]['count'], kv[0])):
        dev = stats['dev']
        xf = dev.get('3', 0)
        ss = dev.get('2', 0)
        star = dev.get('1', 0)
        normal = dev.get('0', 0)
        pos_rows.append(
            (
                '<tr>'
                f"<td>{html.escape(pos)}</td>"
                f"<td class='num'>{xf}</td>"
                f"<td class='num'>{ss}</td>"
                f"<td class='num'>{star}</td>"
                f"<td class='num'>{normal}</td>"
                f"<td class='num'>{stats['count']}</td>"
                f"<td class='num'>{stats['avg_ovr']:.2f}</td>"
                '</tr>'
            )
        )
    pos_table_html = '\n'.join(pos_rows)

    total = analytics['total'] or 1
    xf_total = analytics['dev_counts'].get('3',0)
    ss_total = analytics['dev_counts'].get('2',0)
    star_total = analytics['dev_counts'].get('1',0)
    norm_total = analytics['dev_counts'].get('0',0)
    elites_total = xf_total + ss_total

    # Elite-heavy positions summary (show XF and SS separately)
    pos_elite_sorted = []
    for p in analytics['positions']:
        d = analytics['positions'][p]['dev']
        xf_c = d.get('3',0)
        ss_c = d.get('2',0)
        star_c = d.get('1',0)
        pos_elite_sorted.append((p, xf_c, ss_c, star_c, xf_c+ss_c))
    pos_elite_sorted.sort(key=lambda x: (-x[4], -x[3], x[0]))
    top_pos_lines = []
    for p, xf_c, ss_c, star_c, elite_total in pos_elite_sorted[:6]:
        # Do not reveal tiers in text; summarize as Hidden count
        hidden = xf_c + ss_c + star_c
        top_pos_lines.append(f"<li><b>{html.escape(p)}</b>: {hidden} Hidden</li>")
    top_pos_html = '\n'.join(top_pos_lines)

    html_out = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>__PAGE_TITLE__</title>
  <style>
    :root { --text:#0f172a; --sub:#64748b; --muted:#94a3b8; --grid:#e2e8f0; --bg:#f7f7f7; --card:#ffffff; --accent:#3b82f6; }
    body { margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }
    .topbar { max-width: 1200px; margin: 0 auto 10px; display:flex; align-items:center; gap:10px; }
    .back { display:inline-flex; align-items:center; gap:8px; font-size:13px; color:#1e293b; text-decoration:none; background:#fff; border:1px solid #e5e7eb; padding:6px 10px; border-radius:8px; box-shadow:0 1px 2px rgba(0,0,0,.05); }
    .back:hover { background:#f8fafc; }
    .container { max-width: 1200px; margin: 0 auto; background: var(--card); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow:hidden; }
    header { padding: 18px 20px 8px; border-bottom: 1px solid #ececec; background:linear-gradient(180deg,#ffffff 0%,#fafafa 100%); }
    h1 { margin:0; font-size: 22px; }
    .subtitle { color: var(--sub); margin:8px 0 6px; font-size: 13px; }
    .pill { display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px; border:1px solid #bfdbfe; background:#dbeafe; color:#1e3a8a; font-size:12px; }

    .panel { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
    .kpis { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 10px; }
    .kpi { background:#f8fafc; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; transition: box-shadow .15s ease; }
    .kpi:hover { box-shadow:0 2px 6px rgba(0,0,0,.06); }
    .kpi b { display:block; font-size: 12px; color:#0f172a; }
    .kpi span { color:#334155; font-size: 18px; font-weight: 700; }
    .kpi .gbar { margin-top:6px; height:6px; background:#e5e7eb; border-radius:999px; overflow:hidden; }
    .kpi .gbar .fill { height:100%; background: linear-gradient(90deg, #60a5fa, #22c55e); }

    .section-title { font-size: 14px; font-weight: 700; margin: 0 0 10px; border-left:3px solid var(--accent); padding-left:8px; }
    .grid { display:grid; grid-template-columns: 1.7fr 1.3fr; gap: 12px; }
    .card { background:#fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
    .card h3 { margin: 0 0 8px; font-size: 14px; color:#0f172a; }

    .players { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
    .player { border:1px solid var(--grid); border-radius:10px; padding:10px; background:#fff; transition: transform .12s ease, box-shadow .12s ease; }
    .player:hover { transform: translateY(-2px); box-shadow: 0 3px 10px rgba(0,0,0,.06); }
    .player .hdr { display:flex; align-items:center; }
    .player .logo { width:22px; height:22px; border-radius:4px; box-shadow:0 0 0 1px rgba(0,0,0,.06); }
    .player .tags { margin-left:auto; display:flex; align-items:center; gap:6px; }
    .player .nm { font-weight: 600; margin-top: 2px; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
    .player .meta { color:#475569; font-size: 12px; margin-top: 2px; display:flex; align-items:center; gap:8px; }
    .player .ovr { display:none; }
    .player .dev { margin-top: 4px; }
    .player .pick-badge { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; background:#e0f2fe; color:#075985; border:1px solid #bae6fd; }
    .player .ovr-badge { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; background:#dcfce7; color:#166534; border:1px solid #bbf7d0; }
    .muted { color: var(--muted); }
    .pos-chip { display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid transparent; }
    .pos-QB { background:#fee2e2; color:#991b1b; border-color:#fecaca; }
    .pos-HB, .pos-RB, .pos-FB, .pos-WR, .pos-TE { background:#dbeafe; color:#1e3a8a; border-color:#bfdbfe; }
    .pos-T, .pos-G, .pos-C, .pos-OL { background:#ede9fe; color:#5b21b6; border-color:#ddd6fe; }
    .pos-DE, .pos-DT, .pos-DL { background:#fef3c7; color:#92400e; border-color:#fde68a; }
    .pos-MLB, .pos-LOLB, .pos-ROLB, .pos-LB { background:#dcfce7; color:#166534; border-color:#bbf7d0; }
    .pos-CB, .pos-FS, .pos-SS, .pos-DB { background:#e0f2fe; color:#075985; border-color:#bae6fd; }
    .pos-K, .pos-P { background:#f1f5f9; color:#0f172a; border-color:#e2e8f0; }
    .pos-UNK, .pos-? { background:#e5e7eb; color:#374151; border-color:#d1d5db; }

    table { width:100%; border-collapse: collapse; }
    thead tr { background:#fafafa; }
    tbody tr:nth-child(odd) { background: #fcfcfd; }
    tbody tr:hover { background:#f6faff; }
    th, td { padding: 8px 8px; border-bottom: 1px solid var(--grid); font-size: 13px; text-align:center; }
    th { color:#475569; font-size:12px; user-select:none; }
    table.sortable th { cursor:pointer; }
    td.num { text-align:center; font-variant-numeric: tabular-nums; }
    td.team { display:flex; align-items:center; justify-content:center; gap:8px; }
    td.team img.logo { width:18px; height:18px; border-radius:4px; box-shadow:0 0 0 1px rgba(0,0,0,.05); }

    .dev-badge { display:inline-block; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:600; }
    .dev-xf { background:#fee2e2; color:#991b1b; border:1px solid #fecaca; }
    .dev-ss { background:#dbeafe; color:#1e3a8a; border:1px solid #bfdbfe; }
    .dev-star { background:#fef3c7; color:#92400e; border:1px solid #fde68a; }
    .dev-norm { background:#e5e7eb; color:#374151; border:1px solid #d1d5db; }
    /* Grade badges */
    .grade { display:inline-block; margin-left:6px; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid transparent; }
    .grade-on { background:#dcfce7; color:#166534; border-color:#bbf7d0; }
    .grade-near { background:#fef3c7; color:#92400e; border-color:#fde68a; }
    .grade-below { background:#fee2e2; color:#991b1b; border-color:#fecaca; }

    /* Round hit/miss visualization */
    .rounds-table th.rcol { text-align:center; }
    .round-cell { width: 60px; height: 16px; position: relative; background:#f3f4f6; border:1px solid #e5e7eb; border-radius:6px; overflow:hidden; }
    .round-cell .hit { height:100%; background:#86efac; }
    .round-cell.low .hit { background:#fcd34d; }
    .round-cell.med .hit { background:#a3e635; }
    .round-cell.high .hit { background:#22c55e; }
    .round-cell.zero .hit { background:#e5e7eb; }
    .round-cell .label { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:11px; color:#334155; }
    .rounds-table td.empty { background:#fafafa; }

    /* Sticky sub-nav */
    .subnav { position: sticky; top: 0; z-index: 20; background: rgba(255,255,255,.92); backdrop-filter: saturate(120%) blur(6px); border-bottom: 1px solid #eef2f7; padding: 8px 12px; display:flex; flex-wrap:wrap; gap: 8px; }
    .subnav a { text-decoration:none; font-size:12px; color:#0f172a; background:#f1f5f9; border:1px solid #e2e8f0; padding:6px 10px; border-radius:999px; }
    .subnav a:hover { background:#e2e8f0; }

    /* Responsive tweaks */
    @media (max-width: 1100px) {
      .players { grid-template-columns: repeat(3, minmax(0,1fr)); }
    }
    @media (max-width: 800px) {
      .grid { grid-template-columns: 1fr; }
      .players { grid-template-columns: repeat(2, minmax(0,1fr)); }
      .kpis { grid-template-columns: repeat(3, minmax(0,1fr)); }
    }
    @media (max-width: 520px) {
      .players { grid-template-columns: 1fr; }
      .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); }
    }
  </style>
  <script>
  // Simple table sorter: click any <th> in a .sortable table to sort by that column
  (function() {
    function getCellValue(tr, idx) {
      const td = tr.children[idx];
      if (!td) return '';
      // Prefer data-sort attribute when provided
      const ds = td.getAttribute('data-sort');
      const txt = ds != null ? ds : td.textContent || '';
      return txt.trim();
    }

    function asNumber(v) {
      if (v === '' || v == null) return NaN;
      const n = parseFloat(v.replace(/[,\s]/g, ''));
      return isNaN(n) ? NaN : n;
    }

    function makeComparer(idx, asc) {
      return function(a, b) {
        const va = getCellValue(a, idx);
        const vb = getCellValue(b, idx);
        const na = asNumber(va);
        const nb = asNumber(vb);
        let cmp;
        if (!isNaN(na) && !isNaN(nb)) {
          cmp = na - nb;
        } else {
          cmp = va.localeCompare(vb, undefined, {numeric:true, sensitivity:'base'});
        }
        return asc ? cmp : -cmp;
      }
    }

    function initSortableTables() {
      document.querySelectorAll('table.sortable').forEach(function(table) {
        const thead = table.tHead;
        if (!thead) return;
        const headers = thead.rows[0]?.cells || [];
        Array.from(headers).forEach(function(th, idx) {
          th.addEventListener('click', function() {
            const tbody = table.tBodies[0];
            if (!tbody) return;
            const rows = Array.from(tbody.rows);
            const current = th.getAttribute('data-sort-dir') || 'desc';
            const nextDir = current === 'asc' ? 'desc' : 'asc';
            rows.sort(makeComparer(idx, nextDir === 'asc'));
            // Update attributes for visual state (optional)
            Array.from(headers).forEach(h => h.removeAttribute('data-sort-dir'));
            th.setAttribute('data-sort-dir', nextDir);
            // Re-append rows
            rows.forEach(r => tbody.appendChild(r));
          });
        });
      });
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initSortableTables);
    } else {
      initSortableTables();
    }
  })();
  </script>
</head>
<body>
  <div class=\"topbar\"><a class=\"back\" href=\"../index.html\" title=\"Back to index\">&#8592; Back to Index</a></div>
  <div class=\"container\"> 
    <header>
      <h1>Draft Class __YEAR__ — Analytics Report <span class=\"pill\">__YEAR__</span></h1>
      <div class=\"subtitle\">Elites spotlight + team and position strength analytics</div>
    </header>

    <nav class=\"subnav\">
      <a href=\"#kpis\">KPIs</a>
      <a href=\"#spotlight\">Spotlight</a>
      <a href=\"#teams\">Teams</a>
      <a href=\"#rounds\">Rounds</a>
      <a href=\"#positions\">Positions</a>
    </nav>

    <section id=\"kpis\" class=\"panel\"> 
      <div class=\"kpis\"> 
        <div class=\"kpi\"><b>Total rookies</b><span>__TOTAL__</span></div>
        <div class=\"kpi\"><b>Avg overall</b><span>__AVG_OVR__</span></div>
        <div class=\"kpi\"><b>XF</b><span>__XF__ (__XF_PCT__%) <span class=\"grade __XF_GRADE_CLASS__\">__XF_GRADE_LABEL__</span></span></div>
        <div class=\"kpi\"><b>SS</b><span>__SS__ (__SS_PCT__%) <span class=\"grade __SS_GRADE_CLASS__\">__SS_GRADE_LABEL__</span></span></div>
        <div class=\"kpi\"><b>Star</b><span>__STAR__ (__STAR_PCT__%)</span></div>
        <div class=\"kpi\"><b>Normal</b><span>__NORMAL__ (__NORM_PCT__%)</span></div>
        <div class=\"kpi\"><b>Elites share</b><span>__ELITES_PCT__%</span><div class=\"gbar\"><div class=\"fill\" style=\"width: __ELITES_PCT__%;\"></div></div></div>
      </div>
    </section>

    <section id=\"spotlight\" class=\"panel\"> 
      <div class=\"section-title\">Hidden Spotlight</div>
      <div class=\"players\">__ELITE_CARDS__</div>
    </section>

    <section id=\"teams\" class=\"panel\"> 
      <div class=\"grid\"> 
        <div class=\"card\"> 
          <h3>Team draft quality — by Avg OVR</h3>
          <table class=\"sortable\">
            <thead><tr><th>Team</th><th>XF</th><th>SS</th><th>Star</th><th>Normal</th><th>#</th><th>Avg OVR</th><th>Best OVR</th></tr></thead>
            <tbody>__TEAM_TABLE__</tbody>
          </table>
        </div>
        <div class=\"card\"> 
          <h3>Most elites (XF+SS) — by team</h3>
          <table class=\"sortable\">
            <thead><tr><th>Team</th><th>Elites</th><th>#</th><th>Avg OVR</th></tr></thead>
            <tbody>__TEAM_HIDDENS__</tbody>
          </table>
          <p class=\"muted\" style=\"margin-top:6px;\">Note: based on current team on roster.</p>
        </div>
      </div>
    </section>

    <section id=\"rounds\" class=\"panel\">
      <div class=\"card\">
        <h3>Per-Round Hits by Team — Hit = XF/SS/Star</h3>
        <table class=\"rounds-table\">
          <thead>
            <tr>
              <th>Team</th>
              __ROUND_HEADERS__
            </tr>
          </thead>
          <tbody>
            __ROUND_ROWS__
          </tbody>
        </table>
        <p class=\"muted\" style=\"margin-top:6px;\">Hit counts include XF/SS/Star (non-Normal). Cells show Hit/Total with a bar; empty = no picks.</p>
      </div>
      <div class=\"card\" style=\"margin-top:16px;\">\n        <h3>Per-Round Hits by Team — Hit = Elites (XF/SS)</h3>\n        <table class=\"rounds-table\">\n          <thead>\n            <tr>\n              <th>Team</th>\n              __ROUND_HEADERS__\n            </tr>\n          </thead>\n          <tbody>\n            __ROUND_ROWS_ELITES__\n          </tbody>\n        </table>\n        <p class=\"muted\" style=\"margin-top:6px;\">Elites include only X-Factor and Superstar devs. Cells show Hit/Total with a bar; empty = no picks.</p>\n      </div>
    </section>

    <section id=\"positions\" class=\"panel\"> 
      <div class=\"grid\"> 
        <div class=\"card\"> 
          <h3>Position strength</h3>
          <table class=\"sortable\">
            <thead><tr><th>Position</th><th>XF</th><th>SS</th><th>Star</th><th>Normal</th><th>Total</th><th>Avg OVR</th></tr></thead>
            <tbody>__POS_TABLE__</tbody>
          </table>
        </div>
        <div class=\"card\"> 
          <h3>Hidden-heavy positions</h3>
          <ul>__TOP_POS__</ul>
          <p class=\"muted\" style=\"margin-top:6px;\">Hidden = X-Factor + Superstar + Star</p>
        </div>
      </div>
    </section>

  </div>
</body>
</html>
"""
    # Page title computation with optional branding (safe for verifier)
    if title_override:
        page_title = title_override
    else:
        page_title = f"Draft Class {year} — Analytics"
        if title_suffix:
            page_title = f"{page_title} — {title_suffix}"

    # Inject values
    html_out = html_out.replace('__PAGE_TITLE__', html.escape(page_title))
    html_out = html_out.replace('__YEAR__', str(year))
    html_out = html_out.replace('__TOTAL__', str(total))
    html_out = html_out.replace('__AVG_OVR__', str(analytics['avg_ovr']))
    # KPI numbers and percentages
    html_out = html_out.replace('__XF__', str(xf_total))
    html_out = html_out.replace('__SS__', str(ss_total))
    html_out = html_out.replace('__STAR__', str(star_total))
    html_out = html_out.replace('__NORMAL__', str(norm_total))
    html_out = html_out.replace('__XF_PCT__', str(analytics.get('xf_pct', 0.0)))
    html_out = html_out.replace('__SS_PCT__', str(analytics.get('ss_pct', 0.0)))
    html_out = html_out.replace('__STAR_PCT__', str(analytics.get('star_pct', 0.0)))
    html_out = html_out.replace('__NORM_PCT__', str(analytics.get('norm_pct', 0.0)))
    # Grades
    html_out = html_out.replace('__XF_GRADE_LABEL__', html.escape(analytics.get('xf_grade_label', '')))
    html_out = html_out.replace('__SS_GRADE_LABEL__', html.escape(analytics.get('ss_grade_label', '')))
    html_out = html_out.replace('__XF_GRADE_CLASS__', html.escape(analytics.get('xf_grade_class', 'grade-below')))
    html_out = html_out.replace('__SS_GRADE_CLASS__', html.escape(analytics.get('ss_grade_class', 'grade-below')))
    # Elites share
    html_out = html_out.replace('__ELITES_PCT__', str(analytics.get('elite_share_pct', 0.0)))
    html_out = html_out.replace('__ELITE_CARDS__', elite_cards_html)
    html_out = html_out.replace('__TEAM_TABLE__', team_table_html)
    html_out = html_out.replace('__TEAM_HIDDENS__', team_hiddens_html)
    html_out = html_out.replace('__POS_TABLE__', pos_table_html)
    html_out = html_out.replace('__TOP_POS__', top_pos_html)
    # Round-by-team hidden/miss table injection
    rounds = analytics.get('rounds_sorted', [])
    # Limit the number of columns to keep layout sane (e.g., first 7 rounds)
    rounds = [r for r in rounds if isinstance(r, int)]
    rounds = sorted(rounds)[:10]
    if rounds:
        hdr_cells = ''.join([f"<th class='rcol'>R{int(r)}</th>" for r in rounds])
    else:
        hdr_cells = "<th class='rcol'>R1</th>"
    html_out = html_out.replace('__ROUND_HEADERS__', hdr_cells)

    team_rounds = analytics.get('team_rounds', {})
    round_rows = []
    # Keep team ordering similar to overall team table (by avg OVR desc)
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        cells = []
        per_team = team_rounds.get(team, {})
        for r in rounds:
            cell = per_team.get(r)
            if not cell:
                cells.append("<td class='empty' title='No pick'></td>")
                continue
            hit = int(cell.get('hit', 0))
            total = int(cell.get('total', 0))
            pct = int(round(100.0 * hit / total)) if total else 0
            rate_cls = 'high' if pct >= 75 else ('med' if pct >= 40 else ('low' if pct > 0 else 'zero'))
            bar = (
                f"<div class='round-cell {rate_cls}' title='Hit {hit} of {total}'>"
                f"<div class='hit' style='width:{pct}%'></div>"
                f"<div class='label'>{hit}/{total}</div>"
                f"</div>"
            )
            cells.append(f"<td>{bar}</td>")
        row_html = f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>{''.join(cells)}</tr>"
        round_rows.append(row_html)
    html_out = html_out.replace('__ROUND_ROWS__', '\n'.join(round_rows))
    # Elites-only round table rows
    team_rounds_elites = analytics.get('team_rounds_elites', {})
    round_rows_elites = []
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        cells = []
        per_team = team_rounds_elites.get(team, {})
        for r in rounds:
            cell = per_team.get(r)
            if not cell:
                cells.append("<td class='empty' title='No pick'></td>")
                continue
            hit = int(cell.get('hit', 0))
            total = int(cell.get('total', 0))
            pct = int(round(100.0 * hit / total)) if total else 0
            rate_cls = 'high' if pct >= 75 else ('med' if pct >= 40 else ('low' if pct > 0 else 'zero'))
            bar = (
                f"<div class='round-cell {rate_cls}' title='Elites {hit} of {total}'>"
                f"<div class='hit' style='width:{pct}%'></div>"
                f"<div class='label'>{hit}/{total}</div>"
                f"</div>"
            )
            cells.append(f"<td>{bar}</td>")
        row_html = f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>{''.join(cells)}</tr>"
        round_rows_elites.append(row_html)
    html_out = html_out.replace('__ROUND_ROWS_ELITES__', '\n'.join(round_rows_elites))
    return html_out


def main():
    ap = argparse.ArgumentParser(description='Generate Draft Class Analytics HTML')
    ap.add_argument('--year', type=int, required=True, help='Draft class year (e.g., 2026)')
    ap.add_argument('--players', default='MEGA_players.csv', help='Path to players CSV (default: MEGA_players.csv)')
    ap.add_argument('--teams', default='MEGA_teams.csv', help='Path to teams CSV (default: MEGA_teams.csv)')
    ap.add_argument('--out', default=None, help='Output HTML path (default: docs/draft_class_<year>.html)')
    ap.add_argument('--league-prefix', default='MEGA League', help='Optional league/brand suffix for <title>')
    ap.add_argument('--title', dest='title_override', default=None, help='Optional full page <title> override string')
    args = ap.parse_args()

    out_path = args.out or os.path.join('docs', f'draft_class_{args.year}.html')

    players = read_csv(args.players)
    # Non-fatal schema warnings for players CSV
    warn_missing_columns(
        players,
        required=['rookieYear', 'playerBestOvr', 'playerSchemeOvr', 'devTrait', 'fullName', 'team', 'position'],
        context='players CSV',
    )

    # Teams are optional; if missing, proceed without logos
    teams = []
    if os.path.exists(args.teams):
        try:
            teams = read_csv(args.teams)
        except SystemExit:
            # read_csv already handled printing; continue without logos
            teams = []
    else:
        print(f"warn: teams CSV not found: {args.teams} — continuing without logos", file=sys.stderr)
    team_logo_map = build_team_logo_map(teams)

    rookies = gather_rookies(players, args.year)
    analytics = compute_analytics(rookies)
    html_out = generate_html(
        args.year, rookies, analytics, team_logo_map,
        title_suffix=args.league_prefix, title_override=args.title_override,
    )

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html_out)
    except Exception as e:
        print(f"error: failed to write output HTML '{out_path}': {e}", file=sys.stderr)
        sys.exit(2)

    print(f'Generated: {out_path}')
    print(f"Rookies: {analytics['total']} | Avg OVR: {analytics['avg_ovr']}")


if __name__ == '__main__':
    main()
