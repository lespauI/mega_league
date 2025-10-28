#!/usr/bin/env python3
from collections import defaultdict

def apply_division_tiebreaker(tied_teams, stats, teams_info):
    if len(tied_teams) == 0:
        return []
    if len(tied_teams) == 1:
        return tied_teams
    
    original_count = len(tied_teams)
    
    if len(tied_teams) == 2:
        winner = break_two_team_division_tie(tied_teams, stats, teams_info)
        return [winner]
    else:
        ranked = break_multi_team_division_tie(tied_teams, stats, teams_info)
        return ranked

def break_two_team_division_tie(teams, stats, teams_info):
    team1, team2 = teams[0], teams[1]
    
    h2h1 = stats[team1]['head_to_head'].get(team2, {'W': 0, 'L': 0, 'T': 0})
    h2h_total = h2h1['W'] + h2h1['L'] + h2h1['T']
    if h2h_total > 0:
        h2h1_pct = (h2h1['W'] + 0.5 * h2h1['T']) / h2h_total
        h2h2_pct = (h2h1['L'] + 0.5 * h2h1['T']) / h2h_total
        if h2h1_pct > h2h2_pct:
            return team1
        elif h2h2_pct > h2h1_pct:
            return team2
    
    if stats[team1]['division_pct'] > stats[team2]['division_pct']:
        return team1
    elif stats[team2]['division_pct'] > stats[team1]['division_pct']:
        return team2
    
    common_opps = set(stats[team1]['opponents']) & set(stats[team2]['opponents'])
    if len(common_opps) >= 4:
        common1_w = sum(1 for g in stats[team1]['game_results'] if g['opponent'] in common_opps and g['pf'] > g['pa'])
        common1_l = sum(1 for g in stats[team1]['game_results'] if g['opponent'] in common_opps and g['pf'] < g['pa'])
        common1_t = sum(1 for g in stats[team1]['game_results'] if g['opponent'] in common_opps and g['pf'] == g['pa'])
        common1_total = common1_w + common1_l + common1_t
        common1_pct = (common1_w + 0.5 * common1_t) / common1_total if common1_total > 0 else 0
        
        common2_w = sum(1 for g in stats[team2]['game_results'] if g['opponent'] in common_opps and g['pf'] > g['pa'])
        common2_l = sum(1 for g in stats[team2]['game_results'] if g['opponent'] in common_opps and g['pf'] < g['pa'])
        common2_t = sum(1 for g in stats[team2]['game_results'] if g['opponent'] in common_opps and g['pf'] == g['pa'])
        common2_total = common2_w + common2_l + common2_t
        common2_pct = (common2_w + 0.5 * common2_t) / common2_total if common2_total > 0 else 0
        
        if common1_pct > common2_pct:
            return team1
        elif common2_pct > common1_pct:
            return team2
    
    if stats[team1]['conference_pct'] > stats[team2]['conference_pct']:
        return team1
    elif stats[team2]['conference_pct'] > stats[team1]['conference_pct']:
        return team2
    
    if stats[team1]['strength_of_victory'] > stats[team2]['strength_of_victory']:
        return team1
    elif stats[team2]['strength_of_victory'] > stats[team1]['strength_of_victory']:
        return team2
    
    if stats[team1]['strength_of_schedule'] > stats[team2]['strength_of_schedule']:
        return team1
    elif stats[team2]['strength_of_schedule'] > stats[team1]['strength_of_schedule']:
        return team2
    
    common_net1 = sum(g['pf'] - g['pa'] for g in stats[team1]['game_results'] if g['opponent'] in common_opps)
    common_net2 = sum(g['pf'] - g['pa'] for g in stats[team2]['game_results'] if g['opponent'] in common_opps)
    if common_net1 > common_net2:
        return team1
    elif common_net2 > common_net1:
        return team2
    
    net1 = stats[team1]['points_for'] - stats[team1]['points_against']
    net2 = stats[team2]['points_for'] - stats[team2]['points_against']
    if net1 > net2:
        return team1
    elif net2 > net1:
        return team2
    
    if stats[team1]['touchdowns'] > stats[team2]['touchdowns']:
        return team1
    elif stats[team2]['touchdowns'] > stats[team1]['touchdowns']:
        return team2
    
    return team1

def break_multi_team_division_tie(teams, stats, teams_info):
    remaining = list(teams)
    
    h2h_records = {}
    for team in remaining:
        h2h_w, h2h_l, h2h_t = 0, 0, 0
        for opp in remaining:
            if team != opp:
                h2h = stats[team]['head_to_head'].get(opp, {'W': 0, 'L': 0, 'T': 0})
                h2h_w += h2h['W']
                h2h_l += h2h['L']
                h2h_t += h2h['T']
        h2h_total = h2h_w + h2h_l + h2h_t
        h2h_records[team] = (h2h_w + 0.5 * h2h_t) / h2h_total if h2h_total > 0 else 0
    
    if len(set(h2h_records.values())) == len(remaining):
        remaining.sort(key=lambda t: -h2h_records[t])
        return remaining
    
    remaining.sort(key=lambda t: -stats[t]['division_pct'])
    if stats[remaining[0]]['division_pct'] > stats[remaining[1]]['division_pct']:
        winner = remaining[0]
        rest = remaining[1:]
        if len(rest) == 1:
            return [winner, rest[0]]
        elif len(rest) == 2:
            second = break_two_team_division_tie(rest, stats, teams_info)
            return [winner, second, rest[0] if second == rest[1] else rest[1]]
        else:
            return [winner] + break_multi_team_division_tie(rest, stats, teams_info)
    
    remaining.sort(key=lambda t: -stats[t]['conference_pct'])
    if stats[remaining[0]]['conference_pct'] > stats[remaining[1]]['conference_pct']:
        winner = remaining[0]
        rest = remaining[1:]
        if len(rest) == 1:
            return [winner, rest[0]]
        elif len(rest) == 2:
            second = break_two_team_division_tie(rest, stats, teams_info)
            return [winner, second, rest[0] if second == rest[1] else rest[1]]
        else:
            return [winner] + break_multi_team_division_tie(rest, stats, teams_info)
    
    remaining.sort(key=lambda t: (-stats[t]['strength_of_victory'], -stats[t]['win_pct']))
    return remaining

def apply_wildcard_tiebreaker(tied_teams, stats, teams_info):
    if len(tied_teams) == 0:
        return []
    if len(tied_teams) == 1:
        return tied_teams
    
    same_division = all(teams_info[t]['division'] == teams_info[tied_teams[0]]['division'] for t in tied_teams)
    if same_division:
        return apply_division_tiebreaker(tied_teams, stats, teams_info)
    
    if len(tied_teams) == 2:
        winner = break_two_team_wildcard_tie(tied_teams, stats, teams_info)
        return [winner]
    else:
        ranked = break_multi_team_wildcard_tie(tied_teams, stats, teams_info)
        return ranked

def break_two_team_wildcard_tie(teams, stats, teams_info):
    team1, team2 = teams[0], teams[1]
    
    h2h1 = stats[team1]['head_to_head'].get(team2, {'W': 0, 'L': 0, 'T': 0})
    h2h_total = h2h1['W'] + h2h1['L'] + h2h1['T']
    if h2h_total > 0:
        h2h1_pct = (h2h1['W'] + 0.5 * h2h1['T']) / h2h_total
        h2h2_pct = (h2h1['L'] + 0.5 * h2h1['T']) / h2h_total
        if h2h1_pct > h2h2_pct:
            return team1
        elif h2h2_pct > h2h1_pct:
            return team2
    
    if stats[team1]['conference_pct'] > stats[team2]['conference_pct']:
        return team1
    elif stats[team2]['conference_pct'] > stats[team1]['conference_pct']:
        return team2
    
    common_opps = set(stats[team1]['opponents']) & set(stats[team2]['opponents'])
    if len(common_opps) >= 4:
        common1_w = sum(1 for g in stats[team1]['game_results'] if g['opponent'] in common_opps and g['pf'] > g['pa'])
        common1_l = sum(1 for g in stats[team1]['game_results'] if g['opponent'] in common_opps and g['pf'] < g['pa'])
        common1_t = sum(1 for g in stats[team1]['game_results'] if g['opponent'] in common_opps and g['pf'] == g['pa'])
        common1_total = common1_w + common1_l + common1_t
        common1_pct = (common1_w + 0.5 * common1_t) / common1_total if common1_total > 0 else 0
        
        common2_w = sum(1 for g in stats[team2]['game_results'] if g['opponent'] in common_opps and g['pf'] > g['pa'])
        common2_l = sum(1 for g in stats[team2]['game_results'] if g['opponent'] in common_opps and g['pf'] < g['pa'])
        common2_t = sum(1 for g in stats[team2]['game_results'] if g['opponent'] in common_opps and g['pf'] == g['pa'])
        common2_total = common2_w + common2_l + common2_t
        common2_pct = (common2_w + 0.5 * common2_t) / common2_total if common2_total > 0 else 0
        
        if common1_pct > common2_pct:
            return team1
        elif common2_pct > common1_pct:
            return team2
    
    if stats[team1]['strength_of_victory'] > stats[team2]['strength_of_victory']:
        return team1
    elif stats[team2]['strength_of_victory'] > stats[team1]['strength_of_victory']:
        return team2
    
    if stats[team1]['strength_of_schedule'] > stats[team2]['strength_of_schedule']:
        return team1
    elif stats[team2]['strength_of_schedule'] > stats[team1]['strength_of_schedule']:
        return team2
    
    conf_net1 = stats[team1]['conference_points_for'] - stats[team1]['conference_points_against']
    conf_net2 = stats[team2]['conference_points_for'] - stats[team2]['conference_points_against']
    if conf_net1 > conf_net2:
        return team1
    elif conf_net2 > conf_net1:
        return team2
    
    net1 = stats[team1]['points_for'] - stats[team1]['points_against']
    net2 = stats[team2]['points_for'] - stats[team2]['points_against']
    if net1 > net2:
        return team1
    elif net2 > net1:
        return team2
    
    if stats[team1]['touchdowns'] > stats[team2]['touchdowns']:
        return team1
    elif stats[team2]['touchdowns'] > stats[team1]['touchdowns']:
        return team2
    
    return team1

def break_multi_team_wildcard_tie(teams, stats, teams_info):
    remaining = list(teams)
    
    divisions = defaultdict(list)
    for team in remaining:
        divisions[teams_info[team]['division']].append(team)
    
    div_winners = {}
    for div, div_teams in divisions.items():
        if len(div_teams) > 1:
            ranked = apply_division_tiebreaker(div_teams, stats, teams_info)
            div_winners[div] = ranked[0]
        else:
            div_winners[div] = div_teams[0]
    
    remaining = list(div_winners.values())
    
    if len(remaining) == 1:
        return remaining
    if len(remaining) == 2:
        winner = break_two_team_wildcard_tie(remaining, stats, teams_info)
        return [winner, remaining[0] if winner == remaining[1] else remaining[1]]
    
    h2h_sweep = None
    for team in remaining:
        beats_all = all(stats[team]['head_to_head'].get(opp, {'W': 0})['W'] > 0 for opp in remaining if opp != team)
        if beats_all:
            h2h_sweep = team
            break
    
    if h2h_sweep:
        rest = [t for t in remaining if t != h2h_sweep]
        if len(rest) == 1:
            return [h2h_sweep, rest[0]]
        else:
            return [h2h_sweep] + break_multi_team_wildcard_tie(rest, stats, teams_info)
    
    remaining.sort(key=lambda t: -stats[t]['conference_pct'])
    if stats[remaining[0]]['conference_pct'] > stats[remaining[1]]['conference_pct']:
        winner = remaining[0]
        rest = remaining[1:]
        if len(rest) == 1:
            return [winner, rest[0]]
        elif len(rest) == 2:
            second = break_two_team_wildcard_tie(rest, stats, teams_info)
            return [winner, second, rest[0] if second == rest[1] else rest[1]]
        else:
            return [winner] + break_multi_team_wildcard_tie(rest, stats, teams_info)
    
    remaining.sort(key=lambda t: (-stats[t]['strength_of_victory'], -stats[t]['win_pct']))
    return remaining

def calculate_playoff_seeding(teams_info, stats):
    afc_teams = [team for team in teams_info if teams_info[team]['conference'] == 'AFC']
    nfc_teams = [team for team in teams_info if teams_info[team]['conference'] == 'NFC']
    
    def get_division_winners(conference_teams):
        divisions = defaultdict(list)
        for team in conference_teams:
            divisions[teams_info[team]['division']].append(team)
        
        winners = []
        for div, div_teams in divisions.items():
            div_teams.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['W']))
            same_record_teams = [div_teams[0]]
            for t in div_teams[1:]:
                if abs(stats[t]['win_pct'] - stats[same_record_teams[0]]['win_pct']) < 0.001:
                    same_record_teams.append(t)
                else:
                    break
            
            if len(same_record_teams) > 1:
                ranked = apply_division_tiebreaker(same_record_teams, stats, teams_info)
                winners.append(ranked[0])
            else:
                winners.append(same_record_teams[0])
        
        winners.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['W']))
        return winners
    
    afc_div_winners = get_division_winners(afc_teams)
    nfc_div_winners = get_division_winners(nfc_teams)
    
    afc_div_winner_set = set(afc_div_winners)
    nfc_div_winner_set = set(nfc_div_winners)
    
    afc_wildcard_pool = [t for t in afc_teams if t not in afc_div_winner_set]
    nfc_wildcard_pool = [t for t in nfc_teams if t not in nfc_div_winner_set]
    
    afc_wildcard_pool.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['W']))
    nfc_wildcard_pool.sort(key=lambda t: (-stats[t]['win_pct'], -stats[t]['W']))
    
    afc_wildcards = []
    processed = set()
    for team in afc_wildcard_pool:
        if len(afc_wildcards) >= 3:
            break
        if team in processed:
            continue
        
        candidates = [t for t in afc_wildcard_pool 
                     if t not in processed and abs(stats[t]['win_pct'] - stats[team]['win_pct']) < 0.001]
        
        if len(candidates) > 1:
            ranked = apply_wildcard_tiebreaker(candidates, stats, teams_info)
        else:
            ranked = candidates
        
        spots_remaining = 3 - len(afc_wildcards)
        teams_to_add = ranked[:spots_remaining]
        afc_wildcards.extend(teams_to_add)
        processed.update(candidates)
    
    nfc_wildcards = []
    processed = set()
    for team in nfc_wildcard_pool:
        if len(nfc_wildcards) >= 3:
            break
        if team in processed:
            continue
        
        candidates = [t for t in nfc_wildcard_pool 
                     if t not in processed and abs(stats[t]['win_pct'] - stats[team]['win_pct']) < 0.001]
        
        if len(candidates) > 1:
            ranked = apply_wildcard_tiebreaker(candidates, stats, teams_info)
        else:
            ranked = candidates
        
        spots_remaining = 3 - len(nfc_wildcards)
        teams_to_add = ranked[:spots_remaining]
        nfc_wildcards.extend(teams_to_add)
        processed.update(candidates)
    
    return {
        'AFC': {
            'division_winners': afc_div_winners[:4],
            'wildcards': afc_wildcards[:3]
        },
        'NFC': {
            'division_winners': nfc_div_winners[:4],
            'wildcards': nfc_wildcards[:3]
        }
    }
