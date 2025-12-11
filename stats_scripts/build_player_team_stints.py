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
TeamMap = Dict[str, Dict[str, Any]]


PASSING_FIELDS = [
    "passTotalAtt",
    "passTotalComp",
    "passTotalYds",
    "passTotalTDs",
    "passTotalInts",
    "passTotalSacks",
]

RUSHING_FIELDS = [
    "rushTotalAtt",
    "rushTotalYds",
    "rushTotalTDs",
    "rushTotalBrokenTackles",
    "rushTotalFum",
    "rushTotal20PlusYds",
    "rushTotalYdsAfterContact",
]


def build_team_map(base_path: Path) -> TeamMap:
    """
    Build a mapping from canonical team display name to team meta row from MEGA_teams.csv.

    When multiple rows exist for the same team name, prefer the one with the
    highest seasonIndex (string compare via float for robustness).
    """
    teams = load_csv(base_path / "MEGA_teams.csv")
    team_map: TeamMap = {}

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


def reconcile_offense_with_team_totals(
    stints: Dict[StintKey, Dict[str, Any]],
    team_map: TeamMap,
) -> None:
    """
    Scale multi-team offensive stints so team-level passing and rushing yards
    better align with MEGA_teams offensive yardage (offPassYds, offRushYds).

    Raw fields (*_raw) are left untouched. Only the adjusted fields are
    modified, and only for players who appeared for multiple teams in the
    season (`multi_team_season = True`).
    """
    # Build convenience index from team -> list of stint dicts
    stints_by_team: Dict[str, list[Dict[str, Any]]] = {}
    for stint in stints.values():
        team_name = stint.get("team", "")
        if not team_name:
            continue
        stints_by_team.setdefault(team_name, []).append(stint)

    for team_name, rows in stints_by_team.items():
        team_info = team_map.get(team_name)
        if not team_info:
            continue

        # Passing reconciliation
        off_pass_yds = safe_float(team_info.get("offPassYds"))
        if off_pass_yds > 0:
            single_yds = 0.0
            multi_yds = 0.0
            for r in rows:
                y_raw = safe_float(r.get("passTotalYds_raw"))
                if not y_raw:
                    continue
                if r.get("multi_team_season") in (True, "True", "true", "1", 1):
                    multi_yds += y_raw
                else:
                    single_yds += y_raw

            total_yds = single_yds + multi_yds
            if multi_yds > 0 and total_yds > 0:
                target_multi = off_pass_yds - single_yds
                # Only adjust when the team total is compatible with the
                # single-team share and we have some room to scale multi-team
                # contributions.
                if target_multi > 0:
                    k_pass = target_multi / multi_yds
                    # Guard against extreme scaling.
                    if 0.25 <= k_pass <= 1.25:
                        for r in rows:
                            if r.get("multi_team_season") not in (
                                True,
                                "True",
                                "true",
                                "1",
                                1,
                            ):
                                continue
                            for field in PASSING_FIELDS:
                                raw_val = safe_float(r.get(f"{field}_raw"))
                                r[field] = raw_val * k_pass

        # Rushing reconciliation
        off_rush_yds = safe_float(team_info.get("offRushYds"))
        if off_rush_yds > 0:
            single_yds = 0.0
            multi_yds = 0.0
            for r in rows:
                y_raw = safe_float(r.get("rushTotalYds_raw"))
                if not y_raw:
                    continue
                if r.get("multi_team_season") in (True, "True", "true", "1", 1):
                    multi_yds += y_raw
                else:
                    single_yds += y_raw

            total_yds = single_yds + multi_yds
            if multi_yds > 0 and total_yds > 0:
                target_multi = off_rush_yds - single_yds
                if target_multi > 0:
                    k_rush = target_multi / multi_yds
                    if 0.25 <= k_rush <= 1.25:
                        for r in rows:
                            if r.get("multi_team_season") not in (
                                True,
                                "True",
                                "true",
                                "1",
                                1,
                            ):
                                continue
                            for field in RUSHING_FIELDS:
                                raw_val = safe_float(r.get(f"{field}_raw"))
                                r[field] = raw_val * k_rush


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
            # Passing (raw and adjusted)
            "passTotalAtt_raw": 0.0,
            "passTotalAtt": 0.0,
            "passTotalComp_raw": 0.0,
            "passTotalComp": 0.0,
            "passTotalYds_raw": 0.0,
            "passTotalYds": 0.0,
            "passTotalTDs_raw": 0.0,
            "passTotalTDs": 0.0,
            "passTotalInts_raw": 0.0,
            "passTotalInts": 0.0,
            "passTotalSacks_raw": 0.0,
            "passTotalSacks": 0.0,
            # Rushing (raw and adjusted)
            "rushTotalAtt_raw": 0.0,
            "rushTotalAtt": 0.0,
            "rushTotalYds_raw": 0.0,
            "rushTotalYds": 0.0,
            "rushTotalTDs_raw": 0.0,
            "rushTotalTDs": 0.0,
            "rushTotalBrokenTackles_raw": 0.0,
            "rushTotalBrokenTackles": 0.0,
            "rushTotalFum_raw": 0.0,
            "rushTotalFum": 0.0,
            "rushTotal20PlusYds_raw": 0.0,
            "rushTotal20PlusYds": 0.0,
            "rushTotalYdsAfterContact_raw": 0.0,
            "rushTotalYdsAfterContact": 0.0,
            # Receiving (raw and adjusted)
            "recTotalCatches_raw": 0.0,
            "recTotalCatches": 0.0,
            "recTotalYds_raw": 0.0,
            "recTotalYds": 0.0,
            "recTotalTDs_raw": 0.0,
            "recTotalTDs": 0.0,
            "recTotalDrops_raw": 0.0,
            "recTotalDrops": 0.0,
            "recTotalYdsAfterCatch_raw": 0.0,
            "recTotalYdsAfterCatch": 0.0,
            # Defense (raw and adjusted)
            "defTotalTackles_raw": 0.0,
            "defTotalTackles": 0.0,
            "defTotalSacks_raw": 0.0,
            "defTotalSacks": 0.0,
            "defTotalInts_raw": 0.0,
            "defTotalInts": 0.0,
            "defTotalForcedFum_raw": 0.0,
            "defTotalForcedFum": 0.0,
            "defTotalFumRec_raw": 0.0,
            "defTotalFumRec": 0.0,
            "defTotalTDs_raw": 0.0,
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
        att = safe_float(row.get("passTotalAtt"))
        comp = safe_float(row.get("passTotalComp"))
        yds = safe_float(row.get("passTotalYds"))
        tds = safe_float(row.get("passTotalTDs"))
        ints = safe_float(row.get("passTotalInts"))
        sacks = safe_float(row.get("passTotalSacks"))

        stint["passTotalAtt_raw"] += att
        stint["passTotalAtt"] += att
        stint["passTotalComp_raw"] += comp
        stint["passTotalComp"] += comp
        stint["passTotalYds_raw"] += yds
        stint["passTotalYds"] += yds
        stint["passTotalTDs_raw"] += tds
        stint["passTotalTDs"] += tds
        stint["passTotalInts_raw"] += ints
        stint["passTotalInts"] += ints
        stint["passTotalSacks_raw"] += sacks
        stint["passTotalSacks"] += sacks

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
        att = safe_float(row.get("rushTotalAtt"))
        yds = safe_float(row.get("rushTotalYds"))
        broken = safe_float(row.get("rushTotalBrokenTackles"))
        tds = safe_float(row.get("rushTotalTDs"))
        fum = safe_float(row.get("rushTotalFum"))
        yds20 = safe_float(row.get("rushTotal20PlusYds"))
        yac = safe_float(row.get("rushTotalYdsAfterContact"))

        stint["rushTotalAtt_raw"] += att
        stint["rushTotalAtt"] += att
        stint["rushTotalYds_raw"] += yds
        stint["rushTotalYds"] += yds
        stint["rushTotalTDs_raw"] += tds
        stint["rushTotalTDs"] += tds
        stint["rushTotalBrokenTackles_raw"] += broken
        stint["rushTotalBrokenTackles"] += broken
        stint["rushTotalFum_raw"] += fum
        stint["rushTotalFum"] += fum
        stint["rushTotal20PlusYds_raw"] += yds20
        stint["rushTotal20PlusYds"] += yds20
        stint["rushTotalYdsAfterContact_raw"] += yac
        stint["rushTotalYdsAfterContact"] += yac

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
        catches = safe_float(row.get("recTotalCatches"))
        yds = safe_float(row.get("recTotalYds"))
        tds = safe_float(row.get("recTotalTDs"))
        drops = safe_float(row.get("recTotalDrops"))
        yac = safe_float(row.get("recTotalYdsAfterCatch"))

        stint["recTotalCatches_raw"] += catches
        stint["recTotalCatches"] += catches
        stint["recTotalYds_raw"] += yds
        stint["recTotalYds"] += yds
        stint["recTotalTDs_raw"] += tds
        stint["recTotalTDs"] += tds
        stint["recTotalDrops_raw"] += drops
        stint["recTotalDrops"] += drops
        stint["recTotalYdsAfterCatch_raw"] += yac
        stint["recTotalYdsAfterCatch"] += yac

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
        tackles = safe_float(row.get("defTotalTackles"))
        sacks = safe_float(row.get("defTotalSacks"))
        ints = safe_float(row.get("defTotalInts"))
        ff = safe_float(row.get("defTotalForcedFum"))
        fr = safe_float(row.get("defTotalFumRec"))
        tds = safe_float(row.get("defTotalTDs"))

        stint["defTotalTackles_raw"] += tackles
        stint["defTotalTackles"] += tackles
        stint["defTotalSacks_raw"] += sacks
        stint["defTotalSacks"] += sacks
        stint["defTotalInts_raw"] += ints
        stint["defTotalInts"] += ints
        stint["defTotalForcedFum_raw"] += ff
        stint["defTotalForcedFum"] += ff
        stint["defTotalFumRec_raw"] += fr
        stint["defTotalFumRec"] += fr
        stint["defTotalTDs_raw"] += tds
        stint["defTotalTDs"] += tds

        season_index = stint.get("seasonIndex", "")
        roster_id = stint.get("player__rosterId", "")
        teams_by_player_season[(season_index, roster_id)].add(team_name)

    print(f"Built {len(stints)} stints; deriving multi-team flags...")

    for key, stint in stints.items():
        season_index, _, roster_id = key
        teams = teams_by_player_season.get((season_index, roster_id), set())
        stint["multi_team_season"] = len(teams) > 1

    # After raw aggregation, adjust offensive stats for multi-team seasons so
    # that per-team totals better align with MEGA_teams offensive yardage
    # splits. This keeps raw fields untouched and only scales the adjusted
    # values for traded players.
    reconcile_offense_with_team_totals(stints, team_map)

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
        "passTotalAtt_raw",
        "passTotalAtt",
        "passTotalComp_raw",
        "passTotalComp",
        "passTotalYds_raw",
        "passTotalYds",
        "passTotalTDs_raw",
        "passTotalTDs",
        "passTotalInts_raw",
        "passTotalInts",
        "passTotalSacks_raw",
        "passTotalSacks",
        "gamesPlayed_rushing",
        "rushTotalAtt_raw",
        "rushTotalAtt",
        "rushTotalYds_raw",
        "rushTotalYds",
        "rushTotalTDs_raw",
        "rushTotalTDs",
        "rushTotalBrokenTackles_raw",
        "rushTotalBrokenTackles",
        "rushTotalFum_raw",
        "rushTotalFum",
        "rushTotal20PlusYds_raw",
        "rushTotal20PlusYds",
        "rushTotalYdsAfterContact_raw",
        "rushTotalYdsAfterContact",
        "gamesPlayed_receiving",
        "recTotalCatches_raw",
        "recTotalCatches",
        "recTotalYds_raw",
        "recTotalYds",
        "recTotalTDs_raw",
        "recTotalTDs",
        "recTotalDrops_raw",
        "recTotalDrops",
        "recTotalYdsAfterCatch_raw",
        "recTotalYdsAfterCatch",
        "gamesPlayed_defense",
        "defTotalTackles_raw",
        "defTotalTackles",
        "defTotalSacks_raw",
        "defTotalSacks",
        "defTotalInts_raw",
        "defTotalInts",
        "defTotalForcedFum_raw",
        "defTotalForcedFum",
        "defTotalFumRec_raw",
        "defTotalFumRec",
        "defTotalTDs_raw",
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
