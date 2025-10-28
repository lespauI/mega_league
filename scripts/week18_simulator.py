#!/usr/bin/env python3
import csv
import json
from collections import defaultdict

def load_teams_data():
    teams_info = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            logo_id = row.get('logoId', '').strip()
            logo_url = f'https://cdn.neonsportz.com/teamlogos/256/{logo_id}.png' if logo_id else ''
            teams_info[team] = {
                'division': row.get('divisionName', '').strip(),
                'conference': row.get('conferenceName', '').strip(),
                'logo_url': logo_url
            }
    return teams_info

def load_games():
    games = []
    with open('MEGA_games.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = int(row['status']) if row['status'] else 1
            week = int(row['weekIndex']) if row['weekIndex'] else 0
            home_score = int(row['homeScore']) if row['homeScore'] else 0
            away_score = int(row['awayScore']) if row['awayScore'] else 0
            games.append({
                'id': row['id'],
                'home': row['homeTeam'].strip(),
                'away': row['awayTeam'].strip(),
                'home_score': home_score,
                'away_score': away_score,
                'week': week,
                'status': status,
                'completed': status in [2, 3]
            })
    return games

def calculate_team_stats(teams_info, games):
    stats = {}
    
    for team in teams_info:
        stats[team] = {
            'W': 0, 'L': 0, 'T': 0,
            'conference_W': 0, 'conference_L': 0, 'conference_T': 0,
            'division_W': 0, 'division_L': 0, 'division_T': 0,
            'points_for': 0, 'points_against': 0,
            'conference_points_for': 0, 'conference_points_against': 0,
            'touchdowns': 0,
            'head_to_head': defaultdict(lambda: {'W': 0, 'L': 0, 'T': 0}),
            'opponents': [],
            'defeated_opponents': [],
            'game_results': []
        }
    
    for game in games:
        if not game['completed']:
            continue
        
        home = game['home']
        away = game['away']
        home_score = game['home_score']
        away_score = game['away_score']
        
        if home not in stats or away not in stats:
            continue
        
        stats[home]['game_results'].append({'opponent': away, 'pf': home_score, 'pa': away_score})
        stats[away]['game_results'].append({'opponent': home, 'pf': away_score, 'pa': home_score})
        
        stats[home]['opponents'].append(away)
        stats[away]['opponents'].append(home)
        
        stats[home]['points_for'] += home_score
        stats[home]['points_against'] += away_score
        stats[away]['points_for'] += away_score
        stats[away]['points_against'] += home_score
        
        stats[home]['touchdowns'] += home_score // 7
        stats[away]['touchdowns'] += away_score // 7
        
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

def generate_html():
    teams_info = load_teams_data()
    games = load_games()
    
    completed_games = [g for g in games if g['completed']]
    week18_games = [g for g in games if g['week'] == 17 and not g['completed']]
    
    current_stats = calculate_team_stats(teams_info, completed_games)
    
    week18_games_json = json.dumps([{
        'id': g['id'],
        'home': g['home'],
        'away': g['away']
    } for g in week18_games])
    
    teams_info_json = json.dumps(teams_info)
    completed_games_json = json.dumps([{
        'home': g['home'],
        'away': g['away'],
        'home_score': g['home_score'],
        'away_score': g['away_score']
    } for g in completed_games])
    
    current_standings = {}
    with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row['displayName'].strip()
            w = int(row['totalWins']) if row['totalWins'] else 0
            l = int(row['totalLosses']) if row['totalLosses'] else 0
            t = int(row['totalTies']) if row['totalTies'] else 0
            current_standings[team] = {
                'W': w,
                'L': l,
                'T': t,
                'win_pct': (w + 0.5 * t) / (w + l + t) if (w + l + t) > 0 else 0
            }
    
    standings_json = json.dumps(current_standings)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Week 18 Playoff Simulator</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #1e293b;
            margin-bottom: 10px;
            font-size: 2.8em;
        }}
        .subtitle {{
            text-align: center;
            color: #64748b;
            margin-bottom: 40px;
            font-size: 1.2em;
        }}
        .main-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }}
        .games-section {{
            background: #f8fafc;
            border-radius: 15px;
            padding: 25px;
        }}
        .games-section h2 {{
            color: #0f172a;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3b82f6;
        }}
        .game-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .game-matchup {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .team {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1em;
            font-weight: 600;
            color: #1e293b;
        }}
        .team-logo {{
            width: 32px;
            height: 32px;
            object-fit: contain;
        }}
        .team-logo-small {{
            width: 24px;
            height: 24px;
            object-fit: contain;
        }}
        .at {{
            color: #94a3b8;
            font-size: 0.9em;
        }}
        .game-buttons {{
            display: flex;
            gap: 10px;
        }}
        .game-btn {{
            flex: 1;
            padding: 12px;
            border: 2px solid #e2e8f0;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .game-btn:hover {{
            background: #f1f5f9;
            transform: scale(1.02);
        }}
        .game-btn.selected {{
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
        }}
        .action-buttons {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 30px 0;
        }}
        .btn {{
            padding: 15px 40px;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .btn-primary {{
            background: #3b82f6;
            color: white;
        }}
        .btn-primary:hover {{
            background: #2563eb;
            transform: translateY(-2px);
        }}
        .btn-secondary {{
            background: #64748b;
            color: white;
        }}
        .btn-secondary:hover {{
            background: #475569;
            transform: translateY(-2px);
        }}
        .results-section {{
            background: #f8fafc;
            border-radius: 15px;
            padding: 25px;
            margin-top: 30px;
        }}
        .results-section h2 {{
            color: #0f172a;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #10b981;
        }}
        .conference-results {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        .conference {{
            background: white;
            border-radius: 10px;
            padding: 20px;
        }}
        .conference h3 {{
            color: #1e293b;
            margin-bottom: 15px;
            font-size: 1.5em;
        }}
        .seed-team {{
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            background: #f8fafc;
            border-left: 5px solid #3b82f6;
        }}
        .seed-1 {{ border-left-color: #3b82f6; }}
        .seed-2 {{ border-left-color: #60a5fa; }}
        .seed-3 {{ border-left-color: #93c5fd; }}
        .seed-4 {{ border-left-color: #bfdbfe; }}
        .seed-wc {{ border-left-color: #22c55e; }}
        .seed-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }}
        .seed-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 0.85em;
            background: #3b82f6;
            color: white;
        }}
        .team-name {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.1em;
            font-weight: bold;
            color: #1e293b;
        }}
        .team-record {{
            font-size: 0.95em;
            color: #64748b;
            font-weight: 600;
        }}
        .tiebreaker-info {{
            margin-top: 8px;
            padding: 8px;
            background: #fef3c7;
            border-radius: 5px;
            font-size: 0.85em;
            color: #92400e;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.5;
        }}
        .elimination-info {{
            margin-top: 8px;
            padding: 8px;
            background: #fee2e2;
            border-radius: 5px;
            font-size: 0.85em;
            color: #991b1b;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.5;
        }}
        .eliminated-team {{
            border-left-color: #ef4444 !important;
            opacity: 0.85;
        }}
        .division-label {{
            font-size: 0.8em;
            color: #64748b;
            font-style: italic;
        }}
        @media (max-width: 1024px) {{
            .main-grid, .conference-results {{
                grid-template-columns: 1fr;
            }}
        }}
        .hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏈 Week 18 Playoff Simulator</h1>
        <div class="subtitle">Select game outcomes to see playoff seeding with tiebreaker explanations</div>
        
        <div class="main-grid">
            <div class="games-section">
                <h2>AFC Week 18 Games</h2>
                <div id="afc-games"></div>
            </div>
            
            <div class="games-section">
                <h2>NFC Week 18 Games</h2>
                <div id="nfc-games"></div>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="btn btn-primary" onclick="simulatePlayoffs()">Calculate Playoff Seeding</button>
            <button class="btn btn-secondary" onclick="randomizeGames()">Randomize All Games</button>
            <button class="btn btn-secondary" onclick="resetGames()">Reset Selections</button>
        </div>
        
        <div id="results" class="results-section hidden">
            <h2>Playoff Seeding Results</h2>
            <div class="conference-results">
                <div class="conference">
                    <h3>AFC Playoffs</h3>
                    <div id="afc-results"></div>
                </div>
                <div class="conference">
                    <h3>NFC Playoffs</h3>
                    <div id="nfc-results"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const week18Games = {week18_games_json};
        const teamsInfo = {teams_info_json};
        const completedGames = {completed_games_json};
        const currentStandings = {standings_json};
        
        let gameSelections = {{}};
        
        function initializeGames() {{
            const afcGames = document.getElementById('afc-games');
            const nfcGames = document.getElementById('nfc-games');
            
            week18Games.forEach(game => {{
                const homeConf = teamsInfo[game.home].conference;
                const container = homeConf === 'AFC' ? afcGames : nfcGames;
                
                const awayLogo = teamsInfo[game.away].logo_url;
                const homeLogo = teamsInfo[game.home].logo_url;
                
                const gameCard = document.createElement('div');
                gameCard.className = 'game-card';
                gameCard.innerHTML = `
                    <div class="game-matchup">
                        <span class="team">
                            <img src="${{awayLogo}}" class="team-logo" alt="${{game.away}}">
                            ${{game.away}}
                        </span>
                        <span class="at">@</span>
                        <span class="team">
                            <img src="${{homeLogo}}" class="team-logo" alt="${{game.home}}">
                            ${{game.home}}
                        </span>
                    </div>
                    <div class="game-buttons">
                        <button class="game-btn" onclick="selectWinner('${{game.id}}', '${{game.away}}')">
                            <img src="${{awayLogo}}" class="team-logo-small" alt="${{game.away}}">
                            ${{game.away}} Wins
                        </button>
                        <button class="game-btn" onclick="selectWinner('${{game.id}}', '${{game.home}}')">
                            <img src="${{homeLogo}}" class="team-logo-small" alt="${{game.home}}">
                            ${{game.home}} Wins
                        </button>
                    </div>
                `;
                container.appendChild(gameCard);
            }});
        }}
        
        function selectWinner(gameId, winner) {{
            gameSelections[gameId] = winner;
            
            const buttons = document.querySelectorAll(`[onclick*="${{gameId}}"]`);
            buttons.forEach(btn => {{
                btn.classList.remove('selected');
                if (btn.textContent.includes(winner)) {{
                    btn.classList.add('selected');
                }}
            }});
        }}
        
        function randomizeGames() {{
            week18Games.forEach(game => {{
                const winner = Math.random() > 0.5 ? game.home : game.away;
                selectWinner(game.id, winner);
            }});
        }}
        
        function resetGames() {{
            gameSelections = {{}};
            document.querySelectorAll('.game-btn').forEach(btn => {{
                btn.classList.remove('selected');
            }});
            document.getElementById('results').classList.add('hidden');
        }}
        
        function simulatePlayoffs() {{
            const allGamesSelected = week18Games.every(g => gameSelections[g.id]);
            if (!allGamesSelected) {{
                alert('Please select a winner for all Week 18 games first!');
                return;
            }}
            
            const finalStats = calculateFinalStats();
            const {{ playoffs, eliminated }} = determinePlayoffSeeding(finalStats);
            
            displayResults(playoffs, eliminated, finalStats);
            document.getElementById('results').classList.remove('hidden');
        }}
        
        function calculateFinalStats() {{
            const stats = {{}};
            
            for (let team in teamsInfo) {{
                if (!currentStandings[team]) {{
                    console.error('Missing standings for team:', team);
                    continue;
                }}
                stats[team] = {{
                    W: currentStandings[team].W,
                    L: currentStandings[team].L,
                    T: currentStandings[team].T,
                    win_pct: currentStandings[team].win_pct,
                    conference_W: 0,
                    conference_L: 0,
                    division_W: 0,
                    division_L: 0,
                    points_for: 0,
                    points_against: 0,
                    conference_points_for: 0,
                    conference_points_against: 0,
                    touchdowns: 0,
                    head_to_head: {{}},
                    opponents: [],
                    defeated_opponents: [],
                    game_results: []
                }};
            }}
            
            completedGames.forEach(game => {{
                processGame(stats, game.home, game.away, game.home_score, game.away_score);
            }});
            
            week18Games.forEach(game => {{
                const winner = gameSelections[game.id];
                if (winner) {{
                    const isHomeWin = winner === game.home;
                    const home_score = isHomeWin ? 24 : 17;
                    const away_score = isHomeWin ? 17 : 24;
                    processGame(stats, game.home, game.away, home_score, away_score, true);
                }}
            }});
            
            for (let team in stats) {{
                const total = stats[team].W + stats[team].L + stats[team].T;
                stats[team].win_pct = total > 0 ? (stats[team].W + 0.5 * stats[team].T) / total : 0;
                
                const conf_total = stats[team].conference_W + stats[team].conference_L;
                stats[team].conference_pct = conf_total > 0 ? stats[team].conference_W / conf_total : 0;
                
                const div_total = stats[team].division_W + stats[team].division_L;
                stats[team].division_pct = div_total > 0 ? stats[team].division_W / div_total : 0;
                
                stats[team].strength_of_victory = 0;
                if (stats[team].defeated_opponents.length > 0) {{
                    const sum = stats[team].defeated_opponents.reduce((acc, opp) => acc + stats[opp].win_pct, 0);
                    stats[team].strength_of_victory = sum / stats[team].defeated_opponents.length;
                }}
                
                stats[team].strength_of_schedule = 0;
                if (stats[team].opponents.length > 0) {{
                    const sum = stats[team].opponents.reduce((acc, opp) => acc + stats[opp].win_pct, 0);
                    stats[team].strength_of_schedule = sum / stats[team].opponents.length;
                }}
            }}
            
            return stats;
        }}
        
        function processGame(stats, home, away, home_score, away_score, isWeek18 = false) {{
            if (isWeek18) {{
                if (home_score > away_score) {{
                    stats[home].W++;
                    stats[away].L++;
                }} else {{
                    stats[away].W++;
                    stats[home].L++;
                }}
            }}
            
            stats[home].game_results.push({{ opponent: away, pf: home_score, pa: away_score }});
            stats[away].game_results.push({{ opponent: home, pf: away_score, pa: home_score }});
            
            stats[home].points_for += home_score;
            stats[home].points_against += away_score;
            stats[away].points_for += away_score;
            stats[away].points_against += home_score;
            
            stats[home].touchdowns += Math.floor(home_score / 7);
            stats[away].touchdowns += Math.floor(away_score / 7);
            
            stats[home].opponents.push(away);
            stats[away].opponents.push(home);
            
            const home_conf = teamsInfo[home].conference;
            const away_conf = teamsInfo[away].conference;
            const home_div = teamsInfo[home].division;
            const away_div = teamsInfo[away].division;
            
            if (home_score > away_score) {{
                stats[home].defeated_opponents.push(away);
                
                if (!stats[home].head_to_head[away]) stats[home].head_to_head[away] = {{ W: 0, L: 0 }};
                if (!stats[away].head_to_head[home]) stats[away].head_to_head[home] = {{ W: 0, L: 0 }};
                stats[home].head_to_head[away].W++;
                stats[away].head_to_head[home].L++;
                
                if (home_conf === away_conf) {{
                    stats[home].conference_W++;
                    stats[away].conference_L++;
                    stats[home].conference_points_for += home_score;
                    stats[home].conference_points_against += away_score;
                    stats[away].conference_points_for += away_score;
                    stats[away].conference_points_against += home_score;
                }}
                
                if (home_div === away_div) {{
                    stats[home].division_W++;
                    stats[away].division_L++;
                }}
            }} else if (away_score > home_score) {{
                stats[away].defeated_opponents.push(home);
                
                if (!stats[home].head_to_head[away]) stats[home].head_to_head[away] = {{ W: 0, L: 0 }};
                if (!stats[away].head_to_head[home]) stats[away].head_to_head[home] = {{ W: 0, L: 0 }};
                stats[away].head_to_head[home].W++;
                stats[home].head_to_head[away].L++;
                
                if (home_conf === away_conf) {{
                    stats[away].conference_W++;
                    stats[home].conference_L++;
                    stats[home].conference_points_for += home_score;
                    stats[home].conference_points_against += away_score;
                    stats[away].conference_points_for += away_score;
                    stats[away].conference_points_against += home_score;
                }}
                
                if (home_div === away_div) {{
                    stats[away].division_W++;
                    stats[home].division_L++;
                }}
            }}
        }}
        
        function determinePlayoffSeeding(stats) {{
            const results = {{ AFC: [], NFC: [] }};
            const eliminated = {{ AFC: [], NFC: [] }};
            
            ['AFC', 'NFC'].forEach(conf => {{
                const confTeams = Object.keys(teamsInfo).filter(t => teamsInfo[t].conference === conf);
                
                const divisions = {{}};
                confTeams.forEach(team => {{
                    const div = teamsInfo[team].division;
                    if (!divisions[div]) divisions[div] = [];
                    divisions[div].push(team);
                }});
                
                const divisionWinners = [];
                const divisionRunnerUps = [];
                
                for (let div in divisions) {{
                    const divTeams = divisions[div];
                    const ranked = applyTiebreakers(divTeams, stats, true, divTeams.length);
                    if (ranked && ranked.length > 0) {{
                        divisionWinners.push({{
                            team: ranked[0].team,
                            record: ranked[0].record,
                            tiebreaker: ranked[0].tiebreaker,
                            division: div
                        }});
                        
                        for (let i = 1; i < ranked.length; i++) {{
                            divisionRunnerUps.push({{
                                team: ranked[i].team,
                                record: ranked[i].record,
                                division: div,
                                divRank: i + 1,
                                reason: `${{div.replace(conf + ' ', '')}}: Finished #${{i + 1}} in division${{ranked[i].tiebreaker ? ' (' + ranked[i].tiebreaker + ')' : ''}}`
                            }});
                        }}
                    }}
                }}
                
                divisionWinners.sort((a, b) => {{
                    if (!stats[a.team] || !stats[b.team]) {{
                        console.error('Missing stats for teams:', a.team, b.team);
                        return 0;
                    }}
                    const aPct = stats[a.team].win_pct;
                    const bPct = stats[b.team].win_pct;
                    return bPct - aPct;
                }});
                
                const wildCardTeams = [];
                confTeams.forEach(team => {{
                    if (!divisionWinners.find(dw => dw.team === team)) {{
                        wildCardTeams.push(team);
                    }}
                }});
                
                const rankedWildCards = applyTiebreakers(wildCardTeams, stats, false, wildCardTeams.length);
                const topWildCards = rankedWildCards.slice(0, 3);
                const missedWildCards = rankedWildCards.slice(3);
                
                missedWildCards.forEach((team, index) => {{
                    const wcRank = index + 4;
                    eliminated[conf].push({{
                        team: team.team,
                        record: team.record,
                        reason: `Wild Card: Finished #${{wcRank}} in conference${{team.tiebreaker ? ' (' + team.tiebreaker + ')' : ''}}`
                    }});
                }});
                
                results[conf] = [
                    ...divisionWinners.slice(0, 4),
                    ...topWildCards
                ];
            }});
            
            return {{ playoffs: results, eliminated }};
        }}
        
        function applyTiebreakers(teams, stats, isDivision = false, limit = 1) {{
            if (teams.length === 0) return [];
            if (teams.length === 1) return [{{ team: teams[0], record: `${{stats[teams[0]].W}}-${{stats[teams[0]].L}}-${{stats[teams[0]].T}}`, tiebreaker: null }}];
            
            const winPctGroups = {{}};
            teams.forEach(team => {{
                const pct = stats[team].win_pct;
                if (!winPctGroups[pct]) winPctGroups[pct] = [];
                winPctGroups[pct].push(team);
            }});
            
            const sortedPcts = Object.keys(winPctGroups).map(Number).sort((a, b) => b - a);
            const results = [];
            
            for (let pct of sortedPcts) {{
                const tiedTeams = winPctGroups[pct];
                
                if (tiedTeams.length === 1) {{
                    results.push({{
                        team: tiedTeams[0],
                        record: `${{stats[tiedTeams[0]].W}}-${{stats[tiedTeams[0]].L}}-${{stats[tiedTeams[0]].T}}`,
                        tiebreaker: null
                    }});
                }} else {{
                    const resolved = resolveTie(tiedTeams, stats, isDivision);
                    results.push(...resolved);
                }}
                
                if (results.length >= limit) break;
            }}
            
            return results.slice(0, limit);
        }}
        
        function resolveTie(teams, stats, isDivision) {{
            if (teams.length === 2) {{
                return resolveTwoTeamTie(teams, stats, isDivision);
            }} else {{
                return resolveMultiTeamTie(teams, stats, isDivision);
            }}
        }}
        
        function resolveTwoTeamTie(teams, stats, isDivision) {{
            const t1 = teams[0];
            const t2 = teams[1];
            let winner = null;
            let tiebreaker = '';
            
            const h2h = checkHeadToHead([t1, t2], stats);
            if (h2h.winner) {{
                winner = h2h.winner;
                tiebreaker = `Head-to-head: won ${{h2h.wins}}-${{h2h.losses}}`;
                return formatTiebreakerResults([winner], teams.filter(t => t !== winner), stats, tiebreaker);
            }}
            
            if (isDivision) {{
                const result = checkBestInGroup(teams, stats, 'division_pct');
                if (result.winner) {{
                    return formatTiebreakerResults([result.winner], teams.filter(t => t !== result.winner), stats, 
                        `Division record: ${{result.value.toFixed(3)}}`);
                }}
            }}
            
            const commonGames = getCommonGames(teams, stats);
            if (commonGames.length >= 4) {{
                const result = checkCommonGamesRecord(teams, stats, commonGames);
                if (result.winner) {{
                    return formatTiebreakerResults([result.winner], teams.filter(t => t !== result.winner), stats, 
                        result.detail);
                }}
            }}
            
            const confResult = checkBestInGroup(teams, stats, 'conference_pct');
            if (confResult.winner) {{
                return formatTiebreakerResults([confResult.winner], teams.filter(t => t !== confResult.winner), stats, 
                    `Conference record: ${{confResult.value.toFixed(3)}}`);
            }}
            
            const sovResult = checkBestInGroup(teams, stats, 'strength_of_victory');
            if (sovResult.winner) {{
                return formatTiebreakerResults([sovResult.winner], teams.filter(t => t !== sovResult.winner), stats, 
                    `Strength of victory: ${{sovResult.value.toFixed(3)}}`);
            }}
            
            const sosResult = checkBestInGroup(teams, stats, 'strength_of_schedule');
            if (sosResult.winner) {{
                return formatTiebreakerResults([sosResult.winner], teams.filter(t => t !== sosResult.winner), stats, 
                    `Strength of schedule: ${{sosResult.value.toFixed(3)}}`);
            }}
            
            const confRanking = calculateCombinedRanking(teams, stats, true);
            if (confRanking.winner) {{
                return formatTiebreakerResults([confRanking.winner], teams.filter(t => t !== confRanking.winner), stats, 
                    `Combined ranking (conf): ${{confRanking.score}}`);
            }}
            
            const allRanking = calculateCombinedRanking(teams, stats, false);
            if (allRanking.winner) {{
                return formatTiebreakerResults([allRanking.winner], teams.filter(t => t !== allRanking.winner), stats, 
                    `Combined ranking (all): ${{allRanking.score}}`);
            }}
            
            if (isDivision) {{
                const netPtsCommon = calculateNetPoints(teams, stats, commonGames);
                if (netPtsCommon.winner) {{
                    return formatTiebreakerResults([netPtsCommon.winner], teams.filter(t => t !== netPtsCommon.winner), stats, 
                        netPtsCommon.detail);
                }}
            }} else {{
                const netPtsConf = calculateNetPointsConference(teams, stats);
                if (netPtsConf.winner) {{
                    return formatTiebreakerResults([netPtsConf.winner], teams.filter(t => t !== netPtsConf.winner), stats, 
                        `Net points in conference games: ${{netPtsConf.value > 0 ? '+' : ''}}${{netPtsConf.value}}`);
                }}
            }}
            
            const netPtsAll = calculateNetPointsAll(teams, stats);
            if (netPtsAll.winner) {{
                return formatTiebreakerResults([netPtsAll.winner], teams.filter(t => t !== netPtsAll.winner), stats, 
                    `Net points in all games: ${{netPtsAll.value > 0 ? '+' : ''}}${{netPtsAll.value}}`);
            }}
            
            const netTds = calculateNetTouchdowns(teams, stats);
            if (netTds.winner) {{
                return formatTiebreakerResults([netTds.winner], teams.filter(t => t !== netTds.winner), stats, 
                    `Net touchdowns: ${{netTds.value > 0 ? '+' : ''}}${{netTds.value}}`);
            }}
            
            return formatTiebreakerResults(teams, [], stats, 'Coin toss');
        }}
        
        function resolveMultiTeamTie(teams, stats, isDivision) {{
            let remaining = [...teams];
            const eliminated = [];
            let tiebreaker = '';
            
            if (teams.length >= 2) {{
                const h2hSweep = checkHeadToHeadSweep(remaining, stats);
                if (h2hSweep.winner) {{
                    return formatTiebreakerResults([h2hSweep.winner], remaining.filter(t => t !== h2hSweep.winner), stats, 
                        `Head-to-head sweep`);
                }}
            }}
            
            if (isDivision) {{
                const divResult = eliminateByMetric(remaining, stats, 'division_pct');
                if (divResult.remaining.length < remaining.length) {{
                    remaining = divResult.remaining;
                    if (remaining.length === 1) {{
                        return formatTiebreakerResults(remaining, teams.filter(t => !remaining.includes(t)), stats, 
                            `Division record: ${{divResult.topValue.toFixed(3)}}`);
                    }} else if (remaining.length === 2) {{
                        return resolveTwoTeamTie(remaining, stats, isDivision);
                    }}
                }}
            }}
            
            const commonGames = getCommonGames(remaining, stats);
            if (commonGames.length >= 4) {{
                const cgResult = eliminateByCommonGames(remaining, stats, commonGames);
                if (cgResult.remaining.length < remaining.length) {{
                    remaining = cgResult.remaining;
                    if (remaining.length === 1) {{
                        return formatTiebreakerResults(remaining, teams.filter(t => !remaining.includes(t)), stats, 
                            cgResult.detail);
                    }} else if (remaining.length === 2) {{
                        return resolveTwoTeamTie(remaining, stats, isDivision);
                    }}
                }}
            }}
            
            const confResult = eliminateByMetric(remaining, stats, 'conference_pct');
            if (confResult.remaining.length < remaining.length) {{
                remaining = confResult.remaining;
                if (remaining.length === 1) {{
                    return formatTiebreakerResults(remaining, teams.filter(t => !remaining.includes(t)), stats, 
                        `Conference record: ${{confResult.topValue.toFixed(3)}}`);
                }} else if (remaining.length === 2) {{
                    return resolveTwoTeamTie(remaining, stats, isDivision);
                }}
            }}
            
            const sovResult = eliminateByMetric(remaining, stats, 'strength_of_victory');
            if (sovResult.remaining.length < remaining.length) {{
                remaining = sovResult.remaining;
                if (remaining.length === 1) {{
                    return formatTiebreakerResults(remaining, teams.filter(t => !remaining.includes(t)), stats, 
                        `Strength of victory: ${{sovResult.topValue.toFixed(3)}}`);
                }} else if (remaining.length === 2) {{
                    return resolveTwoTeamTie(remaining, stats, isDivision);
                }}
            }}
            
            const sosResult = eliminateByMetric(remaining, stats, 'strength_of_schedule');
            if (sosResult.remaining.length < remaining.length) {{
                remaining = sosResult.remaining;
                if (remaining.length === 1) {{
                    return formatTiebreakerResults(remaining, teams.filter(t => !remaining.includes(t)), stats, 
                        `Strength of schedule: ${{sosResult.topValue.toFixed(3)}}`);
                }} else if (remaining.length === 2) {{
                    return resolveTwoTeamTie(remaining, stats, isDivision);
                }}
            }}
            
            return formatTiebreakerResults(remaining, teams.filter(t => !remaining.includes(t)), stats, 'Multiple tiebreakers');
        }}
        
        function formatTiebreakerResults(winners, losers, stats, tiebreaker) {{
            const results = [];
            winners.forEach(team => {{
                results.push({{
                    team,
                    record: `${{stats[team].W}}-${{stats[team].L}}-${{stats[team].T}}`,
                    tiebreaker
                }});
            }});
            losers.forEach(team => {{
                results.push({{
                    team,
                    record: `${{stats[team].W}}-${{stats[team].L}}-${{stats[team].T}}`,
                    tiebreaker: null
                }});
            }});
            return results;
        }}
        
        function checkHeadToHead(teams, stats) {{
            if (teams.length !== 2) return {{ winner: null }};
            
            const t1 = teams[0];
            const t2 = teams[1];
            
            const h2h = stats[t1].head_to_head[t2];
            if (!h2h || h2h.W + h2h.L === 0) return {{ winner: null }};
            
            if (h2h.W > h2h.L) {{
                return {{ winner: t1, wins: h2h.W, losses: h2h.L }};
            }} else if (h2h.L > h2h.W) {{
                return {{ winner: t2, wins: h2h.L, losses: h2h.W }};
            }}
            
            return {{ winner: null }};
        }}
        
        function checkHeadToHeadSweep(teams, stats) {{
            for (let team of teams) {{
                let swept = true;
                for (let opp of teams) {{
                    if (team === opp) continue;
                    const h2h = stats[team].head_to_head[opp];
                    if (!h2h || h2h.W === 0 || h2h.L > 0) {{
                        swept = false;
                        break;
                    }}
                }}
                if (swept) return {{ winner: team }};
            }}
            return {{ winner: null }};
        }}
        
        function checkBestInGroup(teams, stats, metric) {{
            let bestTeam = null;
            let bestValue = -1;
            let uniqueBest = true;
            
            teams.forEach(team => {{
                const value = stats[team][metric];
                if (value > bestValue) {{
                    bestValue = value;
                    bestTeam = team;
                    uniqueBest = true;
                }} else if (Math.abs(value - bestValue) < 0.001) {{
                    uniqueBest = false;
                }}
            }});
            
            return uniqueBest ? {{ winner: bestTeam, value: bestValue }} : {{ winner: null }};
        }}
        
        function eliminateByMetric(teams, stats, metric) {{
            if (teams.length === 0) return {{ remaining: [], topValue: 0 }};
            
            let bestValue = -1;
            teams.forEach(team => {{
                const value = stats[team][metric];
                if (value > bestValue) bestValue = value;
            }});
            
            const remaining = teams.filter(team => {{
                return Math.abs(stats[team][metric] - bestValue) < 0.001;
            }});
            
            return {{ remaining, topValue: bestValue }};
        }}
        
        function getCommonGames(teams, stats) {{
            if (teams.length < 2) return [];
            
            const opponentSets = teams.map(team => new Set(stats[team].opponents));
            const commonOpponents = [...opponentSets[0]].filter(opp => {{
                return opponentSets.every(set => set.has(opp));
            }});
            
            return commonOpponents;
        }}
        
        function checkCommonGamesRecord(teams, stats, commonGames) {{
            if (commonGames.length < 4) return {{ winner: null }};
            
            const records = teams.map(team => {{
                let w = 0, l = 0, t = 0;
                const gameDetails = [];
                stats[team].game_results.forEach(game => {{
                    if (commonGames.includes(game.opponent)) {{
                        let result = '';
                        if (game.pf > game.pa) {{
                            w++;
                            result = 'W';
                        }} else if (game.pf < game.pa) {{
                            l++;
                            result = 'L';
                        }} else {{
                            t++;
                            result = 'T';
                        }}
                        gameDetails.push({{ opp: game.opponent, result, score: `${{game.pf}}-${{game.pa}}` }});
                    }}
                }});
                const pct = (w + 0.5 * t) / (w + l + t);
                return {{ team, w, l, t, pct, gameDetails }};
            }});
            
            records.sort((a, b) => b.pct - a.pct);
            
            if (records[0].pct > records[1].pct) {{
                const commonOppList = commonGames.sort().join(', ');
                let detailStr = `Common games (${{commonGames.length}} opponents: ${{commonOppList}}): `;
                
                records.forEach((rec, idx) => {{
                    if (idx > 0) detailStr += ' vs ';
                    detailStr += `${{rec.team}} ${{rec.w}}-${{rec.l}}`;
                    if (rec.t > 0) detailStr += `-${{rec.t}}`;
                    detailStr += ` (`;
                    rec.gameDetails.forEach((game, gidx) => {{
                        if (gidx > 0) detailStr += ', ';
                        detailStr += `${{game.result}} vs ${{game.opp}} ${{game.score}}`;
                    }});
                    detailStr += `)`;
                }});
                
                return {{ winner: records[0].team, record: `${{records[0].w}}-${{records[0].l}}-${{records[0].t}}`, detail: detailStr }};
            }}
            
            return {{ winner: null }};
        }}
        
        function eliminateByCommonGames(teams, stats, commonGames) {{
            if (commonGames.length < 4) return {{ remaining: teams, detail: null }};
            
            const records = teams.map(team => {{
                let w = 0, l = 0, t = 0;
                const gameDetails = [];
                stats[team].game_results.forEach(game => {{
                    if (commonGames.includes(game.opponent)) {{
                        let result = '';
                        if (game.pf > game.pa) {{
                            w++;
                            result = 'W';
                        }} else if (game.pf < game.pa) {{
                            l++;
                            result = 'L';
                        }} else {{
                            t++;
                            result = 'T';
                        }}
                        gameDetails.push({{ opp: game.opponent, result, score: `${{game.pf}}-${{game.pa}}` }});
                    }}
                }});
                const pct = (w + 0.5 * t) / (w + l + t);
                return {{ team, w, l, t, pct, gameDetails }};
            }});
            
            const maxPct = Math.max(...records.map(r => r.pct));
            const remaining = records.filter(r => Math.abs(r.pct - maxPct) < 0.001).map(r => r.team);
            
            const commonOppList = commonGames.sort().join(', ');
            let detailStr = `Common games (${{commonGames.length}} opponents: ${{commonOppList}}): `;
            
            records.sort((a, b) => b.pct - a.pct);
            records.forEach((rec, idx) => {{
                if (idx > 0) detailStr += ' vs ';
                detailStr += `${{rec.team}} ${{rec.w}}-${{rec.l}}`;
                if (rec.t > 0) detailStr += `-${{rec.t}}`;
                detailStr += ` (`;
                rec.gameDetails.forEach((game, gidx) => {{
                    if (gidx > 0) detailStr += ', ';
                    detailStr += `${{game.result}} vs ${{game.opp}} ${{game.score}}`;
                }});
                detailStr += `)`;
            }});
            
            return {{ remaining, detail: detailStr }};
        }}
        
        function calculateCombinedRanking(teams, stats, conferenceOnly) {{
            const conf = teamsInfo[teams[0]].conference;
            const confTeams = Object.keys(teamsInfo).filter(t => teamsInfo[t].conference === conf);
            
            const allTeams = conferenceOnly ? confTeams : Object.keys(teamsInfo);
            
            const pfRanking = [...allTeams].sort((a, b) => stats[b].points_for - stats[a].points_for);
            const paRanking = [...allTeams].sort((a, b) => stats[a].points_against - stats[b].points_against);
            
            const rankings = teams.map(team => {{
                let pfRank = pfRanking.indexOf(team) + 1;
                let paRank = paRanking.indexOf(team) + 1;
                
                for (let i = 0; i < pfRanking.length; i++) {{
                    if (pfRanking[i] === team) break;
                    if (i > 0 && stats[pfRanking[i]].points_for === stats[pfRanking[i-1]].points_for) {{
                        pfRank = pfRanking.indexOf(pfRanking[i-1]) + 1;
                    }}
                }}
                
                for (let i = 0; i < paRanking.length; i++) {{
                    if (paRanking[i] === team) break;
                    if (i > 0 && stats[paRanking[i]].points_against === stats[paRanking[i-1]].points_against) {{
                        paRank = paRanking.indexOf(paRanking[i-1]) + 1;
                    }}
                }}
                
                return {{ team, score: pfRank + paRank }};
            }});
            
            rankings.sort((a, b) => a.score - b.score);
            
            if (rankings[0].score < rankings[1].score) {{
                return {{ winner: rankings[0].team, score: rankings[0].score }};
            }}
            
            return {{ winner: null }};
        }}
        
        function calculateNetPoints(teams, stats, commonGames) {{
            if (commonGames.length < 4) return {{ winner: null }};
            
            const netPoints = teams.map(team => {{
                let pf = 0, pa = 0;
                const gameDetails = [];
                stats[team].game_results.forEach(game => {{
                    if (commonGames.includes(game.opponent)) {{
                        pf += game.pf;
                        pa += game.pa;
                        gameDetails.push({{ opp: game.opponent, score: `${{game.pf}}-${{game.pa}}` }});
                    }}
                }});
                return {{ team, net: pf - pa, pf, pa, gameDetails }};
            }});
            
            netPoints.sort((a, b) => b.net - a.net);
            
            if (netPoints[0].net > netPoints[1].net) {{
                const commonOppList = commonGames.sort().join(', ');
                let detailStr = `Net points in common games (vs ${{commonOppList}}): `;
                
                netPoints.forEach((np, idx) => {{
                    if (idx > 0) detailStr += ' vs ';
                    detailStr += `${{np.team}} ${{np.net > 0 ? '+' : ''}}${{np.net}} (PF:${{np.pf}}, PA:${{np.pa}} - `;
                    np.gameDetails.forEach((game, gidx) => {{
                        if (gidx > 0) detailStr += ', ';
                        detailStr += `${{game.opp}} ${{game.score}}`;
                    }});
                    detailStr += `)`;
                }});
                
                return {{ winner: netPoints[0].team, value: netPoints[0].net, detail: detailStr }};
            }}
            
            return {{ winner: null }};
        }}
        
        function calculateNetPointsConference(teams, stats) {{
            const netPoints = teams.map(team => {{
                const net = stats[team].conference_points_for - stats[team].conference_points_against;
                return {{ team, net }};
            }});
            
            netPoints.sort((a, b) => b.net - a.net);
            
            if (netPoints[0].net > netPoints[1].net) {{
                return {{ winner: netPoints[0].team, value: netPoints[0].net }};
            }}
            
            return {{ winner: null }};
        }}
        
        function calculateNetPointsAll(teams, stats) {{
            const netPoints = teams.map(team => {{
                const net = stats[team].points_for - stats[team].points_against;
                return {{ team, net }};
            }});
            
            netPoints.sort((a, b) => b.net - a.net);
            
            if (netPoints[0].net > netPoints[1].net) {{
                return {{ winner: netPoints[0].team, value: netPoints[0].net }};
            }}
            
            return {{ winner: null }};
        }}
        
        function calculateNetTouchdowns(teams, stats) {{
            const netTds = teams.map(team => {{
                let ownTds = stats[team].touchdowns;
                let oppTds = 0;
                stats[team].game_results.forEach(game => {{
                    oppTds += Math.floor(game.pa / 7);
                }});
                return {{ team, net: ownTds - oppTds }};
            }});
            
            netTds.sort((a, b) => b.net - a.net);
            
            if (netTds[0].net > netTds[1].net) {{
                return {{ winner: netTds[0].team, value: netTds[0].net }};
            }}
            
            return {{ winner: null }};
        }}
        
        function displayResults(playoffSeeds, eliminated, stats) {{
            ['AFC', 'NFC'].forEach(conf => {{
                const container = document.getElementById(`${{conf.toLowerCase()}}-results`);
                container.innerHTML = '';
                
                const playoffHeader = document.createElement('h4');
                playoffHeader.style.marginBottom = '15px';
                playoffHeader.style.color = '#10b981';
                playoffHeader.textContent = '✓ Playoff Teams';
                container.appendChild(playoffHeader);
                
                playoffSeeds[conf].forEach((seed, index) => {{
                    const seedNum = index + 1;
                    const seedClass = seedNum <= 4 ? `seed-${{seedNum}}` : 'seed-wc';
                    const seedLabel = seedNum <= 4 ? `Seed ${{seedNum}}` : `WC ${{seedNum}}`;
                    
                    const divLabel = seed.division ? ` • ${{seed.division.replace(conf + ' ', '')}}` : '';
                    const teamLogo = teamsInfo[seed.team].logo_url;
                    
                    const seedDiv = document.createElement('div');
                    seedDiv.className = `seed-team ${{seedClass}}`;
                    seedDiv.innerHTML = `
                        <div class="seed-header">
                            <span class="seed-badge">${{seedLabel}}</span>
                            <span class="team-record">${{seed.record}}</span>
                        </div>
                        <div class="team-name">
                            <img src="${{teamLogo}}" class="team-logo" alt="${{seed.team}}">
                            <span>${{seed.team}}${{divLabel}}</span>
                        </div>
                        ${{seed.tiebreaker ? `<div class="tiebreaker-info">🔧 Tiebreaker: ${{seed.tiebreaker}}</div>` : ''}}
                    `;
                    container.appendChild(seedDiv);
                }});
                
                if (eliminated[conf].length > 0) {{
                    const elimHeader = document.createElement('h4');
                    elimHeader.style.marginTop = '25px';
                    elimHeader.style.marginBottom = '15px';
                    elimHeader.style.color = '#ef4444';
                    elimHeader.textContent = '✗ Eliminated Teams';
                    container.appendChild(elimHeader);
                    
                    eliminated[conf].sort((a, b) => {{
                        return stats[b.team].win_pct - stats[a.team].win_pct;
                    }});
                    
                    eliminated[conf].forEach(team => {{
                        const teamLogo = teamsInfo[team.team].logo_url;
                        
                        const elimDiv = document.createElement('div');
                        elimDiv.className = 'seed-team eliminated-team';
                        elimDiv.innerHTML = `
                            <div class="seed-header">
                                <span class="team-record">${{team.record}}</span>
                            </div>
                            <div class="team-name">
                                <img src="${{teamLogo}}" class="team-logo" alt="${{team.team}}">
                                <span>${{team.team}}</span>
                            </div>
                            <div class="elimination-info">❌ ${{team.reason}}</div>
                        `;
                        container.appendChild(elimDiv);
                    }});
                }}
            }});
        }}
        
        initializeGames();
    </script>
</body>
</html>
'''
    
    with open('docs/week18_simulator.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Week 18 simulator generated: docs/week18_simulator.html")

if __name__ == '__main__':
    generate_html()
