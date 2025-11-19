#!/usr/bin/env python3
"""
Generate an HTML page with analytics and an interactive table for a given draft class.

Reads MEGA_players.csv (and MEGA_teams.csv for logo enrichment) from the project root.
Outputs docs/draft_class_<YEAR>.html by default.

Usage:
  python3 scripts/generate_draft_class.py --year 2026
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import statistics as st
from collections import Counter, defaultdict


DEV_LABELS = {
    "3": "X-Factor",
    "2": "Superstar",
    "1": "Star",
    "0": "Normal",
}


def read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def safe_int(v: str, default: int | None = None) -> int | None:
    try:
        return int(v)
    except Exception:
        return default


def build_team_logo_map(teams_rows: list[dict]) -> dict:
    # Map common team name tokens to a logo id
    # We try to match by displayName and nickName case-sensitively
    m = {}
    for r in teams_rows:
        logo = r.get("logoId") or ""
        for k in ("displayName", "nickName", "teamName"):
            name = (r.get(k) or "").strip()
            if name:
                m[name] = logo
    return m


def gather_rookies(players: list[dict], year: int) -> list[dict]:
    rookies = []
    for r in players:
        if str(r.get("rookieYear", "")) != str(year):
            continue
        ovr = safe_int(r.get("playerBestOvr"), None)
        if ovr is None:
            ovr = safe_int(r.get("playerSchemeOvr"), 0)
        dev = str(r.get("devTrait", "0"))
        rookies.append(
            {
                "id": r.get("id"),
                "name": r.get("fullName") or r.get("cleanName") or (r.get("firstName", "").strip() + " " + r.get("lastName", "").strip()).strip(),
                "team": r.get("team") or "FA",
                "position": r.get("position") or "?",
                "ovr": ovr or 0,
                "dev": dev if dev in DEV_LABELS else "0",
                "age": safe_int(r.get("age"), None),
            }
        )
    # stable sort: highest OVR first, then name
    rookies.sort(key=lambda x: (-x["ovr"], x["name"]))
    return rookies


def compute_analytics(rows: list[dict]):
    total = len(rows)
    pos_counts = Counter(r["position"] for r in rows)
    dev_counts = Counter(r["dev"] for r in rows)
    team_counts = Counter(r["team"] for r in rows)
    ovrs = [r["ovr"] for r in rows if isinstance(r["ovr"], int)]
    avg_ovr = round(st.mean(ovrs), 2) if ovrs else 0

    avg_by_pos = {}
    holes_by_pos = defaultdict(list)
    for p in sorted(pos_counts):
        xs = [r["ovr"] for r in rows if r["position"] == p]
        if xs:
            avg_by_pos[p] = round(st.mean(xs), 2)
            # mark top 3 per position as highlights
            holes_by_pos[p] = [r for r in rows if r["position"] == p][:3]

    return {
        "total": total,
        "avg_ovr": avg_ovr,
        "pos_counts": pos_counts,
        "dev_counts": dev_counts,
        "team_counts": team_counts,
        "avg_by_pos": avg_by_pos,
    }


def badge_for_dev(dev: str) -> str:
    label = DEV_LABELS.get(dev, "Normal")
    cls = {
        "3": "dev-xf",
        "2": "dev-ss",
        "1": "dev-star",
        "0": "dev-norm",
    }.get(dev, "dev-norm")
    return f'<span class="dev-badge {cls}">{html.escape(label)}</span>'


def generate_html(year: int, rows: list[dict], analytics: dict, team_logo_map: dict) -> str:
    # Build filter option lists
    positions = sorted({r["position"] for r in rows})
    teams = sorted({r["team"] for r in rows})

    def opt_list(opts: list[str]) -> str:
        return "\n".join(f'<option value="{html.escape(o)}">{html.escape(o)}</option>' for o in opts)

    def dev_summary() -> str:
        total = analytics["total"] or 1
        parts = []
        for k in ("3", "2", "1", "0"):
            c = analytics["dev_counts"].get(k, 0)
            pct = round(100 * c / total, 1)
            parts.append(f"{badge_for_dev(k)} {c} ({pct}%)")
        return " \u2022 ".join(parts)

    def pos_summary() -> str:
        pairs = sorted(analytics["pos_counts"].items(), key=lambda x: (-x[1], x[0]))
        return ", ".join(f"{html.escape(p)}: {c}" for p, c in pairs)

    def avg_by_pos_table() -> str:
        pairs = sorted(analytics["avg_by_pos"].items(), key=lambda x: (-x[1], x[0]))
        rows = [
            f"<tr><td>{html.escape(p)}</td><td>{v:.2f}</td></tr>" for p, v in pairs
        ]
        return "\n".join(rows)

    def logo_img(team: str) -> str:
        lid = team_logo_map.get(team)
        if not lid:
            return ""
        # Use 256px logos as requested
        return f'<img class="logo" src="https://cdn.neonsportz.com/teamlogos/256/{lid}.png" alt="{html.escape(team)}" />'

    # Build main table rows
    table_rows = []
    for r in rows:
        team = r["team"]
        pos = r["position"]
        name = r["name"]
        ovr = r["ovr"]
        dev = r["dev"]
        tr = (
            f"<tr data-pos=\"{html.escape(pos)}\" data-team=\"{html.escape(team)}\" data-dev=\"{html.escape(dev)}\">"
            f"<td class=\"name\">{logo_img(team)}<span>{html.escape(name)}</span></td>"
            f"<td>{html.escape(pos)}</td>"
            f"<td>{html.escape(team)}</td>"
            f"<td class=\"ovr\">{int(ovr)}</td>"
            f"<td>{badge_for_dev(dev)}</td>"
            f"</tr>"
        )
        table_rows.append(tr)

    html_out = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Draft Class {year} — MEGA League</title>
  <style>
    :root { --text:#1e293b; --sub:#64748b; --grid:#e5e7eb; --bg:#f7f7f7; }
    body { margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }
    .container { max-width: 1200px; margin: 0 auto; background: #fff; border: 1px solid #e5e5e5; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
    header { padding: 18px 20px 10px; border-bottom: 1px solid #ececec; }
    h1 { margin:0; font-size: 22px; }
    .subtitle { color: var(--sub); margin-top:6px; font-size: 13px; }

    .panel { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }
    .stats { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin-top: 6px; }
    .kpi { background:#f8fafc; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; }
    .kpi b { display:block; font-size: 13px; color:#0f172a; }
    .kpi span { color:#334155; font-size: 18px; font-weight: 700; }

    .filters { display:flex; gap:10px; flex-wrap: wrap; align-items:center; }
    .filters label { font-size:12px; color:#475569; margin-right:6px; }
    .filters select, .filters input[type=number] { padding:6px 8px; border:1px solid #e5e7eb; border-radius:8px; font-size:13px; }
    .filters input[type=search] { padding:6px 8px; border:1px solid #e5e7eb; border-radius:8px; font-size:13px; min-width:180px; }

    table { width:100%; border-collapse: collapse; }
    thead th { text-align:left; font-size:12px; color:#475569; border-bottom:2px solid #e5e7eb; padding:8px; cursor:pointer; user-select:none; }
    tbody td { padding:10px 8px; border-bottom: 1px solid #f1f5f9; font-size:13px; }
    tbody tr:hover { background:#f8fafc; }
    td.name { display:flex; align-items:center; gap:8px; }
    img.logo { width:20px; height:20px; border-radius:4px; box-shadow:0 0 0 1px rgba(0,0,0,.05); }

    .dev-badge { display:inline-block; padding:3px 8px; border-radius:999px; font-size:11px; font-weight:600; }
    .dev-xf { background:#fde68a; color:#92400e; }
    .dev-ss { background:#bfdbfe; color:#1e3a8a; }
    .dev-star { background:#dcfce7; color:#166534; }
    .dev-norm { background:#e5e7eb; color:#374151; }

    .grid { display:grid; grid-template-columns: 2fr 1fr; gap: 10px; }
    .card { background:#fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 12px; }
    .card h3 { margin: 0 0 8px; font-size: 14px; }
    .meta { font-size: 13px; color:#334155; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Draft Class {year}</h1>
      <div class="subtitle">Interactive view of rookie class — position depth, OVR, and dev trait mix</div>
    </header>

    <section class="panel">
      <div class="stats">
        <div class="kpi"><b>Total rookies</b><span>{analytics['total']}</span></div>
        <div class="kpi"><b>Avg overall</b><span>{analytics['avg_ovr']}</span></div>
        <div class="kpi"><b>Dev trait mix</b><span>{dev_summary()}</span></div>
        <div class="kpi"><b>Position counts</b><span class="meta">{pos_summary()}</span></div>
      </div>
    </section>

    <section class="panel">
      <div class="filters">
        <div><label for="posSel">Position</label><select id="posSel"><option value="">All</option>{opt_list(positions)}</select></div>
        <div><label for="teamSel">Team</label><select id="teamSel"><option value="">All</option>{opt_list(teams)}</select></div>
        <div><label for="devSel">Dev Trait</label>
          <select id="devSel">
            <option value="">All</option>
            <option value="3">X-Factor</option>
            <option value="2">Superstar</option>
            <option value="1">Star</option>
            <option value="0">Normal</option>
          </select>
        </div>
        <div><label for="minOvr">Min OVR</label><input id="minOvr" type="number" min="0" max="99" step="1" value="0"></div>
        <div><label for="nameQ">Search</label><input id="nameQ" type="search" placeholder="Player name..."></div>
      </div>
    </section>

    <section class="panel">
      <div class="grid">
        <div class="card">
          <h3>Rookies</h3>
          <table id="rookieTable">
            <thead>
              <tr>
                <th data-sort="name">Name</th>
                <th data-sort="position">Pos</th>
                <th data-sort="team">Team</th>
                <th data-sort="ovr" data-order="desc">OVR</th>
                <th data-sort="dev">Dev</th>
              </tr>
            </thead>
            <tbody>
              {''.join(table_rows)}
            </tbody>
          </table>
        </div>
        <div class="card">
          <h3>Avg OVR by position</h3>
          <table>
            <thead><tr><th>Pos</th><th>Avg OVR</th></tr></thead>
            <tbody>
              {avg_by_pos_table()}
            </tbody>
          </table>
        </div>
      </div>
    </section>

  </div>
  <script>
    (function(){
      const $ = (sel, el=document) => el.querySelector(sel);
      const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));
      const table = $('#rookieTable');
      const tbody = $('tbody', table);
      const posSel = $('#posSel');
      const teamSel = $('#teamSel');
      const devSel = $('#devSel');
      const minOvr = $('#minOvr');
      const nameQ = $('#nameQ');

      function normalize(s){ return (s||'').toLowerCase(); }

      function applyFilters(){
        const pos = posSel.value;
        const team = teamSel.value;
        const dev = devSel.value;
        const min = parseInt(minOvr.value||'0', 10) || 0;
        const q = normalize(nameQ.value);
        $$('#rookieTable tbody tr').forEach(tr => {
          const match = (!pos || tr.dataset.pos === pos)
            && (!team || tr.dataset.team === team)
            && (!dev || tr.dataset.dev === dev)
            && ((parseInt($('.ovr', tr).textContent, 10) || 0) >= min)
            && (!q || normalize($('.name span', tr).textContent).includes(q));
          tr.style.display = match ? '' : 'none';
        });
      }

      [posSel, teamSel, devSel, minOvr, nameQ].forEach(el => el.addEventListener('input', applyFilters));

      // Sorting
      function sortBy(key, order){
        const rows = $$('#rookieTable tbody tr');
        const getVal = (tr) => {
          if (key==='name') return normalize($('.name span', tr).textContent);
          if (key==='ovr') return parseInt($('.ovr', tr).textContent, 10) || 0;
          if (key==='dev') return parseInt(tr.dataset.dev, 10) || 0;
          return normalize($(`td:nth-child(${key==='position'?2:key==='team'?3:1})`, tr).textContent);
        };
        rows.sort((a,b)=>{
          const va = getVal(a), vb = getVal(b);
          if (va < vb) return order==='asc' ? -1 : 1;
          if (va > vb) return order==='asc' ? 1 : -1;
          return 0;
        }).forEach(tr=> tbody.appendChild(tr));
      }

      $$('#rookieTable thead th').forEach(th => {
        th.addEventListener('click', () => {
          const key = th.dataset.sort;
          const cur = th.dataset.order || 'asc';
          const next = (cur==='asc') ? 'desc' : 'asc';
          $$('#rookieTable thead th').forEach(x=> x.removeAttribute('data-order'));
          th.dataset.order = next;
          sortBy(key, next);
        });
      });

      // Initial sort by OVR desc if marked
      const thOvr = $$('#rookieTable thead th').find(x => x.dataset.sort==='ovr');
      if (thOvr) { thOvr.dataset.order = thOvr.dataset.order || 'desc'; sortBy('ovr', thOvr.dataset.order); }

      applyFilters();
    })();
  </script>
</body>
</html>
"""
    # Inject dynamic values via simple replacements to avoid brace escaping in JS/CSS
    html_out = html_out.replace("Draft Class {year}", f"Draft Class {year}")
    html_out = html_out.replace("<title>Draft Class {year} — MEGA League</title>", f"<title>Draft Class {year} — MEGA League</title>")
    html_out = html_out.replace("{analytics['total']}", str(analytics['total']))
    html_out = html_out.replace("{analytics['avg_ovr']}", str(analytics['avg_ovr']))
    html_out = html_out.replace("{dev_summary()}", dev_summary())
    html_out = html_out.replace("{pos_summary()}", pos_summary())
    html_out = html_out.replace("{opt_list(positions)}", opt_list(positions))
    html_out = html_out.replace("{opt_list(teams)}", opt_list(teams))
    html_out = html_out.replace("{''.join(table_rows)}", "".join(table_rows))
    html_out = html_out.replace("{avg_by_pos_table()}", avg_by_pos_table())
    return html_out


def main():
    ap = argparse.ArgumentParser(description="Generate Draft Class HTML page")
    ap.add_argument("--year", type=int, default=2026, help="Draft class year to render")
    ap.add_argument("--players", default="MEGA_players.csv", help="Path to players CSV")
    ap.add_argument("--teams", default="MEGA_teams.csv", help="Path to teams CSV (for logos)")
    ap.add_argument("--out", default=None, help="Output HTML path (default: docs/draft_class_<year>.html)")
    args = ap.parse_args()

    players_path = args.players
    teams_path = args.teams
    out_path = args.out or os.path.join("docs", f"draft_class_{args.year}.html")

    players = read_csv(players_path)
    teams = read_csv(teams_path) if os.path.exists(teams_path) else []
    team_logo_map = build_team_logo_map(teams)

    rookies = gather_rookies(players, args.year)
    analytics = compute_analytics(rookies)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(generate_html(args.year, rookies, analytics, team_logo_map))

    print(f"Generated: {out_path}")
    print(f"Rookies: {analytics['total']} | Avg OVR: {analytics['avg_ovr']}")


if __name__ == "__main__":
    main()
