#!/usr/bin/env python3
"""
Aggregate player usage patterns by team.
Calculates distribution metrics for passing targets, rushing attempts, etc.
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

def calculate_herfindahl_index(shares):
    """Calculate Herfindahl-Hirschman Index for concentration."""
    return sum(s**2 for s in shares) if shares else 0

def aggregate_player_usage(base_path):
    """Aggregate player usage patterns."""
    
    print("Loading data files...")
    
    receiving = load_csv(base_path / 'MEGA_receiving.csv')
    rushing = load_csv(base_path / 'MEGA_rushing.csv')
    teams_csv = load_csv(base_path / 'MEGA_teams.csv')
    
    teams_map = {}
    for t in teams_csv:
        if t.get('displayName'):
            teams_map[t['displayName']] = t
    
    team_names = sorted(teams_map.keys())
    
    print(f"Processing {len(team_names)} teams...")
    
    team_usage = []
    
    for team in team_names:
        if not team:
            continue
            
        usage_data = {'team': team}
        
        team_info = teams_map.get(team, {})
        usage_data['logoId'] = team_info.get('logoId', '')
        usage_data['conference'] = team_info.get('conferenceName', team_info.get('conference', ''))
        usage_data['wins'] = safe_float(team_info.get('totalWins', 0))
        usage_data['losses'] = safe_float(team_info.get('totalLosses', 0))
        usage_data['ties'] = safe_float(team_info.get('totalTies', 0))
        
        total_games = usage_data['wins'] + usage_data['losses'] + usage_data['ties']
        usage_data['win_pct'] = (usage_data['wins'] + 0.5 * usage_data['ties']) / total_games if total_games > 0 else 0
        
        team_receiving = [r for r in receiving if r.get('team__displayName') == team]
        team_rushing = [r for r in rushing if r.get('team__displayName') == team]
        
        total_catches = sum(safe_float(r.get('recTotalCatches')) for r in team_receiving)
        total_rec_yds = sum(safe_float(r.get('recTotalYds')) for r in team_receiving)
        total_rec_tds = sum(safe_float(r.get('recTotalTDs')) for r in team_receiving)
        
        wr_catches = sum(safe_float(r.get('recTotalCatches')) for r in team_receiving if r.get('player__position') == 'WR')
        te_catches = sum(safe_float(r.get('recTotalCatches')) for r in team_receiving if r.get('player__position') == 'TE')
        rb_catches = sum(safe_float(r.get('recTotalCatches')) for r in team_receiving if r.get('player__position') in ['HB', 'FB'])
        
        usage_data['wr_target_share'] = (wr_catches / total_catches * 100) if total_catches > 0 else 0
        usage_data['te_target_share'] = (te_catches / total_catches * 100) if total_catches > 0 else 0
        usage_data['rb_target_share'] = (rb_catches / total_catches * 100) if total_catches > 0 else 0
        
        receivers_sorted = sorted(
            [(safe_float(r.get('recTotalCatches')), r.get('player__fullName', ''), r.get('player__position', '')) 
             for r in team_receiving],
            reverse=True
        )
        
        if receivers_sorted:
            usage_data['wr1_catches'] = receivers_sorted[0][0] if len(receivers_sorted) > 0 else 0
            usage_data['wr1_name'] = receivers_sorted[0][1] if len(receivers_sorted) > 0 else ''
            usage_data['wr1_position'] = receivers_sorted[0][2] if len(receivers_sorted) > 0 else ''
            usage_data['wr1_share'] = (receivers_sorted[0][0] / total_catches * 100) if total_catches > 0 and len(receivers_sorted) > 0 else 0
            
            usage_data['wr2_catches'] = receivers_sorted[1][0] if len(receivers_sorted) > 1 else 0
            usage_data['wr2_share'] = (receivers_sorted[1][0] / total_catches * 100) if total_catches > 0 and len(receivers_sorted) > 1 else 0
            
            usage_data['wr3_catches'] = receivers_sorted[2][0] if len(receivers_sorted) > 2 else 0
            usage_data['wr3_share'] = (receivers_sorted[2][0] / total_catches * 100) if total_catches > 0 and len(receivers_sorted) > 2 else 0
            
            usage_data['top3_share'] = usage_data['wr1_share'] + usage_data['wr2_share'] + usage_data['wr3_share']
        else:
            usage_data['wr1_catches'] = 0
            usage_data['wr1_name'] = ''
            usage_data['wr1_position'] = ''
            usage_data['wr1_share'] = 0
            usage_data['wr2_catches'] = 0
            usage_data['wr2_share'] = 0
            usage_data['wr3_catches'] = 0
            usage_data['wr3_share'] = 0
            usage_data['top3_share'] = 0
        
        rec_shares = [safe_float(r.get('recTotalCatches')) / total_catches for r in team_receiving if total_catches > 0]
        usage_data['pass_concentration'] = calculate_herfindahl_index(rec_shares) * 10000
        
        total_rushes = sum(safe_float(r.get('rushTotalAtt')) for r in team_rushing)
        total_rush_yds = sum(safe_float(r.get('rushTotalYds')) for r in team_rushing)
        total_rush_tds = sum(safe_float(r.get('rushTotalTDs')) for r in team_rushing)
        
        rushers_sorted = sorted(
            [(safe_float(r.get('rushTotalAtt')), r.get('player__fullName', ''), r.get('player__position', '')) 
             for r in team_rushing],
            reverse=True
        )
        
        if rushers_sorted:
            usage_data['rb1_rushes'] = rushers_sorted[0][0] if len(rushers_sorted) > 0 else 0
            usage_data['rb1_name'] = rushers_sorted[0][1] if len(rushers_sorted) > 0 else ''
            usage_data['rb1_position'] = rushers_sorted[0][2] if len(rushers_sorted) > 0 else ''
            usage_data['rb1_share'] = (rushers_sorted[0][0] / total_rushes * 100) if total_rushes > 0 and len(rushers_sorted) > 0 else 0
            
            usage_data['rb2_rushes'] = rushers_sorted[1][0] if len(rushers_sorted) > 1 else 0
            usage_data['rb2_share'] = (rushers_sorted[1][0] / total_rushes * 100) if total_rushes > 0 and len(rushers_sorted) > 1 else 0
            
            usage_data['rbbc'] = usage_data['rb1_share'] < 60 and usage_data['rb2_share'] > 25
        else:
            usage_data['rb1_rushes'] = 0
            usage_data['rb1_name'] = ''
            usage_data['rb1_position'] = ''
            usage_data['rb1_share'] = 0
            usage_data['rb2_rushes'] = 0
            usage_data['rb2_share'] = 0
            usage_data['rbbc'] = False
        
        rush_shares = [safe_float(r.get('rushTotalAtt')) / total_rushes for r in team_rushing if total_rushes > 0]
        usage_data['rush_concentration'] = calculate_herfindahl_index(rush_shares) * 10000
        
        usage_data['pass_distribution_style'] = 'Concentrated' if usage_data['pass_concentration'] > 1500 else ('Balanced' if usage_data['pass_concentration'] > 1000 else 'Spread')
        usage_data['rush_distribution_style'] = 'Bellcow' if usage_data['rb1_share'] > 70 else ('RBBC' if usage_data['rbbc'] else 'Feature Back')
        
        team_usage.append(usage_data)
    
    output_dir = base_path / 'output'
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / 'team_player_usage.csv'
    
    if team_usage:
        fieldnames = list(team_usage[0].keys())
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(team_usage)
        
        print(f"\n✓ Saved player usage data to: {output_file}")
        print(f"  Teams processed: {len(team_usage)}")
        print(f"  Metrics calculated: {len(fieldnames)}")
        
        print("\nSample metrics:")
        for i, metric in enumerate(['wr1_share', 'te_target_share', 'rb1_share', 'pass_concentration', 'rush_concentration'], 1):
            print(f"  {i}. {metric}")
    
    return team_usage

if __name__ == '__main__':
    base_path = Path(__file__).parent.parent
    print(f"Working directory: {base_path}\n")
    
    df = aggregate_player_usage(base_path)
    
    print("\n✓ Done! Use team_player_usage.csv for player usage visualizations.")
