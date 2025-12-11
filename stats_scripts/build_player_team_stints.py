#!/usr/bin/env python3
"""
Build per-team, per-player season stints from MEGA stat CSVs.

Output: output/player_team_stints.csv
 - One row per (seasonIndex, canonical team, player__rosterId)
 - Aggregates passing, rushing, receiving, and defensive volume stats.
"""

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple, Any

from stats_common import load_csv, safe_float, normalize_team_display


StintKey = Tuple[str, str, str]  # (seasonIndex, canonical_team, player__rosterId)


def build_team_map(base_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Build a mapping from canonical team display name to team meta row from MEGA_teams.csv.

    When multiple rows exist for the same team name, prefer the one with the
    highest seasonIndex (string compare via float for robustness).
    """
    teams = load_csv(base_path / "MEGA_teams.csv")
    team_map: Dict[str, Dict[str, Any]] = {}

    for row in teams:
        name = normalize_team_display(row.get("displayName", ""))
        if not name:
            continue

        existing = team_map.get(name)
        if not existing:
            team_map[name] = row
            continue

        # Prefer the row with the largest seasonIndex if multiple exist.
        try:
            current_season = float(row.get("seasonIndex", "") or 0)
            existing_season = float(existing.get("seasonIndex", "") or 0)
        except ValueError:
            current_season = existing_season = 0

        if current_season >= existing_season:
            team_map[name] = row

    return team_map


def get_stint_key(
    row: Dict[str, Any],
    team_name: str,
    team_info: Dict[str, Any],
) -> StintKey:
    """Derive the stint key (seasonIndex, canonical team, rosterId) for a stat row."""
    season_index = ""
    if team_info:
        season_index = str(team_info.get("seasonIndex", "")).strip()

    roster_id = str(row.get("player__rosterId", "")).strip()
    return season_index, team_name, roster_id


def ensure_stint_row(
    stints: Dict[StintKey, Dict[str, Any]],
    key: StintKey,
    row: Dict[str, Any],
    team_name: str,
    team_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Initialize a stint row in the accumulator if it does not exist yet."""
    if key in stints:
        stint = stints[key]
    else:
        season_index, _, _ = key
        stint = {
            "seasonIndex": season_index,
            "team": team_name,
            "team_abbrev": "",
            "player__rosterId": row.get("player__rosterId", ""),
            "player__fullName": row.get("player__fullName", ""),
            "player__position": row.get("player__position", ""),
            # Playing time by phase
            "gamesPlayed_passing": 0.0,
            "gamesPlayed_rushing": 0.0,
            "gamesPlayed_receiving": 0.0,
            "gamesPlayed_defense": 0.0,
            # Passing
            "passTotalAtt": 0.0,
            "passTotalComp": 0.0,
            "passTotalYds": 0.0,
            "passTotalTDs": 0.0,
            "passTotalInts": 0.0,
            "passTotalSacks": 0.0,
            # Rushing
            "rushTotalAtt": 0.0,
            "rushTotalYds": 0.0,
            "rushTotalTDs": 0.0,
            "rushTotalFum": 0.0,
            "rushTotal20PlusYds": 0.0,
            "rushTotalYdsAfterContact": 0.0,
            # Receiving
            "recTotalCatches": 0.0,
            "recTotalYds": 0.0,
            "recTotalTDs": 0.0,
            "recTotalDrops": 0.0,
            "recTotalYdsAfterCatch": 0.0,
            # Defense
            "defTotalTackles": 0.0,
            "defTotalSacks": 0.0,
            "defTotalInts": 0.0,
            "defTotalForcedFum": 0.0,
            "defTotalFumRec": 0.0,
            "defTotalTDs": 0.0,
            # Derived
            "multi_team_season": False,
        }

        # Derive team_abbrev from MEGA_teams first, then fall back to stat row.
        if team_info:
            stint["team_abbrev"] = str(team_info.get("abbrName", "")).strip()
            if not stint["seasonIndex"]:
                stint["seasonIndex"] = str(team_info.get("seasonIndex", "")).strip()
        if not stint["team_abbrev"]:
            stint["team_abbrev"] = str(row.get("team__abbrName", "")).strip()

        stints[key] = stint

    # Backfill identity fields if present and previously empty.
    if not stint.get("player__fullName") and row.get("player__fullName"):
        stint["player__fullName"] = row.get("player__fullName")
    if not stint.get("player__position") and row.get("player__position"):
        stint["player__position"] = row.get("player__position")

    return stint


def build_player_team_stints(base_path: Path) -> None:
    """Build player_team_stints.csv from MEGA stat CSVs."""
    print("Loading stat CSVs...")

    passing = load_csv(base_path / "MEGA_passing.csv")
    rushing = load_csv(base_path / "MEGA_rushing.csv")
    receiving = load_csv(base_path / "MEGA_receiving.csv")
    defense = load_csv(base_path / "MEGA_defense.csv")
    # Punting and kicking are loaded for future extensions; not aggregated today.
    punting = load_csv(base_path / "MEGA_punting.csv")
    kicking = load_csv(base_path / "MEGA_kicking.csv")
    _ = punting, kicking  # avoid unused warnings in static analysis

    team_map = build_team_map(base_path)

    stints: Dict[StintKey, Dict[str, Any]] = {}
    teams_by_player_season: Dict[Tuple[str, str], set] = defaultdict(set)

    print("Aggregating passing stats into stints...")
    for row in passing:
        team_name = normalize_team_display(row.get("team__displayName", ""))
        if not team_name:
            continue

        team_info = team_map.get(team_name, {})
        key = get_stint_key(row, team_name, team_info)
        stint = ensure_stint_row(stints, key, row, team_name, team_info)

        games = safe_float(row.get("gamesPlayed"))
        stint["gamesPlayed_passing"] += games
        stint["passTotalAtt"] += safe_float(row.get("passTotalAtt"))
        stint["passTotalComp"] += safe_float(row.get("passTotalComp"))
        stint["passTotalYds"] += safe_float(row.get("passTotalYds"))
        stint["passTotalTDs"] += safe_float(row.get("passTotalTDs"))
        stint["passTotalInts"] += safe_float(row.get("passTotalInts"))
        stint["passTotalSacks"] += safe_float(row.get("passTotalSacks"))

        season_index = stint.get("seasonIndex", "")
        roster_id = stint.get("player__rosterId", "")
        teams_by_player_season[(season_index, roster_id)].add(team_name)

    print("Aggregating rushing stats into stints...")
    for row in rushing:
        team_name = normalize_team_display(row.get("team__displayName", ""))
        if not team_name:
            continue

        team_info = team_map.get(team_name, {})
        key = get_stint_key(row, team_name, team_info)
        stint = ensure_stint_row(stints, key, row, team_name, team_info)

        games = safe_float(row.get("gamesPlayed"))
        stint["gamesPlayed_rushing"] += games
        stint["rushTotalAtt"] += safe_float(row.get("rushTotalAtt"))
        stint["rushTotalYds"] += safe_float(row.get("rushTotalYds"))
        stint["rushTotalTDs"] += safe_float(row.get("rushTotalTDs"))
        stint["rushTotalFum"] += safe_float(row.get("rushTotalFum"))
        stint["rushTotal20PlusYds"] += safe_float(row.get("rushTotal20PlusYds"))
        stint["rushTotalYdsAfterContact"] += safe_float(
            row.get("rushTotalYdsAfterContact")
        )

        season_index = stint.get("seasonIndex", "")
        roster_id = stint.get("player__rosterId", "")
        teams_by_player_season[(season_index, roster_id)].add(team_name)

    print("Aggregating receiving stats into stints...")
    for row in receiving:
        team_name = normalize_team_display(row.get("team__displayName", ""))
        if not team_name:
            continue

        team_info = team_map.get(team_name, {})
        key = get_stint_key(row, team_name, team_info)
        stint = ensure_stint_row(stints, key, row, team_name, team_info)

        games = safe_float(row.get("gamesPlayed"))
        stint["gamesPlayed_receiving"] += games
        stint["recTotalCatches"] += safe_float(row.get("recTotalCatches"))
        stint["recTotalYds"] += safe_float(row.get("recTotalYds"))
        stint["recTotalTDs"] += safe_float(row.get("recTotalTDs"))
        stint["recTotalDrops"] += safe_float(row.get("recTotalDrops"))
        stint["recTotalYdsAfterCatch"] += safe_float(row.get("recTotalYdsAfterCatch"))

        season_index = stint.get("seasonIndex", "")
        roster_id = stint.get("player__rosterId", "")
        teams_by_player_season[(season_index, roster_id)].add(team_name)

    print("Aggregating defensive stats into stints...")
    for row in defense:
        team_name = normalize_team_display(row.get("team__displayName", ""))
        if not team_name:
            continue

        team_info = team_map.get(team_name, {})
        key = get_stint_key(row, team_name, team_info)
        stint = ensure_stint_row(stints, key, row, team_name, team_info)

        games = safe_float(row.get("gamesPlayed"))
        stint["gamesPlayed_defense"] += games
        stint["defTotalTackles"] += safe_float(row.get("defTotalTackles"))
        stint["defTotalSacks"] += safe_float(row.get("defTotalSacks"))
        stint["defTotalInts"] += safe_float(row.get("defTotalInts"))
        stint["defTotalForcedFum"] += safe_float(row.get("defTotalForcedFum"))
        stint["defTotalFumRec"] += safe_float(row.get("defTotalFumRec"))
        stint["defTotalTDs"] += safe_float(row.get("defTotalTDs"))

        season_index = stint.get("seasonIndex", "")
        roster_id = stint.get("player__rosterId", "")
        teams_by_player_season[(season_index, roster_id)].add(team_name)

    print(f"Built {len(stints)} stints; deriving multi-team flags...")

    for key, stint in stints.items():
        season_index, _, roster_id = key
        teams = teams_by_player_season.get((season_index, roster_id), set())
        stint["multi_team_season"] = len(teams) > 1

    output_dir = base_path / "output"
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / "player_team_stints.csv"

    rows = list(stints.values())

    if not rows:
        print("No stints built; nothing to write.")
        return

    fieldnames = [
        "seasonIndex",
        "team",
        "team_abbrev",
        "player__rosterId",
        "player__fullName",
        "player__position",
        "gamesPlayed_passing",
        "passTotalAtt",
        "passTotalComp",
        "passTotalYds",
        "passTotalTDs",
        "passTotalInts",
        "passTotalSacks",
        "gamesPlayed_rushing",
        "rushTotalAtt",
        "rushTotalYds",
        "rushTotalTDs",
        "rushTotalFum",
        "rushTotal20PlusYds",
        "rushTotalYdsAfterContact",
        "gamesPlayed_receiving",
        "recTotalCatches",
        "recTotalYds",
        "recTotalTDs",
        "recTotalDrops",
        "recTotalYdsAfterCatch",
        "gamesPlayed_defense",
        "defTotalTackles",
        "defTotalSacks",
        "defTotalInts",
        "defTotalForcedFum",
        "defTotalFumRec",
        "defTotalTDs",
        "multi_team_season",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for stint in rows:
            writer.writerow(stint)

    print(f"✓ Saved player team stints to: {output_file}")
    print(f"  Total stints: {len(rows)}")


if __name__ == "__main__":
    BASE_PATH = Path(__file__).parent.parent
    print(f"Working directory: {BASE_PATH}\n")
    build_player_team_stints(BASE_PATH)
    print("\n✓ Done! Use player_team_stints.csv for trade-aware player/team views.")

