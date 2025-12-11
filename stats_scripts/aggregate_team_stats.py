#!/usr/bin/env python3
"""
Aggregate player-level statistics to team-level metrics.
Creates CSV files with team-aggregated stats and derived efficiency metrics.
"""

import csv
from pathlib import Path
from collections import defaultdict

from stats_common import load_csv, safe_float, normalize_team_display


def safe_mean(values):
    """Calculate mean of list, ignoring non-numeric values."""
    nums = [safe_float(v) for v in values if v and v != ""]
    return sum(nums) / len(nums) if nums else 0.0

def aggregate_team_stats(base_path):
    """Aggregate all team statistics from player-level CSVs."""
    
    print("Loading data files...")
    
    # Raw MEGA stat CSVs (used for QB rating, special teams, and defensive extras).
    passing = load_csv(base_path / "MEGA_passing.csv")
    rushing = load_csv(base_path / "MEGA_rushing.csv")
    receiving = load_csv(base_path / "MEGA_receiving.csv")
    defense = load_csv(base_path / "MEGA_defense.csv")
    punting = load_csv(base_path / "MEGA_punting.csv")
    kicking = load_csv(base_path / "MEGA_kicking.csv")
    teams = load_csv(base_path / "MEGA_teams.csv")
    # Trade-aware per-team/per-player stints (source of adjusted team volumes).
    stints = load_csv(base_path / "output" / "player_team_stints.csv")
    
    teams_map = {}
    for t in teams:
        name = normalize_team_display(t.get("displayName", ""))
        if name:
            teams_map[name] = t
    
    team_names = sorted(teams_map.keys())
    
    print(f"Processing {len(team_names)} teams...")
    
    team_stats = []
    
    for team in team_names:
        if not team:
            continue
            
        team_data = {"team": team}
        
        team_info = teams_map.get(team, {})
        team_data["logoId"] = team_info.get("logoId", "")
        team_data["conference"] = team_info.get(
            "conferenceName", team_info.get("conference", "")
        )
        team_data["wins"] = safe_float(team_info.get("totalWins", 0))
        team_data["losses"] = safe_float(team_info.get("totalLosses", 0))
        team_data["ties"] = safe_float(team_info.get("totalTies", 0))
        
        total_games = team_data["wins"] + team_data["losses"] + team_data["ties"]
        team_data["win_pct"] = (
            (team_data["wins"] + 0.5 * team_data["ties"]) / total_games
            if total_games > 0
            else 0
        )

        # Trade-aware per-team stats from player_team_stints (adjusted layer).
        team_stints = [s for s in stints if s.get("team") == team]

        # Offensive passing (adjusted and raw)
        team_data["pass_att"] = sum(
            safe_float(s.get("passTotalAtt")) for s in team_stints
        )
        team_data["pass_comp"] = sum(
            safe_float(s.get("passTotalComp")) for s in team_stints
        )
        team_data["pass_yds"] = sum(
            safe_float(s.get("passTotalYds")) for s in team_stints
        )
        team_data["pass_tds"] = sum(
            safe_float(s.get("passTotalTDs")) for s in team_stints
        )
        team_data["pass_ints"] = sum(
            safe_float(s.get("passTotalInts")) for s in team_stints
        )
        team_data["pass_ints_raw"] = sum(
            safe_float(s.get("passTotalInts_raw")) for s in team_stints
        )
        team_data["pass_ints_adjustment"] = (
            team_data["pass_ints"] - team_data["pass_ints_raw"]
        )
        team_data["pass_sacks"] = sum(
            safe_float(s.get("passTotalSacks")) for s in team_stints
        )

        # QB rating still uses raw MEGA_passing rows.
        team_passing_megarows = [
            p for p in passing if normalize_team_display(p.get("team__displayName", "")) == team
        ]
        team_data["qb_rating"] = safe_mean(
            [
                p.get("passerAvgRating")
                for p in team_passing_megarows
                if safe_float(p.get("passTotalAtt")) >= 20
            ]
        )

        # Offensive rushing (adjusted)
        team_data["rush_att"] = sum(
            safe_float(s.get("rushTotalAtt")) for s in team_stints
        )
        team_data["rush_yds"] = sum(
            safe_float(s.get("rushTotalYds")) for s in team_stints
        )
        team_data["rush_tds"] = sum(
            safe_float(s.get("rushTotalTDs")) for s in team_stints
        )
        team_data["rush_fum"] = sum(
            safe_float(s.get("rushTotalFum")) for s in team_stints
        )
        team_data["rush_broken_tackles"] = sum(
            safe_float(s.get("rushTotalBrokenTackles")) for s in team_stints
        )
        team_data["rush_yac"] = sum(
            safe_float(s.get("rushTotalYdsAfterContact")) for s in team_stints
        )
        team_data["rush_20plus"] = sum(
            safe_float(s.get("rushTotal20PlusYds")) for s in team_stints
        )

        # Receiving (adjusted)
        team_data["rec_catches"] = sum(
            safe_float(s.get("recTotalCatches")) for s in team_stints
        )
        team_data["rec_yds"] = sum(
            safe_float(s.get("recTotalYds")) for s in team_stints
        )
        team_data["rec_tds"] = sum(
            safe_float(s.get("recTotalTDs")) for s in team_stints
        )
        team_data["rec_drops"] = sum(
            safe_float(s.get("recTotalDrops")) for s in team_stints
        )
        team_data["rec_yac"] = sum(
            safe_float(s.get("recTotalYdsAfterCatch")) for s in team_stints
        )

        # Defensive stats remain based on MEGA_defense rows (already split per team).
        team_defense = [
            d for d in defense if normalize_team_display(d.get("team__displayName", "")) == team
        ]
        
        team_data["def_sacks"] = sum(
            safe_float(d.get("defTotalSacks")) for d in team_defense
        )
        team_data["def_ints"] = sum(
            safe_float(d.get("defTotalInts")) for d in team_defense
        )
        team_data["def_forced_fum"] = sum(
            safe_float(d.get("defTotalForcedFum")) for d in team_defense
        )
        team_data["def_fum_rec"] = sum(
            safe_float(d.get("defTotalFumRec")) for d in team_defense
        )
        team_data["def_tds"] = sum(
            safe_float(d.get("defTotalTDs")) for d in team_defense
        )
        team_data["def_tackles"] = sum(
            safe_float(d.get("defTotalTackles")) for d in team_defense
        )
        team_data["def_deflections"] = sum(
            safe_float(d.get("defTotalDeflections")) for d in team_defense
        )

        # Special teams from MEGA_punting / MEGA_kicking (no trade-specific logic needed).
        team_punting = [
            p for p in punting if normalize_team_display(p.get("team__displayName", "")) == team
        ]
        team_kicking = [
            k for k in kicking if normalize_team_display(k.get("team__displayName", "")) == team
        ]

        team_data["punts"] = sum(
            safe_float(p.get("puntTotalAtt")) for p in team_punting
        )
        team_data["punt_avg"] = safe_mean(
            [
                p.get("puntAvgYdsPerAtt")
                for p in team_punting
                if safe_float(p.get("puntTotalAtt")) >= 5
            ]
        )
        team_data["punt_net_avg"] = safe_mean(
            [
                p.get("puntAvgNetYdsPerAtt")
                for p in team_punting
                if safe_float(p.get("puntTotalAtt")) >= 5
            ]
        )
        team_data["punts_in_20"] = sum(
            safe_float(p.get("puntsTotalIn20")) for p in team_punting
        )
        team_data["punts_touchbacks"] = sum(
            safe_float(p.get("puntTotalTBs")) for p in team_punting
        )

        team_data["fg_att"] = sum(
            safe_float(k.get("fGTotalAtt")) for k in team_kicking
        )
        team_data["fg_made"] = sum(
            safe_float(k.get("fGTotalMade")) for k in team_kicking
        )
        team_data["fg_50plus_att"] = sum(
            safe_float(k.get("fGTotal50PlusAtt")) for k in team_kicking
        )
        team_data["fg_50plus_made"] = sum(
            safe_float(k.get("fGTotal50PlusMade")) for k in team_kicking
        )
        team_data["xp_att"] = sum(
            safe_float(k.get("xPTotalAtt")) for k in team_kicking
        )
        team_data["xp_made"] = sum(
            safe_float(k.get("xPTotalMade")) for k in team_kicking
        )
        team_data["kickoff_touchbacks"] = sum(
            safe_float(k.get("kickoffTotalTBs")) for k in team_kicking
        )

        team_data["total_off_plays"] = team_data["pass_att"] + team_data["rush_att"]
        team_data["total_off_yds"] = team_data["pass_yds"] + team_data["rush_yds"]
        team_data["total_off_tds"] = team_data["pass_tds"] + team_data["rush_tds"]
        team_data["total_turnovers"] = team_data["pass_ints"] + team_data["rush_fum"]
        team_data["total_takeaways"] = (
            team_data["def_ints"] + team_data["def_fum_rec"]
        )

        team_data["pass_yds_per_att"] = (
            team_data["pass_yds"] / team_data["pass_att"]
            if team_data["pass_att"] > 0
            else 0
        )
        team_data["rush_yds_per_att"] = (
            team_data["rush_yds"] / team_data["rush_att"]
            if team_data["rush_att"] > 0
            else 0
        )
        team_data["pass_comp_pct"] = (
            team_data["pass_comp"] / team_data["pass_att"] * 100
            if team_data["pass_att"] > 0
            else 0
        )
        team_data["pass_td_pct"] = (
            team_data["pass_tds"] / team_data["pass_att"] * 100
            if team_data["pass_att"] > 0
            else 0
        )
        team_data["pass_int_pct"] = (
            team_data["pass_ints"] / team_data["pass_att"] * 100
            if team_data["pass_att"] > 0
            else 0
        )
        team_data["sack_rate"] = (
            team_data["pass_sacks"]
            / (team_data["pass_att"] + team_data["pass_sacks"])
            * 100
            if (team_data["pass_att"] + team_data["pass_sacks"]) > 0
            else 0
        )

        team_data["rush_td_pct"] = (
            team_data["rush_tds"] / team_data["rush_att"] * 100
            if team_data["rush_att"] > 0
            else 0
        )
        team_data["rush_broken_tackle_rate"] = (
            team_data["rush_broken_tackles"] / team_data["rush_att"]
            if team_data["rush_att"] > 0
            else 0
        )
        team_data["rush_yac_pct"] = (
            team_data["rush_yac"] / team_data["rush_yds"] * 100
            if team_data["rush_yds"] > 0
            else 0
        )
        team_data["rush_explosive_rate"] = (
            team_data["rush_20plus"] / team_data["rush_att"] * 100
            if team_data["rush_att"] > 0
            else 0
        )

        qualified_rec_catches = sum(
            safe_float(s.get("recTotalCatches"))
            for s in team_stints
            if (
                safe_float(s.get("recTotalCatches"))
                + safe_float(s.get("recTotalDrops"))
            )
            >= 5
        )
        qualified_rec_drops = sum(
            safe_float(s.get("recTotalDrops"))
            for s in team_stints
            if (
                safe_float(s.get("recTotalCatches"))
                + safe_float(s.get("recTotalDrops"))
            )
            >= 5
        )
        team_data["drop_rate"] = (
            qualified_rec_drops
            / (qualified_rec_catches + qualified_rec_drops)
            * 100
            if (qualified_rec_catches + qualified_rec_drops) > 0
            else 0
        )
        team_data["rec_yac_pct"] = (
            team_data["rec_yac"] / team_data["rec_yds"] * 100
            if team_data["rec_yds"] > 0
            else 0
        )
        team_data["rec_yds_per_catch"] = (
            team_data["rec_yds"] / team_data["rec_catches"]
            if team_data["rec_catches"] > 0
            else 0
        )

        team_data["td_per_play"] = (
            team_data["total_off_tds"] / team_data["total_off_plays"]
            if team_data["total_off_plays"] > 0
            else 0
        )
        team_data["yds_per_play"] = (
            team_data["total_off_yds"] / team_data["total_off_plays"]
            if team_data["total_off_plays"] > 0
            else 0
        )
        team_data["turnover_diff"] = (
            team_data["total_takeaways"] - team_data["total_turnovers"]
        )

        games = max(
            team_data["wins"] + team_data["losses"] + team_data["ties"],
            1,
        )

        team_data["pass_yds_per_game"] = team_data["pass_yds"] / games
        team_data["rush_yds_per_game"] = team_data["rush_yds"] / games
        team_data["rec_yds_per_game"] = team_data["rec_yds"] / games
        team_data["off_yds_per_game"] = team_data["total_off_yds"] / games
        team_data["pass_att_per_game"] = team_data["pass_att"] / games
        team_data["rush_att_per_game"] = team_data["rush_att"] / games
        team_data["punts_per_game"] = team_data["punts"] / games
        team_data["def_sacks_per_game"] = team_data["def_sacks"] / games
        team_data["def_ints_per_game"] = team_data["def_ints"] / games
        team_data["pass_ints_per_game"] = team_data["pass_ints"] / games
        team_data["sacks_allowed_per_game"] = team_data["pass_sacks"] / games
        team_data["explosive_plays"] = team_data["rush_20plus"]
        team_data["explosive_plays_per_game"] = (
            team_data["explosive_plays"] / games
        )

        team_data["pass_rush_ratio"] = (
            team_data["pass_att"] / team_data["rush_att"]
            if team_data["rush_att"] > 0
            else 0
        )
        team_data["fg_pct"] = (
            team_data["fg_made"] / team_data["fg_att"] * 100
            if team_data["fg_att"] > 0
            else 0
        )
        team_data["fg_50plus_pct"] = (
            team_data["fg_50plus_made"] / team_data["fg_50plus_att"] * 100
            if team_data["fg_50plus_att"] > 0
            else 0
        )
        team_data["xp_pct"] = (
            team_data["xp_made"] / team_data["xp_att"] * 100
            if team_data["xp_att"] > 0
            else 0
        )
        team_data["punts_in_20_pct"] = (
            team_data["punts_in_20"] / team_data["punts"] * 100
            if team_data["punts"] > 0
            else 0
        )
        
        team_stats.append(team_data)
    
    output_dir = base_path / 'output'
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / 'team_aggregated_stats.csv'
    
    if team_stats:
        fieldnames = list(team_stats[0].keys())
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(team_stats)
        
        print(f"\n✓ Saved aggregated stats to: {output_file}")
        print(f"  Teams processed: {len(team_stats)}")
        print(f"  Metrics calculated: {len(fieldnames)}")
        
        print("\nSample metrics available:")
        metrics = [c for c in fieldnames if c not in ['team', 'logoId', 'conference']]
        for i, metric in enumerate(metrics[:15], 1):
            print(f"  {i}. {metric}")
        if len(metrics) > 15:
            print(f"  ... and {len(metrics) - 15} more")
    
    return team_stats

if __name__ == '__main__':
    base_path = Path(__file__).parent.parent
    print(f"Working directory: {base_path}\n")
    
    df = aggregate_team_stats(base_path)
    
    print("\n✓ Done! Use team_aggregated_stats.csv for visualizations.")
