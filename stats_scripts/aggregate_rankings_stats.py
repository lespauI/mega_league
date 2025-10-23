#!/usr/bin/env python3
"""
Aggregate team rankings and statistics for correlation analysis.
Combines MEGA_rankings.csv and MEGA_teams.csv data.
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

def safe_int(value, default=0):
    """Safely convert to int."""
    try:
        return int(value) if value and value != '' else default
    except (ValueError, TypeError):
        return default

def aggregate_rankings_stats(base_path):
    """Aggregate rankings and team statistics."""
    
    print("Loading data files...")
    
    # Load data
    rankings = load_csv(base_path / 'MEGA_rankings.csv')
    teams = load_csv(base_path / 'MEGA_teams.csv')
    
    # Create team lookup
    teams_map = {}
    for t in teams:
        if t.get('displayName'):
            teams_map[t['displayName']] = t
    
    # Get latest rankings (highest week)
    latest_rankings = {}
    for r in rankings:
        team = r.get('team')
        week = safe_int(r.get('weekIndex', 0))
        if team:
            if team not in latest_rankings or week > latest_rankings[team]['weekIndex']:
                latest_rankings[team] = {
                    'weekIndex': week,
                    'rank': safe_int(r.get('rank')),
                    'offTotalYdsRank': safe_int(r.get('offTotalYdsRank')),
                    'defTotalYdsRank': safe_int(r.get('defTotalYdsRank')),
                    'offPassYdsRank': safe_int(r.get('offPassYdsRank')),
                    'offRushYdsRank': safe_int(r.get('offRushYdsRank')),
                    'defPassYdsRank': safe_int(r.get('defPassYdsRank')),
                    'defRushYdsRank': safe_int(r.get('defRushYdsRank')),
                    'ptsForRank': safe_int(r.get('ptsForRank')),
                    'ptsAgainstRank': safe_int(r.get('ptsAgainstRank')),
                }
    
    # Track week-to-week changes
    rank_changes = defaultdict(list)
    for r in rankings:
        team = r.get('team')
        if team:
            rank_changes[team].append({
                'week': safe_int(r.get('weekIndex')),
                'rank': safe_int(r.get('rank')),
                'offRank': safe_int(r.get('offTotalYdsRank')),
                'defRank': safe_int(r.get('defTotalYdsRank')),
            })
    
    # Calculate rank volatility and trends
    for team in rank_changes:
        weeks = sorted(rank_changes[team], key=lambda x: x['week'])
        if len(weeks) > 1:
            ranks = [w['rank'] for w in weeks if w['rank'] > 0]
            if ranks:
                # Calculate standard deviation
                mean = sum(ranks) / len(ranks)
                variance = sum((r - mean) ** 2 for r in ranks) / len(ranks)
                std_dev = variance ** 0.5
                
                # Early vs late season
                mid_point = len(weeks) // 2
                early_ranks = [w['rank'] for w in weeks[:mid_point] if w['rank'] > 0]
                late_ranks = [w['rank'] for w in weeks[mid_point:] if w['rank'] > 0]
                
                early_avg = sum(early_ranks) / len(early_ranks) if early_ranks else 0
                late_avg = sum(late_ranks) / len(late_ranks) if late_ranks else 0
                
                latest_rankings[team]['rankVolatility'] = std_dev
                latest_rankings[team]['earlySeasonRank'] = early_avg
                latest_rankings[team]['lateSeasonRank'] = late_avg
                latest_rankings[team]['rankImprovement'] = early_avg - late_avg
    
    # Combine with team stats
    combined_stats = []
    
    for team_name, team_data in teams_map.items():
        row = {'team': team_name}
        
        # Add team metadata
        row['logoId'] = team_data.get('logoId', '')
        row['conference'] = team_data.get('conferenceName', '')
        row['division'] = team_data.get('divisionName', team_data.get('divName', ''))
        row['teamOvr'] = safe_int(team_data.get('teamOvr', team_data.get('ovrRating', 0)))
        
        # Record
        row['totalWins'] = safe_int(team_data.get('totalWins'))
        row['totalLosses'] = safe_int(team_data.get('totalLosses'))
        row['totalTies'] = safe_int(team_data.get('totalTies'))
        row['winPct'] = safe_float(team_data.get('winPct'))
        
        # Home/Away splits
        row['homeWins'] = safe_int(team_data.get('homeWins'))
        row['homeLosses'] = safe_int(team_data.get('homeLosses'))
        row['awayWins'] = safe_int(team_data.get('awayWins'))
        row['awayLosses'] = safe_int(team_data.get('awayLosses'))
        
        # Calculate home/away win percentages
        home_games = row['homeWins'] + row['homeLosses']
        away_games = row['awayWins'] + row['awayLosses']
        row['homeWinPct'] = row['homeWins'] / home_games if home_games > 0 else 0
        row['awayWinPct'] = row['awayWins'] / away_games if away_games > 0 else 0
        
        # Raw offensive stats
        row['offPassYds'] = safe_int(team_data.get('offPassYds'))
        row['offRushYds'] = safe_int(team_data.get('offRushYds'))
        row['offTotalYds'] = safe_int(team_data.get('offTotalYds'))
        
        # Raw defensive stats
        row['defPassYds'] = safe_int(team_data.get('defPassYds'))
        row['defRushYds'] = safe_int(team_data.get('defRushYds'))
        row['defTotalYds'] = safe_int(team_data.get('defTotalYds'))
        
        # Points
        row['ptsFor'] = safe_int(team_data.get('ptsFor'))
        row['ptsAgainst'] = safe_int(team_data.get('ptsAgainst'))
        row['netPts'] = safe_int(team_data.get('netPts'))
        
        # Turnovers
        row['tODiff'] = safe_int(team_data.get('tODiff'))
        
        # Cap space
        row['capSpent'] = safe_int(team_data.get('capSpent'))
        row['capAvailable'] = safe_int(team_data.get('capAvailable'))
        
        # Schemes
        row['offScheme'] = safe_int(team_data.get('offScheme'))
        row['defScheme'] = safe_int(team_data.get('defScheme'))
        
        # Add rankings if available
        if team_name in latest_rankings:
            rank_data = latest_rankings[team_name]
            row['rank'] = rank_data['rank']
            row['offTotalYdsRank'] = rank_data['offTotalYdsRank']
            row['defTotalYdsRank'] = rank_data['defTotalYdsRank']
            row['offPassYdsRank'] = rank_data['offPassYdsRank']
            row['offRushYdsRank'] = rank_data['offRushYdsRank']
            row['defPassYdsRank'] = rank_data['defPassYdsRank']
            row['defRushYdsRank'] = rank_data['defRushYdsRank']
            row['ptsForRank'] = rank_data['ptsForRank']
            row['ptsAgainstRank'] = rank_data['ptsAgainstRank']
            
            # Volatility metrics
            row['rankVolatility'] = rank_data.get('rankVolatility', 0)
            row['earlySeasonRank'] = rank_data.get('earlySeasonRank', 0)
            row['lateSeasonRank'] = rank_data.get('lateSeasonRank', 0)
            row['rankImprovement'] = rank_data.get('rankImprovement', 0)
        else:
            # Default rankings if not found
            row['rank'] = 0
            row['offTotalYdsRank'] = 0
            row['defTotalYdsRank'] = 0
            row['offPassYdsRank'] = 0
            row['offRushYdsRank'] = 0
            row['defPassYdsRank'] = 0
            row['defRushYdsRank'] = 0
            row['ptsForRank'] = 0
            row['ptsAgainstRank'] = 0
            row['rankVolatility'] = 0
            row['earlySeasonRank'] = 0
            row['lateSeasonRank'] = 0
            row['rankImprovement'] = 0
        
        # Calculate derived metrics
        
        # Balance metrics
        row['offDefRankDiff'] = row['offTotalYdsRank'] - row['defTotalYdsRank'] if row['offTotalYdsRank'] and row['defTotalYdsRank'] else 0
        row['combinedRank'] = (row['offTotalYdsRank'] + row['defTotalYdsRank']) / 2 if row['offTotalYdsRank'] and row['defTotalYdsRank'] else 0
        
        # Pass/Rush balance
        row['offPassRushDiff'] = row['offPassYdsRank'] - row['offRushYdsRank'] if row['offPassYdsRank'] and row['offRushYdsRank'] else 0
        row['defPassRushDiff'] = row['defPassYdsRank'] - row['defRushYdsRank'] if row['defPassYdsRank'] and row['defRushYdsRank'] else 0
        
        # Efficiency metrics
        if row['ptsFor'] > 0:
            row['offYdsPerPt'] = row['offTotalYds'] / row['ptsFor']
        else:
            row['offYdsPerPt'] = 0
            
        if row['ptsAgainst'] > 0:
            row['defYdsPerPt'] = row['defTotalYds'] / row['ptsAgainst']
        else:
            row['defYdsPerPt'] = 0
        
        # Pass/rush ratios
        if row['offRushYds'] > 0:
            row['passRushRatio'] = row['offPassYds'] / row['offRushYds']
        else:
            row['passRushRatio'] = 0
            
        if row['defRushYds'] > 0:
            row['defPassRushRatio'] = row['defPassYds'] / row['defRushYds']
        else:
            row['defPassRushRatio'] = 0
        
        # Yardage balance
        total_off_def_yds = row['offTotalYds'] + row['defTotalYds']
        if total_off_def_yds > 0:
            row['offYdsPct'] = row['offTotalYds'] / total_off_def_yds * 100
            row['defYdsPct'] = row['defTotalYds'] / total_off_def_yds * 100
        else:
            row['offYdsPct'] = 0
            row['defYdsPct'] = 0
        
        # Cap efficiency
        if row['capSpent'] > 0:
            row['winsPerMillion'] = row['totalWins'] / (row['capSpent'] / 1000000)
            row['ovrPerMillion'] = row['teamOvr'] / (row['capSpent'] / 1000000)
        else:
            row['winsPerMillion'] = 0
            row['ovrPerMillion'] = 0
        
        # Rank efficiency (lower is better for ranks)
        row['ptsRankEfficiency'] = row['ptsForRank'] - row['offTotalYdsRank'] if row['ptsForRank'] and row['offTotalYdsRank'] else 0
        row['defRankEfficiency'] = row['defTotalYdsRank'] - row['ptsAgainstRank'] if row['defTotalYdsRank'] and row['ptsAgainstRank'] else 0
        
        combined_stats.append(row)
    
    # Output directory
    output_dir = base_path / 'output'
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / 'team_rankings_stats.csv'
    
    if combined_stats:
        # Sort by overall rank
        combined_stats.sort(key=lambda x: x.get('rank', 99))
        
        fieldnames = list(combined_stats[0].keys())
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(combined_stats)
        
        print(f"\n✓ Saved combined rankings and stats to: {output_file}")
        print(f"  Teams processed: {len(combined_stats)}")
        print(f"  Metrics calculated: {len(fieldnames)}")
        
        print("\nSample metrics available:")
        key_metrics = [
            'rank', 'offTotalYdsRank', 'defTotalYdsRank',
            'offTotalYds', 'defTotalYds', 'ptsFor', 'ptsAgainst',
            'netPts', 'tODiff', 'winPct', 'combinedRank',
            'offYdsPerPt', 'defYdsPerPt', 'passRushRatio'
        ]
        for metric in key_metrics:
            if metric in fieldnames:
                print(f"  • {metric}")
    
    return combined_stats

if __name__ == '__main__':
    base_path = Path(__file__).parent.parent
    print(f"Working directory: {base_path}\n")
    
    stats = aggregate_rankings_stats(base_path)
    
    print("\n✓ Done! Use team_rankings_stats.csv for visualizations.")