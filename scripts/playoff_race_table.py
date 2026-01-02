#!/usr/bin/env python3
import csv
import os
import json
from collections import defaultdict
from datetime import datetime

def read_standings():
    teams_div = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            div = row.get('divisionName', '').strip()
            conf = row.get('conferenceName', '').strip()
            logo_id = row.get('logoId', '').strip()
            logo_url = f'https://cdn.neonsportz.com/teamlogos/256/{logo_id}.png' if logo_id else ''
            teams_div[team] = {'division': div, 'conference': conf, 'logo_url': logo_url}
    
    team_rankings = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            streak_val = row.get('winLossStreak', '0')
            try:
                streak = int(streak_val)
                if streak > 127:
                    streak = streak - 256
            except (ValueError, TypeError):
                streak = 0
            team_rankings[team] = {
                'rank': int(row['rank']) if row.get('rank') else 99,
                'ovrRating': int(row['ovrRating']) if row.get('ovrRating') else 85,
                'winLossStreak': streak
            }
    
    remaining_opponents = defaultdict(list)
    with open('MEGA_games.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get('status', '').strip()
            if status == '1':
                home = row['homeTeam'].strip()
                away = row['awayTeam'].strip()
                week = int(row.get('weekIndex', 0))
                remaining_opponents[home].append({'opponent': away, 'week': week})
                remaining_opponents[away].append({'opponent': home, 'week': week})

    with open('output/ranked_sos_by_conference.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        standings = list(reader)

    afc_divs = defaultdict(list)
    nfc_divs = defaultdict(list)
    
    for row in standings:
        team = row['team']
        conf = row['conference']
        w = int(row['W'])
        l = int(row['L'])
        t = int(row.get('T', 0))
        
        if team in teams_div:
            div = teams_div[team]['division']
            opponents = remaining_opponents.get(team, [])
            opponent_details = []
            for opp_data in opponents:
                opp_name = opp_data['opponent']
                opp_week = opp_data['week']
                if opp_name in team_rankings:
                    opp_rank_data = team_rankings[opp_name]
                    opponent_details.append({
                        'name': opp_name,
                        'rank': opp_rank_data['rank'],
                        'week': opp_week
                    })
            
            team_ovr = team_rankings[team]['ovrRating'] if team in team_rankings else 85
            win_streak = team_rankings[team]['winLossStreak'] if team in team_rankings else 0
            
            team_data = {
                'team': team,
                'W': w,
                'L': l,
                'T': t,
                'win_pct': (w + 0.5 * t) / (w + l + t) if (w + l + t) > 0 else 0,
                'remaining_sos': float(row['ranked_sos_avg']),
                'remaining_games': int(row['remaining_games']),
                'logo_url': teams_div[team]['logo_url'],
                'remaining_opponents': opponent_details,
                'past_ranked_sos_avg': float(row['past_ranked_sos_avg']),
                'team_ovr': team_ovr,
                'win_streak': win_streak
            }
            
            if conf == 'AFC':
                afc_divs[div].append(team_data)
            else:
                nfc_divs[div].append(team_data)
    
    for div in afc_divs:
        afc_divs[div].sort(key=lambda x: x['win_pct'], reverse=True)
    
    for div in nfc_divs:
        nfc_divs[div].sort(key=lambda x: x['win_pct'], reverse=True)
    
    return afc_divs, nfc_divs, teams_div

def get_division_leader_prob(team_name, div_teams, probabilities):
    return probabilities.get(team_name, {}).get('division_win_probability', 0)

def get_round1_bye_prob(team_name, all_div_leaders, probabilities):
    return probabilities.get(team_name, {}).get('bye_probability', 0)

def calculate_superbowl_prob(playoff_prob, div_prob, bye_prob, quality_of_wins, is_top_seed, 
                             win_pct=0.5, past_sos=0.5, win_streak=0):
    if playoff_prob == 0:
        return 0.0
    
    sov_normalized = max(0.0, min(1.0, (quality_of_wins - 0.3) / 0.4))
    
    team_rating = (
        win_pct * 0.70 +
        past_sos * 0.20 +
        sov_normalized * 0.10
    )
    
    streak_bonus = 0.0
    if win_streak >= 4:
        streak_bonus = 0.04
    elif win_streak >= 3:
        streak_bonus = 0.03
    elif win_streak <= -3:
        streak_bonus = -0.03
    
    game_win_prob = team_rating + streak_bonus
    game_win_prob = max(0.30, min(0.70, game_win_prob))
    
    if is_top_seed:
        home_bonus = 0.06
        games_needed = 3
    elif bye_prob > 30:
        home_bonus = 0.05
        games_needed = 3
    elif div_prob > 50:
        home_bonus = 0.03
        games_needed = 4
    else:
        home_bonus = 0.0
        games_needed = 4
    
    adjusted_game_win = game_win_prob + home_bonus
    adjusted_game_win = min(0.75, adjusted_game_win)
    
    conf_champ_prob = (adjusted_game_win ** games_needed)
    
    sb_game_prob = game_win_prob
    
    sb_win_prob = conf_champ_prob * sb_game_prob
    
    final_prob = (playoff_prob / 100) * sb_win_prob * 100
    
    return round(max(0.1, min(final_prob, 35.0)), 1)

def get_playoff_tooltip(playoff_prob, team_name, team_data):
    wins = team_data['W']
    losses = team_data['L']
    ties = team_data['T']
    remaining = team_data['remaining_games']
    
    record_str = f"{wins}-{losses}-{ties}" if ties > 0 else f"{wins}-{losses}"
    
    return f'''<div class="prob-tooltip">
        <strong>Вероятность выхода в плей-офф: {playoff_prob:.0f}%</strong><br><br>
        Рассчитано методом Монте-Карло (1000 симуляций):<br>
        • Текущий счёт: {record_str}<br>
        • Осталось игр: {remaining}<br>
        • В {playoff_prob:.0f}% симуляций команда попала в топ-7 конференции<br><br>
        Вероятность побед рассчитывается по формуле: 70% Win% + 30% SoS (сложность сыгранных игр).
    </div>'''

def get_division_tooltip(div_prob, team_name, div_teams, probabilities):
    team = [t for t in div_teams if t['team'] == team_name][0]
    position = div_teams.index(team) + 1
    wins = team['W']
    losses = team['L']
    ties = team['T']
    
    record_str = f"{wins}-{losses}-{ties}" if ties > 0 else f"{wins}-{losses}"
    
    leader = div_teams[0]
    leader_name = leader['team']
    leader_prob = probabilities.get(leader_name, {}).get('division_win_probability', 0)
    leader_record_str = f"{leader['W']}-{leader['L']}-{leader['T']}" if leader['T'] > 0 else f"{leader['W']}-{leader['L']}"
    
    if position == 1:
        return f'''<div class="prob-tooltip">
            <strong>Вероятность победы в дивизионе: {div_prob:.0f}%</strong><br><br>
            Рассчитано методом Монте-Карло (1000 симуляций):<br>
            • Текущий счёт: {record_str}<br>
            • Лидер дивизиона<br>
            • В {div_prob:.0f}% симуляций команда выиграла дивизион<br><br>
            Учитывается расписание, сила команд и тайбрейкеры.
        </div>'''
    else:
        gap = leader['win_pct'] - team['win_pct']
        return f'''<div class="prob-tooltip">
            <strong>Вероятность победы в дивизионе: {div_prob:.0f}%</strong><br><br>
            Рассчитано методом Монте-Карло (1000 симуляций):<br>
            • Текущий счёт: {record_str}<br>
            • Лидер: {leader_name} ({leader_record_str}, {leader_prob:.0f}%)<br>
            • В {div_prob:.0f}% симуляций команда выиграла дивизион<br><br>
            Учитывается расписание, сила команд и тайбрейкеры.
        </div>'''

def get_bye_tooltip(bye_prob, team_name, all_div_leaders, probabilities):
    playoff_prob = probabilities.get(team_name, {}).get('playoff_probability', 0)
    team_wins = probabilities.get(team_name, {}).get('W', 0)
    
    if bye_prob == 0:
        return f'''<div class="prob-tooltip">
            <strong>Вероятность первого раунда бай: 0%</strong><br><br>
            Рассчитано методом Монте-Карло (1000 симуляций):<br>
            • Текущий счёт: {team_wins} побед<br>
            • В 0% симуляций команда была посевом #1<br><br>
            Только команда с лучшим рекордом в конференции (посев #1) получает бай в первом раунде.
        </div>'''
    
    return f'''<div class="prob-tooltip">
        <strong>Вероятность первого раунда бай: {bye_prob:.0f}%</strong><br><br>
        Рассчитано методом Монте-Карло (1000 симуляций):<br>
        • Текущий счёт: {team_wins} побед<br>
        • В {bye_prob:.0f}% симуляций команда была посевом #1<br><br>
        Только команда с лучшим рекордом в конференции (посев #1) получает бай в первом раунде плей-офф.
    </div>'''

def get_superbowl_tooltip(sb_prob, playoff_prob, div_prob, bye_prob, quality_of_wins, is_top_seed,
                          win_pct=0.5, past_sos=0.5, win_streak=0):
    if playoff_prob == 0:
        return f'''<div class="prob-tooltip">
            <strong>Вероятность Суперкубка: 0%</strong><br><br>
            Команда не попадает в плей-офф.
        </div>'''
    
    if win_pct >= 0.75:
        tier_desc = "Элитная команда"
    elif win_pct >= 0.6:
        tier_desc = "Сильный претендент"
    elif win_pct >= 0.5:
        tier_desc = "Претендент на плей-офф"
    else:
        tier_desc = "Аутсайдер"
    
    streak_text = ""
    if win_streak >= 3:
        streak_text = f"<br>• Серия побед: {win_streak} (+бонус)"
    elif win_streak <= -3:
        streak_text = f"<br>• Серия поражений: {abs(win_streak)} (-штраф)"
    
    seed_text = ""
    if is_top_seed:
        seed_text = "Топ-сид (бай + домашние игры)"
    elif bye_prob > 30:
        seed_text = "Претендент на бай (3 игры до SB)"
    elif div_prob > 50:
        seed_text = "Лидер дивизиона (домашние игры)"
    
    return f'''<div class="prob-tooltip">
        <strong>Вероятность Суперкубка: {sb_prob:.1f}%</strong><br><br>
        {tier_desc}<br><br>
        <b>Факторы (как в симуляции плей-офф):</b><br>
        • Процент побед: {win_pct*100:.0f}% (70%)<br>
        • Сила расписания: {past_sos:.3f} (20%)<br>
        • Качество побед: {quality_of_wins:.3f} (10%){streak_text}<br><br>
        • Плей-офф: {playoff_prob:.0f}%<br>
        • Победа в див.: {div_prob:.0f}%<br>
        • Бай 1-го раунда: {bye_prob:.0f}%<br>
        {f'<br>{seed_text}' if seed_text else ''}<br>
        <i>= вероятность выиграть 3-4 матча плей-офф</i>
    </div>'''

def get_rank_class(rank):
    if rank <= 10:
        return 'rank-elite'
    elif rank <= 20:
        return 'rank-mid'
    else:
        return 'rank-weak'

def create_html_table(afc_divs, nfc_divs, probabilities):
    now = datetime.now()
    html = []
    
    html.append('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEGA League Playoff Race - Week 15</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; 
            background: transparent;
            padding: 0;
            margin: 0;
            color: #1a1a1a;
            overflow-x: hidden;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            padding: 24px 30px;
            border-bottom: 1px solid #e5e5e5;
        }
        
        .conferences-wrapper {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0;
        }
        h1 { 
            font-size: 1.6em; 
            font-weight: 700;
            margin-bottom: 6px;
            color: #1a1a1a;
        }
        .subtitle { 
            color: #666;
            font-size: 0.85em;
            margin-top: 6px;
        }
        .updated {
            color: #999;
            font-size: 0.75em;
            margin-top: 4px;
        }
        
        .conference-section {
            padding: 0;
            border-top: 2px solid #e5e5e5;
        }
        
        .conference-section:nth-child(2) {
            border-left: 2px solid #e5e5e5;
        }
        
        .conference-header {
            background: #f0f0f0;
            padding: 12px 20px;
            font-size: 1.1em;
            font-weight: 700;
            color: #1a1a1a;
            text-align: center;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 1em;
        }
        
        thead th {
            background: #fafafa;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            color: #666;
            border-bottom: 2px solid #e5e5e5;
        }
        
        thead th:nth-child(1) { width: 7%; }
        thead th:nth-child(2) { width: 24%; }
        thead th:nth-child(3) { width: 10%; text-align: center; }
        thead th:nth-child(4) { width: 9%; text-align: center; }
        thead th:nth-child(5) { width: 12%; text-align: center; }
        thead th:nth-child(6) { width: 12%; text-align: center; }
        thead th:nth-child(7) { width: 12%; text-align: center; }
        thead th:nth-child(8) { width: 14%; text-align: center; }
        
        tbody td {
            padding: 14px 8px;
            border-bottom: 1px solid #f5f5f5;
            position: relative;
        }
        
        tbody tr:hover {
            background: #fafafa;
        }
        
        .division-group {
            border-bottom: 2px solid #e5e5e5;
        }
        
        .div-cell {
            font-size: 0.75em;
            color: #999;
            text-transform: uppercase;
            font-weight: 500;
        }
        
        .team-cell {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            font-size: 1em;
            color: #1a1a1a;
            cursor: pointer;
            transition: color 0.2s;
        }
        
        .team-cell:hover {
            color: #2563eb;
            text-decoration: underline;
        }
        
        .team-logo {
            width: 28px;
            height: 28px;
            object-fit: contain;
        }
        
        .team-status {
            font-size: 0.85em;
            margin-left: 4px;
        }
        
        .clinched { color: #16a34a; }
        .eliminated { color: #dc2626; }
        
        .record-cell {
            text-align: center;
            font-size: 1em;
            font-weight: 500;
            color: #1a1a1a;
        }
        
        .sos-badge { 
            display: inline-block;
            background: #dbeafe; 
            color: #1e40af; 
            padding: 4px 10px; 
            border-radius: 12px; 
            font-weight: 600;
            font-size: 0.9em;
            position: relative;
            cursor: help;
        }
        .sos-easy { background: #d1fae5; color: #065f46; }
        .sos-hard { background: #fee2e2; color: #991b1b; }
        
        .sos-tooltip {
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-bottom: 8px;
            background: #1a1a1a;
            color: white;
            padding: 12px 14px;
            border-radius: 8px;
            font-size: 0.85em;
            white-space: nowrap;
            min-width: 220px;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s, visibility 0.2s;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            pointer-events: none;
        }
        
        .sos-tooltip::after {
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-top-color: #1a1a1a;
        }
        
        .sos-badge:hover .sos-tooltip {
            opacity: 1;
            visibility: visible;
        }
        
        .tooltip-title {
            font-weight: 700;
            margin-bottom: 8px;
            border-bottom: 1px solid #444;
            padding-bottom: 6px;
        }
        
        .opponent-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 4px 0;
            font-size: 0.95em;
        }
        
        .opponent-name {
            font-weight: 500;
            flex: 1;
        }
        
        .opponent-details {
            font-size: 0.9em;
            font-weight: 700;
            flex-shrink: 0;
        }
        
        .rank-elite { color: #dc2626; }
        .rank-mid { color: #eab308; }
        .rank-weak { color: #16a34a; }
        
        .prob-cell {
            text-align: center;
            font-weight: 600;
            font-size: 1em;
            padding: 8px 8px !important;
            position: relative;
        }
        
        .prob-wrapper {
            position: relative;
            display: inline-block;
            cursor: help;
        }
        
        .prob-tooltip {
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-bottom: 8px;
            background: #1a1a1a;
            color: white;
            padding: 12px 14px;
            border-radius: 8px;
            font-size: 0.85em;
            white-space: normal;
            min-width: 280px;
            max-width: 320px;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s, visibility 0.2s;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            pointer-events: none;
            text-align: left;
            line-height: 1.5;
        }
        
        .prob-tooltip::after {
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-top-color: #1a1a1a;
        }
        
        .prob-wrapper:hover .prob-tooltip {
            opacity: 1;
            visibility: visible;
        }
        
        .prob-tooltip strong {
            color: #60a5fa;
        }
        
        tbody td:nth-child(7) .prob-tooltip,
        tbody td:nth-child(8) .prob-tooltip {
            left: auto;
            right: 0;
            transform: none;
        }
        
        tbody td:nth-child(7) .prob-tooltip::after,
        tbody td:nth-child(8) .prob-tooltip::after {
            left: auto;
            right: 20px;
            transform: none;
        }
        
        .prob-100 { background: #1e3a5f; color: white; }
        .prob-90-99 { background: #2e4a6f; color: white; }
        .prob-75-89 { background: #4a6fa5; color: white; }
        .prob-50-74 { background: #6b93c0; color: white; }
        .prob-25-49 { background: #a4c2dc; color: #1a1a1a; }
        .prob-10-24 { background: #c8d9e8; color: #1a1a1a; }
        .prob-1-9 { background: #e8f0f6; color: #1a1a1a; }
        .prob-0 { background: #f5f5f5; color: #999; }
        
        .legend {
            padding: 20px 30px;
            background: #fafafa;
            border-top: 1px solid #e5e5e5;
        }
        
        .legend-title {
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #666;
        }
        
        .legend-items {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            font-size: 0.75em;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .legend-color {
            width: 24px;
            height: 14px;
            border-radius: 2px;
            border: 1px solid #ddd;
        }
        
        @media (max-width: 1200px) {
            .conferences-wrapper {
                grid-template-columns: 1fr;
            }
            .conference-section:nth-child(2) {
                border-left: none;
            }
        }
        
        @media (max-width: 768px) {
            .container { border-radius: 0; max-width: 100%; }
            .header, .conference-header, .legend { padding-left: 15px; padding-right: 15px; }
            table { font-size: 0.9em; }
            thead th { padding: 8px 6px; font-size: 0.7em; }
            tbody td { padding: 10px 6px; }
            .team-logo { width: 24px; height: 24px; }
            .sos-tooltip, .prob-tooltip {
                left: auto;
                right: 0;
                transform: none;
                white-space: normal;
                min-width: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏈 MEGA League Playoff Race</h1>
            <div class="subtitle">Week 15 Standings & Playoff Probabilities</div>
            <div class="updated">Updated ''' + now.strftime('%b %d, %Y at %I:%M %p ET') + '''</div>
        </div>

        <div class="conferences-wrapper">
''')
    
    for conf_name, divs in [('AFC', afc_divs), ('NFC', nfc_divs)]:
        all_div_leaders = []
        for div_name in divs:
            if divs[div_name]:
                all_div_leaders.append(divs[div_name][0])
        
        all_conf_teams = []
        for div_name in divs:
            all_conf_teams.extend(divs[div_name])
        
        top_bye_team = None
        max_bye_prob = 0
        for team_data in all_conf_teams:
            team_name = team_data['team']
            bye_prob = get_round1_bye_prob(team_name, all_div_leaders, probabilities)
            if bye_prob > max_bye_prob:
                max_bye_prob = bye_prob
                top_bye_team = team_name
        
        html.append(f'        <div class="conference-section">')
        html.append(f'            <div class="conference-header">{conf_name}</div>')
        html.append('            <table>')
        html.append('                <thead>')
        html.append('                    <tr>')
        html.append('                        <th>DIV.</th>')
        html.append('                        <th>TEAM</th>')
        html.append('                        <th>RECORD</th>')
        html.append('                        <th>SOS</th>')
        html.append('                        <th>MAKE PLAYOFFS</th>')
        html.append('                        <th>WIN DIVISION</th>')
        html.append('                        <th>ROUND 1 BYE</th>')
        html.append('                        <th>SUPER BOWL</th>')
        html.append('                    </tr>')
        html.append('                </thead>')
        html.append('                <tbody>')
        
        for div_name in sorted(divs.keys()):
            teams = divs[div_name]
            div_short = div_name.replace(f'{conf_name} ', '')
            
            for idx, team_data in enumerate(teams):
                team_name = team_data['team']
                prob_data = probabilities.get(team_name, {})
                
                playoff_prob = prob_data.get('playoff_probability', 0)
                div_prob = get_division_leader_prob(team_name, teams, probabilities)
                bye_prob = get_round1_bye_prob(team_name, all_div_leaders, probabilities)
                quality_of_wins = team_data.get('past_ranked_sos_avg', 0.5)
                is_top_seed = (team_name == top_bye_team)
                win_pct = team_data.get('win_pct', 0.5)
                past_sos = quality_of_wins
                win_streak = team_data.get('win_streak', 0)
                sb_prob = calculate_superbowl_prob(
                    playoff_prob, div_prob, bye_prob, quality_of_wins, is_top_seed,
                    win_pct=win_pct, past_sos=past_sos, win_streak=win_streak
                )
                
                sos = team_data['remaining_sos']
                logo_url = team_data.get('logo_url', '')
                
                def get_prob_class(prob):
                    if prob >= 100: return 'prob-100'
                    elif prob >= 90: return 'prob-90-99'
                    elif prob >= 75: return 'prob-75-89'
                    elif prob >= 50: return 'prob-50-74'
                    elif prob >= 25: return 'prob-25-49'
                    elif prob >= 10: return 'prob-10-24'
                    elif prob >= 1: return 'prob-1-9'
                    else: return 'prob-0'
                
                status = ''
                if playoff_prob >= 95:
                    status = '<span class="team-status clinched">✓</span>'
                elif playoff_prob < 5:
                    status = '<span class="team-status eliminated">✗</span>'
                
                sos_badge_class = 'sos-badge'
                if sos < 0.45:
                    sos_badge_class += ' sos-easy'
                elif sos > 0.55:
                    sos_badge_class += ' sos-hard'
                
                tooltip_html = ''
                remaining_opps = team_data.get('remaining_opponents', [])
                if remaining_opps:
                    tooltip_html = '<div class="sos-tooltip">'
                    tooltip_html += '<div class="tooltip-title">Remaining Schedule</div>'
                    sorted_opps = sorted(remaining_opps, key=lambda x: x['week'])
                    for opp in sorted_opps:
                        rank_class = get_rank_class(opp["rank"])
                        tooltip_html += f'<div class="opponent-row">'
                        tooltip_html += f'<span class="opponent-name">Week {opp["week"]}: {opp["name"]}</span>'
                        tooltip_html += f'<span class="opponent-details {rank_class}">#{opp["rank"]}</span>'
                        tooltip_html += '</div>'
                    tooltip_html += '</div>'
                
                row_class = 'division-group' if idx == len(teams) - 1 else ''
                
                logo_html = f'<img src="{logo_url}" class="team-logo" alt="{team_name}">' if logo_url else ''
                
                playoff_tooltip = get_playoff_tooltip(playoff_prob, team_name, team_data)
                div_tooltip = get_division_tooltip(div_prob, team_name, teams, probabilities)
                bye_tooltip = get_bye_tooltip(bye_prob, team_name, all_div_leaders, probabilities)
                sb_tooltip = get_superbowl_tooltip(
                    sb_prob, playoff_prob, div_prob, bye_prob, quality_of_wins, is_top_seed,
                    win_pct=win_pct, past_sos=past_sos, win_streak=win_streak
                )
                
                record_display = f'{team_data["W"]}-{team_data["L"]}-{team_data["T"]}' if team_data["T"] > 0 else f'{team_data["W"]}-{team_data["L"]}'
                
                html.append(f'                    <tr class="{row_class}">')
                html.append(f'                        <td class="div-cell">{div_short if idx == 0 else ""}</td>')
                html.append(f'                        <td><div class="team-cell">{logo_html}<span>{team_name}{status}</span></div></td>')
                html.append(f'                        <td class="record-cell">{record_display}</td>')
                html.append(f'                        <td class="record-cell"><span class="{sos_badge_class}">{sos:.3f}{tooltip_html}</span></td>')
                html.append(f'                        <td class="prob-cell {get_prob_class(playoff_prob)}"><span class="prob-wrapper">{playoff_prob:.0f}%{playoff_tooltip}</span></td>')
                html.append(f'                        <td class="prob-cell {get_prob_class(div_prob)}"><span class="prob-wrapper">{div_prob:.0f}%{div_tooltip}</span></td>')
                html.append(f'                        <td class="prob-cell {get_prob_class(bye_prob)}"><span class="prob-wrapper">{bye_prob:.0f}%{bye_tooltip}</span></td>')
                html.append(f'                        <td class="prob-cell {get_prob_class(sb_prob)}"><span class="prob-wrapper">{sb_prob:.0f}%{sb_tooltip}</span></td>')
                html.append('                    </tr>')
        
        html.append('                </tbody>')
        html.append('            </table>')
        html.append('        </div>')
    
    html.append('        </div>')
    
    html.append('''
        <div class="legend">
            <div class="legend-title">Probability Scale</div>
            <div class="legend-items">
                <div class="legend-item">
                    <div class="legend-color prob-100"></div>
                    <span>100%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-90-99"></div>
                    <span>90-99%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-75-89"></div>
                    <span>75-89%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-50-74"></div>
                    <span>50-74%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-25-49"></div>
                    <span>25-49%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-10-24"></div>
                    <span>10-24%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-1-9"></div>
                    <span>1-9%</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color prob-0"></div>
                    <span>0%</span>
                </div>
            </div>
            <div style="margin-top: 12px; font-size: 0.75em; color: #666;">
                <strong>✓</strong> Clinched playoff spot (≥95%) | 
                <strong>✗</strong> Eliminated (&lt;5%)
            </div>
        </div>
    </div>
    <script>
        function resizeIframe() {
            const height = document.documentElement.scrollHeight;
            window.parent.postMessage({ type: 'resize', height: height }, '*');
        }
        
        window.addEventListener('load', resizeIframe);
        window.addEventListener('resize', resizeIframe);
        
        document.addEventListener('DOMContentLoaded', function() {
            const teamCells = document.querySelectorAll('.team-cell');
            teamCells.forEach(cell => {
                cell.addEventListener('click', function() {
                    const teamName = this.querySelector('img').alt;
                    window.location.href = 'team_scenarios.html?team=' + encodeURIComponent(teamName);
                });
            });
        });
    </script>
</body>
</html>''')
    
    return '\n'.join(html)

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("Loading playoff probabilities...")
    with open('output/playoff_probabilities.json', 'r', encoding='utf-8') as f:
        probabilities = json.load(f)
    
    print("Reading standings data...")
    afc_divs, nfc_divs, teams_div = read_standings()
    
    print("Generating NYT-style table...")
    html_output = create_html_table(afc_divs, nfc_divs, probabilities)
    
    os.makedirs('docs', exist_ok=True)
    
    with open('docs/playoff_race_table.html', 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print("\n" + "="*80)
    print("PLAYOFF RACE TABLE GENERATED!")
    print("="*80)
    print("\nGenerated file:")
    print("  ✓ docs/playoff_race_table.html")
    print("\nOpen this file in your browser to view the NYT-style playoff race table!")

if __name__ == "__main__":
    main()
