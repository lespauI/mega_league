#!/usr/bin/env python3
"""
Strength of Schedule (SoS) via ELO — parameterized for any season.

CLI contract:
  python3 scripts/calc_sos_elo.py \
    --season-index N \
    [--start-row N] \
    [--games-csv PATH] [--teams-csv PATH] [--elo-csv PATH] \
    [--include-home-advantage true|false] \
    [--hfa-elo-points N] [--index-scale zscore-mean100-sd15|none] \
    [--out-dir output]

Output paths are derived from --season-index:
  output/sos/season{N}_elo.csv
  output/sos/season{N}_elo.json
  output/schedules/season{N}/all_schedules.json

Default --start-row values: season 2 → 287, season 3 → 571.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
from typing import Any, Dict, List, Tuple

from common import normalize_team_name, read_elo_map, read_team_meta

_DEFAULT_START_ROWS: Dict[int, int] = {
    2: 287,
    3: 571,
}


def read_games(games_csv: str, start_row: int, season_index: int) -> List[Dict[str, Any]]:
    """Read the season slice of games from MEGA_games.csv starting near `start_row`.

    Robustness fixes:
    - Some exports duplicate the header line; DictReader treats the duplicate header as a data row.
      Relying strictly on a row cut can therefore drop the first real game of the season.
    - We infer the target `seasonIndex` from the first valid row at or after `start_row`,
      then include all rows that match that `seasonIndex` (regular season only: stageIndex == 1).

    Notes:
    - `start_row` is a 1-based index over DATA rows yielded by DictReader (first data row is 1).
    - Returns a list of dicts preserving file order for deterministic schedules.
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

    all_rows: List[Tuple[int, Dict[str, Any]]] = []
    with open(games_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            normalized = {k: row.get(k, "") for k in row.keys()}
            for col in needed_cols:
                normalized.setdefault(col, "")
            all_rows.append((idx, normalized))

    target_season: str | None = None
    for idx, r in all_rows:
        if idx >= start_row:
            si = str(r.get("seasonIndex", "")).strip()
            if si.isdigit():
                target_season = si
                break

    if target_season is None:
        rows = [r for idx, r in all_rows if idx >= start_row]
        logging.warning(
            "Could not infer target seasonIndex at/after row %d; using raw slice with %d rows",
            start_row,
            len(rows),
        )
        return rows

    rows: List[Dict[str, Any]] = []
    for idx, r in all_rows:
        if str(r.get("seasonIndex", "")).strip() == target_season and str(r.get("stageIndex", "")).strip() == "1":
            rows.append(r)

    logging.info(
        "Season %d slice: %d games from %s (seasonIndex=%s inferred from row %d; start_row arg=%d)",
        season_index,
        len(rows),
        games_csv,
        target_season,
        next((i for i, _ in all_rows if i >= start_row), start_row),
        start_row,
    )
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
            meta_key = normalize_team_name(team_name)
            meta = teams_meta.get(meta_key, {}) if teams_meta else {}
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
            logging.debug("Skipping row without teams: %s", row)
            continue

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


def _parse_decimal_comma(val: str) -> float:
    if val is None:
        raise ValueError("Missing numeric value")
    s = str(val).strip().replace(" ", "")
    s = s.replace(",", ".")
    return float(s)


def compute_sos_elo(
    schedules: Dict[str, Dict[str, Any]],
    elo_map: Dict[str, float],
    *,
    include_home_advantage: bool,
    hfa_elo_points: int,
    index_scale: str,
) -> List[Dict[str, Any]]:
    """Compute SoS metrics per team using opponents' ELO."""
    logging.info(
        "Compute SoS for %d teams using %d ELO entries (HFA=%s,%d; scale=%s)",
        len(schedules),
        len(elo_map),
        include_home_advantage,
        hfa_elo_points,
        index_scale,
    )

    per_team_avgs: Dict[str, float] = {}
    rows: List[Dict[str, Any]] = []

    for team, obj in schedules.items():
        entries = obj.get("schedule", []) or []
        opp_elos: List[float] = []
        for e in entries:
            opp = (e.get("opponent") or "").strip()
            key = normalize_team_name(opp)
            base = elo_map.get(key)
            if base is None:
                logging.warning("Missing ELO for opponent %r (team %r, game %r)", opp, team, e.get("gameId"))
                e["oppElo"] = None
                continue

            adj = base
            if include_home_advantage:
                ha = (e.get("homeAway") or "").strip().lower()
                if ha == "home":
                    adj = base - float(hfa_elo_points)
                elif ha == "away":
                    adj = base + float(hfa_elo_points)
            e["oppElo"] = adj
            opp_elos.append(float(adj))

        avg_opp_elo = sum(opp_elos) / len(opp_elos) if opp_elos else 0.0
        per_team_avgs[team] = avg_opp_elo

    if per_team_avgs:
        league_avg = sum(per_team_avgs.values()) / len(per_team_avgs)
    else:
        league_avg = 0.0

    def _stddev(vals: List[float]) -> float:
        n = len(vals)
        if n <= 1:
            return 0.0
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n
        return var ** 0.5

    avgs_list = list(per_team_avgs.values())
    sd = _stddev(avgs_list)

    for team, obj in schedules.items():
        avg_opp_elo = per_team_avgs.get(team, 0.0)
        plus_minus = avg_opp_elo - league_avg
        if index_scale == "zscore-mean100-sd15":
            if sd > 0:
                z = (avg_opp_elo - (sum(avgs_list) / len(avgs_list))) / sd
                sos_index = 100.0 + 15.0 * z
            else:
                sos_index = 100.0
        else:
            sos_index = avg_opp_elo

        row = {
            "team": team,
            "games": int(obj.get("games") or len(obj.get("schedule", []) or [])),
            "avg_opp_elo": float(avg_opp_elo),
            "league_avg_opp_elo": float(league_avg),
            "plus_minus_vs_avg": float(plus_minus),
            "sos_index": float(sos_index),
            "conference": obj.get("conference"),
            "division": obj.get("division"),
        }
        rows.append(row)

    rows.sort(key=lambda r: (-r["avg_opp_elo"], normalize_team_name(r["team"])))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    logging.info("Computed SoS rows: %d", len(rows))
    return rows


def write_outputs(rows: List[Dict[str, Any]], out_dir: str, season_index: int) -> None:
    """Write CSV/JSON outputs for SoS."""
    os.makedirs(os.path.join(out_dir, "sos"), exist_ok=True)
    csv_path = os.path.join(out_dir, "sos", f"season{season_index}_elo.csv")
    json_path = os.path.join(out_dir, "sos", f"season{season_index}_elo.json")

    fieldnames = [
        "team",
        "games",
        "avg_opp_elo",
        "league_avg_opp_elo",
        "plus_minus_vs_avg",
        "sos_index",
        "rank",
        "conference",
        "division",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    logging.info("Wrote SoS CSV: %s", csv_path)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logging.info("Wrote SoS JSON: %s", json_path)


def _bool_choice(val: str) -> bool:
    lower = (val or "").strip().lower()
    if lower in {"true", "t", "1", "yes", "y"}:
        return True
    if lower in {"false", "f", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected true|false")


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="SoS via ELO (parameterized by season)")
    ap.add_argument("--season-index", type=int, required=True, help="Season index to process (e.g. 2 or 3)")
    ap.add_argument("--start-row", type=int, default=None, help="Row index to start season slice (1-based data row; defaults: season 2=287, season 3=571)")
    ap.add_argument("--games-csv", default="MEGA_games.csv", help="Path to games CSV (default: MEGA_games.csv)")
    ap.add_argument("--teams-csv", default="MEGA_teams.csv", help="Path to teams CSV (default: MEGA_teams.csv)")
    ap.add_argument("--elo-csv", default="MEGA_elo.csv", help="Path to ELO CSV (default: MEGA_elo.csv)")
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

    season_index: int = args.season_index
    start_row: int = args.start_row if args.start_row is not None else _DEFAULT_START_ROWS.get(season_index, 1)

    logging.info("Starting SoS Season %d ELO calculation", season_index)
    logging.info(
        "Args: games_csv=%s teams_csv=%s elo_csv=%s start_row=%d include_home_advantage=%s hfa_elo_points=%d index_scale=%s out_dir=%s",
        args.games_csv,
        args.teams_csv,
        args.elo_csv,
        start_row,
        args.include_home_advantage,
        args.hfa_elo_points,
        args.index_scale,
        args.out_dir,
    )

    games_rows = read_games(args.games_csv, start_row, season_index)
    teams_meta = read_team_meta(args.teams_csv)
    schedules = build_schedules(games_rows, teams_meta)

    try:
        out_sched_dir = os.path.join(args.out_dir, "schedules", f"season{season_index}")
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

    if not args.dry_run:
        write_outputs(sos_rows, args.out_dir, season_index)

    logging.info("Finished Season %d SoS ELO calculation.", season_index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
