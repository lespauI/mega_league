#!/usr/bin/env python3
"""Strict CSV loading and input/output column contracts for stats tools."""

import csv
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_HEADERS_BY_NAME = {
    "MEGA_teams.csv": {"displayName", "seasonIndex"},
    "MEGA_games.csv": {"gameId", "homeTeam", "awayTeam", "seasonIndex", "stageIndex"},
    "MEGA_rankings.csv": {"team", "seasonIndex", "stageIndex", "weekIndex", "rank"},
    "MEGA_passing.csv": {"player__rosterId", "team__displayName", "gamesPlayed", "passTotalYds"},
    "MEGA_rushing.csv": {"player__rosterId", "team__displayName", "gamesPlayed", "rushTotalYds"},
    "MEGA_receiving.csv": {"player__rosterId", "team__displayName", "gamesPlayed", "recTotalYds"},
    "MEGA_defense.csv": {"player__rosterId", "team__displayName", "gamesPlayed", "defTotalTackles"},
    "MEGA_punting.csv": {"player__rosterId", "team__displayName", "gamesPlayed"},
    "MEGA_kicking.csv": {"player__rosterId", "team__displayName", "gamesPlayed"},
    "player_team_stints.csv": {"seasonIndex", "team", "player__rosterId", "multi_team_season"},
    "team_aggregated_stats.csv": {"team", "wins", "losses", "ties"},
    "team_player_usage.csv": {"team"},
    "team_rankings_stats.csv": {"team", "rank"},
}


def load_csv(filepath: Path) -> List[Dict[str, Any]]:
    """Load a structurally valid CSV, preserving valid header-only exports.

    A missing, unreadable, headerless, or malformed file is an input error. It
    must not look like a valid export containing zero rows. A header-only file
    remains valid for optional exports whose schema permits no records.
    """
    path = Path(filepath)
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        if not fieldnames or not any(name and name.strip() for name in fieldnames):
            raise ValueError(f"CSV has no header row: {path}")
        if len(set(fieldnames)) != len(fieldnames):
            raise ValueError(f"CSV has duplicate column names: {path}")
        required = REQUIRED_HEADERS_BY_NAME.get(path.name, set())
        missing = sorted(required - set(fieldnames))
        if missing:
            raise ValueError(f"CSV is missing required columns {missing}: {path}")

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"CSV row has more fields than its header at {path}:{line_number}")
            if any(value is None for value in row.values()):
                raise ValueError(f"CSV row has fewer fields than its header at {path}:{line_number}")
            rows.append(row)
        return rows
