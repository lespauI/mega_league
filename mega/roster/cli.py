"""Command-line entry point for roster power rankings."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .inputs import build_team_index, export_team_rosters, normalize_player_row, read_players, read_teams
from .scoring import (
    DEFAULT_DEV_MULTIPLIERS,
    DEFAULT_OVERALL_UNIT_WEIGHTS,
    build_team_metrics,
    write_power_rankings_csv,
)
from ..reporting.roster_power import compute_league_context, render_html_report

def _load_json_spec(spec: str, *, label: str) -> dict:
    """Load a JSON mapping from a file path or inline JSON string.

    The *spec* value may be either a path to a JSON file or a literal
    JSON object string. This helper is used for configuration flags like
    ``--weights-json`` and ``--dev-multipliers-json`` so that callers
    can keep small configs inline or in separate files.
    """

    if not spec:
        return {}

    # Prefer treating *spec* as a file path when it exists on disk.
    if os.path.exists(spec):
        try:
            with open(spec, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"error: failed to load {label} JSON from file {spec}: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)
    else:
        try:
            data = json.loads(spec)
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"error: failed to parse {label} JSON value: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)

    if not isinstance(data, dict):
        print(
            f"error: {label} JSON must be a mapping/object (got {type(data).__name__})",
            file=sys.stderr,
        )
        sys.exit(2)

    return data


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Roster-based power rankings: roster exports and unit scoring"
        )
    )

    parser.add_argument(
        "--players",
        default="MEGA_players.csv",
        help="Path to MEGA_players.csv (default: MEGA_players.csv)",
    )
    parser.add_argument(
        "--teams",
        default="MEGA_teams.csv",
        help="Path to MEGA_teams.csv (default: MEGA_teams.csv)",
    )
    parser.add_argument(
        "--rosters-dir",
        default=os.path.join("output", "team_rosters"),
        help="Directory for per-team roster CSVs (default: output/team_rosters)",
    )

    # Roster export on by default; allow explicit opt-out.
    parser.add_argument(
        "--export-rosters",
        dest="export_rosters",
        action="store_true",
        help="Export per-team roster CSVs (default)",
    )
    parser.add_argument(
        "--no-export-rosters",
        dest="export_rosters",
        action="store_false",
        help="Skip per-team roster CSV export",
    )
    parser.set_defaults(export_rosters=True)

    parser.add_argument(
        "--out-csv",
        default=os.path.join("output", "power_rankings_roster.csv"),
        help="Output CSV for power rankings (default: output/power_rankings_roster.csv)",
    )
    parser.add_argument(
        "--out-html",
        default=os.path.join("docs", "power_rankings_roster.html"),
        help="Output HTML report path (default: docs/power_rankings_roster.html)",
    )
    parser.add_argument(
        "--include-st",
        action="store_true",
        help="Include Special Teams unit in exports and scoring",
    )
    parser.add_argument(
        "--weights-json",
        help=(
            "JSON mapping for overall unit weights (path to file or inline JSON). "
            "Example: '{\"off_pass\": 0.35, \"off_run\": 0.15, "
            "\"def_coverage\": 0.30, \"pass_rush\": 0.20}'."
        ),
    )
    parser.add_argument(
        "--dev-multipliers-json",
        help=(
            "JSON mapping for dev multipliers by dev tier and OVR band "
            "(path to file or inline JSON). Keys are devTrait codes "
            "('3' X-Factor, '2' Superstar, '1' Star, '0' Normal) and values "
            "are [ovr_threshold, bonus] pairs; e.g. '{\"3\": [[90, 0.15], [85, 0.10]]}'."
        ),
    )
    parser.add_argument(
        "--normalization",
        choices=["zscore", "minmax"],
        default="zscore",
        help="Normalization method for unit scores (default: zscore)",
    )
    parser.add_argument(
        "--no-clobber",
        action="store_true",
        help=(
            "Fail if target outputs already exist instead of overwriting "
            "(applies to CSV/HTML and roster CSVs)."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Optional JSON-based configuration for overall unit weights and
    # dev multipliers. These override the hard-coded defaults when
    # provided, enabling experimentation without code changes.
    overall_weights: dict[str, float] | None = None
    dev_multipliers: dict | None = None

    if getattr(args, "weights_json", None):
        raw = _load_json_spec(args.weights_json, label="weights")
        # Cast values to float defensively.
        overall_weights = {str(k): float(v) for k, v in raw.items()}

    if getattr(args, "dev_multipliers_json", None):
        dev_multipliers = _load_json_spec(args.dev_multipliers_json, label="dev-multipliers")

    # Respect --no-clobber by refusing to overwrite existing primary
    # outputs (CSV/HTML and roster CSVs).
    if getattr(args, "no_clobber", False):
        existing: list[str] = []
        if os.path.exists(args.out_csv):
            existing.append(args.out_csv)
        if os.path.exists(args.out_html):
            existing.append(args.out_html)
        if args.export_rosters and os.path.isdir(args.rosters_dir):
            for name in os.listdir(args.rosters_dir):
                if name.lower().endswith(".csv"):
                    existing.append(os.path.join(args.rosters_dir, name))
                    break
        if existing:
            print(
                "error: --no-clobber specified and one or more outputs already exist: "
                + ", ".join(existing),
                file=sys.stderr,
            )
            return 1

    if args.verbose:
        print(
            f"info: loading teams from {args.teams} and players from {args.players}",
            file=sys.stderr,
        )

    teams = read_teams(args.teams)
    team_index = build_team_index(teams)

    players_raw = read_players(args.players)
    players: list[dict] = [normalize_player_row(r, team_index) for r in players_raw]

    # Pre-compute players grouped by team abbrev so both the scoring
    # pipeline and HTML renderer can reason about per-team rosters
    # without re-deriving this mapping.
    players_by_team: dict[str, list[dict]] = {}
    for p in players:
        abbr = (p.get("team_abbrev") or "").strip()
        if not abbr or abbr == "FA":
            continue
        players_by_team.setdefault(abbr, []).append(p)

    if args.export_rosters:
        if args.verbose:
            print(
                f"info: exporting team rosters to {args.rosters_dir}",
                file=sys.stderr,
            )
        export_team_rosters(
            players,
            team_index,
            args.rosters_dir,
            split_units=True,
            include_st=args.include_st,
        )
    else:
        if args.verbose:
            print("info: --no-export-rosters specified; skipping roster export", file=sys.stderr)

    # Phase 2: compute unit scores and overall power rankings CSV.
    if args.verbose:
        print(
            "info: computing unit scores and overall power rankings",
            file=sys.stderr,
        )

    teams_metrics = build_team_metrics(
        players,
        team_index,
        include_st=args.include_st,
        normalization=args.normalization,
        overall_weights=overall_weights,
        dev_multipliers=dev_multipliers,
    )
    write_power_rankings_csv(args.out_csv, teams_metrics)

    # Phase 3: HTML report generation.
    league_ctx = compute_league_context(teams_metrics)
    html_config = {
        "normalization": args.normalization,
        "include_st": bool(args.include_st),
        "overall_unit_weights": overall_weights or DEFAULT_OVERALL_UNIT_WEIGHTS,
        "dev_multipliers": dev_multipliers or DEFAULT_DEV_MULTIPLIERS,
    }
    if args.verbose:
        print(
            f"info: rendering HTML report to {args.out_html}",
            file=sys.stderr,
        )
    render_html_report(
        args.out_html,
        teams_metrics,
        config=html_config,
        league_context=league_ctx,
        players_by_team=players_by_team,
    )

    return 0
