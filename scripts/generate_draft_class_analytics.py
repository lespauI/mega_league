#!/usr/bin/env python3
"""
Generate an analytics-focused HTML page for a given draft class.

Focus:
- Show ONLY elite rookies (X-Factor + Superstar)
- Team draft analytics (who picked best OVR, how many rookies, elite counts)
- Position strength analytics (counts by dev trait, avg OVR)

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


DEV_LABELS = {"3": "X-Factor", "2": "Superstar", "1": "Star", "0": "Normal"}


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
        if not lid or lid == '0':
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

        # Team and position normalization
        team = (r.get('team') or '').strip() or 'FA'
        pos = (r.get('position') or '').strip() or '?'

        out.append({
            'id': r.get('id'),
            'name': name,
            'team': team,
            'position': pos,
            'ovr': int(ovr),
            'dev': dev,
        })
    # Deterministic sorting: OVR desc, then name asc
    out.sort(key=lambda x: (-x['ovr'], x['name']))
    return out


def compute_analytics(rows: list[dict]):
    total = len(rows)
    dev_counts = Counter(r['dev'] for r in rows)
    pos_counts = Counter(r['position'] for r in rows)
    team_counts = Counter(r['team'] for r in rows)
    ovrs = [r['ovr'] for r in rows]
    avg_ovr = round(st.mean(ovrs), 2) if ovrs else 0

    teams = {}
    for team in sorted(team_counts):
        trs = [r for r in rows if r['team'] == team]
        tovrs = [r['ovr'] for r in trs]
        teams[team] = {
            'count': len(trs),
            'avg_ovr': round(st.mean(tovrs), 2) if tovrs else 0,
            'best_ovr': max(tovrs) if tovrs else 0,
            'dev': Counter(r['dev'] for r in trs),
        }

    positions = {}
    for pos in sorted(pos_counts):
        prs = [r for r in rows if r['position'] == pos]
        povrs = [r['ovr'] for r in prs]
        positions[pos] = {
            'count': len(prs),
            'avg_ovr': round(st.mean(povrs), 2) if povrs else 0,
            'dev': Counter(r['dev'] for r in prs),
        }

    return {
        'total': total,
        'avg_ovr': avg_ovr,
        'dev_counts': dev_counts,
        'teams': teams,
        'positions': positions,
    }


def badge_for_dev(dev: str) -> str:
    label = DEV_LABELS.get(dev, 'Normal')
    cls = {'3':'dev-xf','2':'dev-ss','1':'dev-star','0':'dev-norm'}.get(dev,'dev-norm')
    return f'<span class="dev-badge {cls}">{html.escape(label)}</span>'


def generate_html(year: int, rows: list[dict], analytics: dict, team_logo_map: dict) -> str:
    elites = [r for r in rows if r['dev'] in ('3','2')]
    elites.sort(key=lambda r: (-int(r['dev']), -int(r['ovr']), r['name']))

    def logo_img(team: str) -> str:
        # Try exact then case-insensitive lookup
        lid = team_logo_map.get(team) or team_logo_map.get(team.lower()) or team_logo_map.get(team.upper())
        if not lid:
            return ''
        return f'<img class="logo" src="https://cdn.neonsportz.com/teamlogos/256/{lid}.png" alt="{html.escape(team)}" />'

    elite_cards = []
    for r in elites:
        elite_cards.append(
            (
                '<div class="player">'
                f"{logo_img(r['team'])}"
                f"<div class=\"nm\">{html.escape(r['name'])}</div>"
                f"<div class=\"meta\">{html.escape(r['position'])} · {html.escape(r['team'])}</div>"
                f"<div class=\"ovr\">OVR {int(r['ovr'])}</div>"
                f"<div class=\"dev\">{badge_for_dev(r['dev'])}</div>"
                '</div>'
            )
        )
    elite_cards_html = '\n'.join(elite_cards) if elite_cards else "<div class='muted'>No X-Factor or Superstar rookies.</div>"

    # Teams tables
    team_rows = []
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: (-kv[1]['avg_ovr'], kv[0])):
        dev = stats['dev']
        team_rows.append(
            (
                '<tr>'
                f"<td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td>"
                f"<td class='num'>{stats['count']}</td>"
                f"<td class='num'>{stats['avg_ovr']:.2f}</td>"
                f"<td class='num'>{stats['best_ovr']}</td>"
                f"<td class='num'>{dev.get('3',0)}</td>"
                f"<td class='num'>{dev.get('2',0)}</td>"
                f"<td class='num'>{dev.get('1',0)}</td>"
                f"<td class='num'>{dev.get('0',0)}</td>"
                '</tr>'
            )
        )
    team_table_html = '\n'.join(team_rows)

    # Most hiddens: XF + SS + Star
    team_hidden_rows = []
    for team, stats in sorted(analytics['teams'].items(), key=lambda kv: -(kv[1]['dev'].get('3',0)+kv[1]['dev'].get('2',0)+kv[1]['dev'].get('1',0))):
        hidden = stats['dev'].get('3',0) + stats['dev'].get('2',0) + stats['dev'].get('1',0)
        team_hidden_rows.append(
            f"<tr><td class='team'>{logo_img(team)}<span>{html.escape(team)}</span></td><td class='num'>{hidden}</td><td class='num'>{stats['count']}</td><td class='num'>{stats['avg_ovr']:.2f}</td></tr>"
        )
    team_hiddens_html = '\n'.join(team_hidden_rows)

    # Positions table
    pos_rows = []
    for pos, stats in sorted(analytics['positions'].items(), key=lambda kv: (-kv[1]['avg_ovr'], -kv[1]['count'], kv[0])):
        dev = stats['dev']
        pos_rows.append(
            (
                '<tr>'
                f"<td>{html.escape(pos)}</td>"
                f"<td class='num'>{stats['count']}</td>"
                f"<td class='num'>{stats['avg_ovr']:.2f}</td>"
                f"<td class='num'>{dev.get('3',0)}</td>"
                f"<td class='num'>{dev.get('2',0)}</td>"
                f"<td class='num'>{dev.get('1',0)}</td>"
                f"<td class='num'>{dev.get('0',0)}</td>"
                '</tr>'
            )
        )
    pos_table_html = '\n'.join(pos_rows)

    total = analytics['total'] or 1
    xf = analytics['dev_counts'].get('3',0)
    ss = analytics['dev_counts'].get('2',0)
    star = analytics['dev_counts'].get('1',0)
    norm = analytics['dev_counts'].get('0',0)
    elite = xf + ss
    elite_pct = round(100*elite/total, 1)

    # Elite-heavy positions summary (show XF and SS separately)
    pos_elite_sorted = []
    for p in analytics['positions']:
        d = analytics['positions'][p]['dev']
        xf = d.get('3',0)
        ss = d.get('2',0)
        st = d.get('1',0)
        pos_elite_sorted.append((p, xf, ss, st, xf+ss))
    pos_elite_sorted.sort(key=lambda x: (-x[4], -x[3], x[0]))
    top_pos_lines = []
    for p, xf, ss, st, elite_total in pos_elite_sorted[:6]:
        top_pos_lines.append(f"<li><b>{html.escape(p)}</b>: {xf} XF, {ss} SS, {st} Stars</li>")
    top_pos_html = '\n'.join(top_pos_lines)

    html_out = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Draft Class __YEAR__ — Analytics — MEGA League</title>
  <style>
    :root { --text:#0f172a; --sub:#64748b; --muted:#94a3b8; --grid:#e2e8f0; --bg:#f7f7f7; --card:#ffffff; }
    body { margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }
    .container { max-width: 1200px; margin: 0 auto; background: var(--card); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
    header { padding: 18px 20px 4px; border-bottom: 1px solid #ececec; }
    h1 { margin:0; font-size: 22px; }
    .subtitle { color: var(--sub); margin:8px 0 6px; font-size: 13px; }

    .panel { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
    .kpis { display: grid; grid-template-columns: repeat(6, minmax(0,1fr)); gap: 10px; }
    .kpi { background:#f8fafc; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; }
    .kpi b { display:block; font-size: 12px; color:#0f172a; }
    .kpi span { color:#334155; font-size: 18px; font-weight: 700; }

    .section-title { font-size: 14px; font-weight: 700; margin: 0 0 10px; }
    .grid { display:grid; grid-template-columns: 1.7fr 1.3fr; gap: 12px; }
    .card { background:#fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
    .card h3 { margin: 0 0 8px; font-size: 14px; }

    .players { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; }
    .player { border:1px solid var(--grid); border-radius:10px; padding:10px; background:#fff; }
    .player .logo { width:22px; height:22px; border-radius:4px; vertical-align:middle; margin-right:6px; box-shadow:0 0 0 1px rgba(0,0,0,.06); }
    .player .nm { font-weight: 600; margin-top: 2px; }
    .player .meta { color:#475569; font-size: 12px; margin-top: 2px; }
    .player .ovr { margin-top: 4px; font-weight:700; }
    .player .dev { margin-top: 4px; }
    .muted { color: var(--muted); }

    table { width:100%; border-collapse: collapse; }
    th, td { padding: 8px 8px; border-bottom: 1px solid var(--grid); font-size: 13px; }
    th { text-align:left; color:#475569; font-size:12px; }
    td.num { text-align:right; font-variant-numeric: tabular-nums; }
    td.team { display:flex; align-items:center; gap:8px; }
    td.team img.logo { width:18px; height:18px; border-radius:4px; box-shadow:0 0 0 1px rgba(0,0,0,.05); }

    .dev-badge { display:inline-block; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:600; }
    .dev-xf { background:#fde68a; color:#92400e; }
    .dev-ss { background:#bfdbfe; color:#1e3a8a; }
    .dev-star { background:#dcfce7; color:#166534; }
    .dev-norm { background:#e5e7eb; color:#374151; }
  </style>
</head>
<body>
  <div class=\"container\"> 
    <header>
      <h1>Draft Class __YEAR__ — Analytics Report</h1>
      <div class=\"subtitle\">Elites spotlight + team and position strength analytics</div>
    </header>

    <section class=\"panel\">
      <div class=\"kpis\"> 
        <div class=\"kpi\"><b>Total rookies</b><span>__TOTAL__</span></div>
        <div class=\"kpi\"><b>Avg overall</b><span>__AVG_OVR__</span></div>
        <div class=\"kpi\"><b>X-Factors</b><span>__XF__</span></div>
        <div class=\"kpi\"><b>Superstars</b><span>__SS__</span></div>
        <div class=\"kpi\"><b>Stars</b><span>__STAR__</span></div>
        <div class=\"kpi\"><b>Elites share</b><span>__ELITE__ (__ELITE_PCT__%)</span></div>
      </div>
    </section>

    <section class=\"panel\"> 
      <div class=\"section-title\">Elites Spotlight — X-Factors and Superstars</div>
      <div class=\"players\">__ELITE_CARDS__</div>
    </section>

    <section class=\"panel\"> 
      <div class=\"grid\"> 
        <div class=\"card\"> 
          <h3>Team draft quality — by Avg OVR</h3>
          <table>
            <thead><tr><th>Team</th><th>#</th><th>Avg OVR</th><th>Best OVR</th><th>XF</th><th>SS</th><th>Star</th><th>Norm</th></tr></thead>
            <tbody>__TEAM_TABLE__</tbody>
          </table>
        </div>
        <div class=\"card\"> 
          <h3>Most hiddens (XF+SS+S) — by team</h3>
          <table>
            <thead><tr><th>Team</th><th>Hiddens</th><th>#</th><th>Avg OVR</th></tr></thead>
            <tbody>__TEAM_HIDDENS__</tbody>
          </table>
          <p class=\"muted\" style=\"margin-top:6px;\">Note: based on current team on roster.</p>
        </div>
      </div>
    </section>

    <section class=\"panel\"> 
      <div class=\"grid\"> 
        <div class=\"card\"> 
          <h3>Position strength</h3>
          <table>
            <thead><tr><th>Pos</th><th>Total</th><th>Avg OVR</th><th>XF</th><th>SS</th><th>Star</th><th>Norm</th></tr></thead>
            <tbody>__POS_TABLE__</tbody>
          </table>
        </div>
        <div class=\"card\"> 
          <h3>Elite-heavy positions</h3>
          <ul>__TOP_POS__</ul>
          <p class=\"muted\" style=\"margin-top:6px;\">Elites = X-Factor + Superstar</p>
        </div>
      </div>
    </section>

  </div>
</body>
</html>
"""
    # Inject values
    html_out = html_out.replace('__YEAR__', str(year))
    html_out = html_out.replace('__TOTAL__', str(total))
    html_out = html_out.replace('__AVG_OVR__', str(analytics['avg_ovr']))
    html_out = html_out.replace('__XF__', str(xf))
    html_out = html_out.replace('__SS__', str(ss))
    html_out = html_out.replace('__STAR__', str(star))
    html_out = html_out.replace('__ELITE__', str(elite))
    html_out = html_out.replace('__ELITE_PCT__', str(elite_pct))
    html_out = html_out.replace('__ELITE_CARDS__', elite_cards_html)
    html_out = html_out.replace('__TEAM_TABLE__', team_table_html)
    html_out = html_out.replace('__TEAM_HIDDENS__', team_hiddens_html)
    html_out = html_out.replace('__POS_TABLE__', pos_table_html)
    html_out = html_out.replace('__TOP_POS__', top_pos_html)
    return html_out


def main():
    ap = argparse.ArgumentParser(description='Generate Draft Class Analytics HTML')
    ap.add_argument('--year', type=int, required=True, help='Draft class year (e.g., 2026)')
    ap.add_argument('--players', default='MEGA_players.csv', help='Path to players CSV (default: MEGA_players.csv)')
    ap.add_argument('--teams', default='MEGA_teams.csv', help='Path to teams CSV (default: MEGA_teams.csv)')
    ap.add_argument('--out', default=None, help='Output HTML path (default: docs/draft_class_<year>.html)')
    args = ap.parse_args()

    out_path = args.out or os.path.join('docs', f'draft_class_{args.year}.html')

    players = read_csv(args.players)
    teams = read_csv(args.teams) if os.path.exists(args.teams) else []
    team_logo_map = build_team_logo_map(teams)

    rookies = gather_rookies(players, args.year)
    analytics = compute_analytics(rookies)
    html_out = generate_html(args.year, rookies, analytics, team_logo_map)

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_out)

    print(f'Generated: {out_path}')
    print(f"Rookies: {analytics['total']} | Avg OVR: {analytics['avg_ovr']}")


if __name__ == '__main__':
    main()
