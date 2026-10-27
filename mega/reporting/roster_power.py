"""HTML reporting and team narrative helpers for roster power rankings."""
from __future__ import annotations

import json
import math
import os
import sys
from html import escape

from ..roster.scoring import (
    DEFAULT_DEV_MULTIPLIERS,
    DEFAULT_OVERALL_UNIT_WEIGHTS,
    DEV_LABELS,
    UNIT_POSITION_WEIGHTS,
    _score_unit_with_breakdown,
)
from ..roster.inputs import assign_unit, get_top_attrs_for_player, safe_int

def compute_league_context(teams_metrics: list[dict]) -> dict:
    """Compute simple league-wide context statistics for key metrics.

    Returns a mapping of metric name -> summary stats, where each summary
    contains avg/min/max and 25th/50th/75th percentiles. This is intended
    both for display in the HTML report and for narrative helpers in
    later phases.
    """

    def _metric_stats(key: str) -> dict:
        vals: list[float] = []
        for row in teams_metrics:
            v = row.get(key)
            if v is None or v == "":
                continue
            try:
                vals.append(float(v))
            except Exception:
                continue
        if not vals:
            return {}
        vals.sort()
        n = len(vals)

        def pct(p: float) -> float:
            if n == 1:
                return vals[0]
            # Simple nearest-rank percentile.
            idx = int(round((p / 100.0) * (n - 1)))
            if idx < 0:
                idx = 0
            if idx >= n:
                idx = n - 1
            return vals[idx]

        avg = sum(vals) / n
        return {
            "avg": avg,
            "min": vals[0],
            "max": vals[-1],
            "p25": pct(25.0),
            "p50": pct(50.0),
            "p75": pct(75.0),
        }

    metrics = {
        "overall_score": _metric_stats("overall_score"),
        "off_pass_score": _metric_stats("off_pass_score"),
        "off_run_score": _metric_stats("off_run_score"),
        "def_cover_score": _metric_stats("def_cover_score"),
        "def_pass_rush_score": _metric_stats("def_pass_rush_score"),
        "def_run_score": _metric_stats("def_run_score"),
    }

    # Filter out completely empty entries.
    return {k: v for k, v in metrics.items() if v}


def generate_team_narrative(team_metrics: dict, league_context: dict) -> dict[str, str]:
    """Generate narrative text describing a team's strengths and weaknesses.

    The output dict contains ``strengths``, ``weaknesses``, and ``summary``
    keys. The content is heuristic but grounded in the same metrics that
    feed the CSV/HTML report.
    """

    # Core unit keys and human labels.
    unit_keys = [
        ("off_pass_score", "Off Pass"),
        ("off_run_score", "Off Run"),
        ("def_cover_score", "Pass Coverage"),
        ("def_pass_rush_score", "Pass Rush"),
        ("def_run_score", "Run Defense"),
    ]

    scores: dict[str, float] = {}
    for key, _ in unit_keys:
        try:
            scores[key] = float(team_metrics.get(key) or 0.0)
        except Exception:
            scores[key] = 0.0

    def _ctx(key: str) -> dict:
        if isinstance(league_context, dict):
            return league_context.get(key, {})
        return {}

    strengths: list[str] = []
    weaknesses: list[str] = []

    # Strong if >= 75th percentile, weak if <= 25th.
    for key, label in unit_keys:
        ctx = _ctx(key)
        score = scores.get(key, 0.0)
        if ctx:
            high = ctx.get("p75", ctx.get("p50", 0.0))
            low = ctx.get("p25", ctx.get("p50", 0.0))
        else:
            high = 70.0
            low = 40.0

        if score >= high:
            strengths.append(f"{label} unit grades as a clear strength ({score:.1f}).")
        elif score <= low:
            weaknesses.append(f"{label} unit looks like a liability ({score:.1f}).")

    # Ensure at least one strength/weakness.
    if not strengths and scores:
        best_key = max(scores, key=scores.get)
        best_label = dict(unit_keys).get(best_key, best_key)
        strengths.append(f"{best_label} is the most reliable unit on this roster.")

    if not weaknesses and scores:
        worst_key = min(scores, key=scores.get)
        worst_label = dict(unit_keys).get(worst_key, worst_key)
        weaknesses.append(f"{worst_label} lags behind the rest of the build.")

    dev_xf = int(team_metrics.get("dev_xf") or 0)
    dev_ss = int(team_metrics.get("dev_ss") or 0)
    dev_star = int(team_metrics.get("dev_star") or 0)
    dev_norm = int(team_metrics.get("dev_normal") or 0)
    total_premium = dev_xf + dev_ss
    total_dev = total_premium + dev_star + dev_norm

    dev_phrase = ""
    if total_premium >= 6:
        dev_phrase = f" built around {total_premium} X-Factor/Superstar pieces"
    elif total_premium >= 3:
        dev_phrase = " with a solid premium dev core"

    top_contrib_str = str(team_metrics.get("top_contributors") or "")
    top_contrib = ""
    if top_contrib_str:
        first = top_contrib_str.split(";")[0].strip()
        if first:
            top_contrib = first

    team_name = str(
        team_metrics.get("team_name") or team_metrics.get("team_abbrev") or ""
    ).strip()
    overall_rank = int(team_metrics.get("overall_rank") or 0)

    primary_strength = strengths[0] if strengths else ""
    primary_weakness = weaknesses[0] if weaknesses else ""

    summary_parts: list[str] = []
    if team_name:
        if overall_rank:
            summary_parts.append(
                f"{team_name} currently grades #{overall_rank} in roster power"
            )
        else:
            summary_parts.append(
                f"{team_name} sits in the middle of the roster power pack"
            )
    if dev_phrase:
        summary_parts.append(dev_phrase)
    if top_contrib:
        summary_parts.append(f" headlined by {top_contrib}")

    summary = ""
    if summary_parts:
        summary = "".join(summary_parts) + "."
        if primary_strength or primary_weakness:
            summary += " " + " ".join(
                s for s in [primary_strength, primary_weakness] if s
            )

    return {
        "strengths": " ".join(strengths) if strengths else primary_strength,
        "weaknesses": " ".join(weaknesses) if weaknesses else primary_weakness,
        "summary": summary,
    }


def render_html_report(
    path: str,
    teams_metrics: list[dict],
    config: dict | None = None,
    league_context: dict | None = None,
    players_by_team: dict[str, list[dict]] | None = None,
) -> None:
    """Render a basic HTML report for roster-based power rankings.

    Phase 3 scope focuses on a league-wide sortable/searchable table and
    simple bar-style charts, while keeping the layout visually aligned
    with existing docs pages such as draft_class_2026 and
    rankings_explorer.
    """

    if not teams_metrics:
        print("warn: render_html_report called with no team metrics; skipping HTML output", file=sys.stderr)
        return

    cfg = dict(config or {})
    league_ctx = dict(league_context or {})

    # Prepare compact JS data blob.
    js_teams: list[dict] = []
    for row in teams_metrics:
        js_teams.append(
            {
                "team_abbrev": row.get("team_abbrev"),
                "team_name": row.get("team_name"),
                "overall_score": row.get("overall_score"),
                "overall_rank": row.get("overall_rank"),
                "off_pass_score": row.get("off_pass_score"),
                "off_run_score": row.get("off_run_score"),
                "def_cover_score": row.get("def_cover_score"),
                "def_pass_rush_score": row.get("def_pass_rush_score"),
                "def_run_score": row.get("def_run_score"),
                "dev_xf": row.get("dev_xf"),
                "dev_ss": row.get("dev_ss"),
                "dev_star": row.get("dev_star"),
                "dev_normal": row.get("dev_normal"),
            }
        )

    # Optional per-team roster + unit breakdown data for team detail pages.
    rosters_payload: dict[str, list[dict]] = {}
    unit_breakdowns: dict[str, dict] = {}

    if players_by_team:
        # Use the same dev multipliers that drove scoring so that
        # per-unit breakdowns line up with the main grades.
        dev_cfg = cfg.get("dev_multipliers") or DEFAULT_DEV_MULTIPLIERS

        unit_labels = {
            "off_pass": "Off Pass",
            "off_run": "Off Run",
            "def_coverage": "Pass Coverage",
            "pass_rush": "Pass Rush",
            "run_defense": "Run Defense",
        }

        score_key_map = {
            "off_pass": "off_pass_score",
            "off_run": "off_run_score",
            "def_coverage": "def_cover_score",
            "pass_rush": "def_pass_rush_score",
            "run_defense": "def_run_score",
        }

        # Build payloads keyed by team abbrev so JS can quickly map
        # from a clicked team to its roster and unit breakdown.
        for row in teams_metrics:
            team_abbrev = str(row.get("team_abbrev") or "").strip()
            if not team_abbrev:
                continue

            team_players = list(players_by_team.get(team_abbrev, []))
            if team_players:
                # Sort by OVR descending for a nicer default ordering.
                team_players.sort(
                    key=lambda p: (-safe_int(p.get("ovr"), 0) or 0, p.get("player_name", "")),
                )

            roster_rows: list[dict] = []
            for p in team_players:
                dev = str(p.get("dev") or "0")
                roster_rows.append(
                    {
                        "player_id": str(p.get("player_id") or p.get("id") or ""),
                        "name": p.get("player_name") or p.get("fullName") or "?",
                        "position": p.get("position") or "?",
                        "normalized_pos": p.get("normalized_pos") or _normalize_pos_for_mapping(p.get("position", "")),
                        "ovr": safe_int(p.get("ovr"), 0) or 0,
                        "dev": dev,
                        "dev_label": DEV_LABELS.get(dev, "Normal"),
                        "top_attrs": get_top_attrs_for_player(p),
                    }
                )

            if roster_rows:
                rosters_payload[team_abbrev] = roster_rows

            if team_players:
                offense = [
                    p
                    for p in team_players
                    if assign_unit(p.get("position", "")) == "Offense"
                ]
                defense = [
                    p
                    for p in team_players
                    if assign_unit(p.get("position", "")) == "Defense"
                ]

                unit_details: dict[str, dict] = {}
                for unit_key in [
                    "off_pass",
                    "off_run",
                    "def_coverage",
                    "pass_rush",
                    "run_defense",
                ]:
                    pool = offense if unit_key.startswith("off_") else defense
                    raw_score, breakdown = _score_unit_with_breakdown(
                        pool,
                        unit_key,
                        dev_multipliers=dev_cfg,
                    )
                    norm_key = score_key_map.get(unit_key)
                    norm_val = row.get(norm_key) if norm_key else None
                    try:
                        norm_score = (float(norm_val) if norm_val is not None else None)
                    except Exception:
                        norm_score = None

                    unit_details[unit_key] = {
                        "label": unit_labels.get(unit_key, unit_key),
                        "raw_score": round(float(raw_score), 2),
                        "norm_score": norm_score,
                        "positions": breakdown.get("positions", []),
                    }

                unit_breakdowns[team_abbrev] = unit_details

    data_dict: dict[str, object] = {
        "teams": js_teams,
        "config": cfg,
        "league": league_ctx,
    }
    if rosters_payload:
        data_dict["rosters"] = rosters_payload
    if unit_breakdowns:
        data_dict["unit_breakdowns"] = unit_breakdowns

    data_blob = json.dumps(data_dict, ensure_ascii=False)

    normalization = cfg.get("normalization", "zscore")

    title = "Roster Power Rankings — Roster Analytics"
    subtitle = f"League-wide roster strength overview (normalization: {normalization})"

    # Small helper for per-team radar / spider-style visualization.
    def _radar_svg(team_row: dict) -> str:
        metrics = [
            ("off_pass_score", "OP"),
            ("off_run_score", "OR"),
            ("def_cover_score", "Cov"),
            ("def_pass_rush_score", "Rush"),
            ("def_run_score", "Run"),
        ]
        cx, cy, radius = 60.0, 60.0, 42.0

        # Background polygon at ~70% radius for visual context.
        bg_pts: list[str] = []
        for idx, _ in enumerate(metrics):
            angle = -math.pi / 2.0 + (2.0 * math.pi * idx) / len(metrics)
            r_bg = radius * 0.7
            x = cx + r_bg * math.cos(angle)
            y = cy + r_bg * math.sin(angle)
            bg_pts.append(f"{x:.1f},{y:.1f}")

        # Data polygon from unit scores.
        data_pts: list[tuple[float, float]] = []
        for idx, (key, _label) in enumerate(metrics):
            try:
                score = float(team_row.get(key) or 0.0)
            except Exception:
                score = 0.0
            score = max(0.0, min(100.0, score))
            angle = -math.pi / 2.0 + (2.0 * math.pi * idx) / len(metrics)
            r = radius * (score / 100.0)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            data_pts.append((x, y))

        poly_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts)

        abbr = str(team_row.get("team_abbrev") or "")

        svg_parts: list[str] = []
        svg_parts.append(
            '<svg class="radar-chart" viewBox="0 0 120 120" '
            f'data-team-abbr="{escape(abbr)}">'
        )
        svg_parts.append('<g class="radar-bg"><polygon points="' + " ".join(bg_pts) + '"/></g>')
        svg_parts.append('<g class="radar-axes">')
        for idx, _ in enumerate(metrics):
            angle = -math.pi / 2.0 + (2.0 * math.pi * idx) / len(metrics)
            x2 = cx + radius * math.cos(angle)
            y2 = cy + radius * math.sin(angle)
            svg_parts.append(
                '<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'.format(
                    x1=cx,
                    y1=cy,
                    x2=x2,
                    y2=y2,
                )
            )
        svg_parts.append("</g>")
        svg_parts.append('<polygon class="radar-poly" points="' + poly_pts + '"/>')
        for x, y in data_pts:
            svg_parts.append(
                '<circle class="radar-point" cx="{x:.1f}" cy="{y:.1f}" r="2"/>'.format(
                    x=x,
                    y=y,
                )
            )
        svg_parts.append("</svg>")
        return "".join(svg_parts)

    # Build HTML structure. Keep the style and table sorter closely
    # aligned with draft_class_2026.html for visual consistency.
    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang=\"en\">")
    parts.append("<head>")
    parts.append("  <meta charset=\"utf-8\" />")
    parts.append("  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />")
    parts.append(f"  <title>{escape(title)}</title>")
    parts.append("  <style>")
    parts.append("    :root { --text:#0f172a; --sub:#64748b; --muted:#94a3b8; --grid:#e2e8f0; --bg:#f7f7f7; --card:#ffffff; --accent:#3b82f6; }")
    parts.append("    body { margin:16px; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color:var(--text); background:var(--bg); }")
    parts.append("    .topbar { max-width: 1200px; margin: 0 auto 10px; display:flex; align-items:center; gap:10px; }")
    parts.append("    .back { display:inline-flex; align-items:center; gap:8px; font-size:13px; color:#1e293b; text-decoration:none; background:#fff; border:1px solid #e5e7eb; padding:6px 10px; border-radius:8px; box-shadow:0 1px 2px rgba(0,0,0,.05); }")
    parts.append("    .back:hover { background:#f8fafc; }")
    parts.append("    .container { max-width: 1200px; margin: 0 auto; background: var(--card); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow:hidden; }")
    parts.append("    header { padding: 18px 20px 10px; border-bottom: 1px solid #ececec; background:linear-gradient(180deg,#ffffff 0%,#fafafa 100%); }")
    parts.append("    h1 { margin:0; font-size: 22px; }")
    parts.append("    .subtitle { color: var(--sub); margin:8px 0 4px; font-size: 13px; }")
    parts.append("    .pill { display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px; border:1px solid #bfdbfe; background:#dbeafe; color:#1e3a8a; font-size:12px; }")
    parts.append("    .panel { padding: 14px 18px; border-bottom: 1px solid #f0f0f0; }")
    parts.append("    .section-title { font-size: 14px; font-weight: 700; margin: 0 0 10px; border-left:3px solid var(--accent); padding-left:8px; }")
    parts.append("    .section-intro { white-space: pre-wrap; color: #334155; font-size: 13px; margin: 4px 0 10px; }")
    parts.append("    .kpis { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:10px; }")
    parts.append("    .kpi { background:#f8fafc; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px; }")
    parts.append("    .kpi b { display:block; font-size: 12px; color:#0f172a; }")
    parts.append("    .kpi span { color:#334155; font-size: 18px; font-weight: 700; }")
    parts.append("    .kpi .gbar { margin-top:6px; height:6px; background:#e5e7eb; border-radius:999px; overflow:hidden; }")
    parts.append("    .kpi .gbar .fill { height:100%; background: linear-gradient(90deg, #60a5fa, #22c55e); }")
    parts.append("    .controls { display:flex; flex-wrap:wrap; align-items:center; gap:10px; font-size:13px; }")
    parts.append("    .controls label { font-weight:500; color:#475569; }")
    parts.append("    .controls input[type='search'] { padding:6px 8px; border-radius:8px; border:1px solid #e5e7eb; min-width: 220px; font-size:13px; }")
    parts.append("    .controls select { padding:6px 8px; border-radius:8px; border:1px solid #e5e7eb; font-size:13px; }")
    parts.append("    .table-wrap { margin-top:10px; border:1px solid #e5e7eb; border-radius:10px; overflow:auto; }")
    parts.append("    table { width:100%; border-collapse:collapse; font-size:12px; }")
    parts.append("    thead { background:#f8fafc; position:sticky; top:0; z-index:1; }")
    parts.append("    th, td { padding:6px 8px; border-bottom:1px solid #e5e7eb; text-align:left; }")
    parts.append("    th { font-weight:600; color:#475569; cursor:pointer; white-space:nowrap; }")
    parts.append("    tr:nth-child(even) { background:#f9fafb; }")
    parts.append("    tr:hover { background:#eef2ff; }")
    parts.append("    .num { text-align:right; font-variant-numeric: tabular-nums; }")
    parts.append("    .rank-cell { font-weight:700; }")
    parts.append("    .team-cell { display:flex; align-items:center; gap:6px; }")
    parts.append("    .team-tag { display:inline-flex; align-items:center; gap:4px; font-weight:600; }")
    parts.append("    .team-tag span { font-size:11px; color:#64748b; }")
    parts.append("    .metric { display:flex; flex-direction:column; gap:2px; }")
    parts.append("    .metric-value { font-weight:600; }")
    parts.append("    .metric-bar { height:6px; background:#e5e7eb; border-radius:999px; overflow:hidden; }")
    parts.append("    .metric-bar-fill { height:100%; background:linear-gradient(90deg,#3b82f6,#22c55e); }")
    parts.append("    .dev-chips { display:flex; flex-wrap:wrap; gap:4px; }")
    parts.append("    .chip { padding:2px 6px; border-radius:999px; border:1px solid #e5e7eb; font-size:11px; background:#f9fafb; }")
    parts.append("    .chip-xf { border-color:#fecaca; background:#fee2e2; color:#b91c1c; }")
    parts.append("    .chip-ss { border-color:#facc15; background:#fef9c3; color:#854d0e; }")
    parts.append("    .chip-star { border-color:#d4d4d8; background:#e4e4e7; color:#27272a; }")
    parts.append("    .chip-norm { border-color:#c4b5fd; background:#e0e7ff; color:#3730a3; }")
    parts.append("    .chart-strip { margin-top:8px; display:flex; flex-wrap:wrap; gap:4px; }")
    parts.append("    .chart-bar { flex:1 1 40px; min-width:40px; height:36px; background:#f8fafc; border:1px solid #e5e7eb; border-radius:6px; position:relative; overflow:hidden; }")
    parts.append("    .chart-bar-fill { position:absolute; left:0; top:0; bottom:0; background:linear-gradient(90deg,#22c55e,#16a34a); opacity:0.3; }")
    parts.append("    .chart-bar-label { position:relative; z-index:1; padding:4px 6px; font-size:11px; display:flex; flex-direction:column; justify-content:center; }")
    parts.append("    .chart-bar-label b { font-size:12px; }")
    parts.append("    .methodology-grid { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin-top:8px; font-size:12px; color:#111827; }")
    parts.append("    .methodology-col { background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; }")
    parts.append("    .methodology-col h3 { margin:0 0 6px; font-size:12px; text-transform:uppercase; letter-spacing:0.03em; color:#6b7280; }")
    parts.append("    .methodology-list { margin:0; padding-left:16px; }")
    parts.append("    .methodology-list li { margin:2px 0; }")
    parts.append("    .team-grid { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:12px; }")
    parts.append("    .team-card { border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; background:#f9fafb; display:flex; flex-direction:column; gap:8px; }")
    parts.append("    .team-card-header { display:flex; justify-content:space-between; align-items:baseline; gap:8px; }")
    parts.append("    .team-card-title { font-size:13px; font-weight:600; color:#0f172a; }")
    parts.append("    .team-card-sub { font-size:11px; color:#6b7280; }")
    parts.append("    .team-card-dev { font-size:11px; color:#4b5563; }")
    parts.append("    .team-card-dev strong { font-weight:600; }")
    parts.append("    .team-card-dev span { margin-right:6px; }")
    parts.append("    .team-card.dev-elite { border-color:#f97316; box-shadow:0 0 0 1px rgba(249,115,22,0.35); }")
    parts.append("    .team-card-body { display:flex; gap:10px; align-items:stretch; }")
    parts.append("    .radar-shell { flex:0 0 120px; display:flex; flex-direction:column; align-items:center; justify-content:center; }")
    parts.append("    .radar-chart { width:120px; height:120px; }")
    parts.append("    .radar-bg polygon { fill:#eff6ff; stroke:#dbeafe; stroke-width:1; }")
    parts.append("    .radar-axes line { stroke:#e5e7eb; stroke-width:1; }")
    parts.append("    .radar-poly { fill:rgba(59,130,246,0.3); stroke:#2563eb; stroke-width:1.5; }")
    parts.append("    .radar-point { fill:#1d4ed8; stroke:#eff6ff; stroke-width:1; r:2; }")
    parts.append("    .radar-labels { display:flex; flex-wrap:wrap; gap:4px; justify-content:center; margin-top:4px; font-size:10px; color:#6b7280; }")
    parts.append("    .radar-labels span { padding:1px 4px; border-radius:999px; background:#e5e7eb; }")
    parts.append("    .team-narrative { flex:1 1 auto; font-size:12px; color:#111827; display:flex; flex-direction:column; gap:4px; }")
    parts.append("    .team-narrative p { margin:0; }")
    parts.append("    .team-narrative strong { color:#0f172a; }")
    parts.append("    .team-narrative .label { text-transform:uppercase; font-size:11px; letter-spacing:0.04em; color:#6b7280; }")
    parts.append("    #teams-table tbody tr, .team-card { cursor:pointer; }")
    parts.append("    .team-detail-overlay { position:fixed; inset:0; display:none; align-items:flex-start; justify-content:center; padding:40px 12px; z-index:40; }")
    parts.append("    .team-detail-overlay.visible { display:flex; }")
    parts.append("    .team-detail-backdrop { position:absolute; inset:0; background:rgba(15,23,42,0.55); }")
    parts.append("    .team-detail-panel { position:relative; max-width:980px; width:100%; max-height:100%; background:#ffffff; border-radius:12px; box-shadow:0 22px 45px rgba(15,23,42,0.45); padding:16px 18px 18px; overflow:auto; }")
    parts.append("    .team-detail-close { position:absolute; top:8px; right:10px; border:none; background:transparent; font-size:18px; cursor:pointer; color:#64748b; }")
    parts.append("    .team-detail-header h2 { margin:0; font-size:18px; }")
    parts.append("    .team-detail-sub { margin:2px 0 10px; font-size:12px; color:#6b7280; }")
    parts.append("    .team-detail-body { font-size:11px; color:#111827; }")
    parts.append("    .team-detail-radar-shell { margin-bottom:8px; display:flex; justify-content:center; }")
    parts.append("    .team-detail-columns { display:grid; grid-template-columns: minmax(0,1.4fr) minmax(0,1.1fr); gap:12px; }")
    parts.append("    .team-detail-col h3 { margin:0 0 6px; font-size:13px; }")
    parts.append("    .team-detail-table { width:100%; border-collapse:collapse; font-size:11px; }")
    parts.append("    .team-detail-table th, .team-detail-table td { padding:4px 6px; border-bottom:1px solid #e5e7eb; text-align:left; }")
    parts.append("    .team-detail-table th { font-weight:600; color:#475569; background:#f9fafb; position:sticky; top:0; z-index:1; }")
    parts.append("    .team-detail-table .num { text-align:right; font-variant-numeric:tabular-nums; }")
    parts.append("    .team-detail-attr { font-variant-numeric:tabular-nums; }")
    parts.append("    .team-detail-breakdown { font-size:11px; display:flex; flex-direction:column; gap:6px; }")
    parts.append("    .team-detail-breakdown-unit { border:1px solid #e5e7eb; border-radius:8px; padding:6px 8px; background:#f8fafc; }")
    parts.append("    .team-detail-breakdown-unit h4 { margin:0 0 4px; font-size:12px; }")
    parts.append("    .team-detail-breakdown-unit table { width:100%; border-collapse:collapse; font-size:11px; }")
    parts.append("    .team-detail-breakdown-unit th, .team-detail-breakdown-unit td { padding:2px 4px; text-align:left; }")
    parts.append("    .team-detail-breakdown-unit th { color:#6b7280; font-weight:500; }")
    parts.append("    @media (max-width: 900px) { .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); } .team-grid { grid-template-columns: 1fr; } }")
    parts.append("    @media (max-width: 600px) { .kpis { grid-template-columns: 1fr; } th:nth-child(4), td:nth-child(4), th:nth-child(5), td:nth-child(5), th:nth-child(6), td:nth-child(6) { display:none; } .team-card-body { flex-direction:column; } .team-detail-columns { grid-template-columns: 1fr; } .team-detail-panel { padding:12px 10px 14px; } }")
    parts.append("  </style>")
    parts.append("  <script>")
    # Simple table sorter: mirror the behavior and structure used by
    # draft_class_2026 so that clicking any <th> in a .sortable table
    # sorts rows by that column, preferring numeric comparison when
    # possible and falling back to locale-aware string comparison.
    parts.append("  // Simple table sorter: click any <th> in a .sortable table to sort by that column")
    parts.append("  (function() {")
    parts.append("    function getCellValue(tr, idx) {")
    parts.append("      const td = tr.children[idx];")
    parts.append("      if (!td) return '';")
    parts.append("      // Prefer data-sort attribute when provided")
    parts.append("      const ds = td.getAttribute('data-sort');")
    parts.append("      const txt = ds != null ? ds : td.textContent || '';")
    parts.append("      return txt.trim();")
    parts.append("    }")
    parts.append("")
    parts.append("    function asNumber(v) {")
    parts.append("      if (v === '' || v == null) return NaN;")
    parts.append("      const n = parseFloat(v.replace(/[,\\s]/g, ''));")
    parts.append("      return isNaN(n) ? NaN : n;")
    parts.append("    }")
    parts.append("")
    parts.append("    function makeComparer(idx, asc) {")
    parts.append("      return function(a, b) {")
    parts.append("        const va = getCellValue(a, idx);")
    parts.append("        const vb = getCellValue(b, idx);")
    parts.append("        const na = asNumber(va);")
    parts.append("        const nb = asNumber(vb);")
    parts.append("        let cmp;")
    parts.append("        if (!isNaN(na) && !isNaN(nb)) {")
    parts.append("          cmp = na - nb;")
    parts.append("        } else {")
    parts.append("          cmp = va.localeCompare(vb, undefined, {numeric:true, sensitivity:'base'});")
    parts.append("        }")
    parts.append("        return asc ? cmp : -cmp;")
    parts.append("      }")
    parts.append("    }")
    parts.append("")
    parts.append("    function initSortableTables() {")
    parts.append("      document.querySelectorAll('table.sortable').forEach(function(table) {")
    parts.append("        const thead = table.tHead;")
    parts.append("        if (!thead) return;")
    parts.append("        const headers = thead.rows[0]?.cells || [];")
    parts.append("        Array.from(headers).forEach(function(th, idx) {")
    parts.append("          th.addEventListener('click', function() {")
    parts.append("            const tbody = table.tBodies[0];")
    parts.append("            if (!tbody) return;")
    parts.append("            const rows = Array.from(tbody.rows);")
    parts.append("            const current = th.getAttribute('data-sort-dir') || 'desc';")
    parts.append("            const nextDir = current === 'asc' ? 'desc' : 'asc';")
    parts.append("            rows.sort(makeComparer(idx, nextDir === 'asc'));")
    parts.append("            // Update attributes for visual state (optional)")
    parts.append("            Array.from(headers).forEach(h => h.removeAttribute('data-sort-dir'));")
    parts.append("            th.setAttribute('data-sort-dir', nextDir);")
    parts.append("            // Re-append rows")
    parts.append("            rows.forEach(r => tbody.appendChild(r));")
    parts.append("          });")
    parts.append("        });")
    parts.append("      });")
    parts.append("    }")
    parts.append("")
    parts.append("    if (document.readyState === 'loading') {")
    parts.append("      document.addEventListener('DOMContentLoaded', initSortableTables);")
    parts.append("    } else {")
    parts.append("      initSortableTables();")
    parts.append("    }")
    parts.append("  })();")
    parts.append("  (function() {")
    parts.append("    function getData() {")
    parts.append("      const el = document.getElementById('teams-data');")
    parts.append("      if (!el) return null;")
    parts.append("      try { return JSON.parse(el.textContent || '{}'); } catch (e) { return null; }")
    parts.append("    }")
    parts.append("    function initSearch() {")
    parts.append("      const input = document.getElementById(\"team-search\");")
    parts.append("      if (!input) return;")
    parts.append("      input.addEventListener(\"input\", function() {")
    parts.append("        const q = (this.value || '').toLowerCase();")
    parts.append("        const rows = document.querySelectorAll(\"#teams-table tbody tr\");")
    parts.append("        rows.forEach(function(tr) {")
    parts.append("          const name = (tr.getAttribute(\"data-team-name\") || '').toLowerCase();")
    parts.append("          const abbr = (tr.getAttribute(\"data-team-abbr\") || '').toLowerCase();")
    parts.append("          const hay = name + ' '+ abbr;")
    parts.append("          tr.style.display = hay.indexOf(q) === -1 ? 'none' : '';")
    parts.append("        });")
    parts.append("      });")
    parts.append("    }")
    parts.append("    function closeTeamDetail() {")
    parts.append("      const overlay = document.getElementById('team-detail-overlay');")
    parts.append("      if (!overlay) return;")
    parts.append("      overlay.classList.remove('visible');")
    parts.append("      overlay.setAttribute('aria-hidden', 'true');")
    parts.append("    }")
    parts.append("    function openTeamDetail(abbr, DATA) {")
    parts.append("      if (!DATA || !DATA.rosters) return;")
    parts.append("      const rosterMap = DATA.rosters || {};")
    parts.append("      const unitsMap = DATA.unit_breakdowns || {};")
    parts.append("      const roster = rosterMap[abbr];")
    parts.append("      if (!roster || !roster.length) return;")
    parts.append("      const overlay = document.getElementById('team-detail-overlay');")
    parts.append("      if (!overlay) return;")
    parts.append("      const teamMeta = (DATA.teams || []).find(function(t) { return String(t.team_abbrev || '') === String(abbr || ''); });")
    parts.append("      const titleEl = document.getElementById('team-detail-title');")
    parts.append("      const subEl = document.getElementById('team-detail-subtitle');")
    parts.append("      const rosterTable = document.getElementById('team-detail-roster');")
    parts.append("      const breakdownRoot = document.getElementById('team-detail-breakdown');")
    parts.append("      if (!rosterTable || !breakdownRoot) return;")
    parts.append("      const name = teamMeta && (teamMeta.team_name || teamMeta.team_abbrev || abbr) || abbr;")
    parts.append("      const rank = teamMeta && teamMeta.overall_rank;")
    parts.append("      const overall = teamMeta && teamMeta.overall_score;")
    parts.append("      if (titleEl) { titleEl.textContent = name + ' (' + abbr + ')'; }")
    parts.append("      if (subEl) {")
    parts.append("        const bits = [];")
    parts.append("        if (typeof rank === 'number' && rank) bits.push('#' + rank + ' overall roster grade');")
    parts.append("        if (typeof overall === 'number') bits.push('Overall ' + overall.toFixed(1));")
    parts.append("        subEl.textContent = bits.join(' • ');")
    parts.append("      }")
    parts.append("      const radarHost = document.getElementById('team-detail-radar');")
    parts.append("      if (radarHost) {")
    parts.append("        radarHost.innerHTML = '';")
    parts.append("        let source = null;")
    parts.append("        document.querySelectorAll('.radar-chart').forEach(function(el) {")
    parts.append("          if (String(el.getAttribute('data-team-abbr') || '') === String(abbr || '')) { source = el; }")
    parts.append("        });")
    parts.append("        if (source) { radarHost.innerHTML = source.outerHTML; }")
    parts.append("      }")
    parts.append("      const byId = {};")
    parts.append("      roster.forEach(function(p) { if (p && p.player_id != null) byId[String(p.player_id)] = p; });")
    parts.append("      rosterTable.innerHTML = '';")
    parts.append("      const thead = document.createElement('thead');")
    parts.append("      thead.innerHTML = '<tr><th>Pos</th><th>Player</th><th class=num>OVR</th><th>Dev</th><th>Top attributes</th></tr>';")
    parts.append("      rosterTable.appendChild(thead);")
    parts.append("      const tbody = document.createElement('tbody');")
    parts.append("      roster.forEach(function(p) {")
    parts.append("        const tr = document.createElement('tr');")
    parts.append("        const attrs = (p.top_attrs || []).map(function(a) { return a.key + ': ' + a.value; }).join(', ');")
    parts.append("        tr.innerHTML = '<td>' + (p.position || '') + '</td>' +")
    parts.append("          '<td>' + (p.name || '') + '</td>' +")
    parts.append("          '<td class=num>' + (p.ovr != null ? p.ovr : '') + '</td>' +")
    parts.append("          '<td>' + (p.dev_label || '') + '</td>' +")
    parts.append("          '<td class=team-detail-attr>' + attrs + '</td>';")
    parts.append("        tbody.appendChild(tr);")
    parts.append("      });")
    parts.append("      rosterTable.appendChild(tbody);")
    parts.append("      breakdownRoot.innerHTML = '';")
    parts.append("      const allUnits = ['off_pass','off_run','def_coverage','pass_rush','run_defense'];")
    parts.append("      const labels = { off_pass: 'Off Pass', off_run: 'Off Run', def_coverage: 'Pass Coverage', pass_rush: 'Pass Rush', run_defense: 'Run Defense' };")
    parts.append("      const teamUnits = unitsMap && unitsMap[abbr];")
    parts.append("      if (teamUnits) {")
    parts.append("        allUnits.forEach(function(key) {")
    parts.append("          const u = teamUnits[key];")
    parts.append("          if (!u) return;")
    parts.append("          const card = document.createElement('div');")
    parts.append("          card.className = 'team-detail-breakdown-unit';")
    parts.append("          const h = document.createElement('h4');")
    parts.append("          const label = (u.label || labels[key] || key);")
    parts.append("          let grade = '';")
    parts.append("          if (typeof u.norm_score === 'number') grade = ' — grade ' + u.norm_score.toFixed(1);")
    parts.append("          h.textContent = label + grade;")
    parts.append("          card.appendChild(h);")
    parts.append("          if (typeof u.raw_score === 'number') {")
    parts.append("            const p = document.createElement('p');")
    parts.append("            p.textContent = 'Raw starter blend: ' + u.raw_score.toFixed(1);")
    parts.append("            card.appendChild(p);")
    parts.append("          }")
    parts.append("          const tbl = document.createElement('table');")
    parts.append("          const th = document.createElement('thead');")
    parts.append("          th.innerHTML = '<tr><th>Pos</th><th class=num>Wt%</th><th class=num>Pos score</th><th>Starters used</th></tr>';")
    parts.append("          tbl.appendChild(th);")
    parts.append("          const tb = document.createElement('tbody');")
    parts.append("          (u.positions || []).forEach(function(posInfo) {")
    parts.append("            const tr = document.createElement('tr');")
    parts.append("            const wtPct = (posInfo.weight_share != null ? (posInfo.weight_share * 100).toFixed(0) : '');")
    parts.append("            const posScore = (posInfo.avg_unit_score != null ? posInfo.avg_unit_score.toFixed(1) : '');")
    parts.append("            const starters = (posInfo.players || []).map(function(pl) {")
    parts.append("              const pid = pl.player_id != null ? String(pl.player_id) : '';")
    parts.append("              const base = pid && byId[pid] ? byId[pid] : null;")
    parts.append("              if (!base) return '';")
    parts.append("              const tag = (base.position || '') + ' ' + (base.name || '');")
    parts.append("              const ovr = base.ovr != null ? base.ovr : '';")
    parts.append("              const dev = base.dev_label || '';")
    parts.append("              const parts = [tag];")
    parts.append("              if (ovr !== '') parts.push(String(ovr));")
    parts.append("              if (dev) parts.push(dev);")
    parts.append("              return parts.join(' ');")
    parts.append("            }).filter(Boolean).join('; ');")
    parts.append("            tr.innerHTML = '<td>' + (posInfo.pos || '') + '</td>' +")
    parts.append("              '<td class=num>' + wtPct + '</td>' +")
    parts.append("              '<td class=num>' + posScore + '</td>' +")
    parts.append("              '<td>' + starters + '</td>';")
    parts.append("            tb.appendChild(tr);")
    parts.append("          });")
    parts.append("          tbl.appendChild(tb);")
    parts.append("          card.appendChild(tbl);")
    parts.append("          breakdownRoot.appendChild(card);")
    parts.append("        });")
    parts.append("      }")
    parts.append("      overlay.classList.add('visible');")
    parts.append("      overlay.setAttribute('aria-hidden', 'false');")
    parts.append("    }")
    parts.append("    function attachTeamDetailHandlers() {")
    parts.append("      initSearch();")
    parts.append("      const DATA = getData();")
    parts.append("      if (!DATA) return;")
    parts.append("      const rows = document.querySelectorAll('#teams-table tbody tr[data-team-abbr]');")
    parts.append("      rows.forEach(function(tr) {")
    parts.append("        tr.addEventListener('click', function() {")
    parts.append("          const abbr = tr.getAttribute('data-team-abbr');")
    parts.append("          if (abbr) openTeamDetail(abbr, DATA);")
    parts.append("        });")
    parts.append("      });")
    parts.append("      const cards = document.querySelectorAll('.team-card[data-team-abbr]');")
    parts.append("      cards.forEach(function(card) {")
    parts.append("        card.addEventListener('click', function() {")
    parts.append("          const abbr = card.getAttribute('data-team-abbr');")
    parts.append("          if (abbr) openTeamDetail(abbr, DATA);")
    parts.append("        });")
    parts.append("      });")
    parts.append("      const overlay = document.getElementById('team-detail-overlay');")
    parts.append("      if (overlay) {")
    parts.append("        const closeBtn = overlay.querySelector('.team-detail-close');")
    parts.append("        const backdrop = overlay.querySelector('.team-detail-backdrop');")
    parts.append("        if (closeBtn) closeBtn.addEventListener('click', closeTeamDetail);")
    parts.append("        if (backdrop) backdrop.addEventListener('click', closeTeamDetail);")
    parts.append("      }")
    parts.append("      document.addEventListener('keydown', function(ev) { if (ev.key === 'Escape') closeTeamDetail(); });")
    parts.append("    }")
    parts.append("    if (document.readyState === 'loading') {")
    parts.append("      document.addEventListener('DOMContentLoaded', attachTeamDetailHandlers);")
    parts.append("    } else {")
    parts.append("      attachTeamDetailHandlers();")
    parts.append("    }")
    parts.append("  })();")
    parts.append("  </script>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append("  <div class=\"topbar\"><a class=\"back\" href=\"../index.html\" title=\"Back to index\">&#8592; Back to Index</a></div>")
    parts.append("  <div class=\"container\">")
    parts.append("    <header>")
    parts.append(f"      <h1>{escape(title)} <span class=\"pill\">Roster-based</span></h1>")
    parts.append(f"      <div class=\"subtitle\">{escape(subtitle)}</div>")
    parts.append(
        "      <div class=\"subtitle\">"
        "For X/Y roster unit comparison charts (Off vs Def, Pass vs Run, coverage vs pass rush), "
        "open the <a href='power_rankings_roster_charts.html'>Roster Power Explorer</a>."
        "</div>"
    )
    parts.append("    </header>")

    # Overview KPIs: show how strong the league actually is instead of
    # three ~50.0 averages from z-score normalization.
    parts.append("    <section class=\"panel\" id=\"overview\">")
    parts.append("      <div class=\"section-title\">League Overview</div>")
    parts.append(
        "      <div class=\"section-intro\">Scores are normalized 0–100 across the league. "
        "Around 50 is an average roster, 70+ is contender territory, and 40 or below flags a problem build. "
        "These snapshots show the spread of overall roster strength this season.</div>"
    )
    parts.append("      <div class=\"kpis\">")

    def _fmt(val: float | None) -> str:
        try:
            if val is None:
                return "—"
            return f"{val:.1f}"
        except Exception:
            return "—"

    ov = league_ctx.get("overall_score") or {}
    parts.append(
        "        <div class=\"kpi\"><b>Best roster score</b><span>"
        + escape(_fmt(ov.get("max")))
        + "</span><div class=\"gbar\"><div class=\"fill\" style=\"width: "
        + escape(_fmt(ov.get("max")))
        + "%\"></div></div></div>"
    )
    parts.append(
        "        <div class=\"kpi\"><b>League median</b><span>"
        + escape(_fmt(ov.get("p50")))
        + "</span><div class=\"gbar\"><div class=\"fill\" style=\"width: "
        + escape(_fmt(ov.get("p50")))
        + "%\"></div></div></div>"
    )
    parts.append(
        "        <div class=\"kpi\"><b>Weakest roster score</b><span>"
        + escape(_fmt(ov.get("min")))
        + "</span><div class=\"gbar\"><div class=\"fill\" style=\"width: "
        + escape(_fmt(ov.get("min")))
        + "%\"></div></div></div>"
    )

    parts.append("      </div>")
    parts.append("      <div class=\"chart-strip\" id=\"overall-chart\"></div>")
    parts.append("    </section>")

    # Methodology / configuration overview.
    parts.append("    <section class=\"panel\" id=\"methodology\">")
    parts.append("      <div class=\"section-title\">Methodology &amp; Config</div>")

    norm_text = "z-score (mean ~50, spread by standard deviation)"
    if normalization == "minmax":
        norm_text = "min–max to [0,100] across teams"

    parts.append(
        '      <div class="section-intro">'
        + escape(
            "Each unit score is a position-weighted blend of starter-quality ratings, "
            "boosted by premium dev traits at high OVR bands and then normalized to a 0–100 scale ("
            + norm_text
            + ")."
        )
        + "</div>"
    )

    # Unit position weighting lines (always based on the position-level
    # weights baked into this script so that readers can see which
    # positions drive each unit, regardless of overall unit weight
    # tweaks).
    unit_weight_lines: list[str] = []
    unit_labels = {
        "off_pass": "Off Pass (QB/WR/TE/OL)",
        "off_run": "Off Run (RB/FB/TE/OL)",
        "def_coverage": "Pass Coverage (CB/S/LB)",
        "pass_rush": "Pass Rush (DE/DT/LB)",
        "run_defense": "Run Defense (DE/DT/LB/S)",
    }
    for key in ["off_pass", "off_run", "def_coverage", "pass_rush", "run_defense"]:
        weights = UNIT_POSITION_WEIGHTS.get(key, {})
        if not weights:
            continue
        total = sum(v for v in weights.values() if v > 0)
        if total <= 0:
            continue
        parts_line: list[str] = []
        for pos, w in sorted(weights.items(), key=lambda kv: -kv[1]):
            if w <= 0:
                continue
            pct = (w / total) * 100.0
            parts_line.append(f"{pos} {pct:.0f}%")
        if parts_line:
            unit_label = unit_labels.get(key, key)
            unit_weight_lines.append(f"{unit_label}: " + ", ".join(parts_line))

    # Dev trait ladder description. Prefer any runtime configuration
    # provided via the CLI, falling back to defaults.
    dev_cfg = cfg.get("dev_multipliers") or DEFAULT_DEV_MULTIPLIERS
    dev_lines: list[str] = []
    for dev_code, label in DEV_LABELS.items():
        ladder = dev_cfg.get(dev_code) or DEFAULT_DEV_MULTIPLIERS.get(dev_code, [])
        if not ladder:
            dev_lines.append(f"{label}: baseline impact only (no extra multiplier by default).")
            continue
        parts_line = []
        for threshold, bonus in ladder:
            parts_line.append(f"+{bonus * 100:.0f}% above {threshold} OVR")
        dev_lines.append(f"{label}: " + ", ".join(parts_line))

    # Overall weighting text. Prefer runtime-configured overall unit
    # weights so the explanation matches the actual composite score.
    overall_cfg = cfg.get("overall_unit_weights") or DEFAULT_OVERALL_UNIT_WEIGHTS
    overall_parts: list[str] = []
    for key, label in [
        ("off_pass", "Off Pass"),
        ("off_run", "Off Run"),
        ("def_coverage", "Pass Coverage"),
        ("pass_rush", "Pass Rush"),
    ]:
        w = (overall_cfg.get(key) if isinstance(overall_cfg, dict) else None)
        if w is None or w <= 0:
            continue
        overall_parts.append(f"{label} {w * 100:.0f}%")
    overall_text = " + ".join(overall_parts)

    parts.append("      <div class=\"methodology-grid\">")
    parts.append("        <div class=\"methodology-col\">")
    parts.append("          <h3>Units &amp; position weighting</h3>")
    parts.append("          <ul class=\"methodology-list\">")
    for line in unit_weight_lines:
        parts.append("            <li>" + escape(line) + "</li>")
    parts.append("          </ul>")
    parts.append("        </div>")

    parts.append("        <div class=\"methodology-col\">")
    parts.append("          <h3>Dev traits impact</h3>")
    parts.append("          <ul class=\"methodology-list\">")
    for line in dev_lines:
        parts.append("            <li>" + escape(line) + "</li>")
    parts.append("          </ul>")
    parts.append("        </div>")

    parts.append("        <div class=\"methodology-col\">")
    parts.append("          <h3>Normalization &amp; overall score</h3>")
    if overall_text:
        parts.append(
            "          <p>" + escape(
                "Overall roster power combines normalized unit scores using: "
                + overall_text
                + ". Run Defense is shown as its own unit but not currently weighted into the composite score by default."
            )
            + "</p>"
        )
    parts.append(
        "          <p>" + escape(
            "Normalization method: " + normalization + " (" + norm_text + ")."
        )
        + "</p>"
    )
    parts.append("        </div>")
    parts.append("      </div>")
    parts.append("    </section>")

    # Controls + league-wide table.
    parts.append("    <section class=\"panel\" id=\"teams\">")
    parts.append("      <div class=\"section-title\">Teams – Roster Power Table</div>")
    parts.append("      <div class=\"controls\">")
    parts.append("        <label for=\"team-search\">Search team:</label>")
    parts.append("        <input id=\"team-search\" type=\"search\" placeholder=\"Filter by team or abbrev...\" />")
    parts.append("        <span style=\"flex:1 0 auto\"></span>")
    parts.append("        <span>Tip: click column headers to sort (overall or any unit).</span>")
    parts.append("      </div>")
    parts.append("      <div class=\"table-wrap\">")
    parts.append("        <table class=\"sortable\" id=\"teams-table\">")
    parts.append("          <thead><tr>"
                 "<th>Rank</th>"
                 "<th>Team</th>"
                 "<th>Overall</th>"
                 "<th>Off Pass</th>"
                 "<th>Off Run</th>"
                 "<th>Def Coverage</th>"
                 "<th>Pass Rush</th>"
                 "<th>Run Def</th>"
                 "<th>Dev traits</th>"
                 "<th>Top contributors</th>"
                 "</tr></thead>")
    parts.append("          <tbody>")

    for row in teams_metrics:
        team_abbrev = str(row.get("team_abbrev") or "")
        team_name = str(row.get("team_name") or team_abbrev)
        overall_score = float(row.get("overall_score") or 0.0)
        off_pass_score = float(row.get("off_pass_score") or 0.0)
        off_run_score = float(row.get("off_run_score") or 0.0)
        def_cover_score = float(row.get("def_cover_score") or 0.0)
        def_pr_score = float(row.get("def_pass_rush_score") or 0.0)
        def_run_score = float(row.get("def_run_score") or 0.0)
        overall_rank = int(row.get("overall_rank") or 0)
        dev_xf = int(row.get("dev_xf") or 0)
        dev_ss = int(row.get("dev_ss") or 0)
        dev_star = int(row.get("dev_star") or 0)
        dev_norm = int(row.get("dev_normal") or 0)
        contrib = str(row.get("top_contributors") or "")

        parts.append(
            "            <tr data-team-abbr=\""
            + escape(team_abbrev)
            + "\" data-team-name=\""
            + escape(team_name)
            + "\">"
        )
        parts.append(
            "              <td class=\"num rank-cell\" data-sort=\""
            + escape(str(overall_rank))
            + "\">"
            + escape(str(overall_rank))
            + "</td>"
        )
        parts.append(
            "              <td><div class=\"team-cell\"><span class=\"team-tag\">"
            + escape(team_name)
            + "<span>"
            + escape(team_abbrev)
            + "</span></span></div></td>"
        )

        def _metric_cell(val: float) -> str:
            pct = max(0.0, min(100.0, float(val)))
            return (
                "<td class=\"num\" data-sort=\""
                + escape(f"{val:.1f}")
                + "\"><div class=\"metric\"><span class=\"metric-value\">"
                + escape(f"{val:.1f}")
                + "</span><div class=\"metric-bar\"><div class=\"metric-bar-fill\" style=\"width: "
                + escape(f"{pct:.1f}")
                + "%\"></div></div></div></td>"
            )

        parts.append("              " + _metric_cell(overall_score))
        parts.append("              " + _metric_cell(off_pass_score))
        parts.append("              " + _metric_cell(off_run_score))
        parts.append("              " + _metric_cell(def_cover_score))
        parts.append("              " + _metric_cell(def_pr_score))
        parts.append("              " + _metric_cell(def_run_score))

        dev_html = [
            f"<span class=\"chip chip-xf\">XF {dev_xf}</span>",
            f"<span class=\"chip chip-ss\">SS {dev_ss}</span>",
            f"<span class=\"chip chip-star\">Star {dev_star}</span>",
            f"<span class=\"chip chip-norm\">Norm {dev_norm}</span>",
        ]
        parts.append(
            "              <td><div class=\"dev-chips\">"
            + "".join(dev_html)
            + "</div></td>"
        )

        parts.append("              <td>" + escape(contrib) + "</td>")
        parts.append("            </tr>")

    parts.append("          </tbody>")
    parts.append("        </table>")
    parts.append("      </div>")
    parts.append("    </section>")

    # Team-level cards with radar-style unit overview and narrative.
    parts.append("    <section class=\"panel\" id=\"team-insights\">")
    parts.append("      <div class=\"section-title\">Team Unit Profiles &amp; Narratives</div>")
    parts.append(
        '      <div class="section-intro">'
        + escape(
            "Per-team view of unit balance, dev-trait composition, and roster storylines. "
            "Use alongside the table above when scouting matchups or trade targets."
        )
        + "</div>"
    )
    parts.append("      <div class=\"team-grid\">")

    for row in teams_metrics:
        team_abbrev = str(row.get("team_abbrev") or "")
        team_name = str(row.get("team_name") or team_abbrev)
        overall_score = float(row.get("overall_score") or 0.0)
        overall_rank = int(row.get("overall_rank") or 0)
        dev_xf = int(row.get("dev_xf") or 0)
        dev_ss = int(row.get("dev_ss") or 0)
        dev_star = int(row.get("dev_star") or 0)
        dev_norm = int(row.get("dev_normal") or 0)

        premium_dev = dev_xf + dev_ss
        card_classes = ["team-card"]
        if premium_dev >= 6:
            card_classes.append("dev-elite")
        card_class = " ".join(card_classes)

        narrative = generate_team_narrative(row, league_ctx)
        strengths_text = str(narrative.get("strengths") or "").strip()
        weaknesses_text = str(narrative.get("weaknesses") or "").strip()
        summary_text = str(narrative.get("summary") or "").strip()

        parts.append(
            "        <article class=\""
            + card_class
            + "\" data-team-abbr=\""
            + escape(team_abbrev)
            + "\">"
        )
        parts.append("          <div class=\"team-card-header\">")
        parts.append("            <div>")
        parts.append(
            '              <div class="team-card-title">'
            + escape(team_name)
            + " <span>("
            + escape(team_abbrev)
            + ")</span></div>"
        )
        parts.append(
            '              <div class="team-card-sub">Overall '
            + escape(f"{overall_score:.1f}")
            + " (rank "
            + escape(str(overall_rank))
            + ")</div>"
        )
        parts.append("            </div>")
        parts.append("            <div class=\"team-card-dev\">")
        parts.append(
            "              <strong>Dev traits:</strong> "
            + "<span>XF "
            + escape(str(dev_xf))
            + "</span><span>SS "
            + escape(str(dev_ss))
            + "</span><span>Star "
            + escape(str(dev_star))
            + "</span><span>Norm "
            + escape(str(dev_norm))
            + "</span>"
        )
        parts.append("            </div>")
        parts.append("          </div>")

        radar_html = _radar_svg(row)

        # Radar + legend: show the actual numeric unit grades and
        # spell out what each corner means so the polygon is easier
        # to read at a glance.
        off_pass = float(row.get("off_pass_score") or 0.0)
        off_run = float(row.get("off_run_score") or 0.0)
        cov = float(row.get("def_cover_score") or 0.0)
        rush = float(row.get("def_pass_rush_score") or 0.0)
        run_def = float(row.get("def_run_score") or 0.0)

        parts.append("          <div class=\"team-card-body\">")
        parts.append("            <div class=\"radar-shell\">")
        parts.append("              " + radar_html)
        parts.append(
            "              <div class=\"radar-labels\">"
            + "<span>Off Pass "
            + escape(f"{off_pass:.0f}")
            + "</span><span>Off Run "
            + escape(f"{off_run:.0f}")
            + "</span><span>Coverage "
            + escape(f"{cov:.0f}")
            + "</span><span>Pass Rush "
            + escape(f"{rush:.0f}")
            + "</span><span>Run Def "
            + escape(f"{run_def:.0f}")
            + "</span>"
            + "</div>"
        )
        parts.append("            </div>")

        parts.append(
            '            <div class="team-narrative" data-team-abbr="'
            + escape(team_abbrev)
            + "\">"
        )
        if summary_text:
            parts.append("              <p class=\"label\">Summary</p>")
            parts.append("              <p>" + escape(summary_text) + "</p>")
        if strengths_text:
            parts.append("              <p class=\"label\">Strengths</p>")
            parts.append("              <p>" + escape(strengths_text) + "</p>")
        if weaknesses_text:
            parts.append("              <p class=\"label\">Weaknesses</p>")
            parts.append("              <p>" + escape(weaknesses_text) + "</p>")
        parts.append("            </div>")
        parts.append("          </div>")
        parts.append("        </article>")

    parts.append("      </div>")
    parts.append("    </section>")

    # Team detail overlay used as an in-page "team page". Clicking a
    # row in the table or a team card opens this panel and shows the
    # full roster plus a per-unit scoring breakdown for that team.
    parts.append("    <div id=\"team-detail-overlay\" class=\"team-detail-overlay\" aria-hidden=\"true\">")
    parts.append("      <div class=\"team-detail-backdrop\"></div>")
    parts.append("      <div class=\"team-detail-panel\">")
    parts.append("        <button type=\"button\" class=\"team-detail-close\" aria-label=\"Close team detail\">&#x00D7;</button>")
    parts.append("        <div class=\"team-detail-header\">")
    parts.append("          <h2 id=\"team-detail-title\"></h2>")
    parts.append("          <p id=\"team-detail-subtitle\" class=\"team-detail-sub\"></p>")
    parts.append("        </div>")
    parts.append("        <div class=\"team-detail-body\">")
    parts.append("          <div class=\"team-detail-radar-shell\"><div id=\"team-detail-radar\"></div></div>")
    parts.append("          <div class=\"team-detail-columns\">")
    parts.append("            <section class=\"team-detail-col\">")
    parts.append("              <h3>Roster overview (OVR &amp; key attributes)</h3>")
    parts.append("              <table id=\"team-detail-roster\" class=\"team-detail-table\"></table>")
    parts.append("            </section>")
    parts.append("            <section class=\"team-detail-col\">")
    parts.append("              <h3>Unit strength breakdown</h3>")
    parts.append("              <div id=\"team-detail-breakdown\" class=\"team-detail-breakdown\"></div>")
    parts.append("            </section>")
    parts.append("          </div>")
    parts.append("        </div>")
    parts.append("      </div>")
    parts.append("    </div>")

    parts.append("  </div>")
    parts.append("  <script id=\"teams-data\" type=\"application/json\">")
    parts.append(data_blob)
    parts.append("  </script>")
    parts.append("</body>")
    parts.append("</html>")

    html_out = "\n".join(parts)
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    print(f"wrote power rankings HTML report to {path}", file=sys.stdout)
