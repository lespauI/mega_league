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
import csv
import json
import logging
import os
from typing import Any, Dict, List, Tuple


# -----------------------------
# Stubbed processing functions
# -----------------------------

def read_games_season2(games_csv: str, start_row: int) -> List[Dict[str, Any]]:
    """Read Season 2 slice of games from MEGA_games.csv starting at `start_row`.

    Notes:
    - `start_row` is 1-based index counting DATA rows (header not counted) and is inclusive.
    - Returns a list of dicts preserving file order for deterministic schedules.
    - Only the subset of columns needed downstream is retained if present.
    """
    needed_cols = {
        "homeTeam",
        "awayTeam",
        "gameId",
        "scheduled_date_time",
        "seasonIndex",
        "stageIndex",
        "weekIndex",
    }
    rows: List[Dict[str, Any]] = []
    with open(games_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # DictReader iterates data rows directly; enumerate starting at 1 for first data row
        for idx, row in enumerate(reader, start=1):
            if idx < start_row:
                continue
            # Normalize: ensure required keys exist; if not, default to empty string
            normalized = {k: row.get(k, "") for k in row.keys()}
            # If columns are missing in the file, still produce keys for downstream code
            for col in needed_cols:
                normalized.setdefault(col, "")
            rows.append(normalized)

    logging.info("Season 2 slice: %d games from %s starting row %d", len(rows), games_csv, start_row)
    return rows


def build_schedules(
    games_rows: List[Dict[str, Any]],
    teams_meta: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Build per-team schedules structure from sliced games and optional team metadata.

    Output schema:
      {
        [team]: {
          team, conference, division, games, schedule: [
            {opponent, homeAway, date, gameId, oppElo: null}
          ]
        }
      }
    """
    schedules: Dict[str, Dict[str, Any]] = {}

    def ensure_team(team_name: str) -> Dict[str, Any]:
        if team_name not in schedules:
            meta = teams_meta.get(team_name, {}) if teams_meta else {}
            schedules[team_name] = {
                "team": team_name,
                "conference": meta.get("conference"),
                "division": meta.get("division"),
                "games": 0,
                "schedule": [],
            }
        return schedules[team_name]

    for row in games_rows:
        home = (row.get("homeTeam") or "").strip()
        away = (row.get("awayTeam") or "").strip()
        game_id = (row.get("gameId") or "").strip()
        date = (row.get("scheduled_date_time") or "").strip()

        if not home or not away:
            # Skip malformed rows without teams
            logging.debug("Skipping row without teams: %s", row)
            continue

        # Home team entry
        home_obj = ensure_team(home)
        home_obj["schedule"].append(
            {
                "opponent": away,
                "homeAway": "home",
                "date": date,
                "gameId": game_id,
                "oppElo": None,
            }
        )
        home_obj["games"] += 1

        # Away team entry
        away_obj = ensure_team(away)
        away_obj["schedule"].append(
            {
                "opponent": home,
                "homeAway": "away",
                "date": date,
                "gameId": game_id,
                "oppElo": None,
            }
        )
        away_obj["games"] += 1

    logging.info("Built schedules for %d teams", len(schedules))
    return schedules


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
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, still writes schedules but skips non-essential outputs",
    )
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

    # Always write schedules JSON, including during dry-run
    try:
        out_sched_dir = os.path.join(args.out_dir, "schedules", "season2")
        os.makedirs(out_sched_dir, exist_ok=True)
        all_path = os.path.join(out_sched_dir, "all_schedules.json")
        with open(all_path, "w", encoding="utf-8") as f:
            json.dump(schedules, f, ensure_ascii=False, indent=2)
        logging.info("Wrote schedules JSON: %s", all_path)
    except Exception as e:
        logging.error("Failed writing schedules JSON: %s", e)
        raise
    elo_map = read_elo_map(args.elo_csv)
    sos_rows = compute_sos_elo(
        schedules,
        elo_map,
        include_home_advantage=args.include_home_advantage,
        hfa_elo_points=args.hfa_elo_points,
        index_scale=args.index_scale,
    )
    # Even in dry-run, writing schedules is already done above; SoS outputs will be implemented later
    if not args.dry_run:
        write_outputs(sos_rows, args.out_dir)

    logging.info("Finished (scaffold). Downstream steps will implement calculations and outputs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
