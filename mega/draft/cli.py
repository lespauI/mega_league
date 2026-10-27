"""Command-line entry point for draft class analytics."""
from __future__ import annotations

import argparse
import os
import sys

from .analytics import (
    build_round1_entries,
    build_team_logo_map,
    compute_analytics,
    gather_rookies,
    read_csv,
    read_mock_draft_md,
    read_section_intros,
    warn_missing_columns,
)
from ..reporting.draft_class import generate_html

def main():
    ap = argparse.ArgumentParser(description='Generate Draft Class Analytics HTML')
    ap.add_argument('--year', type=int, required=True, help='Draft class year (e.g., 2026)')
    ap.add_argument('--players', default='MEGA_players.csv', help='Path to players CSV (default: MEGA_players.csv)')
    ap.add_argument('--teams', default='MEGA_teams.csv', help='Path to teams CSV (default: MEGA_teams.csv)')
    ap.add_argument('--out', default=None, help='Output HTML path (default: docs/draft_class_<year>.html)')
    ap.add_argument('--league-prefix', default='MEGA League', help='Optional league/brand suffix for <title>')
    ap.add_argument('--title', dest='title_override', default=None, help='Optional full page <title> override string')
    ap.add_argument('--section-intros', dest='section_intros', default=None, help='Path to JSON mapping for section intros')
    ap.add_argument('--intro-default', dest='intro_default', default=None, help='Default intro text used when a section is missing in mapping')
    ap.add_argument('--mock-md', dest='mock_md', default=None, help='Path to mock draft markdown (docs/draft_mock.md). If omitted and default exists, it will be used.')
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
    intros_map = read_section_intros(args.section_intros)
    # Mock draft notes (optional)
    mock_md_path = args.mock_md
    if not mock_md_path:
        default_md = os.path.join('docs', 'draft_mock.md')
        if os.path.exists(default_md):
            mock_md_path = default_md
    mock_lookup = read_mock_draft_md(mock_md_path)
    # Build round 1 entries from raw players to access full ratings/traits
    round1_entries = build_round1_entries(players, team_logo_map, year=args.year)
    html_out = generate_html(
        args.year, rookies, analytics, team_logo_map,
        title_suffix=args.league_prefix,
        title_override=args.title_override,
        section_intros=intros_map,
        intro_default=args.intro_default,
        round1_entries=round1_entries,
        round1_mock=mock_lookup,
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
