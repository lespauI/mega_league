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
    """Read Season 2 slice of games from MEGA_games.csv starting near `start_row`.

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

    # Determine target seasonIndex from the first valid row at/after start_row
    target_season: str | None = None
    for idx, r in all_rows:
        if idx >= start_row:
            si = str(r.get("seasonIndex", "")).strip()
            if si.isdigit():
                target_season = si
                break

    # Fallback: if not found (unexpected), include rows at/after start_row
    if target_season is None:
        rows = [r for idx, r in all_rows if idx >= start_row]
        logging.warning(
            "Could not infer target seasonIndex at/after row %d; using raw slice with %d rows",
            start_row,
            len(rows),
        )
        return rows

    # Filter to the inferred season and regular season stage (stageIndex == 1)
    rows: List[Dict[str, Any]] = []
    for idx, r in all_rows:
        if str(r.get("seasonIndex", "")).strip() == target_season and str(r.get("stageIndex", "")).strip() == "1":
            rows.append(r)

    logging.info(
        "Season 2 slice: %d games from %s (seasonIndex=%s inferred from row %d; start_row arg=%d)",
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
            # Look up metadata using normalized key if available
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


def _parse_decimal_comma(val: str) -> float:
    if val is None:
        raise ValueError("Missing numeric value")
    s = str(val).strip().replace(" ", "")
    # Replace decimal comma with dot
    s = s.replace(",", ".")
    return float(s)


def normalize_team_name(name: str) -> str:
    """Normalize team names for consistent joins across files.

    Strategy: lowercase, strip, remove punctuation and spaces.
    This keeps names like '49ers' intact while unifying variants.
    """
    if name is None:
        return ""
    s = name.strip().lower()
    # Remove common punctuation/spaces
    for ch in ["'", "\"", ".", ",", "-", "_", "(", ")", "/", "\\", "&", "  "]:
        s = s.replace(ch, " ")
    s = "".join(ch for ch in s if ch.isalnum())
    return s


def read_elo_map(elo_csv: str) -> Dict[str, float]:
    """Read team -> ELO map from mega_elo.csv (semicolon delimiter, decimal commas)."""
    elo_map: Dict[str, float] = {}
    with open(elo_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            team_raw = row.get("Team")
            start_raw = row.get("START")
            if not team_raw or not start_raw:
                continue
            key = normalize_team_name(team_raw)
            try:
                elo = _parse_decimal_comma(start_raw)
            except ValueError:
                logging.warning("Skipping ELO row with invalid START: team=%r START=%r", team_raw, start_raw)
                continue
            elo_map[key] = elo
    logging.info("Loaded ELO map: %d teams from %s", len(elo_map), elo_csv)
    return elo_map


def read_team_meta(teams_csv: str) -> Dict[str, Dict[str, Any]]:
    """Read team metadata (conference, division, logoId) from MEGA_teams.csv.

    Returns a dict keyed by normalized team name for consistent joins.
    Values include source teamName for reference.
    """
    meta: Dict[str, Dict[str, Any]] = {}
    with open(teams_csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("teamName") or row.get("displayName") or "").strip()
            if not name:
                continue
            key = normalize_team_name(name)
            meta[key] = {
                "teamName": name,
                "conference": (row.get("conferenceName") or "").strip() or None,
                "division": (row.get("divName") or "").strip() or None,
                "logoId": (row.get("logoId") or "").strip() or None,
            }
    logging.info("Loaded team metadata: %d teams from %s", len(meta), teams_csv)
    return meta


def compute_sos_elo(
    schedules: Dict[str, Dict[str, Any]],
    elo_map: Dict[str, float],
    *,
    include_home_advantage: bool,
    hfa_elo_points: int,
    index_scale: str,
) -> List[Dict[str, Any]]:
    """Compute SoS metrics per team using opponents' ELO.
    """
    logging.info(
        "Compute SoS for %d teams using %d ELO entries (HFA=%s,%d; scale=%s)",
        len(schedules),
        len(elo_map),
        include_home_advantage,
        hfa_elo_points,
        index_scale,
    )

    # Enrich schedules in-place with oppElo and build per-team aggregates
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

        games = int(obj.get("games") or len(entries) or 0)
        avg_opp_elo = sum(opp_elos) / len(opp_elos) if opp_elos else 0.0
        per_team_avgs[team] = avg_opp_elo

    # League averages for scaling and plus/minus
    if per_team_avgs:
        league_avg = sum(per_team_avgs.values()) / len(per_team_avgs)
    else:
        league_avg = 0.0

    # Standard deviation for z-score scaling
    def _stddev(vals: List[float]) -> float:
        n = len(vals)
        if n <= 1:
            return 0.0
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n
        return var ** 0.5

    avgs_list = list(per_team_avgs.values())
    sd = _stddev(avgs_list)

    # Build rows with metadata
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
            # Rank will be added after sorting
            "conference": obj.get("conference"),
            "division": obj.get("division"),
        }
        rows.append(row)

    # Deterministic ranking: hardest schedule first (highest avg_opp_elo), tie-break by team name
    rows.sort(key=lambda r: (-r["avg_opp_elo"], normalize_team_name(r["team"])))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    logging.info("Computed SoS rows: %d", len(rows))
    return rows


def write_outputs(rows: List[Dict[str, Any]], out_dir: str) -> None:
    """Write CSV/JSON outputs for SoS.
    """
    os.makedirs(os.path.join(out_dir, "sos"), exist_ok=True)
    csv_path = os.path.join(out_dir, "sos", "season2_elo.csv")
    json_path = os.path.join(out_dir, "sos", "season2_elo.json")

    # Define CSV column order; logoId is optional and not included here by default
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

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})
    logging.info("Wrote SoS CSV: %s", csv_path)

    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logging.info("Wrote SoS JSON: %s", json_path)


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
