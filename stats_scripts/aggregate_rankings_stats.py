#!/usr/bin/env python3
"""
Aggregate team rankings and statistics for correlation analysis.
Combines MEGA_rankings.csv and MEGA_teams.csv data.
"""

from pathlib import Path
from collections import defaultdict
import csv

from stats_common import load_csv, safe_float, normalize_team_display

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

    # Load team-level aggregated stats (player-based) and Elo ratings
    team_stats_rows = load_csv(base_path / 'output' / 'team_aggregated_stats.csv')
    
    elo_map = {}
    elo_path = base_path / 'mega_elo.csv'
    try:
        with elo_path.open('r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            header = next(reader, None)
            for row in reader:
                if not row or len(row) < 5:
                    continue
                team_name = normalize_team_display(row[2])
                if not team_name or team_name.lower() == 'team':
                    continue
                start_raw = row[4].strip()
                elo_start = safe_float(start_raw, 0.0) if start_raw else 0.0
                elo_index = safe_int(row[0])
                elo_map[team_name] = {
                    'eloIndex': elo_index,
                    'eloStart': elo_start,
                }
    except FileNotFoundError:
        elo_map = {}
    
    # Create team lookup
    teams_map = {}
    for t in teams:
        name = normalize_team_display(t.get('displayName', ''))
        if name:
            teams_map[name] = t
    
    # Map of aggregated team stats keyed by canonical team name
    team_stats_map = {}
    for s in team_stats_rows:
        name = normalize_team_display(s.get('team', ''))
        if name:
            team_stats_map[name] = s
    
    # Get latest rankings (highest week)
    latest_rankings = {}
    for r in rankings:
        team = normalize_team_display(r.get('team', ''))
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
        team = normalize_team_display(r.get('team', ''))
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
        
        # Calculate games and home/away win percentages
        home_games = row['homeWins'] + row['homeLosses']
        away_games = row['awayWins'] + row['awayLosses']
        row['homeWinPct'] = row['homeWins'] / home_games if home_games > 0 else 0
        row['awayWinPct'] = row['awayWins'] / away_games if away_games > 0 else 0
        row['games'] = row['totalWins'] + row['totalLosses'] + row['totalTies']
        
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
        
        # Add Elo ratings if available
        elo = elo_map.get(team_name, {})
        row['eloIndex'] = elo.get('eloIndex', 0)
        row['eloStart'] = elo.get('eloStart', 0.0)
        
        # Merge in player-based aggregated team stats where available,
        # without overwriting existing keys.
        agg_stats = team_stats_map.get(team_name)
        if agg_stats:
            for key, value in agg_stats.items():
                if key not in row:
                    row[key] = value
        
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
        
        # Per-game rates (guard for missing games)
        g = row['games'] if row['games'] > 0 else 0
        row['offTotalYdsPg'] = (row['offTotalYds'] / g) if g else 0
        row['defTotalYdsPg'] = (row['defTotalYds'] / g) if g else 0
        row['ptsForPg'] = (row['ptsFor'] / g) if g else 0
        row['ptsAgainstPg'] = (row['ptsAgainst'] / g) if g else 0
        row['netPtsPg'] = (row['netPts'] / g) if g else 0
        row['tODiffPerGame'] = (row['tODiff'] / g) if g else 0

        # Scoring efficiency variants
        row['ptsPer100Yds'] = (row['ptsFor'] / row['offTotalYds'] * 100) if row['offTotalYds'] > 0 else 0
        row['oppPtsPer100Yds'] = (row['ptsAgainst'] / row['defTotalYds'] * 100) if row['defTotalYds'] > 0 else 0

        # Pass share of offense
        row['passShare'] = (row['offPassYds'] / row['offTotalYds']) if row['offTotalYds'] > 0 else 0
        row['rushShare'] = (row['offRushYds'] / row['offTotalYds']) if row['offTotalYds'] > 0 else 0

        # Cap efficiency
        if row['capSpent'] > 0:
            row['winsPerMillion'] = row['totalWins'] / (row['capSpent'] / 1000000)
            row['ovrPerMillion'] = row['teamOvr'] / (row['capSpent'] / 1000000)
        else:
            row['winsPerMillion'] = 0
            row['ovrPerMillion'] = 0

        # Pythagorean expectation (NFL commonly ~2.3-2.37)
        try:
            exp = 2.37
            pf = float(row['ptsFor'])
            pa = float(row['ptsAgainst'])
            denom = (pf ** exp + pa ** exp)
            row['pythExpWinPct'] = (pf ** exp) / denom if denom > 0 else 0
        except Exception:
            row['pythExpWinPct'] = 0
        row['pythOverUnder'] = row['winPct'] - row.get('pythExpWinPct', 0)
        
        # Rank efficiency (lower is better for ranks)
        row['ptsRankEfficiency'] = row['ptsForRank'] - row['offTotalYdsRank'] if row['ptsForRank'] and row['offTotalYdsRank'] else 0
        row['defRankEfficiency'] = row['defTotalYdsRank'] - row['ptsAgainstRank'] if row['defTotalYdsRank'] and row['ptsAgainstRank'] else 0
        
        combined_stats.append(row)
    
    # Output directory
    output_dir = base_path / 'output'
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / 'team_rankings_stats.csv'
    
    if combined_stats:
        # Compute z-scores for select per-game metrics
        def mean_std(values):
            vals = [v for v in values if isinstance(v, (int, float))]
            if not vals:
                return 0.0, 1.0
            m = sum(vals) / len(vals)
            var = sum((x - m) ** 2 for x in vals) / len(vals)
            s = var ** 0.5
            return m, (s if s > 1e-9 else 1.0)

        off_ppg_mean, off_ppg_std = mean_std([r['ptsForPg'] for r in combined_stats])
        def_ppg_mean, def_ppg_std = mean_std([r['ptsAgainstPg'] for r in combined_stats])

        for r in combined_stats:
            r['offenseIndexZ'] = (r['ptsForPg'] - off_ppg_mean) / off_ppg_std
            # Defense better when allowing fewer points; invert sign so higher is better
            r['defenseIndexZ'] = (def_ppg_mean - r['ptsAgainstPg']) / def_ppg_std
            r['teamStrengthIndex'] = r['offenseIndexZ'] + r['defenseIndexZ']
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
            'offTotalYdsPg', 'defTotalYdsPg', 'ptsForPg', 'ptsAgainstPg',
            'netPtsPg', 'tODiffPerGame', 'winPct', 'combinedRank',
            'ptsPer100Yds', 'oppPtsPer100Yds', 'passShare', 'pythExpWinPct',
            'pythOverUnder', 'teamStrengthIndex'
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
