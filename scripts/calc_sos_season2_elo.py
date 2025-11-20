#!/usr/bin/env python3
"""
Season 2 Strength of Schedule (SoS) via ELO — scaffolding.

CLI contract:
  python3 scripts/calc_sos_season2_elo.py \
    [--games-csv PATH] [--teams-csv PATH] [--elo-csv PATH] \
    [--season2-start-row N] [--include-home-advantage true|false] \
    [--hfa-elo-points N] [--index-scale zscore-mean100-sd15|none] \
    [--out-dir output]

This file currently implements argument parsing and logging scaffolding,
along with stubbed functions that will be implemented in subsequent steps.
"""

from __future__ import annotations

import argparse
import logging
from typing import Any, Dict, List, Tuple


# -----------------------------
# Stubbed processing functions
# -----------------------------

def read_games_season2(games_csv: str, start_row: int) -> List[Dict[str, Any]]:
    """Read Season 2 slice of games from MEGA_games.csv starting at `start_row`.

    Stub: returns empty list. Implementation comes in next step.
    """
    logging.info("[stub] read_games_season2(games_csv=%s, start_row=%d)", games_csv, start_row)
    return []


def build_schedules(games_rows: List[Dict[str, Any]], teams_meta: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build per-team schedules structure from sliced games and team metadata.

    Stub: returns empty dict. Implementation comes in next step.
    """
    logging.info("[stub] build_schedules(games_rows=%d, teams_meta=%d)", len(games_rows), len(teams_meta))
    return {}


def read_elo_map(elo_csv: str) -> Dict[str, float]:
    """Read team -> ELO map from mega_elo.csv (semicolon delimiter, decimal commas).

    Stub: returns empty dict. Implementation comes later.
    """
    logging.info("[stub] read_elo_map(elo_csv=%s)", elo_csv)
    return {}


def read_team_meta(teams_csv: str) -> Dict[str, Dict[str, Any]]:
    """Read team metadata (conference, division, logoId) from MEGA_teams.csv.

    Stub: returns empty dict. Implementation comes later.
    """
    logging.info("[stub] read_team_meta(teams_csv=%s)", teams_csv)
    return {}


def compute_sos_elo(
    schedules: Dict[str, Dict[str, Any]],
    elo_map: Dict[str, float],
    *,
    include_home_advantage: bool,
    hfa_elo_points: int,
    index_scale: str,
) -> List[Dict[str, Any]]:
    """Compute SoS metrics per team using opponents' ELO.

    Stub: returns empty list. Implementation comes later.
    """
    logging.info(
        "[stub] compute_sos_elo(schedules=%d, elo_map=%d, include_home_advantage=%s, hfa_elo_points=%d, index_scale=%s)",
        len(schedules),
        len(elo_map),
        include_home_advantage,
        hfa_elo_points,
        index_scale,
    )
    return []


def write_outputs(rows: List[Dict[str, Any]], out_dir: str) -> None:
    """Write CSV/JSON outputs for SoS.

    Stub: does nothing. Implementation comes later.
    """
    logging.info("[stub] write_outputs(rows=%d, out_dir=%s)", len(rows), out_dir)


# -----------------------------
# CLI / main
# -----------------------------


def _bool_choice(val: str) -> bool:
    lower = (val or "").strip().lower()
    if lower in {"true", "t", "1", "yes", "y"}:
        return True
    if lower in {"false", "f", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected true|false")


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Season 2 SoS via ELO (scaffold)")
    ap.add_argument("--games-csv", default="MEGA_games.csv", help="Path to games CSV (default: MEGA_games.csv)")
    ap.add_argument("--teams-csv", default="MEGA_teams.csv", help="Path to teams CSV (default: MEGA_teams.csv)")
    ap.add_argument("--elo-csv", default="mega_elo.csv", help="Path to ELO CSV (default: mega_elo.csv)")
    ap.add_argument("--season2-start-row", type=int, default=287, help="Row index to start Season 2 slice (default: 287)")
    ap.add_argument(
        "--include-home-advantage",
        type=_bool_choice,
        default=False,
        metavar="true|false",
        help="Whether to include home-field advantage when averaging opponent ELO (default: false)",
    )
    ap.add_argument(
        "--hfa-elo-points",
        type=int,
        default=55,
        help="Home-field advantage ELO points to add/subtract when enabled (default: 55)",
    )
    ap.add_argument(
        "--index-scale",
        choices=["zscore-mean100-sd15", "none"],
        default="zscore-mean100-sd15",
        help="Scaling for SoS index (default: zscore-mean100-sd15)",
    )
    ap.add_argument("--out-dir", default="output", help="Output directory (default: output)")
    return ap


def main(argv: List[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    logging.info("Starting SoS Season 2 ELO calculation (scaffold)")
    logging.info(
        "Args: games_csv=%s teams_csv=%s elo_csv=%s season2_start_row=%d include_home_advantage=%s hfa_elo_points=%d index_scale=%s out_dir=%s",
        args.games_csv,
        args.teams_csv,
        args.elo_csv,
        args.season2_start_row,
        args.include_home_advantage,
        args.hfa_elo_points,
        args.index_scale,
        args.out_dir,
    )

    # Pipeline (stubbed)
    games_rows = read_games_season2(args.games_csv, args.season2_start_row)
    teams_meta = read_team_meta(args.teams_csv)
    schedules = build_schedules(games_rows, teams_meta)
    elo_map = read_elo_map(args.elo_csv)
    sos_rows = compute_sos_elo(
        schedules,
        elo_map,
        include_home_advantage=args.include_home_advantage,
        hfa_elo_points=args.hfa_elo_points,
        index_scale=args.index_scale,
    )
    write_outputs(sos_rows, args.out_dir)

    logging.info("Finished (scaffold). Downstream steps will implement calculations and outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

