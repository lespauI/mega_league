#!/usr/bin/env python3
"""
Aggregate player-level statistics to team-level metrics.
Creates CSV files with team-aggregated stats and derived efficiency metrics.
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

def load_csv(filepath):
    """Load CSV with error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return []

def safe_float(value, default=0.0):
    """Safely convert to float."""
    try:
        return float(value) if value and value != '' else default
    except (ValueError, TypeError):
        return default

def safe_mean(values):
    """Calculate mean of list, ignoring non-numeric values."""
    nums = [safe_float(v) for v in values if v and v != '']
    return sum(nums) / len(nums) if nums else 0.0

def aggregate_team_stats(base_path):
    """Aggregate all team statistics from player-level CSVs."""
    
    print("Loading data files...")
    
    passing = load_csv(base_path / 'MEGA_passing.csv')
    rushing = load_csv(base_path / 'MEGA_rushing.csv')
    receiving = load_csv(base_path / 'MEGA_receiving.csv')
    defense = load_csv(base_path / 'MEGA_defense.csv')
    punting = load_csv(base_path / 'MEGA_punting.csv')
    kicking = load_csv(base_path / 'MEGA_kicking.csv')
    teams = load_csv(base_path / 'MEGA_teams.csv')
    
    teams_map = {}
    for t in teams:
        if t.get('displayName'):
            teams_map[t['displayName']] = t
    
    team_names = sorted(teams_map.keys())
    
    print(f"Processing {len(team_names)} teams...")
    
    team_stats = []
    
    for team in team_names:
        if not team:
            continue
            
        team_data = {'team': team}
        
        team_info = teams_map.get(team, {})
        team_data['logoId'] = team_info.get('logoId', '')
        team_data['conference'] = team_info.get('conferenceName', team_info.get('conference', ''))
        team_data['wins'] = safe_float(team_info.get('totalWins', 0))
        team_data['losses'] = safe_float(team_info.get('totalLosses', 0))
        team_data['ties'] = safe_float(team_info.get('totalTies', 0))
        
        total_games = team_data['wins'] + team_data['losses'] + team_data['ties']
        team_data['win_pct'] = (team_data['wins'] + 0.5 * team_data['ties']) / total_games if total_games > 0 else 0
        
        team_passing = [p for p in passing if p.get('team__displayName') == team]
        team_rushing = [r for r in rushing if r.get('team__displayName') == team]
        team_receiving = [r for r in receiving if r.get('team__displayName') == team]
        team_defense = [d for d in defense if d.get('team__displayName') == team]
        team_punting = [p for p in punting if p.get('team__displayName') == team]
        team_kicking = [k for k in kicking if k.get('team__displayName') == team]
        
        team_data['pass_att'] = sum(safe_float(p.get('passTotalAtt')) for p in team_passing)
        team_data['pass_comp'] = sum(safe_float(p.get('passTotalComp')) for p in team_passing)
        team_data['pass_yds'] = sum(safe_float(p.get('passTotalYds')) for p in team_passing)
        team_data['pass_tds'] = sum(safe_float(p.get('passTotalTDs')) for p in team_passing)
        team_data['pass_ints'] = sum(safe_float(p.get('passTotalInts')) for p in team_passing)
        team_data['pass_sacks'] = sum(safe_float(p.get('passTotalSacks')) for p in team_passing)
        team_data['qb_rating'] = safe_mean([p.get('passerAvgRating') for p in team_passing if safe_float(p.get('passTotalAtt')) >= 20])
        team_data['pass_yds_per_game'] = safe_mean([p.get('passAvgYdsPerGame') for p in team_passing if safe_float(p.get('passTotalAtt')) >= 20])
        
        team_data['rush_att'] = sum(safe_float(r.get('rushTotalAtt')) for r in team_rushing)
        team_data['rush_yds'] = sum(safe_float(r.get('rushTotalYds')) for r in team_rushing)
        team_data['rush_tds'] = sum(safe_float(r.get('rushTotalTDs')) for r in team_rushing)
        team_data['rush_fum'] = sum(safe_float(r.get('rushTotalFum')) for r in team_rushing)
        team_data['rush_broken_tackles'] = sum(safe_float(r.get('rushTotalBrokenTackles')) for r in team_rushing)
        team_data['rush_yac'] = sum(safe_float(r.get('rushTotalYdsAfterContact')) for r in team_rushing)
        team_data['rush_20plus'] = sum(safe_float(r.get('rushTotal20PlusYds')) for r in team_rushing)
        team_data['rush_yds_per_game'] = safe_mean([r.get('rushAvgYdsPerGame') for r in team_rushing if safe_float(r.get('rushTotalAtt')) >= 10])
        
        team_data['rec_catches'] = sum(safe_float(r.get('recTotalCatches')) for r in team_receiving)
        team_data['rec_yds'] = sum(safe_float(r.get('recTotalYds')) for r in team_receiving)
        team_data['rec_tds'] = sum(safe_float(r.get('recTotalTDs')) for r in team_receiving)
        team_data['rec_drops'] = sum(safe_float(r.get('recTotalDrops')) for r in team_receiving)
        team_data['rec_yac'] = sum(safe_float(r.get('recTotalYdsAfterCatch')) for r in team_receiving)
        team_data['rec_yds_per_game'] = safe_mean([r.get('recAvgYdsPerGame') for r in team_receiving if safe_float(r.get('recTotalCatches')) >= 5])
        
        team_data['def_sacks'] = sum(safe_float(d.get('defTotalSacks')) for d in team_defense)
        team_data['def_ints'] = sum(safe_float(d.get('defTotalInts')) for d in team_defense)
        team_data['def_forced_fum'] = sum(safe_float(d.get('defTotalForcedFum')) for d in team_defense)
        team_data['def_fum_rec'] = sum(safe_float(d.get('defTotalFumRec')) for d in team_defense)
        team_data['def_tds'] = sum(safe_float(d.get('defTotalTDs')) for d in team_defense)
        team_data['def_tackles'] = sum(safe_float(d.get('defTotalTackles')) for d in team_defense)
        team_data['def_deflections'] = sum(safe_float(d.get('defTotalDeflections')) for d in team_defense)
        
        team_data['punts'] = sum(safe_float(p.get('puntTotalAtt')) for p in team_punting)
        team_data['punt_avg'] = safe_mean([p.get('puntAvgYdsPerAtt') for p in team_punting if safe_float(p.get('puntTotalAtt')) >= 5])
        team_data['punt_net_avg'] = safe_mean([p.get('puntAvgNetYdsPerAtt') for p in team_punting if safe_float(p.get('puntTotalAtt')) >= 5])
        team_data['punts_in_20'] = sum(safe_float(p.get('puntsTotalIn20')) for p in team_punting)
        team_data['punts_touchbacks'] = sum(safe_float(p.get('puntTotalTBs')) for p in team_punting)
        
        team_data['fg_att'] = sum(safe_float(k.get('fGTotalAtt')) for k in team_kicking)
        team_data['fg_made'] = sum(safe_float(k.get('fGTotalMade')) for k in team_kicking)
        team_data['fg_50plus_att'] = sum(safe_float(k.get('fGTotal50PlusAtt')) for k in team_kicking)
        team_data['fg_50plus_made'] = sum(safe_float(k.get('fGTotal50PlusMade')) for k in team_kicking)
        team_data['xp_att'] = sum(safe_float(k.get('xPTotalAtt')) for k in team_kicking)
        team_data['xp_made'] = sum(safe_float(k.get('xPTotalMade')) for k in team_kicking)
        team_data['kickoff_touchbacks'] = sum(safe_float(k.get('kickoffTotalTBs')) for k in team_kicking)
        
        team_data['total_off_plays'] = team_data['pass_att'] + team_data['rush_att']
        team_data['total_off_yds'] = team_data['pass_yds'] + team_data['rush_yds']
        team_data['total_off_tds'] = team_data['pass_tds'] + team_data['rush_tds']
        team_data['total_turnovers'] = team_data['pass_ints'] + team_data['rush_fum']
        team_data['total_takeaways'] = team_data['def_ints'] + team_data['def_fum_rec']
        
        team_data['pass_yds_per_att'] = team_data['pass_yds'] / team_data['pass_att'] if team_data['pass_att'] > 0 else 0
        team_data['rush_yds_per_att'] = team_data['rush_yds'] / team_data['rush_att'] if team_data['rush_att'] > 0 else 0
        team_data['pass_comp_pct'] = team_data['pass_comp'] / team_data['pass_att'] * 100 if team_data['pass_att'] > 0 else 0
        team_data['pass_td_pct'] = team_data['pass_tds'] / team_data['pass_att'] * 100 if team_data['pass_att'] > 0 else 0
        team_data['pass_int_pct'] = team_data['pass_ints'] / team_data['pass_att'] * 100 if team_data['pass_att'] > 0 else 0
        team_data['sack_rate'] = team_data['pass_sacks'] / (team_data['pass_att'] + team_data['pass_sacks']) * 100 if (team_data['pass_att'] + team_data['pass_sacks']) > 0 else 0
        
        team_data['rush_td_pct'] = team_data['rush_tds'] / team_data['rush_att'] * 100 if team_data['rush_att'] > 0 else 0
        team_data['rush_broken_tackle_rate'] = team_data['rush_broken_tackles'] / team_data['rush_att'] if team_data['rush_att'] > 0 else 0
        team_data['rush_yac_pct'] = team_data['rush_yac'] / team_data['rush_yds'] * 100 if team_data['rush_yds'] > 0 else 0
        team_data['rush_explosive_rate'] = team_data['rush_20plus'] / team_data['rush_att'] * 100 if team_data['rush_att'] > 0 else 0
        
        qualified_rec_catches = sum(safe_float(r.get('recTotalCatches')) for r in team_receiving if (safe_float(r.get('recTotalCatches')) + safe_float(r.get('recTotalDrops'))) >= 5)
        qualified_rec_drops = sum(safe_float(r.get('recTotalDrops')) for r in team_receiving if (safe_float(r.get('recTotalCatches')) + safe_float(r.get('recTotalDrops'))) >= 5)
        team_data['drop_rate'] = qualified_rec_drops / (qualified_rec_catches + qualified_rec_drops) * 100 if (qualified_rec_catches + qualified_rec_drops) > 0 else 0
        team_data['rec_yac_pct'] = team_data['rec_yac'] / team_data['rec_yds'] * 100 if team_data['rec_yds'] > 0 else 0
        team_data['rec_yds_per_catch'] = team_data['rec_yds'] / team_data['rec_catches'] if team_data['rec_catches'] > 0 else 0
        
        team_data['td_per_play'] = team_data['total_off_tds'] / team_data['total_off_plays'] if team_data['total_off_plays'] > 0 else 0
        team_data['yds_per_play'] = team_data['total_off_yds'] / team_data['total_off_plays'] if team_data['total_off_plays'] > 0 else 0
        team_data['turnover_diff'] = team_data['total_takeaways'] - team_data['total_turnovers']
        
        games = max(team_data['wins'] + team_data['losses'] + team_data['ties'], 1)
        
        team_data['off_yds_per_game'] = team_data['total_off_yds'] / games
        team_data['pass_att_per_game'] = team_data['pass_att'] / games
        team_data['rush_att_per_game'] = team_data['rush_att'] / games
        team_data['punts_per_game'] = team_data['punts'] / games
        team_data['def_sacks_per_game'] = team_data['def_sacks'] / games
        team_data['def_ints_per_game'] = team_data['def_ints'] / games
        team_data['pass_ints_per_game'] = team_data['pass_ints'] / games
        team_data['sacks_allowed_per_game'] = team_data['pass_sacks'] / games
        team_data['explosive_plays'] = team_data['rush_20plus']
        team_data['explosive_plays_per_game'] = team_data['explosive_plays'] / games
        
        team_data['pass_rush_ratio'] = team_data['pass_att'] / team_data['rush_att'] if team_data['rush_att'] > 0 else 0
        team_data['fg_pct'] = team_data['fg_made'] / team_data['fg_att'] * 100 if team_data['fg_att'] > 0 else 0
        team_data['fg_50plus_pct'] = team_data['fg_50plus_made'] / team_data['fg_50plus_att'] * 100 if team_data['fg_50plus_att'] > 0 else 0
        team_data['xp_pct'] = team_data['xp_made'] / team_data['xp_att'] * 100 if team_data['xp_att'] > 0 else 0
        team_data['punts_in_20_pct'] = team_data['punts_in_20'] / team_data['punts'] * 100 if team_data['punts'] > 0 else 0
        
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
