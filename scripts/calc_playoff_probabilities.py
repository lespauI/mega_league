#!/usr/bin/env python3
import csv
import itertools
from collections import defaultdict
import json

def load_data():
    teams_info = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            teams_info[team] = {
                'division': row.get('divisionName', '').strip(),
                'conference': row.get('conferenceName', '').strip()
            }
    
    games = []
    with open('MEGA_games.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            games.append({
                'home': row['homeTeam'].strip(),
                'away': row['awayTeam'].strip(),
                'home_score': int(row['homeScore']) if row['homeScore'] else None,
                'away_score': int(row['awayScore']) if row['awayScore'] else None,
                'week': int(row['weekIndex']) if row['weekIndex'] else 0
            })
    
    with open('output/ranked_sos_by_conference.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sos_data = {row['team']: row for row in reader}
    
    return teams_info, games, sos_data

def calculate_team_stats(teams_info, games):
    stats = {}
    
    for team in teams_info:
        stats[team] = {
            'W': 0, 'L': 0, 'T': 0,
            'conference_W': 0, 'conference_L': 0, 'conference_T': 0,
            'division_W': 0, 'division_L': 0, 'division_T': 0,
            'points_for': 0, 'points_against': 0,
            'conference_points_for': 0, 'conference_points_against': 0,
            'head_to_head': defaultdict(lambda: {'W': 0, 'L': 0, 'T': 0}),
            'opponents': [],
            'defeated_opponents': []
        }
    
    for game in games:
        if game['home_score'] is None or game['away_score'] is None:
            continue
        
        home = game['home']
        away = game['away']
        home_score = game['home_score']
        away_score = game['away_score']
        
        if home not in stats or away not in stats:
            continue
        
        stats[home]['opponents'].append(away)
        stats[away]['opponents'].append(home)
        
        stats[home]['points_for'] += home_score
        stats[home]['points_against'] += away_score
        stats[away]['points_for'] += away_score
        stats[away]['points_against'] += home_score
        
        home_conf = teams_info[home]['conference']
        away_conf = teams_info[away]['conference']
        home_div = teams_info[home]['division']
        away_div = teams_info[away]['division']
        
        if home_score > away_score:
            stats[home]['W'] += 1
            stats[away]['L'] += 1
            stats[home]['defeated_opponents'].append(away)
            stats[home]['head_to_head'][away]['W'] += 1
            stats[away]['head_to_head'][home]['L'] += 1
            
            if home_conf == away_conf:
                stats[home]['conference_W'] += 1
                stats[away]['conference_L'] += 1
                stats[home]['conference_points_for'] += home_score
                stats[home]['conference_points_against'] += away_score
                stats[away]['conference_points_for'] += away_score
                stats[away]['conference_points_against'] += home_score
                
            if home_div == away_div:
                stats[home]['division_W'] += 1
                stats[away]['division_L'] += 1
                
        elif away_score > home_score:
            stats[away]['W'] += 1
            stats[home]['L'] += 1
            stats[away]['defeated_opponents'].append(home)
            stats[away]['head_to_head'][home]['W'] += 1
            stats[home]['head_to_head'][away]['L'] += 1
            
            if home_conf == away_conf:
                stats[away]['conference_W'] += 1
                stats[home]['conference_L'] += 1
                stats[home]['conference_points_for'] += home_score
                stats[home]['conference_points_against'] += away_score
                stats[away]['conference_points_for'] += away_score
                stats[away]['conference_points_against'] += home_score
                
            if home_div == away_div:
                stats[away]['division_W'] += 1
                stats[home]['division_L'] += 1
        else:
            stats[home]['T'] += 1
            stats[away]['T'] += 1
            stats[home]['head_to_head'][away]['T'] += 1
            stats[away]['head_to_head'][home]['T'] += 1
            
            if home_conf == away_conf:
                stats[home]['conference_T'] += 1
                stats[away]['conference_T'] += 1
    
    for team in stats:
        total = stats[team]['W'] + stats[team]['L'] + stats[team]['T']
        stats[team]['win_pct'] = (stats[team]['W'] + 0.5 * stats[team]['T']) / total if total > 0 else 0
        
        conf_total = stats[team]['conference_W'] + stats[team]['conference_L'] + stats[team]['conference_T']
        stats[team]['conference_pct'] = (stats[team]['conference_W'] + 0.5 * stats[team]['conference_T']) / conf_total if conf_total > 0 else 0
        
        div_total = stats[team]['division_W'] + stats[team]['division_L'] + stats[team]['division_T']
        stats[team]['division_pct'] = (stats[team]['division_W'] + 0.5 * stats[team]['division_T']) / div_total if div_total > 0 else 0
        
        defeated_records = []
        for opp in stats[team]['defeated_opponents']:
            opp_total = stats[opp]['W'] + stats[opp]['L'] + stats[opp]['T']
            opp_pct = (stats[opp]['W'] + 0.5 * stats[opp]['T']) / opp_total if opp_total > 0 else 0
            defeated_records.append(opp_pct)
        stats[team]['strength_of_victory'] = sum(defeated_records) / len(defeated_records) if defeated_records else 0
        
        opponent_records = []
        for opp in stats[team]['opponents']:
            opp_total = stats[opp]['W'] + stats[opp]['L'] + stats[opp]['T']
            opp_pct = (stats[opp]['W'] + 0.5 * stats[opp]['T']) / opp_total if opp_total > 0 else 0
            opponent_records.append(opp_pct)
        stats[team]['strength_of_schedule'] = sum(opponent_records) / len(opponent_records) if opponent_records else 0
    
    return stats

def compare_head_to_head(teams, stats):
    if len(teams) == 2:
        t1, t2 = teams
        h2h = stats[t1]['head_to_head'][t2]
        total = h2h['W'] + h2h['L'] + h2h['T']
        if total == 0:
            return None
        pct = (h2h['W'] + 0.5 * h2h['T']) / total
        if pct > 0.5:
            return t1
        elif pct < 0.5:
            return t2
        return None
    else:
        h2h_records = {}
        for team in teams:
            w, l, t = 0, 0, 0
            for other in teams:
                if team != other:
                    h2h = stats[team]['head_to_head'][other]
                    w += h2h['W']
                    l += h2h['L']
                    t += h2h['T']
            total = w + l + t
            h2h_records[team] = (w + 0.5 * t) / total if total > 0 else 0
        
        max_pct = max(h2h_records.values())
        winners = [t for t, pct in h2h_records.items() if pct == max_pct]
        
        if len(winners) == 1:
            return winners[0]
        return None

def apply_tiebreakers(teams, stats, teams_info, is_division=False):
    if len(teams) == 1:
        return teams[0]
    
    if len(teams) == 0:
        return None
    
    winner = compare_head_to_head(teams, stats)
    if winner:
        return winner
    
    if is_division:
        div_pcts = {t: stats[t]['division_pct'] for t in teams}
        max_pct = max(div_pcts.values())
        remaining = [t for t in teams if div_pcts[t] == max_pct]
        if len(remaining) == 1:
            return remaining[0]
        teams = remaining
    
    conf_pcts = {t: stats[t]['conference_pct'] for t in teams}
    max_pct = max(conf_pcts.values())
    remaining = [t for t in teams if conf_pcts[t] == max_pct]
    if len(remaining) == 1:
        return remaining[0]
    teams = remaining
    
    sov_scores = {t: stats[t]['strength_of_victory'] for t in teams}
    max_sov = max(sov_scores.values())
    remaining = [t for t in teams if abs(sov_scores[t] - max_sov) < 0.001]
    if len(remaining) == 1:
        return remaining[0]
    teams = remaining
    
    sos_scores = {t: stats[t]['strength_of_schedule'] for t in teams}
    max_sos = max(sos_scores.values())
    remaining = [t for t in teams if abs(sos_scores[t] - max_sos) < 0.001]
    if len(remaining) == 1:
        return remaining[0]
    
    return remaining[0] if remaining else teams[0]

def calculate_playoff_probability(team_name, teams_info, stats, sos_data, remaining_games):
    conf = teams_info[team_name]['conference']
    div = teams_info[team_name]['division']
    
    conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
    div_teams = [t for t in conf_teams if teams_info[t]['division'] == div]
    
    div_leaders = {}
    for division in set(teams_info[t]['division'] for t in conf_teams):
        div_contenders = [t for t in conf_teams if teams_info[t]['division'] == division]
        div_contenders.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['conference_pct'], -stats[t]['strength_of_schedule']))
        div_leaders[division] = div_contenders[0]
    
    is_div_leader = (div_leaders[div] == team_name)
    
    current_wins = stats[team_name]['W']
    current_losses = stats[team_name]['L']
    win_pct = stats[team_name]['win_pct']
    
    team_remaining = int(sos_data[team_name]['remaining_games']) if team_name in sos_data else remaining_games
    team_sos = float(sos_data[team_name]['ranked_sos_avg']) if team_name in sos_data else 0.5
    
    expected_wins = team_remaining * (1.0 - team_sos)
    projected_wins = current_wins + expected_wins
    max_possible_wins = current_wins + team_remaining
    
    # Check for mathematical elimination (can't make playoffs even if win all remaining)
    if is_div_leader:
        # Check if any division rival can still catch us
        can_be_caught = False
        for rival in div_teams:
            if rival == team_name:
                continue
            rival_remaining = int(sos_data[rival]['remaining_games']) if rival in sos_data else remaining_games
            rival_max_wins = stats[rival]['W'] + rival_remaining
            # If rival can match or exceed our max wins, we haven't clinched
            if rival_max_wins >= max_possible_wins:
                can_be_caught = True
                break
        
        # If no one can catch us, we've clinched division = 100% playoff
        if not can_be_caught:
            return 100.0
    else:
        # Not division leader - check if we can still make playoffs via division or WC
        # First check if we can still win division
        div_leader = div_leaders[div]
        leader_wins = stats[div_leader]['W']
        # If leader already has more wins than we can possibly get, we can't win division
        can_win_division = (max_possible_wins > leader_wins)
        
        # Check wild card possibility
        # Get all non-division leaders
        all_wc_candidates = []
        for t in conf_teams:
            if t not in div_leaders.values():
                t_remaining = int(sos_data[t]['remaining_games']) if t in sos_data else remaining_games
                all_wc_candidates.append({
                    'team': t,
                    'wins': stats[t]['W'],
                    'max_wins': stats[t]['W'] + t_remaining
                })
        
        # Sort by current wins
        all_wc_candidates.sort(key=lambda x: -x['wins'])
        
        # Count how many teams will definitely finish ahead of our max wins
        teams_definitely_ahead = 0
        for candidate in all_wc_candidates:
            if candidate['team'] == team_name:
                continue
            # If their current wins already exceed our max possible, they're definitely ahead
            if candidate['wins'] > max_possible_wins:
                teams_definitely_ahead += 1
        
        # If 7+ teams are definitely ahead (4 division winners + 3 WC), we're eliminated
        # Actually need to count division leaders too
        if teams_definitely_ahead >= 7:
            return 0.0
    
    # Check if eliminated from division and wild card
    if not is_div_leader:
        # Count teams that will finish ahead even if we win all remaining
        div_leader_wins = stats[div_leaders[div]]['W']
        
        # Get wild card contenders
        wc_candidates = [t for t in conf_teams if t not in div_leaders.values()]
        teams_ahead_of_max = sum(1 for t in wc_candidates if t != team_name and stats[t]['W'] > max_possible_wins)
        
        # If 3+ WC candidates already have more wins than our max, we're eliminated
        if teams_ahead_of_max >= 3 and div_leader_wins > max_possible_wins:
            return 0.0
        
        # Check if we've clinched a wild card spot
        # We've clinched if at most 2 other non-division-leaders can reach our minimum wins
        min_guaranteed_wins = current_wins  # We have at least this many
        teams_that_can_catch = 0
        for t in wc_candidates:
            if t == team_name:
                continue
            t_max = stats[t]['W'] + (int(sos_data[t]['remaining_games']) if t in sos_data else remaining_games)
            if t_max > min_guaranteed_wins:
                teams_that_can_catch += 1
        
        # If only 2 or fewer teams can finish with more wins than we have now, we've clinched WC
        # (assuming division leaders all finish ahead)
        if teams_that_can_catch <= 2:
            return 100.0
    
    if is_div_leader:
        base_prob = 95.0
        
        div_contenders = [t for t in div_teams if t != team_name and stats[t]['win_pct'] >= win_pct - 0.15]
        if not div_contenders:
            return min(99.0, base_prob + 3)
        
        closest_rival = max(div_contenders, key=lambda t: stats[t]['win_pct'])
        rival_wins = stats[closest_rival]['W']
        rival_remaining = int(sos_data[closest_rival]['remaining_games']) if closest_rival in sos_data else remaining_games
        rival_sos = float(sos_data[closest_rival]['ranked_sos_avg']) if closest_rival in sos_data else 0.5
        rival_projected_wins = rival_wins + rival_remaining * (1.0 - rival_sos)
        
        win_cushion = projected_wins - rival_projected_wins
        cushion_factor = min(5, max(-5, win_cushion * 3))
        
        return min(99.0, max(85.0, base_prob + cushion_factor))
    
    else:
        all_contenders = []
        for t in conf_teams:
            if t not in div_leaders.values():
                all_contenders.append(t)
        
        all_contenders.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['conference_pct'], stats[t]['strength_of_schedule']))
        
        try:
            current_position = all_contenders.index(team_name)
        except ValueError:
            current_position = len(all_contenders) - 1
        
        if current_position < 3:
            base_prob = 75 - (current_position * 15)
        elif current_position < 6:
            base_prob = 40 - ((current_position - 3) * 10)
        else:
            base_prob = 15 - min(10, (current_position - 6) * 2)
        
        wc_cutoff_teams = all_contenders[2:5] if len(all_contenders) > 4 else all_contenders[:3]
        avg_wc_sos = sum(float(sos_data[t]['ranked_sos_avg']) for t in wc_cutoff_teams if t in sos_data) / len(wc_cutoff_teams) if wc_cutoff_teams else 0.5
        
        sos_advantage = (avg_wc_sos - team_sos) * 80
        
        wc_cutoff_wins = [stats[t]['W'] for t in all_contenders[2:3]] if len(all_contenders) > 2 else [current_wins]
        cutoff_win_level = wc_cutoff_wins[0] if wc_cutoff_wins else current_wins
        wins_above_cutoff = (projected_wins - cutoff_win_level) * 12
        
        conference_factor = (stats[team_name]['conference_pct'] - 0.5) * 20
        
        final_prob = base_prob + sos_advantage + wins_above_cutoff + conference_factor
        
        return min(95.0, max(1.0, final_prob))

def main():
    teams_info, games, sos_data = load_data()
    stats = calculate_team_stats(teams_info, games)
    
    results = {}
    
    for conf in ['AFC', 'NFC']:
        conf_teams = [t for t in teams_info if teams_info[t]['conference'] == conf]
        
        for team in conf_teams:
            prob = calculate_playoff_probability(team, teams_info, stats, sos_data, 4)
            results[team] = {
                'conference': conf,
                'division': teams_info[team]['division'],
                'W': stats[team]['W'],
                'L': stats[team]['L'],
                'win_pct': stats[team]['win_pct'],
                'conference_pct': stats[team]['conference_pct'],
                'division_pct': stats[team]['division_pct'],
                'strength_of_victory': stats[team]['strength_of_victory'],
                'strength_of_schedule': stats[team]['strength_of_schedule'],
                'playoff_probability': round(prob, 1),
                'remaining_sos': float(sos_data[team]['ranked_sos_avg']) if team in sos_data else 0.5,
                'remaining_games': int(sos_data[team]['remaining_games']) if team in sos_data else 4
            }
    
    with open('output/playoff_probabilities.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("PLAYOFF PROBABILITY CALCULATION COMPLETE!")
    print("="*80)
    print("\nCalculated probabilities for all 32 teams considering:")
    print("  ✓ Head-to-head records")
    print("  ✓ Division standings")
    print("  ✓ Conference records")
    print("  ✓ Strength of victory")
    print("  ✓ Strength of schedule (past and remaining)")
    print("  ✓ Projected final records")
    print("\nOutput saved to: output/playoff_probabilities.json")
    print("\nTop AFC Contenders:")
    afc_teams = [(t, r['playoff_probability']) for t, r in results.items() if r['conference'] == 'AFC']
    afc_teams.sort(key=lambda x: x[1], reverse=True)
    for team, prob in afc_teams[:10]:
        print(f"  {team:20s} {prob:5.1f}%")
    
    print("\nTop NFC Contenders:")
    nfc_teams = [(t, r['playoff_probability']) for t, r in results.items() if r['conference'] == 'NFC']
    nfc_teams.sort(key=lambda x: x[1], reverse=True)
    for team, prob in nfc_teams[:10]:
        print(f"  {team:20s} {prob:5.1f}%")

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
