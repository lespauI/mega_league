#!/usr/bin/env python3
"""
Generate a Round-by-Round Recap HTML page for rounds 1-7 of a draft class.

Usage:
  python3 scripts/generate_draft_rounds_recap.py --year 2027 \
      --players MEGA_players.csv --teams MEGA_teams.csv \
      --out docs/draft_rounds_1_7_2027.html
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import sys

DEV_LABELS = {"3": "X-Factor", "2": "Superstar", "1": "Star", "0": "Normal"}


def read_csv(path: str) -> list[dict]:
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


def build_team_logo_map(teams_rows: list[dict]) -> dict:
    mapping: dict[str, str] = {}
    if not teams_rows:
        return mapping
    for r in teams_rows:
        lid = str(r.get('logoId') or '').strip()
        if lid == '':
            continue
        for key in ('displayName', 'nickName', 'teamName'):
            name = (r.get(key) or '').strip()
            if not name:
                continue
            for variant in {name, name.lower(), name.upper()}:
                mapping[variant] = lid
    return mapping


def _pos_key(pos: str) -> str:
    try:
        return (pos or '').strip().upper()
    except Exception:
        return ''


def get_attr_keys_for_pos(pos: str) -> list[str]:
    p = _pos_key(pos)
    if p == 'QB':
        return ['throwAccShortRating','throwAccMidRating','throwAccDeepRating','throwPowerRating',
                'throwUnderPressureRating','throwOnRunRating','playActionRating','awareRating',
                'speedRating','breakSackRating']
    if p in {'HB','RB'}:
        return ['speedRating','accelRating','agilityRating','breakTackleRating',
                'truckRating','jukeMoveRating','spinMoveRating','stiffArmRating',
                'carryRating','catchRating','bCVRating']
    if p == 'FB':
        return ['runBlockRating','leadBlockRating','impactBlockRating','strengthRating','truckRating','catchRating']
    if p == 'WR':
        return ['catchRating','specCatchRating','cITRating','speedRating',
                'routeRunShortRating','routeRunMedRating','routeRunDeepRating',
                'releaseRating','agilityRating','changeOfDirectionRating']
    if p == 'TE':
        return ['catchRating','cITRating','runBlockRating','passBlockRating',
                'speedRating','routeRunShortRating','routeRunMedRating','strengthRating','specCatchRating']
    if p in {'LT','LG','RT','RG','T','G','C','OL'}:
        return ['passBlockRating','passBlockPowerRating','passBlockFinesseRating',
                'runBlockRating','runBlockPowerRating','runBlockFinesseRating',
                'strengthRating','awareRating','impactBlockRating']
    if p in {'LE','RE','DE','LEDGE','REDGE'}:
        return ['powerMovesRating','finesseMovesRating','blockShedRating','pursuitRating','tackleRating','strengthRating','speedRating','hitPowerRating']
    if p == 'DT':
        return ['powerMovesRating','blockShedRating','strengthRating','tackleRating','pursuitRating','hitPowerRating']
    if p in {'MLB','LOLB','ROLB','OLB','LB','MIKE','WILL','SAM'}:
        return ['tackleRating','pursuitRating','hitPowerRating','blockShedRating','playRecRating','zoneCoverRating','manCoverRating','speedRating','awareRating']
    if p == 'CB':
        return ['manCoverRating','zoneCoverRating','speedRating','accelRating','agilityRating','pressRating','playRecRating','catchRating','changeOfDirectionRating']
    if p in {'FS','SS','S'}:
        return ['zoneCoverRating','tackleRating','hitPowerRating','speedRating','playRecRating','pursuitRating','manCoverRating','awareRating','catchRating']
    if p == 'K' or p == 'P':
        return ['kickPowerRating','kickAccRating']
    return ['speedRating','strengthRating','agilityRating','awareRating']


def build_round_entries(players_rows: list[dict], team_logo_map: dict, *, year: int, rounds: list[int]) -> dict[int, list[dict]]:
    entries_by_round: dict[int, list[dict]] = {r: [] for r in rounds}
    
    for r in players_rows:
        if str(r.get('rookieYear', '')).strip() != str(year):
            continue
        rd = safe_int(r.get('draftRound'), None)
        pk = safe_int(r.get('draftPick'), None)
        if rd is None or pk is None or rd not in rounds:
            continue

        fn = (r.get('fullName') or '').strip()
        cn = (r.get('cleanName') or '').strip()
        first = (r.get('firstName') or '').strip()
        last = (r.get('lastName') or '').strip()
        name = fn or cn or (f"{first} {last}".strip())

        team = (r.get('team') or '').strip() or 'FA'
        pos = (r.get('position') or '').strip() or '?'
        ovr = safe_int(r.get('playerBestOvr'), None)
        if ovr is None:
            ovr = safe_int(r.get('playerSchemeOvr'), 0) or 0
        dev = str(r.get('devTrait') or '0').strip()
        portrait_id = (r.get('portraitId') or '').strip()

        lid = team_logo_map.get(team) or team_logo_map.get(team.lower()) or team_logo_map.get(team.upper())
        logo_url = f"https://cdn.neonsportz.com/teamlogos/256/{lid}.png" if lid not in (None, '') else ''

        attr_keys = get_attr_keys_for_pos(pos)
        attrs = []
        for k in attr_keys:
            if k in r and str(r.get(k) or '').strip() != '':
                try:
                    val = int(float(str(r[k]).strip()))
                except Exception:
                    continue
                attrs.append((k, val))

        photo_url = ''
        if portrait_id.isdigit():
            photo_url = f"https://ratings-images-prod.pulse.ea.com/madden-nfl-26/portraits/{portrait_id}.png"

        entries_by_round[rd].append({
            'round': rd,
            'pick': pk,
            'team': team,
            'team_logo': logo_url,
            'name': name,
            'position': pos,
            'ovr': int(ovr),
            'dev': dev,
            'photo': photo_url,
            'attrs': attrs,
        })

    for rd in entries_by_round:
        entries_by_round[rd].sort(key=lambda e: e['pick'] if e['pick'] is not None else 999)
    
    return entries_by_round


def badge_for_dev(dev: str) -> str:
    mapping = {
        '3': ('X-Factor', 'dev-xf'),
        '2': ('Superstar', 'dev-ss'),
        '1': ('Star', 'dev-star'),
        '0': ('Normal', 'dev-norm'),
    }
    label, cls = mapping.get(str(dev), ('Normal', 'dev-norm'))
    return f'<span class="dev-badge {cls}">{html.escape(label)}</span>'


def _grade_for_ovr(ovr: int) -> tuple[str, str]:
    try:
        o = int(ovr)
    except Exception:
        o = 0
    if o >= 78:
        return ('A', 'grade-on')
    if o >= 72:
        return ('B', 'grade-near')
    return ('C', 'grade-below')


def _ovr_badge_cls(ovr: int) -> str:
    try:
        o = int(ovr)
    except Exception:
        o = 0
    if o >= 75:
        return 'ovr-green'
    if o >= 65:
        return 'ovr-yellow'
    return 'ovr-red'


def render_round_cards(entries: list[dict]) -> str:
    if not entries:
        return "<div class='muted'>No picks found.</div>"

    def esc(s: str) -> str:
        return html.escape(str(s))

    def _attr_label(key: str) -> str:
        k = str(key or '')
        if k.endswith('Rating'):
            k = k[:-6]
        if k == 'throwUnderPressure':
            return 'TUP'
        return k

    def _val_cls(v: int) -> str:
        try:
            iv = int(v)
        except Exception:
            iv = 0
        if iv >= 85:
            return 'val-elite'
        if iv >= 80:
            return 'val-good'
        if iv >= 75:
            return 'val-warn'
        return 'val-low'

    cards = []
    for e in entries:
        grade_label, grade_cls = _grade_for_ovr(e.get('ovr', 0))
        if str(e.get('dev')) in ('2','3'):
            grade_label = f"{grade_label}+"

        logo_img = f"<img class=\"team-logo\" src=\"{esc(e['team_logo'])}\" alt=\"{esc(e['team'])}\" />" if e.get('team_logo') else ''
        photo = e.get('photo')
        photo_html = f"<img class=\"r1-photo\" src=\"{esc(photo)}\" alt=\"{esc(e['name'])}\" />" if photo else ''

        attr_lines = []
        for k, v in (e.get('attrs') or [])[:10]:
            label = _attr_label(k)
            v_cls = _val_cls(v)
            attr_lines.append(f"<div class=\"attr\"><span class=\"k\">{esc(label)}</span><span class=\"v {v_cls}\">{int(v)}</span></div>")
        attrs_html = ''.join(attr_lines) if attr_lines else "<div class='muted' style='grid-column:1/-1;'>No attributes.</div>"

        dev_badge = badge_for_dev(e.get('dev', '0'))
        pick_label = f"R{e['round']}.{e['pick']}"

        cards.append(
            f"""<div class="r1-card">
  <div class="head">{photo_html}<div class="head-right"><div class="pick">{esc(pick_label)}</div>{logo_img}</div></div>
  <div class="name"><b>{esc(e['name'])}</b> <span class="pos">{esc(e['position'])}</span> <span class="grade {esc(grade_cls)}">{esc(grade_label)}</span></div>
  <div class="meta">Team: {esc(e['team'])} &nbsp; • &nbsp; OVR {int(e.get('ovr',0))}</div>
  <div class="attrs">{attrs_html}</div>
  <div class="real-eval-block">
    <div class="real-eval-title">Оценка реального пика</div>
    <div class="real-eval">Оценка: <span class="grade {esc(grade_cls)}">{esc(grade_label)}</span></div>
    <div class="real-eval">OVR: <span class="ovr-badge {_ovr_badge_cls(e.get('ovr',0))}">{int(e.get('ovr',0))}</span></div>
    <div class="real-eval">DevTrait: {dev_badge}</div>
  </div>
</div>"""
        )
    return '<div class="r1-list">' + '\n'.join(cards) + '</div>'


def generate_html(year: int, entries_by_round: dict[int, list[dict]], rounds: list[int]) -> str:
    round_sections = []
    for rd in rounds:
        entries = entries_by_round.get(rd, [])
        cards_html = render_round_cards(entries)
        round_sections.append(f"""
    <section id="round{rd}" class="panel">
      <div class="section-title">Round {rd} Recap</div>
      <div class="card">
        {cards_html}
        <p class="muted" style="margin-top:6px;"></p>
      </div>
    </section>
""")

    nav_links = ' '.join([f'<a href="#round{rd}">Round {rd}</a>' for rd in rounds])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Draft Rounds 1-7 Recap — {year} — MEGA League</title>
  <style>
    :root {{ --text:#0f172a; --sub:#64748b; --muted:#94a3b8; --grid:#e2e8f0; --bg:#f7f7f7; --card:#ffffff; --accent:#3b82f6; }}
    body {{ margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }}
    .topbar {{ max-width: 1200px; margin: 0 auto 10px; display:flex; align-items:center; gap:10px; }}
    .back {{ display:inline-flex; align-items:center; gap:8px; font-size:13px; color:#1e293b; text-decoration:none; background:#fff; border:1px solid #e5e7eb; padding:6px 10px; border-radius:8px; box-shadow:0 1px 2px rgba(0,0,0,.05); }}
    .back:hover {{ background:#f8fafc; }}
    .container {{ max-width: 1200px; margin: 0 auto; background: var(--card); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow:hidden; }}
    header {{ padding: 18px 20px 8px; border-bottom: 1px solid #ececec; background:linear-gradient(180deg,#ffffff 0%,#fafafa 100%); }}
    h1 {{ margin:0; font-size: 22px; }}
    .subtitle {{ color: var(--sub); margin:8px 0 6px; font-size: 13px; }}
    .pill {{ display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px; border:1px solid #bfdbfe; background:#dbeafe; color:#1e3a8a; font-size:12px; }}

    .panel {{ padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }}
    .section-title {{ font-size: 14px; font-weight: 700; margin: 0 0 10px; border-left:3px solid var(--accent); padding-left:8px; }}
    .card {{ background:#fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }}
    .muted {{ color: var(--muted); }}

    .subnav {{ position: sticky; top: 0; z-index: 20; background: rgba(255,255,255,.92); backdrop-filter: saturate(120%) blur(6px); border-bottom: 1px solid #eef2f7; padding: 8px 12px; display:flex; flex-wrap:wrap; gap: 8px; }}
    .subnav a {{ text-decoration:none; font-size:12px; color:#0f172a; background:#f1f5f9; border:1px solid #e2e8f0; padding:6px 10px; border-radius:999px; }}
    .subnav a:hover {{ background:#e2e8f0; }}

    .r1-list {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
    .r1-card {{ border:1px solid var(--grid); border-radius:10px; padding:12px; background:#fff; position:relative; }}
    .r1-card .head {{ display:flex; align-items:center; gap:8px; justify-content:space-between; }}
    .r1-card .head .head-right {{ display:flex; align-items:center; gap:8px; margin-left:auto; }}
    .r1-card .head img.r1-photo {{ width:56px; height:56px; border-radius:8px; object-fit:cover; box-shadow:0 2px 6px rgba(0,0,0,.08); }}
    .r1-card img.team-logo {{ width:24px; height:24px; border-radius:6px; box-shadow:0 0 0 1px rgba(0,0,0,.08); }}
    .r1-card .pick {{ margin-left:auto; font-weight:700; font-size:12px; color:#0f172a; background:#f1f5f9; border:1px solid #e2e8f0; padding:2px 8px; border-radius:999px; }}
    .r1-card .name {{ margin-top:4px; }}
    .r1-card .name .pos {{ color:#475569; font-weight:600; }}
    .r1-card .name .grade {{ margin-left:6px; padding:1px 6px; border-radius:999px; font-size:11px; border:1px solid #e5e7eb; }}
    .r1-card .name .grade.grade-on {{ background:#dcfce7; color:#166534; border-color:#bbf7d0; }}
    .r1-card .name .grade.grade-near {{ background:#fef9c3; color:#92400e; border-color:#fde68a; }}
    .r1-card .name .grade.grade-below {{ background:#fee2e2; color:#991b1b; border-color:#fecaca; }}
    .r1-card .meta {{ color:#64748b; font-size:12px; margin-top:2px; }}
    .r1-card .attrs {{ margin-top:6px; display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:6px; }}
    .r1-card .attr {{ display:flex; justify-content:space-between; gap:8px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:8px; padding:6px 8px; font-size:12px; }}
    .r1-card .attr .k {{ color:#334155; font-weight:600; }}
    .r1-card .attr .v {{ font-weight:700; border-radius:6px; padding:0 6px; border:1px solid transparent; }}
    .r1-card .attr .v.val-elite {{ background:#dcfce7; color:#166534; border-color:#bbf7d0; }}
    .r1-card .attr .v.val-good {{ background:#ecfdf5; color:#047857; border-color:#a7f3d0; }}
    .r1-card .attr .v.val-warn {{ background:#fef9c3; color:#92400e; border-color:#fde68a; }}
    .r1-card .attr .v.val-low {{ background:#f9f1e7; color:#7c3e00; border-color:#e7c3a5; }}
    .real-eval-block {{ margin-top:8px; }}
    .real-eval-title {{ color:#475569; font-weight:600; }}
    .real-eval {{ color:#475569; font-size:12px; margin-top:6px; }}
    .ovr-badge {{ display:inline-block; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; }}
    .ovr-green {{ background:#dcfce7; color:#166534; border:1px solid #bbf7d0; }}
    .ovr-yellow {{ background:#fef9c3; color:#92400e; border:1px solid #fde68a; }}
    .ovr-red {{ background:#fee2e2; color:#991b1b; border:1px solid #fecaca; }}

    .dev-badge {{ display:inline-block; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:600; }}
    .dev-xf {{ background:#fee2e2; color:#991b1b; border:1px solid #fecaca; }}
    .dev-ss {{ background:#dbeafe; color:#1e3a8a; border:1px solid #bfdbfe; }}
    .dev-star {{ background:#fef3c7; color:#92400e; border:1px solid #fde68a; }}
    .dev-norm {{ background:#e5e7eb; color:#374151; border:1px solid #d1d5db; }}

    .grade {{ display:inline-block; margin-left:6px; padding:2px 7px; border-radius:999px; font-size:11px; font-weight:700; border:1px solid transparent; }}
    .grade-on {{ background:#dcfce7; color:#166534; border-color:#bbf7d0; }}
    .grade-near {{ background:#fef3c7; color:#92400e; border-color:#fde68a; }}
    .grade-below {{ background:#fee2e2; color:#991b1b; border-color:#fecaca; }}

    @media (max-width: 800px) {{
      .r1-list {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
    }}
    @media (max-width: 520px) {{
      .r1-list {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="topbar"><a class="back" href="../index.html" title="Back to index">&#8592; Back to Index</a></div>
  <div class="container">
    <header>
      <h1>Round by Round Recap <span class="pill">{year}</span></h1>
      <div class="subtitle">Rounds 1-7 draft picks with player cards</div>
    </header>

    <nav class="subnav">
      {nav_links}
    </nav>

{''.join(round_sections)}
  </div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate Rounds 1-7 Recap HTML")
    parser.add_argument("--year", type=int, required=True, help="Draft year to filter")
    parser.add_argument("--players", required=True, help="Path to players CSV")
    parser.add_argument("--teams", required=True, help="Path to teams CSV")
    parser.add_argument("--out", required=True, help="Output HTML path")
    parser.add_argument("--rounds", default="1,2,3,4,5,6,7", help="Comma-separated rounds to include (default: 1,2,3,4,5,6,7)")
    args = parser.parse_args()

    rounds = [int(r.strip()) for r in args.rounds.split(",")]

    players = read_csv(args.players)
    teams = read_csv(args.teams)
    team_logo_map = build_team_logo_map(teams)

    entries_by_round = build_round_entries(players, team_logo_map, year=args.year, rounds=rounds)

    html_content = generate_html(args.year, entries_by_round, rounds)

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write(html_content)

    total = sum(len(v) for v in entries_by_round.values())
    print(f"Generated {args.out} with {total} picks across rounds {rounds}")


if __name__ == "__main__":
    main()
