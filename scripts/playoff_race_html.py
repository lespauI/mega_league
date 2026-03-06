#!/usr/bin/env python3
import argparse
import csv
import os
import json
from collections import defaultdict

def read_standings(season_index=2):
    teams_div = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            div = row.get('divisionName', '').strip()
            conf = row.get('conferenceName', '').strip()
            teams_div[team] = {'division': div, 'conference': conf}
    
    team_rankings = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            team_rankings[team] = {
                'rank': int(row['rank']) if row.get('rank') else 99
            }
    
    remaining_opponents = defaultdict(list)
    with open('MEGA_games.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = row.get('status', '').strip()
            row_season_index = int(row.get('seasonIndex', -1))
            stage_index = int(row.get('stageIndex', -1))
            if status == '1' and row_season_index == season_index and stage_index == 1:
                home = row['homeTeam'].strip()
                away = row['awayTeam'].strip()
                week_index = int(row.get('weekIndex', 0))
                week = week_index + 1
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
            
            team_data = {
                'team': team,
                'W': w,
                'L': l,
                'T': t,
                'win_pct': (w + 0.5 * t) / (w + l + t) if (w + l + t) > 0 else 0,
                'remaining_sos': float(row['ranked_sos_avg']),
                'past_sos': float(row['past_ranked_sos_avg']),
                'total_sos': float(row['total_ranked_sos']),
                'remaining_games': int(row['remaining_games']),
                'remaining_opponents': opponent_details
            }
            
            if conf == 'AFC':
                afc_divs[div].append(team_data)
            else:
                nfc_divs[div].append(team_data)
    
    for div in afc_divs:
        afc_divs[div].sort(key=lambda x: x['win_pct'], reverse=True)
    
    for div in nfc_divs:
        nfc_divs[div].sort(key=lambda x: x['win_pct'], reverse=True)
    
    return afc_divs, nfc_divs

def calculate_playoff_chances(team, all_contenders, cutoff_position):
    base_wins = team['W']
    remaining = team['remaining_games']
    max_wins = base_wins + remaining
    team_sos = team['remaining_sos']
    
    contenders_at_cutoff = [t for t in all_contenders if all_contenders.index(t) <= cutoff_position + 3]
    avg_sos = sum(t['remaining_sos'] for t in contenders_at_cutoff) / len(contenders_at_cutoff) if contenders_at_cutoff else 0.5
    
    sos_advantage = (avg_sos - team_sos) * 100
    
    current_position = all_contenders.index(team)
    position_factor = max(0, (cutoff_position + 4 - current_position) * 8)
    
    expected_wins_from_remaining = remaining * (1.0 - team_sos)
    projected_total_wins = base_wins + expected_wins_from_remaining
    
    wins_above_bubble = (projected_total_wins - (cutoff_position * 0.7 + 6)) * 10
    
    base_chance = min(95, max(5, 50 + position_factor + sos_advantage + wins_above_bubble))
    
    if current_position < cutoff_position:
        base_chance = min(95, base_chance + 15)
    elif current_position == cutoff_position:
        base_chance = min(85, base_chance + 10)
    
    return round(base_chance, 1)

def get_rank_class(rank):
    if rank <= 10:
        return 'rank-elite'
    elif rank <= 20:
        return 'rank-mid'
    else:
        return 'rank-weak'

def get_playoff_picture(divs, probabilities):
    leaders = []
    for div_name in sorted(divs.keys()):
        leader = divs[div_name][0].copy()
        leader['division'] = div_name
        team_name = leader['team']
        leader['playoff_chance'] = probabilities.get(team_name, {}).get('playoff_probability', 99.0)
        leaders.append(leader)
    
    leaders.sort(key=lambda x: x['win_pct'], reverse=True)
    
    wc_candidates = []
    for div_name in divs:
        for team in divs[div_name][1:]:
            team_copy = team.copy()
            team_name = team_copy['team']
            team_copy['playoff_chance'] = probabilities.get(team_name, {}).get('playoff_probability', 50.0)
            wc_candidates.append(team_copy)
    
    wc_candidates.sort(key=lambda x: (-x['W'], -x['win_pct'], x['remaining_sos']))
    
    return leaders, wc_candidates

def get_draft_race(afc_divs, nfc_divs):
    all_teams = []
    
    for div_name in afc_divs:
        for team in afc_divs[div_name]:
            team_copy = team.copy()
            team_copy['conf'] = 'AFC'
            all_teams.append(team_copy)
    
    for div_name in nfc_divs:
        for team in nfc_divs[div_name]:
            team_copy = team.copy()
            team_copy['conf'] = 'NFC'
            all_teams.append(team_copy)
    
    all_teams.sort(key=lambda x: (x['win_pct'], -x['remaining_sos']))
    
    return all_teams[:16]

def create_html_report(afc_divs, afc_leaders, afc_wc, nfc_divs, nfc_leaders, nfc_wc):
    html = []
    html.append('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEGA League Playoff Race - Week 14</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
               background: transparent; 
               padding: 0; margin: 0; color: #333; overflow-x: hidden; }
        .container { max-width: 100%; margin: 0 auto; background: white; 
                     border-radius: 20px; padding: 30px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        h1 { text-align: center; color: #1e293b; margin-bottom: 10px; font-size: 2.5em; }
        .subtitle { text-align: center; color: #64748b; margin-bottom: 30px; font-size: 1.1em; }
        .conferences { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 40px; }
        .conference { background: #f8fafc; border-radius: 15px; padding: 25px; }
        .conference h2 { color: #0f172a; margin-bottom: 20px; padding-bottom: 10px; 
                         border-bottom: 3px solid #3b82f6; }
        .playoff-team { background: white; border-radius: 10px; padding: 15px; margin-bottom: 12px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .playoff-team:hover { transform: translateX(5px); }
        .seed-1 { border-left: 5px solid #3b82f6; }
        .seed-2 { border-left: 5px solid #60a5fa; }
        .seed-3 { border-left: 5px solid #93c5fd; }
        .seed-4 { border-left: 5px solid #bfdbfe; }
        .seed-wc { border-left: 5px solid #22c55e; }
        .seed-bubble { border-left: 5px solid #eab308; }
        .seed-out { border-left: 5px solid #ef4444; opacity: 0.7; }
        .pick-top3 { border-left: 5px solid #dc2626; }
        .pick-top10 { border-left: 5px solid #f59e0b; }
        .pick-rest { border-left: 5px solid #84cc16; }
        .team-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .team-name { font-size: 1.2em; font-weight: bold; color: #1e293b; }
        .team-record { font-size: 1.1em; color: #475569; font-weight: 600; }
        .team-details { display: flex; gap: 15px; font-size: 0.9em; color: #64748b; }
        .sos-badge { background: #dbeafe; color: #1e40af; padding: 4px 12px; 
                     border-radius: 20px; font-weight: 600; position: relative; cursor: help; }
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
        .seed-badge { display: inline-block; padding: 4px 12px; border-radius: 6px; 
                      font-weight: bold; font-size: 0.85em; margin-right: 10px; }
        .badge-div { background: #3b82f6; color: white; }
        .badge-wc { background: #22c55e; color: white; }
        .badge-bubble { background: #eab308; color: white; }
        .badge-out { background: #ef4444; color: white; }
        .badge-pick-top3 { background: #dc2626; color: white; }
        .badge-pick-top10 { background: #f59e0b; color: white; }
        .badge-pick-rest { background: #84cc16; color: white; }
        .divisions { margin-top: 30px; }
        .division { background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; }
        .division h3 { color: #0f172a; margin-bottom: 15px; padding-bottom: 8px; 
                       border-bottom: 2px solid #e2e8f0; }
        .div-team { padding: 10px; margin-bottom: 8px; background: #f8fafc; 
                    border-radius: 8px; display: flex; justify-content: space-between; }
        .analysis { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); 
                    border-radius: 15px; padding: 25px; margin: 30px 0; }
        .analysis h2 { color: #92400e; margin-bottom: 15px; }
        .draft-analysis { background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); 
                    border-radius: 15px; padding: 25px; margin: 30px 0; }
        .draft-analysis h2 { color: #7f1d1d; margin-bottom: 15px; }
        .analysis-item { background: white; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
        .analysis-item h3 { color: #1e293b; margin-bottom: 10px; }
        .legend { display: flex; gap: 20px; justify-content: center; margin: 30px 0; 
                  flex-wrap: wrap; }
        .legend-item { display: flex; align-items: center; gap: 8px; padding: 10px 20px;
                       background: #f1f5f9; border-radius: 10px; }
        .legend-box { width: 20px; height: 20px; border-radius: 4px; }
        .table-embed {
            width: 100%;
            border: none;
            margin: 30px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            height: 1300px;
        }
        @media (max-width: 1024px) {
            .conferences { grid-template-columns: 1fr; }
            .table-embed { height: 2400px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 MEGA League Playoff Race</h1>
        <div class="subtitle">Remaining Strength of Schedule Analysis</div>
        
        <iframe src="playoff_race_table.html" class="table-embed" id="tableFrame"></iframe>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-box" style="background: #3b82f6;"></div>
                <span>Division Leaders (Seeds 1-4)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #22c55e;"></div>
                <span>Wild Card (Seeds 5-7)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #eab308;"></div>
                <span>Bubble (>5% chance)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #ef4444;"></div>
                <span>Long Shot (<5%)</span>
            </div>
        </div>
''')

    html.append('        <div class="conferences">')
    
    for conf_name, leaders, wc, divs in [('AFC', afc_leaders, afc_wc, afc_divs), 
                                          ('NFC', nfc_leaders, nfc_wc, nfc_divs)]:
        html.append(f'            <div class="conference">')
        html.append(f'                <h2>{conf_name} Playoff Picture</h2>')
        
        wc_with_chances = [t for t in wc if t.get('playoff_chance', 0) > 5]
        all_teams = leaders[:4] + wc_with_chances
        
        for i, team in enumerate(all_teams):
            seed = i + 1
            playoff_chance = team.get('playoff_chance', 50)
            
            if i < 4:
                seed_class = f'seed-{seed}'
                badge_class = 'badge-div'
                badge_text = f'Seed {seed}'
            elif i < 7:
                seed_class = 'seed-wc'
                badge_class = 'badge-wc'
                badge_text = f'WC {seed}'
            elif playoff_chance > 5:
                seed_class = 'seed-bubble'
                badge_class = 'badge-bubble'
                badge_text = f'#{seed}'
            else:
                seed_class = 'seed-out'
                badge_class = 'badge-out'
                badge_text = f'#{seed}'
            
            sos_class = ''
            if team['remaining_sos'] < 0.45:
                sos_class = 'sos-easy'
            elif team['remaining_sos'] > 0.55:
                sos_class = 'sos-hard'
            
            tooltip_html = ''
            if 'remaining_opponents' in team and team['remaining_opponents']:
                tooltip_html = '<div class="sos-tooltip">'
                tooltip_html += '<div class="tooltip-title">Remaining Schedule</div>'
                sorted_opps = sorted(team['remaining_opponents'], key=lambda x: x['week'])
                for opp in sorted_opps:
                    rank_class = get_rank_class(opp['rank'])
                    tooltip_html += f'<div class="opponent-row">'
                    tooltip_html += f'<span class="opponent-name">Week {opp["week"]}: {opp["name"]}</span>'
                    tooltip_html += f'<span class="opponent-details {rank_class}">#{opp["rank"]}</span>'
                    tooltip_html += '</div>'
                tooltip_html += '</div>'
            
            div_label = ''
            if 'division' in team:
                div_label = f" • {team['division'].replace(conf_name + ' ', '')}"
            
            playoff_chance = team.get('playoff_chance', 50)
            
            html.append(f'                <div class="playoff-team {seed_class}">')
            record_display = f'{team["W"]}-{team["L"]}-{team["T"]}' if team["T"] > 0 else f'{team["W"]}-{team["L"]}'
            
            html.append(f'                    <div class="team-header">')
            html.append(f'                        <div>')
            html.append(f'                            <span class="seed-badge {badge_class}">{badge_text}</span>')
            html.append(f'                            <span class="team-name">{team["team"]}</span>')
            html.append(f'                        </div>')
            html.append(f'                        <span class="team-record">{record_display}</span>')
            html.append(f'                    </div>')
            html.append(f'                    <div class="team-details">')
            html.append(f'                        <span>Playoff Chance: {playoff_chance}%</span>')
            html.append(f'                        <span>•</span>')
            html.append(f'                        <span class="sos-badge {sos_class}">SOS: {team["remaining_sos"]:.3f}{tooltip_html}</span>')
            html.append(f'                        <span>•</span>')
            html.append(f'                        <span>{team["remaining_games"]} games left</span>')
            if div_label:
                html.append(f'                        <span>{div_label}</span>')
            html.append(f'                    </div>')
            html.append(f'                </div>')
        
        html.append(f'            </div>')
    
    html.append('        </div>')
    
    bottom_teams = get_draft_race(afc_divs, nfc_divs)
    
    html.append('''        
        <div class="draft-analysis">
            <h2>📉 Гонка за топ-пиками драфта</h2>
            <p style="text-align: center; margin-bottom: 20px; font-size: 1.1em;">Команды борются за лучшие позиции в драфте. Чем меньше побед = выше выбор в драфте!</p>
            
            <div class="legend" style="margin-bottom: 20px;">
                <div class="legend-item">
                    <div class="legend-box" style="background: #dc2626;"></div>
                    <span>Топ-3 Пики (QB Территория)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: #f59e0b;"></div>
                    <span>Топ-10 (Премиум Таланты)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box" style="background: #84cc16;"></div>
                    <span>Пики 11-16 (Нормальная Цена)</span>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">''')
    
    for i, team in enumerate(bottom_teams, 1):
        if i <= 3:
            pick_class = 'pick-top3'
            badge_class = 'badge-pick-top3'
        elif i <= 10:
            pick_class = 'pick-top10'
            badge_class = 'badge-pick-top10'
        else:
            pick_class = 'pick-rest'
            badge_class = 'badge-pick-rest'
        
        sos_class = ''
        if team['remaining_sos'] < 0.45:
            sos_class = 'sos-easy'
            sos_note = '⚠️ Риск побед!'
        elif team['remaining_sos'] > 0.55:
            sos_class = 'sos-hard'
            sos_note = '✓ Танк надёжен'
        else:
            sos_note = '→ Средняк'
        
        tooltip_html = ''
        if 'remaining_opponents' in team and team['remaining_opponents']:
            tooltip_html = '<div class="sos-tooltip">'
            tooltip_html += '<div class="tooltip-title">Remaining Schedule</div>'
            sorted_opps = sorted(team['remaining_opponents'], key=lambda x: x['week'])
            for opp in sorted_opps:
                rank_class = get_rank_class(opp['rank'])
                tooltip_html += f'<div class="opponent-row">'
                tooltip_html += f'<span class="opponent-name">Week {opp["week"]}: {opp["name"]}</span>'
                tooltip_html += f'<span class="opponent-details {rank_class}">#{opp["rank"]}</span>'
                tooltip_html += '</div>'
            tooltip_html += '</div>'
        
        expected_final_losses = team['L'] + (team['remaining_games'] * team['remaining_sos'])
        
        record_display = f'{team["W"]}-{team["L"]}-{team["T"]}' if team["T"] > 0 else f'{team["W"]}-{team["L"]}'
        
        html.append(f'                <div class="playoff-team {pick_class}">')
        html.append(f'                    <div class="team-header">')
        html.append(f'                        <div>')
        html.append(f'                            <span class="seed-badge {badge_class}">Пик {i}</span>')
        html.append(f'                            <span class="team-name">{team["team"]}</span>')
        html.append(f'                        </div>')
        html.append(f'                        <span class="team-record">{record_display}</span>')
        html.append(f'                    </div>')
        html.append(f'                    <div class="team-details">')
        html.append(f'                        <span>{team["conf"]}</span>')
        html.append(f'                        <span>•</span>')
        html.append(f'                        <span class="sos-badge {sos_class}">SOS: {team["remaining_sos"]:.3f}{tooltip_html}</span>')
        html.append(f'                        <span>•</span>')
        html.append(f'                        <span>{sos_note}</span>')
        html.append(f'                    </div>')
        html.append(f'                    <div style="margin-top: 8px; font-size: 0.85em; color: #64748b;">')
        html.append(f'                        Прогноз: ~{team["W"] + team["remaining_games"] * (1.0 - team["remaining_sos"]):.1f}-{expected_final_losses:.1f}')
        html.append(f'                    </div>')
        html.append(f'                </div>')
    

    html.append('''                </ul>
            </div>
        </div>
        
        <div class="analysis">
            <h2>🧮 Как считаются шансы на плей-офф? Разбираем формулу</h2>
            
            <div class="analysis-item">
                <p style="margin-bottom: 15px;">Значит так, ребятки, давайте разберёмся как я высчитываю эти проценты шансов. Тут не просто циферка из жопы - используется <strong>метод Монте-Карло</strong>, как у New York Times! Это когда компьютер прогоняет 10,000 симуляций сезона и смотрит, в скольких из них твоя команда попадает в плей-офф.</p>
                
                <h3 style="margin-top: 20px;">🎲 Шаг 1: Симулируем оставшиеся игры</h3>
                <p>Для каждой ещё не сыгранной игры определяем случайный исход на основе силы команд:</p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li>Считаем <strong>рейтинг команды</strong> = 70% от Win% + 20% от Past SoS (сложность сыгранных игр) + 10% от SoV (сила побеждённых)</li>
                    <li><strong>Базовая</strong> вероятность победы хозяев = рейтинг хозяев / (рейтинг хозяев + рейтинг гостей)</li>
                    <li>Добавляем модификаторы: <strong>+2%</strong> за домашнее поле, <strong>±3%</strong> за серии (3+ побед/поражений)</li>
                    <li>Если это <strong>дивизионная</strong> игра — чуть тянем к 50/50 (15% регрессия, потому что в дивизионе всегда дичь)</li>
                    <li>С шансом ~<strong>0.3%</strong> вообще выпадает ничья (и обеим по 0.5 победы)</li>
                    <li>Ограничиваем итог: минимум 25%, максимум 75% (никаких гарантий в Madden!)</li>
                    <li>Бросаем виртуальный кубик — если выпало меньше вероятности, хозяева WIN, иначе гости</li>
                </ul>
                <p style="background: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <strong>Пример:</strong> Cowboys (Win% 57%, Past SoS 0.48, SoV 0.56, серия +3) играют дома против Chargers (Win% 54%, Past SoS 0.52, SoV 0.50).<br>
                    Рейтинг Cowboys = (0.57 × 0.70) + (0.48 × 0.20) + (0.56 × 0.10) = 0.551<br>
                    Рейтинг Chargers = (0.54 × 0.70) + (0.52 × 0.20) + (0.50 × 0.10) = 0.532<br>
                    База для Cowboys = 0.551 / (0.551 + 0.532) = 50.9%<br>
                    + Домашнее поле: 50.9% + 2% = 52.9%<br>
                    + Серия побед (3+): 52.9% + 3% = <strong>55.9%</strong><br>
                    Кубик выдал 0.38 → 38% < 55.9% → <strong>Cowboys выиграли!</strong>
                </p>
                
                <h3 style="margin-top: 20px;">🏆 Шаг 2: Определяем плей-офф команды</h3>
                <p>После симуляции всех игр применяем <strong>ОФИЦИАЛЬНЫЕ правила NFL</strong> для определения 7 команд плей-офф в каждой конференции:</p>
                
                <p style="margin-top: 15px;"><strong>А) Находим 4 победителей дивизионов:</strong></p>
                <ol style="margin: 10px 0 10px 25px;">
                    <li>Сортируем команды в каждом дивизионе по тайбрейкерам NFL:</li>
                    <ul style="margin-left: 20px;">
                        <li><strong>1. Win %</strong> - общий процент побед (главное!)</li>
                        <li><strong>2. Head-to-Head</strong> - личные встречи (кто кого победил)</li>
                        <li><strong>3. Division %</strong> - процент побед внутри дивизиона</li>
                        <li><strong>4. Conference %</strong> - процент побед в конференции</li>
                        <li><strong>5. Strength of Victory</strong> - сила побеждённых команд</li>
                        <li><strong>6. Strength of Schedule</strong> - сила всех соперников</li>
                    </ul>
                    <li>Лидер каждого дивизиона = автоматически в плей-офф!</li>
                </ol>
                
                <p style="margin-top: 15px;"><strong>Б) Выбираем 3 Wild Card команды:</strong></p>
                <ol style="margin: 10px 0 10px 25px;">
                    <li>Берём все команды конференции, <strong>не выигравшие дивизион</strong></li>
                    <li>Сортируем по тем же тайбрейкерам (Win% → H2H → Conf% → SoV → SoS)</li>
                    <li>Топ-3 из них = Wild Card места!</li>
                </ol>
                
                <p style="background: #dbeafe; padding: 12px; border-radius: 5px; margin: 15px 0;">
                    <strong>💡 Важно:</strong> В каждой симуляции обновляются H2H рекорды, дивизионные и конференционные победы!<br>
                    Например, если в симуляции Cowboys побеждают Giants, то H2H Cowboys становится 1-0, а дивизионный рекорд улучшается. Это влияет на тайбрейкеры!
                </p>
                
                <h3 style="margin-top: 20px;">📊 Шаг 3: Считаем вероятности</h3>
                <p>Прогоняем эту симуляцию <strong>10,000 раз</strong> для каждой команды и считаем три типа вероятностей:</p>
                
                <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p style="margin-bottom: 10px;"><strong>🎯 Плей-офф вероятность:</strong></p>
                    <code style="background: white; padding: 8px; display: block; border-radius: 4px;">
                        (Число симуляций с выходом в плей-офф / 10,000) × 100%
                    </code>
                    <p style="margin: 10px 0;"><strong>Пример:</strong> Если Lions попали в плей-офф в 9,180 из 10,000 симуляций = <strong>91.8%</strong></p>
                    
                    <p style="margin: 15px 0 10px;"><strong>👑 Победа в дивизионе:</strong></p>
                    <code style="background: white; padding: 8px; display: block; border-radius: 4px;">
                        (Число симуляций с победой в дивизионе / 10,000) × 100%
                    </code>
                    <p style="margin: 10px 0;"><strong>Пример:</strong> Cowboys выиграли NFC East в 4,330 из 10,000 симуляций = <strong>43.3%</strong></p>
                    
                    <p style="margin: 15px 0 10px;"><strong>😎 Бай первого раунда (посев #1):</strong></p>
                    <code style="background: white; padding: 8px; display: block; border-radius: 4px;">
                        (Число симуляций с лучшим рекордом в конференции / 10,000) × 100%
                    </code>
                    <p style="margin: 10px 0;"><strong>Важно:</strong> Только команда с <strong>посевом #1</strong> получает бай! Сортируем победителей дивизионов по рекорду в каждой симуляции.</p>
                </div>
                
                <h3 style="margin-top: 20px;">🔥 Почему Монте-Карло круче формул?</h3>
                <ol style="margin: 10px 0 15px 25px;">
                    <li><strong>Учитывает ВСЕ возможные сценарии</strong> - не угадывает, а моделирует реальность</li>
                    <li><strong>Применяет настоящие тайбрейкеры NFL</strong> - в каждой симуляции!</li>
                    <li><strong>Показывает взаимосвязи</strong> - если Lions проигрывают, шансы Bears растут автоматически</li>
                    <li><strong>Точнее при равной борьбе</strong> - две команды 8-5 могут иметь разные шансы из-за расписания</li>
                    <li><strong>Используется NYT, FiveThirtyEight</strong> - это индустриальный стандарт!</li>
                </ol>
                
                <h3 style="margin-top: 20px;">💡 Разбираем реальный пример - Cowboys 70% плей-офф</h3>
                <p style="color: #0f172a; font-weight: bold; margin-top: 15px;">🤠 Cowboys (8-6) имеют 70.3% шансов на плей-офф. Как это вышло?</p>
                
                <p><strong>Оставшиеся игры Cowboys:</strong></p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li>Week 15: vs Chargers (7-6, Past SoS 0.516)</li>
                    <li>Week 16: @ Commanders (7-6, Past SoS 0.542)</li>
                    <li>Week 17: @ Giants (8-5, Past SoS 0.558)</li>
                </ul>
                
                <p style="margin-top: 15px;"><strong>Симуляция #1 - Cowboys проходят в плей-офф:</strong></p>
                <ol style="margin: 10px 0 10px 25px; background: #f0fdf4; padding: 15px; border-radius: 8px;">
                    <li><strong>vs Chargers:</strong> База 50.9% → +дом поле 2% → +серия 3% = 55.9% → Кубик 0.38 → WIN ✓</li>
                    <li><strong>@ Commanders:</strong> В гостях домашний бонус уже у Commanders → шанс Cowboys ~48-50% → Кубик 0.62 → LOSE ✗</li>
                    <li><strong>@ Giants:</strong> Giants сильнее по SoV/SoS, плюс гостевая → шанс Cowboys ~46-48% → Кубик 0.41 → WIN ✓</li>
                    <li><strong>Итог:</strong> Cowboys 10-7, Giants 9-7, Commanders 8-7</li>
                    <li><strong>Применяем тайбрейкеры:</strong> Cowboys выигрывают NFC East (H2H 1-0 vs Giants) → ПЛЕЙ-ОФФ! ✓</li>
                </ol>
                
                <p style="margin-top: 15px;"><strong>Симуляция #2 - Cowboys пролетают:</strong></p>
                <ol style="margin: 10px 0 10px 25px; background: #fef2f2; padding: 15px; border-radius: 8px;">
                    <li><strong>vs Chargers:</strong> Кубик 0.67 → LOSE ✗</li>
                    <li><strong>@ Commanders:</strong> Кубик 0.29 → WIN ✓</li>
                    <li><strong>@ Giants:</strong> Кубик 0.81 → LOSE ✗</li>
                    <li><strong>Итог:</strong> Cowboys 9-8, Giants 10-7</li>
                    <li><strong>Проверяем Wild Card:</strong> Cowboys на 8-м месте в NFC → МИМО ПЛЕЙ-ОФФА! ✗</li>
                </ol>
                
                <p style="margin-top: 15px;"><strong>После 10,000 симуляций:</strong> Cowboys прошли в 7,030 раз = <strong>70.3%</strong></p>
                
                <p style="color: #dc2626; font-weight: bold; margin-top: 20px;">⚠️ Почему Broncos (12-1) не имеют 100% на #1 сид?</p>
                <p>Хотя они почти гарантированно в плей-офф:</p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li>Шанс на плей-офф = <strong>100%</strong> (попали во всех 10,000 симуляциях)</li>
                    <li>Шанс на #1 сид = <strong>80.2%</strong> (в 198 симуляциях Titans или Patriots их обогнали!)</li>
                    <li>Сценарий: Broncos теряют 2 игры И Titans идут 3-0 → рекорды равны → тайбрейкеры решают</li>
                    <li>Маловероятно, но возможно - вот что показывает Монте-Карло!</li>
                </ul>
                
                <p style="margin-top: 20px; padding: 15px; background: #dbeafe; border-left: 4px solid #3b82f6; border-radius: 4px;">
                    <strong>📌 Суть метода Монте-Карло:</strong><br>
                    Не пытаемся предсказать будущее формулой. Вместо этого проигрываем сезон 10,000 раз с разными случайными исходами, но с учётом реальной силы команд (SoV, SoS, дом/гости, серии). Получаем не "что будет", а "что МОЖЕТ быть и с какой вероятностью". Это статистическая магия, чуваки! 🎯✨
                </p>
                
                <p style="margin-top: 15px;">Вот такая движуха, малята. Не формулы и догадки, а чистая математическая симуляция реальности! 🔥</p>
            </div>
        </div>
        
        <div style="text-align: center; color: #64748b; margin-top: 30px; padding: 20px; background: #f8fafc; border-radius: 10px;">
            <p><strong>Методология:</strong> SOS (Strength of Schedule) рассчитывается на основе рейтингов соперников по атаке, защите и общей производительности.</p>
            <p style="margin-top: 10px;">Высокий SOS = Тяжёлое расписание | Низкий SOS = Лёгкий путь в плей-офф</p>
        </div>
    </div>
    <script>
        function sendHeight() {
            const height = document.documentElement.scrollHeight;
            window.parent.postMessage({ type: 'resize', height: height }, '*');
        }
        
        window.addEventListener('load', function() {
            setTimeout(sendHeight, 200);
        });
        
        window.addEventListener('resize', sendHeight);
    </script>
</body>
</html>''')
    
    return '\n'.join(html)

def main(season_index=2):
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("Loading playoff probabilities...")
    with open('output/playoff_probabilities.json', 'r', encoding='utf-8') as f:
        probabilities = json.load(f)
    
    afc_divs, nfc_divs = read_standings(season_index=season_index)
    afc_leaders, afc_wc = get_playoff_picture(afc_divs, probabilities)
    nfc_leaders, nfc_wc = get_playoff_picture(nfc_divs, probabilities)
    
    os.makedirs('docs', exist_ok=True)
    
    html_report = create_html_report(afc_divs, afc_leaders, afc_wc, nfc_divs, nfc_leaders, nfc_wc)
    with open('docs/playoff_race.html', 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print("\n" + "="*80)
    print("PLAYOFF RACE ANALYSIS COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print("  ✓ docs/playoff_race.html")
    print("\nKey findings:")
    print("  • AFC: Five teams at 6-7 battling for Wild Card spots")
    print("  • NFC South: Four teams within one game - complete chaos!")
    print("  • Schedule strength will determine playoff fates")
    print("\nOpen playoff_race.html in your browser to view the full analysis!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate playoff race HTML report')
    parser.add_argument('--season-index', type=int, default=2,
                        help='Season index to filter games (default: 2)')
    args = parser.parse_args()
    main(season_index=args.season_index)
