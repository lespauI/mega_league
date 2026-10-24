#!/usr/bin/env python3
import argparse
import csv
import os
import json
from collections import defaultdict

def read_standings(season_index=0):
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
    <title>MEGA League Playoff Race - Current Standings</title>
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
            <h2>How the probabilities are calculated</h2>
            <p>The report uses 10,000 Monte Carlo simulations of the remaining schedule.
            Game probabilities combine the supplied ELO ratings, current win percentage,
            schedule strength and strength of victory, with the existing home-field,
            streak and divisional adjustments. The existing tiebreakers determine the
            playoff teams in each simulation.</p>
            <p>The tables above show the current export's results.
            <a href="../Formula.md">Formula reference</a> ·
            <a href="data/import_metadata.json">Export and ELO provenance</a></p>
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

def main(season_index=0):
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
    print(f"  • Current CSV seasonIndex: {season_index}")
    print("  • Schedule strength will determine playoff fates")
    print("\nOpen playoff_race.html in your browser to view the full analysis!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate playoff race HTML report')
    parser.add_argument('--season-index', type=int, default=0,
                        help='Season index to filter games (default: 0)')
    args = parser.parse_args()
    main(season_index=args.season_index)
