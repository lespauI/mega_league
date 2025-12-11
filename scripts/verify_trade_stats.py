#!/usr/bin/env python3
"""
Verify trade-aware stats consistency and emit a traded-players report.

Usage:
  python3 scripts/verify_trade_stats.py
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set


BASE_PATH = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_PATH / "stats_scripts"))

from stats_common import load_csv, safe_float, normalize_team_display  # type: ignore  # noqa: E402


StatFieldMap = Dict[str, str]


STAT_FIELD_MAP: StatFieldMap = {
    # Passing
    "passTotalYds": "pass_yds",
    "passTotalTDs": "pass_tds",
    "passTotalInts": "pass_ints",
    "passTotalSacks": "pass_sacks",
    # Rushing
    "rushTotalYds": "rush_yds",
    "rushTotalTDs": "rush_tds",
    "rushTotalFum": "rush_fum",
    "rushTotal20PlusYds": "rush_20plus",
    "rushTotalYdsAfterContact": "rush_yac",
    # Receiving
    "recTotalCatches": "rec_catches",
    "recTotalYds": "rec_yds",
    "recTotalTDs": "rec_tds",
    "recTotalDrops": "rec_drops",
    "recTotalYdsAfterCatch": "rec_yac",
    # Defense
    "defTotalSacks": "def_sacks",
    "defTotalInts": "def_ints",
    "defTotalForcedFum": "def_forced_fum",
    "defTotalFumRec": "def_fum_rec",
    "defTotalTDs": "def_tds",
    "defTotalTackles": "def_tackles",
}


def load_data(base_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    data: Dict[str, List[Dict[str, Any]]] = {}
    data["passing"] = load_csv(base_path / "MEGA_passing.csv")
    data["rushing"] = load_csv(base_path / "MEGA_rushing.csv")
    data["receiving"] = load_csv(base_path / "MEGA_receiving.csv")
    data["team_stats"] = load_csv(base_path / "output" / "team_aggregated_stats.csv")
    data["stints"] = load_csv(base_path / "output" / "player_team_stints.csv")
    return data


def build_player_season_teams(
    stints: List[Dict[str, Any]]
) -> Dict[Tuple[str, str], Set[str]]:
    teams_by_player_season: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for row in stints:
        season = str(row.get("seasonIndex", "")).strip()
        roster_id = str(row.get("player__rosterId", "")).strip()
        team = normalize_team_display(row.get("team", ""))
        if not season or not roster_id or not team:
            continue
        teams_by_player_season[(season, roster_id)].add(team)
    return teams_by_player_season


def write_traded_players_report(
    base_path: Path,
    stints: List[Dict[str, Any]],
    teams_by_player_season: Dict[Tuple[str, str], Set[str]],
) -> Tuple[int, int]:
    multi_team_keys = {
        key for key, teams in teams_by_player_season.items() if len(teams) > 1
    }
    if not stints:
        print("No stints data available; skipping traded players report.")
        return 0, 0

    output_dir = base_path / "output"
    output_dir.mkdir(exist_ok=True, parents=True)
    output_file = output_dir / "traded_players_report.csv"

    base_fields = list(stints[0].keys())
    extra_fields = ["multi_team_teams", "multi_team_team_count"]
    fieldnames = base_fields + extra_fields

    import csv

    rows_written = 0
    multi_team_player_count = len(multi_team_keys)

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in stints:
            season = str(row.get("seasonIndex", "")).strip()
            roster_id = str(row.get("player__rosterId", "")).strip()
            key = (season, roster_id)
            if key not in multi_team_keys:
                continue

            teams = sorted(teams_by_player_season.get(key, set()))
            out_row = dict(row)
            out_row["multi_team_teams"] = "|".join(teams)
            out_row["multi_team_team_count"] = str(len(teams))
            writer.writerow(out_row)
            rows_written += 1

    print(f"✓ Wrote traded players report to {output_file}")
    print(f"  Multi-team players (by season): {multi_team_player_count}")
    print(f"  Multi-team stint rows written: {rows_written}")
    return multi_team_player_count, rows_written


def build_team_indexes(
    team_stats: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in team_stats:
        team_name = normalize_team_display(row.get("team", ""))
        if not team_name:
            continue
        index[team_name] = row
    return index


def compute_stint_sums_by_team(
    stints: List[Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    team_sums: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    league_sums: Dict[str, float] = defaultdict(float)

    for row in stints:
        team = normalize_team_display(row.get("team", ""))
        if not team:
            continue

        for stint_field, team_field in STAT_FIELD_MAP.items():
            value = safe_float(row.get(stint_field))
            team_sums[team][team_field] += value
            league_sums[team_field] += value

    return team_sums, league_sums


def check_team_invariants(
    team_stats: List[Dict[str, Any]],
    stints: List[Dict[str, Any]],
) -> Tuple[int, int]:
    team_index = build_team_indexes(team_stats)
    stint_team_sums, league_stint_sums = compute_stint_sums_by_team(stints)

    all_teams = set(team_index.keys()) | set(stint_team_sums.keys())
    all_team_fields = set(STAT_FIELD_MAP.values())

    abs_tolerance = 1e-6
    rel_tolerance = 1e-6

    team_discrepancies = 0

    print("\nChecking per-team invariants...")

    for team in sorted(all_teams):
        team_row = team_index.get(team)
        stint_sums = stint_team_sums.get(team, {})

        for team_field in all_team_fields:
            if team_row is None and team_field not in stint_sums:
                continue

            team_value = safe_float(team_row.get(team_field)) if team_row else 0.0
            stint_total = stint_sums.get(team_field, 0.0)

            diff = abs(team_value - stint_total)
            max_base = max(abs(team_value), abs(stint_total), 1.0)
            rel_diff = diff / max_base

            if diff > abs_tolerance and rel_diff > rel_tolerance:
                team_discrepancies += 1
                print(
                    f"[TEAM MISMATCH] team={team}, stat={team_field}, "
                    f"team_stats={team_value}, stints_sum={stint_total}, "
                    f"abs_diff={diff}, rel_diff={rel_diff}"
                )

    league_team_totals: Dict[str, float] = defaultdict(float)
    for row in team_stats:
        for team_field in all_team_fields:
            league_team_totals[team_field] += safe_float(row.get(team_field))

    league_discrepancies = 0

    print("\nChecking league-wide invariants...")

    for team_field in sorted(all_team_fields):
        team_total = league_team_totals.get(team_field, 0.0)
        stint_total = league_stint_sums.get(team_field, 0.0)

        diff = abs(team_total - stint_total)
        max_base = max(abs(team_total), abs(stint_total), 1.0)
        rel_diff = diff / max_base

        if diff > abs_tolerance and rel_diff > rel_tolerance:
            league_discrepancies += 1
            print(
                f"[LEAGUE MISMATCH] stat={team_field}, "
                f"team_total={team_total}, stints_total={stint_total}, "
                f"abs_diff={diff}, rel_diff={rel_diff}"
            )

    print(
        f"\nInvariant summary: team discrepancies={team_discrepancies}, "
        f"league discrepancies={league_discrepancies}"
    )

    return team_discrepancies, league_discrepancies


def analyze_raw_multi_team_players(
    passing: List[Dict[str, Any]],
    rushing: List[Dict[str, Any]],
    receiving: List[Dict[str, Any]],
    teams_by_player_season: Dict[Tuple[str, str], Set[str]],
) -> None:
    raw_teams_by_player: Dict[str, Set[str]] = defaultdict(set)

    for rows in (passing, rushing, receiving):
        for row in rows:
            roster_id = str(row.get("player__rosterId", "")).strip()
            team = normalize_team_display(row.get("team__displayName", ""))
            if not roster_id or not team:
                continue
            raw_teams_by_player[roster_id].add(team)

    raw_multi = {rid for rid, teams in raw_teams_by_player.items() if len(teams) > 1}
    stints_multi = {
        roster_id
        for (season, roster_id), teams in teams_by_player_season.items()
        if len(teams) > 1
    }

    only_in_raw = raw_multi - stints_multi
    only_in_stints = stints_multi - raw_multi

    print("\nRaw MEGA multi-team players summary:")
    print(f"  Multi-team players in raw stats: {len(raw_multi)}")
    print(f"  Multi-team players in stints:    {len(stints_multi)}")

    if only_in_raw:
        sample = list(sorted(only_in_raw))[:5]
        print(
            "  Warning: players multi-team in raw stats but not in stints "
            f"(showing up to 5 rosterIds): {', '.join(sample)}"
        )
    if only_in_stints:
        sample = list(sorted(only_in_stints))[:5]
        print(
            "  Warning: players multi-team in stints but not detected in raw stats "
            f"(showing up to 5 rosterIds): {', '.join(sample)}"
        )


def main() -> None:
    print(f"Working directory: {BASE_PATH}\n")
    data = load_data(BASE_PATH)

    stints = data["stints"]
    team_stats = data["team_stats"]

    print(
        f"Loaded {len(data['passing'])} passing rows, "
        f"{len(data['rushing'])} rushing rows, "
        f"{len(data['receiving'])} receiving rows."
    )
    print(
        f"Loaded {len(team_stats)} team_aggregated_stats rows and "
        f"{len(stints)} player_team_stints rows."
    )

    teams_by_player_season = build_player_season_teams(stints)

    multi_team_player_count, rows_written = write_traded_players_report(
        BASE_PATH, stints, teams_by_player_season
    )

    team_discrepancies, league_discrepancies = check_team_invariants(
        team_stats, stints
    )

    analyze_raw_multi_team_players(
        data["passing"],
        data["rushing"],
        data["receiving"],
        teams_by_player_season,
    )

    if team_discrepancies or league_discrepancies:
        print(
            "\n✗ Trade stats verification failed due to invariant discrepancies. "
            "See details above."
        )
        sys.exit(1)

    print(
        "\n✓ Trade stats verification completed successfully.\n"
        f"  Multi-team players reported: {multi_team_player_count}\n"
        f"  Multi-team stint rows:      {rows_written}"
    )


if __name__ == "__main__":
    main()

