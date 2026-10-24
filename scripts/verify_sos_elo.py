#!/usr/bin/env python3
"""Validate the published schedule and ELO SoS artifacts for one season."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)
REQUIRED_SOS_FIELDS = {
    "team", "games", "avg_opp_elo", "league_avg_opp_elo",
    "plus_minus_vs_avg", "sos_index", "rank",
}


def _load_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON from {path}: {exc}") from exc


def _number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric, got {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite, got {value!r}")
    return number


def check_schedules(root: Path, season_number: int) -> dict[str, int]:
    path = root / "output" / "schedules" / f"season{season_number}" / "all_schedules.json"
    schedules = _load_json(path)
    if not isinstance(schedules, dict) or not schedules:
        raise ValueError(f"Schedule artifact must be a non-empty team mapping: {path}")

    game_sides: dict[str, list[tuple[str, str]]] = {}
    total_entries = 0
    for team_name, team in schedules.items():
        if not isinstance(team, dict) or team.get("team") != team_name:
            raise ValueError(f"Schedule identity mismatch for {team_name!r} in {path}")
        entries = team.get("schedule")
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"Team {team_name!r} has no schedule entries")
        if team.get("games") != len(entries):
            raise ValueError(f"Team {team_name!r} games does not match its schedule length")

        seen_game_ids: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid schedule entry for {team_name!r}: {entry!r}")
            opponent = str(entry.get("opponent") or "").strip()
            game_id = str(entry.get("gameId") or "").strip()
            if not opponent or opponent == team_name or not game_id:
                raise ValueError(f"Schedule entry has invalid opponent or gameId for {team_name!r}")
            if opponent not in schedules:
                raise ValueError(f"Unknown opponent {opponent!r} in {team_name!r} schedule")
            if game_id in seen_game_ids:
                raise ValueError(f"Duplicate gameId {game_id!r} in {team_name!r} schedule")
            seen_game_ids.add(game_id)
            _number(entry.get("oppElo"), f"{team_name} vs {opponent} opponent ELO")
            game_sides.setdefault(game_id, []).append((team_name, opponent))
            total_entries += 1

    if total_entries % 2:
        raise ValueError("Schedule entries must have two team sides per game")
    for game_id, sides in game_sides.items():
        if len(sides) != 2 or sides[0] != (sides[1][1], sides[1][0]):
            raise ValueError(f"Game {game_id!r} does not have reciprocal team schedule entries")
    return {"teams": len(schedules), "games": len(game_sides)}


def check_sos(root: Path, season_number: int, schedule_summary: dict[str, int] | None = None) -> dict[str, int]:
    csv_path = root / "output" / "sos" / f"season{season_number}_elo.csv"
    json_path = root / "output" / "sos" / f"season{season_number}_elo.json"
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or [])
            if not REQUIRED_SOS_FIELDS.issubset(fields):
                missing = sorted(REQUIRED_SOS_FIELDS - fields)
                raise ValueError(f"SoS CSV missing columns {missing}: {csv_path}")
            csv_rows = list(reader)
    except OSError as exc:
        raise ValueError(f"Cannot read SoS CSV {csv_path}: {exc}") from exc

    json_rows = _load_json(json_path)
    if not isinstance(json_rows, list) or not csv_rows:
        raise ValueError("SoS artifacts must contain a non-empty list of team rows")
    if not isinstance(schedule_summary, dict):
        schedule_summary = check_schedules(root, season_number)
    schedules = _load_json(root / "output" / "schedules" / f"season{season_number}" / "all_schedules.json")

    by_team: dict[str, dict[str, Any]] = {}
    scores: list[tuple[int, float, str]] = []
    league_avgs: list[float] = []
    for row in csv_rows:
        team = (row.get("team") or "").strip()
        if not team or team in by_team:
            raise ValueError(f"SoS CSV has an empty or duplicate team row: {team!r}")
        if team not in schedules:
            raise ValueError(f"SoS team {team!r} is absent from schedules")
        games = int(row.get("games", ""))
        if games <= 0:
            raise ValueError(f"SoS games must be positive for {team!r}")
        if games != int(schedules[team].get("games", -1)):
            raise ValueError(f"SoS game count does not match the schedule for {team!r}")
        for field in ("avg_opp_elo", "league_avg_opp_elo", "plus_minus_vs_avg", "sos_index"):
            _number(row.get(field), f"{team} {field}")
        if not math.isclose(
            _number(row["plus_minus_vs_avg"], f"{team} plus/minus"),
            _number(row["avg_opp_elo"], f"{team} average ELO")
            - _number(row["league_avg_opp_elo"], f"{team} league average"),
            rel_tol=1e-12,
            abs_tol=1e-9,
        ):
            raise ValueError(f"SoS plus/minus value is inconsistent for {team!r}")
        rank = int(row.get("rank", ""))
        if rank <= 0:
            raise ValueError(f"SoS rank must be positive for {team!r}")
        average = _number(row["league_avg_opp_elo"], f"{team} league average")
        league_avgs.append(average)
        scores.append((rank, _number(row["sos_index"], f"{team} SoS index"), team))
        by_team[team] = row

    if len(by_team) != schedule_summary["teams"]:
        raise ValueError("SoS team count does not match schedule team count")
    if sorted(rank for rank, _, _ in scores) != list(range(1, len(scores) + 1)):
        raise ValueError("SoS ranks must be unique and consecutive from 1")
    if any(value != league_avgs[0] for value in league_avgs[1:]):
        raise ValueError("SoS rows disagree on league average ELO")
    ranked = sorted(scores)
    if any(ranked[index][1] < ranked[index + 1][1] for index in range(len(ranked) - 1)):
        raise ValueError("SoS rank order does not follow descending SoS index")

    json_by_team = {row.get("team"): row for row in json_rows if isinstance(row, dict)}
    if len(json_by_team) != len(json_rows) or set(json_by_team) != set(by_team):
        raise ValueError("SoS JSON team rows do not match the CSV")
    for team, csv_row in by_team.items():
        json_row = json_by_team[team]
        for field in REQUIRED_SOS_FIELDS - {"team"}:
            if not math.isclose(_number(csv_row[field], f"{team} CSV {field}"),
                                _number(json_row.get(field), f"{team} JSON {field}"),
                                rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"SoS CSV/JSON mismatch for {team!r} field {field!r}")
    return {"teams": len(by_team), "games_per_team": int(csv_rows[0]["games"])}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify season schedule and ELO SoS artifacts")
    parser.add_argument("--season-index", type=int, required=True,
                        help="One-based display season used in artifact names (1 for CSV index 0)")
    parser.add_argument("--check", choices=("schedules", "sos", "all"), default="all")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_arg_parser().parse_args(argv)
    if args.season_index < 1:
        LOGGER.error("Display season must be at least 1")
        return 2
    try:
        summary = None
        if args.check in ("schedules", "all"):
            summary = check_schedules(args.root, args.season_index)
            LOGGER.info("Schedules valid: %d teams, %d games", summary["teams"], summary["games"])
        if args.check in ("sos", "all"):
            result = check_sos(args.root, args.season_index, summary)
            LOGGER.info("ELO SoS valid: %d teams, %d games per team", result["teams"], result["games_per_team"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        LOGGER.error("Verification failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
