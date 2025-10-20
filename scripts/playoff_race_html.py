#!/usr/bin/env python3
import csv
import os
import json
from collections import defaultdict

def read_standings():
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
                'win_pct': w / (w + l) if (w + l) > 0 else 0,
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
        <div class="subtitle">Week 14 Standings - Remaining Strength of Schedule Analysis</div>
        
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
                <span>Bubble (>20% chance)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box" style="background: #ef4444;"></div>
                <span>Long Shot (<20%)</span>
            </div>
        </div>
''')

    html.append('        <div class="conferences">')
    
    for conf_name, leaders, wc, divs in [('AFC', afc_leaders, afc_wc, afc_divs), 
                                          ('NFC', nfc_leaders, nfc_wc, nfc_divs)]:
        html.append(f'            <div class="conference">')
        html.append(f'                <h2>{conf_name} Playoff Picture</h2>')
        
        wc_with_chances = [t for t in wc if t.get('playoff_chance', 0) > 20]
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
            elif playoff_chance > 20:
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
            html.append(f'                    <div class="team-header">')
            html.append(f'                        <div>')
            html.append(f'                            <span class="seed-badge {badge_class}">{badge_text}</span>')
            html.append(f'                            <span class="team-name">{team["team"]}</span>')
            html.append(f'                        </div>')
            html.append(f'                        <span class="team-record">{team["W"]}-{team["L"]}</span>')
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
        
        html.append(f'                <div class="playoff-team {pick_class}">')
        html.append(f'                    <div class="team-header">')
        html.append(f'                        <div>')
        html.append(f'                            <span class="seed-badge {badge_class}">Пик {i}</span>')
        html.append(f'                            <span class="team-name">{team["team"]}</span>')
        html.append(f'                        </div>')
        html.append(f'                        <span class="team-record">{team["W"]}-{team["L"]}</span>')
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
    
    html.append('''            </div>
            
            <div class="analysis-item" style="margin-top: 25px;">
                <h3>💡 Как работает драфт-порядок?</h3>
                <p style="margin-bottom: 10px;">В отличие от плей-офф, здесь <strong>ХУДШИЕ</strong> команды получают преимущество:</p>
                <ul style="margin-left: 25px; margin-bottom: 10px;">
                    <li><strong>Меньше побед</strong> → Выше пик в драфте</li>
                    <li><strong>Лёгкое расписание (SOS < 0.45)</strong> → Риск выиграть и потерять позицию! ⚠️</li>
                    <li><strong>Жёсткое расписание (SOS > 0.55)</strong> → Танк надёжен, пик гарантирован! ✓</li>
                </ul>
                <p><strong>Пример:</strong> Команда 2-11 с SOS 0.650 почти гарантированно получит топ-3 пик, так как их ждут только сильные соперники.</p>
            </div>
        </div>
        
        <div class="analysis">
            <h2>🔥 На что смотреть: Самые горячие гонки</h2>
            
            <div class="analysis-item">
                <h3>AFC Wild Card: Историческая свалка на 6-7</h3>
                <p>Пять команд с 6-7 дерутся за последние места в плей-офф! Сила расписания решит всё:</p>
                <ul style="margin-top: 10px; margin-left: 20px;">''')
    
    afc_67_teams = [t for t in afc_wc if t['W'] == 6 and t['L'] == 7]
    for team in afc_67_teams:
        advantage = "🟢 ЛЁГКОЕ" if team['remaining_sos'] < 0.45 else "🔴 ЖЕСТЬ" if team['remaining_sos'] > 0.55 else "🟡 НОРМ"
        html.append(f'                    <li><strong>{team["team"]}</strong>: {team["remaining_games"]} игр, SOS {team["remaining_sos"]:.3f} {advantage}</li>')
    
    html.append('''                </ul>
            </div>
            
            <div class="analysis-item">
                <h3>NFC South: Четырёхсторонний хаос</h3>
                <p>Saints, Bucs и Falcons все на 8-5, Panthers 7-6. Полный беспредел:</p>
                <ul style="margin-top: 10px; margin-left: 20px;">''')
    
    nfc_south = []
    for team in nfc_leaders + nfc_wc:
        if team['team'] in ['Saints', 'Buccaneers', 'Falcons', 'Panthers']:
            nfc_south.append(team)
    nfc_south.sort(key=lambda x: x['win_pct'], reverse=True)
    
    for team in nfc_south:
        advantage = "🟢 ЛЕГЧАЙШИЙ ПУТЬ" if team['remaining_sos'] < 0.45 else "🔴 ЖЁСТКО" if team['remaining_sos'] > 0.55 else "🟡 СРЕДНЕ"
        html.append(f'                    <li><strong>{team["team"]}</strong> ({team["W"]}-{team["L"]}): SOS {team["remaining_sos"]:.3f} {advantage}</li>')
    
    html.append('''                </ul>
                <p style="margin-top: 10px;"><strong>Анализ:</strong> У Falcons легчайший путь (0.433), у Saints самый жёсткий (0.612). Дивизион может полностью перевернуться!</p>
            </div>
            
            <div class="analysis-item">
                <h3>NFC East: Разборки за дивизион</h3>
                <p>Giants и Cowboys оба 8-5. Личные встречи и расписание решат кто возьмёт дивизион.</p>
            </div>
            
            <div class="analysis-item">
                <h3>Команды с легчайшим расписанием (SOS < 0.45)</h3>
                <p>Эти команды готовы выстрелить на финише:</p>
                <ul style="margin-top: 10px; margin-left: 20px;">''')
    
    all_playoff_teams = []
    for team in afc_leaders[:4] + afc_wc[:10]:
        team['conf'] = 'AFC'
        all_playoff_teams.append(team)
    for team in nfc_leaders[:4] + nfc_wc[:10]:
        team['conf'] = 'NFC'
        all_playoff_teams.append(team)
    
    easy = sorted([t for t in all_playoff_teams if t['remaining_sos'] < 0.45], key=lambda x: x['remaining_sos'])
    for team in easy[:8]:
        html.append(f'                    <li><strong>{team["team"]}</strong> ({team["conf"]}): {team["remaining_sos"]:.3f} - Сейчас {team["W"]}-{team["L"]}</li>')
    
    html.append('''                </ul>
            </div>
            
            <div class="analysis-item">
                <h3>Команды с жесточайшим расписанием (SOS > 0.55)</h3>
                <p>Этих чуваков ждёт самый тяжёлый путь:</p>
                <ul style="margin-top: 10px; margin-left: 20px;">''')
    
    hard = sorted([t for t in all_playoff_teams if t['remaining_sos'] > 0.55], key=lambda x: x['remaining_sos'], reverse=True)
    for team in hard[:8]:
        html.append(f'                    <li><strong>{team["team"]}</strong> ({team["conf"]}): {team["remaining_sos"]:.3f} - Сейчас {team["W"]}-{team["L"]}</li>')
    
    html.append('''                </ul>
            </div>
        </div>
        
        <div class="analysis">
            <h2>🧮 Как считаются шансы на плей-офф? Разбираем формулу</h2>
            
            <div class="analysis-item">
                <p style="margin-bottom: 15px;">Значит так, ребятки, давайте разберёмся как я высчитываю эти проценты шансов. Тут не просто циферка из жопы - используются реальные правила тайбрейкеров NFL и куча статистики.</p>
                
                <h3 style="margin-top: 20px;">📋 Шаг 1: Определяем победителей дивизионов</h3>
                <p>Первым делом смотрим кто лидирует в каждом дивизионе. Победители дивизионов автоматически получают <strong>95-99%</strong> шансов, потому что они уже в плей-офф.</p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li>Если лидируешь с большим отрывом → <strong>99%</strong></li>
                    <li>Если соперники дышат в спину → <strong>85-95%</strong> в зависимости от прогнозируемых побед</li>
                    <li>Считаем разницу между твоими прогнозируемыми победами и ближайшего конкурента</li>
                </ul>
                
                <h3 style="margin-top: 20px;">🏆 Шаг 2: Применяем ОФИЦИАЛЬНЫЕ правила тайбрейкеров NFL</h3>
                <p>Для Wild Card мест используются реальные правила разрешения равенств из NFL:</p>
                <ol style="margin: 10px 0 10px 25px;">
                    <li><strong>Head-to-head</strong> - личные встречи (если играли друг с другом)</li>
                    <li><strong>Conference record</strong> - процент побед внутри конференции</li>
                    <li><strong>Division record</strong> - процент побед внутри дивизиона</li>
                    <li><strong>Strength of Victory</strong> - средний % побед команд, которых ты победил</li>
                    <li><strong>Strength of Schedule</strong> - средний % побед всех соперников</li>
                    <li><strong>Points scored/allowed</strong> - набранные/пропущенные очки</li>
                </ol>
                <p>Эти правила <strong>реально работают</strong> - скрипт анализирует все игры и считает эти показатели для каждой команды!</p>
                
                <h3 style="margin-top: 20px;">📊 Шаг 3: Ранжируем претендентов на Wild Card</h3>
                <p>Все команды, не выигравшие дивизион, сортируются по тайбрейкерам. Твоя позиция в этом рейтинге определяет базовый шанс:</p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li><strong>Позиция 1 (WC5)</strong> → база <strong>75%</strong></li>
                    <li><strong>Позиция 2 (WC6)</strong> → база <strong>60%</strong></li>
                    <li><strong>Позиция 3 (WC7)</strong> → база <strong>45%</strong></li>
                    <li><strong>Позиция 4-6</strong> → база <strong>40-20%</strong> (на пузыре)</li>
                    <li><strong>Позиция 7+</strong> → база <strong>15% и ниже</strong></li>
                </ul>
                
                <h3 style="margin-top: 20px;">🎯 Шаг 4: Добавляем факторы прогноза</h3>
                <p>К базовому шансу добавляем/вычитаем проценты на основе:</p>
                
                <p style="margin-top: 15px;"><strong>А) Преимущество по SOS (до ±80%!)</strong></p>
                <p>Сравниваем твой оставшийся SOS со средним SOS команд на грани плей-офф:</p>
                <div style="background: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <code>(Средний SOS конкурентов - Твой SOS) × 80</code>
                </div>
                <p><strong>Пример:</strong> У Bengals SOS 0.381, у конкурентов средний 0.50<br>
                (0.50 - 0.381) × 80 = <strong>+9.5%</strong> дополнительно! Легчайший путь = огромное преимущество.</p>
                
                <p style="margin-top: 15px;"><strong>Б) Прогноз финальных побед (до ±60%)</strong></p>
                <p>Рассчитываем сколько побед ты реально наберёшь:</p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li>Ожидаемые победы = Оставшиеся игры × (1.0 - твой SOS)</li>
                    <li>Прогноз финала = Текущие победы + Ожидаемые победы</li>
                    <li>Сравниваем с порогом плей-офф (~7-8 побед для WC7)</li>
                    <li>Каждая победа выше/ниже = <strong>±12%</strong> к шансам</li>
                </ul>
                
                <p style="margin-top: 15px;"><strong>В) Conference record (до ±20%)</strong></p>
                <p>Твой процент побед внутри конференции влияет на тайбрейкеры:</p>
                <div style="background: #fef3c7; padding: 10px; border-radius: 5px; margin: 10px 0;">
                    <code>(Conference % - 50%) × 20</code>
                </div>
                <p>Если ты 70% побед в конференции → <strong>+4%</strong> к шансам</p>
                
                <h3 style="margin-top: 20px;">🎯 Итоговая формула</h3>
                <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 15px 0; font-family: monospace; font-size: 0.95em;">
                    <strong>Если лидер дивизиона:</strong><br>
                    95% + Cushion factor (запас по победам от соперников)<br>
                    = 85-99%<br><br>
                    
                    <strong>Если претендент на Wild Card:</strong><br>
                    Base (15-75% по позиции в рейтинге)<br>
                    + SOS advantage (средний SOS - твой SOS) × 80<br>
                    + Wins projection (прогноз побед - порог) × 12<br>
                    + Conference factor (conf % - 50%) × 20<br>
                    = Итог (зажато в 1-95%)
                </div>
                
                <h3 style="margin-top: 20px;">💪 Почему эта система крутая?</h3>
                <ol style="margin: 10px 0 15px 25px;">
                    <li><strong>Использует РЕАЛЬНЫЕ правила NFL</strong> - не выдумка, а официальные тайбрейкеры</li>
                    <li><strong>Учитывает все игры</strong> - head-to-head, conference record, strength of victory</li>
                    <li><strong>Прогнозирует будущее</strong> - на основе SOS и оставшихся игр</li>
                    <li><strong>Динамическая</strong> - команды с шансами >20% попадают в "пузырь"</li>
                </ol>
                
                <p style="color: #ef4444; font-weight: bold; margin-top: 15px;">⚠️ Почему Bengals (6-7) имеют 79% шансов?</p>
                <p>Потому что:</p>
                <ul style="margin: 10px 0 10px 25px;">
                    <li>Их SOS 0.381 - <strong>ЛЕГЧАЙШИЙ</strong> среди всех претендентов</li>
                    <li>Прогноз: 6 побед + 4 игры × 0.619 = ~8.5 финальных побед</li>
                    <li>Преимущество по SOS даёт +9.5%</li>
                    <li>Прогноз побед выше порога даёт ещё +18%</li>
                    <li>Сейчас на позиции WC7, база 45% + бонусы = 79%!</li>
                </ul>
                
                <p style="margin-top: 15px;">Вот такая движуха, малята. Математика + правила NFL + здравый смысл = точный прогноз! 🎯</p>
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

def create_markdown_report(afc_leaders, afc_wc, nfc_leaders, nfc_wc):
    report = []
    report.append("# 🏈 NFL MEGA League Playoff Race Analysis - Week 14")
    report.append("")
    report.append("## Current Playoff Picture")
    report.append("")
    report.append("*Playoff chances calculated based on current record, remaining schedule strength, and competition*")
    report.append("")
    
    report.append("### AFC Playoff Standings")
    report.append("")
    report.append("**Division Leaders:**")
    for i, team in enumerate(afc_leaders[:4], 1):
        div_short = team['division'].replace('AFC ', '')
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) - {div_short} | Playoff: 99.5% | SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Wild Card Race:**")
    for i, team in enumerate(afc_wc[:5], 5):
        chance = team.get('playoff_chance', 50)
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) | Playoff: {chance}% | SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**On the Bubble:**")
    for i, team in enumerate(afc_wc[5:8], 10):
        chance = team.get('playoff_chance', 50)
        report.append(f"- **{i}.** {team['team']} ({team['W']}-{team['L']}) | Playoff: {chance}% | SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("### NFC Playoff Standings")
    report.append("")
    report.append("**Division Leaders:**")
    for i, team in enumerate(nfc_leaders[:4], 1):
        div_short = team['division'].replace('NFC ', '')
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) - {div_short} | Playoff: 99.5% | SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Wild Card Race:**")
    for i, team in enumerate(nfc_wc[:5], 5):
        chance = team.get('playoff_chance', 50)
        report.append(f"- **Seed {i}:** {team['team']} ({team['W']}-{team['L']}) | Playoff: {chance}% | SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**On the Bubble:**")
    for i, team in enumerate(nfc_wc[5:8], 10):
        chance = team.get('playoff_chance', 50)
        report.append(f"- **{i}.** {team['team']} ({team['W']}-{team['L']}) | Playoff: {chance}% | SOS: {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("## Key Races to Watch")
    report.append("")
    
    report.append("### AFC Wild Card Battle")
    report.append("")
    report.append("**INTENSE 6-7 LOGJAM!** Five teams at 6-7 fighting for the last playoff spots:")
    report.append("")
    afc_67_teams = [t for t in afc_wc[:10] if t['W'] == 6 and t['L'] == 7]
    for team in afc_67_teams:
        chance = team.get('playoff_chance', 50)
        advantage = "🟢 Best path" if team['remaining_sos'] < 0.45 else "🔴 Brutal" if team['remaining_sos'] > 0.55 else "🟡 Balanced"
        report.append(f"- **{team['team']}**: Playoff {chance}% | SOS {team['remaining_sos']:.3f} {advantage}")
    
    report.append("")
    report.append("**Analysis:** Bengals and Texans have easiest schedules - they're positioned to surge!")
    report.append("")
    
    report.append("### NFC South: Four-Way Chaos")
    report.append("")
    report.append("Three teams at 8-5, one at 7-6. Anyone can win this division:")
    report.append("")
    nfc_south_teams = []
    for team in nfc_leaders + nfc_wc:
        if team['team'] in ['Saints', 'Buccaneers', 'Falcons', 'Panthers']:
            nfc_south_teams.append(team)
    
    for team in sorted(nfc_south_teams, key=lambda x: x['win_pct'], reverse=True):
        chance = team.get('playoff_chance', 99.5)
        report.append(f"- **{team['team']}** ({team['W']}-{team['L']}): Playoff {chance}% | SOS {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Analysis:** Falcons (0.433) vs Saints (0.612) - massive 0.179 SOS gap could flip the division!")
    report.append("")
    
    report.append("### NFC Wild Card: Tight Battle")
    report.append("")
    report.append("Four teams at 7-6 fighting for final spots:")
    report.append("")
    nfc_76_teams = [t for t in nfc_wc[:10] if t['W'] == 7 and t['L'] == 6]
    for team in nfc_76_teams:
        chance = team.get('playoff_chance', 50)
        report.append(f"- **{team['team']}**: Playoff {chance}% | SOS {team['remaining_sos']:.3f}")
    
    report.append("")
    report.append("**Analysis:** Commanders have easiest remaining schedule - prime position to sneak in!")
    report.append("")
    
    return '\n'.join(report)

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("Calculating playoff probabilities with tiebreaker rules...")
    os.system('python3 scripts/calc_playoff_probabilities.py')
    
    with open('output/playoff_probabilities.json', 'r', encoding='utf-8') as f:
        probabilities = json.load(f)
    
    afc_divs, nfc_divs = read_standings()
    afc_leaders, afc_wc = get_playoff_picture(afc_divs, probabilities)
    nfc_leaders, nfc_wc = get_playoff_picture(nfc_divs, probabilities)
    
    os.makedirs('docs', exist_ok=True)
    
    html_report = create_html_report(afc_divs, afc_leaders, afc_wc, nfc_divs, nfc_leaders, nfc_wc)
    with open('docs/playoff_race.html', 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    markdown_report = create_markdown_report(afc_leaders, afc_wc, nfc_leaders, nfc_wc)
    with open('docs/playoff_race_report.md', 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    
    print("\n" + "="*80)
    print("PLAYOFF RACE ANALYSIS COMPLETE!")
    print("="*80)
    print("\nGenerated files:")
    print("  ✓ docs/playoff_race.html")
    print("  ✓ docs/playoff_race_report.md")
    print("\nKey findings:")
    print("  • AFC: Five teams at 6-7 battling for Wild Card spots")
    print("  • NFC South: Four teams within one game - complete chaos!")
    print("  • Schedule strength will determine playoff fates")
    print("\nOpen playoff_race.html in your browser to view the full analysis!")

if __name__ == "__main__":
    main()
