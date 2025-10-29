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
        .qualification-info {{
            margin-top: 8px;
            padding: 8px;
            background: #d1fae5;
            border-radius: 5px;
            font-size: 0.85em;
            color: #065f46;
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
                
                if (!stats[home].head_to_head[away]) stats[home].head_to_head[away] = {{ W: 0, L: 0, T: 0 }};
                if (!stats[away].head_to_head[home]) stats[away].head_to_head[home] = {{ W: 0, L: 0, T: 0 }};
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
                
                if (!stats[home].head_to_head[away]) stats[home].head_to_head[away] = {{ W: 0, L: 0, T: 0 }};
                if (!stats[away].head_to_head[home]) stats[away].head_to_head[home] = {{ W: 0, L: 0, T: 0 }};
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
        
        function breakTwoTeamDivisionTie(teams, stats) {{
            const [team1, team2] = teams;
            
            const h2h1 = stats[team1].head_to_head[team2] || {{ W: 0, L: 0, T: 0 }};
            const h2hTotal = h2h1.W + h2h1.L + h2h1.T;
            if (h2hTotal > 0) {{
                const h2h1Pct = (h2h1.W + 0.5 * h2h1.T) / h2hTotal;
                const h2h2Pct = (h2h1.L + 0.5 * h2h1.T) / h2hTotal;
                if (h2h1Pct > h2h2Pct) return {{ winner: team1, tiebreaker: `Head-to-head: won ${{h2h1.W}}-${{h2h1.L}}` }};
                if (h2h2Pct > h2h1Pct) return {{ winner: team2, tiebreaker: `Head-to-head: won ${{h2h1.L}}-${{h2h1.W}}` }};
            }}
            
            if (stats[team1].division_pct > stats[team2].division_pct) {{
                return {{ winner: team1, tiebreaker: `Division record: ${{stats[team1].division_W}}-${{stats[team1].division_L}}` }};
            }}
            if (stats[team2].division_pct > stats[team1].division_pct) {{
                return {{ winner: team2, tiebreaker: `Division record: ${{stats[team2].division_W}}-${{stats[team2].division_L}}` }};
            }}
            
            const commonOpps = new Set(stats[team1].opponents.filter(o => stats[team2].opponents.includes(o)));
            if (commonOpps.size >= 4) {{
                const common1W = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf > g.pa).length;
                const common1L = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf < g.pa).length;
                const common1T = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf === g.pa).length;
                const common1Total = common1W + common1L + common1T;
                const common1Pct = common1Total > 0 ? (common1W + 0.5 * common1T) / common1Total : 0;
                
                const common2W = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf > g.pa).length;
                const common2L = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf < g.pa).length;
                const common2T = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf === g.pa).length;
                const common2Total = common2W + common2L + common2T;
                const common2Pct = common2Total > 0 ? (common2W + 0.5 * common2T) / common2Total : 0;
                
                if (common1Pct > common2Pct) {{
                    return {{ winner: team1, tiebreaker: `Common games: ${{common1W}}-${{common1L}}-${{common1T}}` }};
                }}
                if (common2Pct > common1Pct) {{
                    return {{ winner: team2, tiebreaker: `Common games: ${{common2W}}-${{common2L}}-${{common2T}}` }};
                }}
            }}
            
            if (stats[team1].conference_pct > stats[team2].conference_pct) {{
                return {{ winner: team1, tiebreaker: `Conference record: ${{stats[team1].conference_W}}-${{stats[team1].conference_L}}` }};
            }}
            if (stats[team2].conference_pct > stats[team1].conference_pct) {{
                return {{ winner: team2, tiebreaker: `Conference record: ${{stats[team2].conference_W}}-${{stats[team2].conference_L}}` }};
            }}
            
            if (stats[team1].strength_of_victory > stats[team2].strength_of_victory) {{
                return {{ winner: team1, tiebreaker: `Strength of victory: ${{stats[team1].strength_of_victory.toFixed(3)}}` }};
            }}
            if (stats[team2].strength_of_victory > stats[team1].strength_of_victory) {{
                return {{ winner: team2, tiebreaker: `Strength of victory: ${{stats[team2].strength_of_victory.toFixed(3)}}` }};
            }}
            
            if (stats[team1].strength_of_schedule > stats[team2].strength_of_schedule) {{
                return {{ winner: team1, tiebreaker: `Strength of schedule: ${{stats[team1].strength_of_schedule.toFixed(3)}}` }};
            }}
            if (stats[team2].strength_of_schedule > stats[team1].strength_of_schedule) {{
                return {{ winner: team2, tiebreaker: `Strength of schedule: ${{stats[team2].strength_of_schedule.toFixed(3)}}` }};
            }}
            
            const commonNet1 = stats[team1].game_results.filter(g => commonOpps.has(g.opponent)).reduce((sum, g) => sum + (g.pf - g.pa), 0);
            const commonNet2 = stats[team2].game_results.filter(g => commonOpps.has(g.opponent)).reduce((sum, g) => sum + (g.pf - g.pa), 0);
            if (commonNet1 > commonNet2) {{
                return {{ winner: team1, tiebreaker: `Net points in common games: +${{commonNet1}}` }};
            }}
            if (commonNet2 > commonNet1) {{
                return {{ winner: team2, tiebreaker: `Net points in common games: +${{commonNet2}}` }};
            }}
            
            const net1 = stats[team1].points_for - stats[team1].points_against;
            const net2 = stats[team2].points_for - stats[team2].points_against;
            if (net1 > net2) {{
                return {{ winner: team1, tiebreaker: `Net points in all games: +${{net1}}` }};
            }}
            if (net2 > net1) {{
                return {{ winner: team2, tiebreaker: `Net points in all games: +${{net2}}` }};
            }}
            
            if (stats[team1].touchdowns > stats[team2].touchdowns) {{
                return {{ winner: team1, tiebreaker: `Net touchdowns: ${{stats[team1].touchdowns}}` }};
            }}
            if (stats[team2].touchdowns > stats[team1].touchdowns) {{
                return {{ winner: team2, tiebreaker: `Net touchdowns: ${{stats[team2].touchdowns}}` }};
            }}
            
            return {{ winner: team1, tiebreaker: 'Coin toss' }};
        }}
        
        function breakMultiTeamDivisionTie(teams, stats) {{
            let remaining = [...teams];
            
            const h2hRecords = {{}};
            for (const team of remaining) {{
                let h2hW = 0, h2hL = 0, h2hT = 0;
                for (const opp of remaining) {{
                    if (team !== opp) {{
                        const h2h = stats[team].head_to_head[opp] || {{ W: 0, L: 0, T: 0 }};
                        h2hW += h2h.W;
                        h2hL += h2h.L;
                        h2hT += h2h.T;
                    }}
                }}
                const h2hTotal = h2hW + h2hL + h2hT;
                h2hRecords[team] = h2hTotal > 0 ? (h2hW + 0.5 * h2hT) / h2hTotal : 0;
            }}
            
            const uniqueH2HPercentages = new Set(Object.values(h2hRecords));
            if (uniqueH2HPercentages.size === remaining.length) {{
                remaining.sort((a, b) => h2hRecords[b] - h2hRecords[a]);
                return {{ ranked: remaining, tiebreaker: 'Head-to-head record' }};
            }}
            
            remaining.sort((a, b) => stats[b].division_pct - stats[a].division_pct);
            if (stats[remaining[0]].division_pct > stats[remaining[1]].division_pct) {{
                const winner = remaining[0];
                const rest = remaining.slice(1);
                const tiebreaker = `Division record: ${{stats[winner].division_W}}-${{stats[winner].division_L}}`;
                if (rest.length === 1) {{
                    return {{ ranked: [winner, rest[0]], tiebreaker }};
                }} else if (rest.length === 2) {{
                    const result = breakTwoTeamDivisionTie(rest, stats);
                    return {{ ranked: [winner, result.winner, rest.find(t => t !== result.winner)], tiebreaker }};
                }} else {{
                    const subResult = breakMultiTeamDivisionTie(rest, stats);
                    return {{ ranked: [winner, ...subResult.ranked], tiebreaker }};
                }}
            }}
            
            remaining.sort((a, b) => stats[b].conference_pct - stats[a].conference_pct);
            if (stats[remaining[0]].conference_pct > stats[remaining[1]].conference_pct) {{
                const winner = remaining[0];
                const rest = remaining.slice(1);
                const tiebreaker = `Conference record: ${{stats[winner].conference_W}}-${{stats[winner].conference_L}}`;
                if (rest.length === 1) {{
                    return {{ ranked: [winner, rest[0]], tiebreaker }};
                }} else if (rest.length === 2) {{
                    const result = breakTwoTeamDivisionTie(rest, stats);
                    return {{ ranked: [winner, result.winner, rest.find(t => t !== result.winner)], tiebreaker }};
                }} else {{
                    const subResult = breakMultiTeamDivisionTie(rest, stats);
                    return {{ ranked: [winner, ...subResult.ranked], tiebreaker }};
                }}
            }}
            
            remaining.sort((a, b) => {{
                if (stats[b].strength_of_victory !== stats[a].strength_of_victory) {{
                    return stats[b].strength_of_victory - stats[a].strength_of_victory;
                }}
                return stats[b].win_pct - stats[a].win_pct;
            }});
            return {{ ranked: remaining, tiebreaker: `Strength of victory (${{stats[remaining[0]].strength_of_victory.toFixed(3)}})` }};
        }}
        
        function breakTwoTeamWildcardTie(teams, stats) {{
            const [team1, team2] = teams;
            
            const h2h1 = stats[team1].head_to_head[team2] || {{ W: 0, L: 0, T: 0 }};
            const h2hTotal = h2h1.W + h2h1.L + h2h1.T;
            if (h2hTotal > 0) {{
                const h2h1Pct = (h2h1.W + 0.5 * h2h1.T) / h2hTotal;
                const h2h2Pct = (h2h1.L + 0.5 * h2h1.T) / h2hTotal;
                if (h2h1Pct > h2h2Pct) return {{ winner: team1, tiebreaker: `Head-to-head: won ${{h2h1.W}}-${{h2h1.L}}` }};
                if (h2h2Pct > h2h1Pct) return {{ winner: team2, tiebreaker: `Head-to-head: won ${{h2h1.L}}-${{h2h1.W}}` }};
            }}
            
            if (stats[team1].conference_pct > stats[team2].conference_pct) {{
                return {{ winner: team1, tiebreaker: `Conference record: ${{stats[team1].conference_W}}-${{stats[team1].conference_L}}` }};
            }}
            if (stats[team2].conference_pct > stats[team1].conference_pct) {{
                return {{ winner: team2, tiebreaker: `Conference record: ${{stats[team2].conference_W}}-${{stats[team2].conference_L}}` }};
            }}
            
            const commonOpps = new Set(stats[team1].opponents.filter(o => stats[team2].opponents.includes(o)));
            if (commonOpps.size >= 4) {{
                const common1W = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf > g.pa).length;
                const common1L = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf < g.pa).length;
                const common1T = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf === g.pa).length;
                const common1Total = common1W + common1L + common1T;
                const common1Pct = common1Total > 0 ? (common1W + 0.5 * common1T) / common1Total : 0;
                
                const common2W = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf > g.pa).length;
                const common2L = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf < g.pa).length;
                const common2T = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf === g.pa).length;
                const common2Total = common2W + common2L + common2T;
                const common2Pct = common2Total > 0 ? (common2W + 0.5 * common2T) / common2Total : 0;
                
                if (common1Pct > common2Pct) {{
                    return {{ winner: team1, tiebreaker: `Common games: ${{common1W}}-${{common1L}}-${{common1T}}` }};
                }}
                if (common2Pct > common1Pct) {{
                    return {{ winner: team2, tiebreaker: `Common games: ${{common2W}}-${{common2L}}-${{common2T}}` }};
                }}
            }}
            
            if (stats[team1].strength_of_victory > stats[team2].strength_of_victory) {{
                return {{ winner: team1, tiebreaker: `Strength of victory: ${{stats[team1].strength_of_victory.toFixed(3)}}` }};
            }}
            if (stats[team2].strength_of_victory > stats[team1].strength_of_victory) {{
                return {{ winner: team2, tiebreaker: `Strength of victory: ${{stats[team2].strength_of_victory.toFixed(3)}}` }};
            }}
            
            if (stats[team1].strength_of_schedule > stats[team2].strength_of_schedule) {{
                return {{ winner: team1, tiebreaker: `Strength of schedule: ${{stats[team1].strength_of_schedule.toFixed(3)}}` }};
            }}
            if (stats[team2].strength_of_schedule > stats[team1].strength_of_schedule) {{
                return {{ winner: team2, tiebreaker: `Strength of schedule: ${{stats[team2].strength_of_schedule.toFixed(3)}}` }};
            }}
            
            const confNet1 = stats[team1].conference_points_for - stats[team1].conference_points_against;
            const confNet2 = stats[team2].conference_points_for - stats[team2].conference_points_against;
            if (confNet1 > confNet2) {{
                return {{ winner: team1, tiebreaker: `Net points in conference: +${{confNet1}}` }};
            }}
            if (confNet2 > confNet1) {{
                return {{ winner: team2, tiebreaker: `Net points in conference: +${{confNet2}}` }};
            }}
            
            const net1 = stats[team1].points_for - stats[team1].points_against;
            const net2 = stats[team2].points_for - stats[team2].points_against;
            if (net1 > net2) {{
                return {{ winner: team1, tiebreaker: `Net points in all games: +${{net1}}` }};
            }}
            if (net2 > net1) {{
                return {{ winner: team2, tiebreaker: `Net points in all games: +${{net2}}` }};
            }}
            
            if (stats[team1].touchdowns > stats[team2].touchdowns) {{
                return {{ winner: team1, tiebreaker: `Net touchdowns: ${{stats[team1].touchdowns}}` }};
            }}
            if (stats[team2].touchdowns > stats[team1].touchdowns) {{
                return {{ winner: team2, tiebreaker: `Net touchdowns: ${{stats[team2].touchdowns}}` }};
            }}
            
            return {{ winner: team1, tiebreaker: 'Coin toss' }};
        }}
        
        function breakMultiTeamWildcardTie(teams, stats) {{
            let remaining = [...teams];
            
            const divisions = {{}};
            for (const team of remaining) {{
                const div = teamsInfo[team].division;
                if (!divisions[div]) divisions[div] = [];
                divisions[div].push(team);
            }}
            
            const divWinners = {{}};
            for (const [div, divTeams] of Object.entries(divisions)) {{
                if (divTeams.length > 1) {{
                    const result = applyDivisionTiebreaker(divTeams, stats);
                    divWinners[div] = result.ranked[0];
                }} else {{
                    divWinners[div] = divTeams[0];
                }}
            }}
            
            remaining = Object.values(divWinners);
            
            if (remaining.length === 1) return {{ ranked: remaining, tiebreaker: null }};
            if (remaining.length === 2) {{
                const result = breakTwoTeamWildcardTie(remaining, stats);
                return {{ ranked: [result.winner, remaining.find(t => t !== result.winner)], tiebreaker: result.tiebreaker }};
            }}
            
            let h2hSweep = null;
            for (const team of remaining) {{
                const beatsAll = remaining.every(opp => {{
                    if (opp === team) return true;
                    const h2h = stats[team].head_to_head[opp] || {{ W: 0 }};
                    return h2h.W > 0;
                }});
                if (beatsAll) {{
                    h2hSweep = team;
                    break;
                }}
            }}
            
            if (h2hSweep) {{
                const rest = remaining.filter(t => t !== h2hSweep);
                if (rest.length === 1) {{
                    return {{ ranked: [h2hSweep, rest[0]], tiebreaker: 'Head-to-head sweep' }};
                }} else {{
                    const subResult = breakMultiTeamWildcardTie(rest, stats);
                    return {{ ranked: [h2hSweep, ...subResult.ranked], tiebreaker: 'Head-to-head sweep' }};
                }}
            }}
            
            remaining.sort((a, b) => stats[b].conference_pct - stats[a].conference_pct);
            if (stats[remaining[0]].conference_pct > stats[remaining[1]].conference_pct) {{
                const winner = remaining[0];
                const rest = remaining.slice(1);
                const tiebreaker = `Conference record: ${{stats[winner].conference_W}}-${{stats[winner].conference_L}}`;
                if (rest.length === 1) {{
                    return {{ ranked: [winner, rest[0]], tiebreaker }};
                }} else if (rest.length === 2) {{
                    const result = breakTwoTeamWildcardTie(rest, stats);
                    return {{ ranked: [winner, result.winner, rest.find(t => t !== result.winner)], tiebreaker }};
                }} else {{
                    const subResult = breakMultiTeamWildcardTie(rest, stats);
                    return {{ ranked: [winner, ...subResult.ranked], tiebreaker }};
                }}
            }}
            
            remaining.sort((a, b) => {{
                if (stats[b].strength_of_victory !== stats[a].strength_of_victory) {{
                    return stats[b].strength_of_victory - stats[a].strength_of_victory;
                }}
                return stats[b].win_pct - stats[a].win_pct;
            }});
            return {{ ranked: remaining, tiebreaker: `Strength of victory (${{stats[remaining[0]].strength_of_victory.toFixed(3)}})` }};
        }}
        
        function applyDivisionTiebreaker(tiedTeams, stats) {{
            if (tiedTeams.length === 0) return {{ ranked: [], tiebreaker: null }};
            if (tiedTeams.length === 1) return {{ ranked: tiedTeams, tiebreaker: null }};
            
            if (tiedTeams.length === 2) {{
                const result = breakTwoTeamDivisionTie(tiedTeams, stats);
                return {{ ranked: [result.winner], tiebreaker: result.tiebreaker }};
            }} else {{
                return breakMultiTeamDivisionTie(tiedTeams, stats);
            }}
        }}
        
        function applyWildcardTiebreaker(tiedTeams, stats) {{
            if (tiedTeams.length === 0) return {{ ranked: [], tiebreaker: null }};
            if (tiedTeams.length === 1) return {{ ranked: tiedTeams, tiebreaker: null }};
            
            const sameDivision = tiedTeams.every(t => teamsInfo[t].division === teamsInfo[tiedTeams[0]].division);
            if (sameDivision) {{
                return applyDivisionTiebreaker(tiedTeams, stats);
            }}
            
            if (tiedTeams.length === 2) {{
                const result = breakTwoTeamWildcardTie(tiedTeams, stats);
                return {{ ranked: [result.winner], tiebreaker: result.tiebreaker }};
            }} else {{
                return breakMultiTeamWildcardTie(tiedTeams, stats);
            }}
        }}
        
        function getSeedingTiebreaker(team1, team2, stats) {{
            if (stats[team1].win_pct > stats[team2].win_pct) {{
                return `Better record (${{stats[team1].W}}-${{stats[team1].L}} vs ${{stats[team2].W}}-${{stats[team2].L}})`;
            }}
            
            const h2h1 = stats[team1].head_to_head[team2];
            if (h2h1) {{
                const h2hTotal = h2h1.W + h2h1.L + (h2h1.T || 0);
                if (h2hTotal > 0) {{
                    const h2h1Pct = (h2h1.W + 0.5 * (h2h1.T || 0)) / h2hTotal;
                    const h2h2Pct = (h2h1.L + 0.5 * (h2h1.T || 0)) / h2hTotal;
                    if (h2h1Pct > h2h2Pct) return `Head-to-head (${{h2h1.W}}-${{h2h1.L}})`;
                    if (h2h2Pct > h2h1Pct) return null;
                }}
            }}
            
            if (stats[team1].conference_pct > stats[team2].conference_pct) {{
                return `Conference record (${{stats[team1].conference_W}}-${{stats[team1].conference_L}} vs ${{stats[team2].conference_W}}-${{stats[team2].conference_L}})`;
            }}
            if (stats[team2].conference_pct > stats[team1].conference_pct) {{
                return null;
            }}
            
            const commonOpps = new Set(stats[team1].opponents.filter(o => stats[team2].opponents.includes(o)));
            if (commonOpps.size >= 4) {{
                const common1W = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf > g.pa).length;
                const common1L = stats[team1].game_results.filter(g => commonOpps.has(g.opponent) && g.pf < g.pa).length;
                const common2W = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf > g.pa).length;
                const common2L = stats[team2].game_results.filter(g => commonOpps.has(g.opponent) && g.pf < g.pa).length;
                
                const common1Pct = common1W / (common1W + common1L) || 0;
                const common2Pct = common2W / (common2W + common2L) || 0;
                
                if (common1Pct > common2Pct) {{
                    return `Common games (${{common1W}}-${{common1L}} vs ${{common2W}}-${{common2L}})`;
                }}
                if (common2Pct > common1Pct) {{
                    return null;
                }}
            }}
            
            if (stats[team1].strength_of_victory > stats[team2].strength_of_victory) {{
                return `Strength of victory (${{stats[team1].strength_of_victory.toFixed(3)}} vs ${{stats[team2].strength_of_victory.toFixed(3)}})`;
            }}
            if (stats[team2].strength_of_victory > stats[team1].strength_of_victory) {{
                return null;
            }}
            
            if (stats[team1].strength_of_schedule > stats[team2].strength_of_schedule) {{
                return `Strength of schedule (${{stats[team1].strength_of_schedule.toFixed(3)}} vs ${{stats[team2].strength_of_schedule.toFixed(3)}})`;
            }}
            if (stats[team2].strength_of_schedule > stats[team1].strength_of_schedule) {{
                return null;
            }}
            
            const confNet1 = stats[team1].conference_points_for - stats[team1].conference_points_against;
            const confNet2 = stats[team2].conference_points_for - stats[team2].conference_points_against;
            if (confNet1 > confNet2) {{
                return `Conference net points (+${{confNet1}} vs +${{confNet2}})`;
            }}
            if (confNet2 > confNet1) {{
                return null;
            }}
            
            const net1 = stats[team1].points_for - stats[team1].points_against;
            const net2 = stats[team2].points_for - stats[team2].points_against;
            if (net1 > net2) {{
                return `Net points (+${{net1}} vs +${{net2}})`;
            }}
            
            return null;
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
                
                for (let div in divisions) {{
                    const divTeams = divisions[div];
                    divTeams.sort((a, b) => {{
                        if (stats[b].win_pct !== stats[a].win_pct) return stats[b].win_pct - stats[a].win_pct;
                        return stats[b].W - stats[a].W;
                    }});
                    
                    const sameRecordTeams = [divTeams[0]];
                    for (let i = 1; i < divTeams.length; i++) {{
                        if (Math.abs(stats[divTeams[i]].win_pct - stats[sameRecordTeams[0]].win_pct) < 0.001) {{
                            sameRecordTeams.push(divTeams[i]);
                        }} else {{
                            break;
                        }}
                    }}
                    
                    let winner, tiebreaker = null;
                    if (sameRecordTeams.length > 1) {{
                        const result = applyDivisionTiebreaker(sameRecordTeams, stats);
                        winner = result.ranked[0];
                        tiebreaker = result.tiebreaker;
                    }} else {{
                        winner = sameRecordTeams[0];
                    }}
                    
                    let qualification = 'Division winner';
                    if (tiebreaker) {{
                        qualification = `Division winner (won tiebreaker: ${{tiebreaker}})`;
                    }}
                    
                    divisionWinners.push({{
                        team: winner,
                        record: `${{stats[winner].W}}-${{stats[winner].L}}-${{stats[winner].T}}`,
                        division: div,
                        qualification: qualification,
                        divRecord: `${{stats[winner].division_W}}-${{stats[winner].division_L}}`,
                        confRecord: `${{stats[winner].conference_W}}-${{stats[winner].conference_L}}`
                    }});
                }}
                
                divisionWinners.sort((a, b) => {{
                    if (stats[b.team].win_pct !== stats[a.team].win_pct) {{
                        return stats[b.team].win_pct - stats[a.team].win_pct;
                    }}
                    
                    const h2h_a = stats[a.team].head_to_head[b.team];
                    if (h2h_a) {{
                        const h2hTotal = h2h_a.W + h2h_a.L + (h2h_a.T || 0);
                        if (h2hTotal > 0) {{
                            const h2h_a_pct = (h2h_a.W + 0.5 * (h2h_a.T || 0)) / h2hTotal;
                            if (h2h_a_pct > 0.5) return -1;
                            if (h2h_a_pct < 0.5) return 1;
                        }}
                    }}
                    
                    if (stats[a.team].conference_pct !== stats[b.team].conference_pct) {{
                        return stats[b.team].conference_pct - stats[a.team].conference_pct;
                    }}
                    
                    if (stats[a.team].strength_of_victory !== stats[b.team].strength_of_victory) {{
                        return stats[b.team].strength_of_victory - stats[a.team].strength_of_victory;
                    }}
                    
                    if (stats[a.team].strength_of_schedule !== stats[b.team].strength_of_schedule) {{
                        return stats[b.team].strength_of_schedule - stats[a.team].strength_of_schedule;
                    }}
                    
                    const confNet_a = stats[a.team].conference_points_for - stats[a.team].conference_points_against;
                    const confNet_b = stats[b.team].conference_points_for - stats[b.team].conference_points_against;
                    if (confNet_a !== confNet_b) {{
                        return confNet_b - confNet_a;
                    }}
                    
                    const net_a = stats[a.team].points_for - stats[a.team].points_against;
                    const net_b = stats[b.team].points_for - stats[b.team].points_against;
                    return net_b - net_a;
                }});
                
                const wildCardPool = confTeams.filter(t => !divisionWinners.find(dw => dw.team === t));
                wildCardPool.sort((a, b) => {{
                    if (stats[b].win_pct !== stats[a].win_pct) return stats[b].win_pct - stats[a].win_pct;
                    return stats[b].W - stats[a].W;
                }});
                
                const wildCards = [];
                let currentIndex = 0;
                
                while (wildCards.length < 3 && currentIndex < wildCardPool.length) {{
                    const currentTeam = wildCardPool[currentIndex];
                    const currentWinPct = stats[currentTeam].win_pct;
                    
                    const tiedTeams = [];
                    for (let i = currentIndex; i < wildCardPool.length; i++) {{
                        if (Math.abs(stats[wildCardPool[i]].win_pct - currentWinPct) < 0.001) {{
                            tiedTeams.push(wildCardPool[i]);
                        }} else {{
                            break;
                        }}
                    }}
                    
                    let rankedTeams, tiebreakerInfo = null;
                    if (tiedTeams.length > 1) {{
                        const result = applyWildcardTiebreaker(tiedTeams, stats);
                        rankedTeams = result.ranked;
                        tiebreakerInfo = result.tiebreaker;
                    }} else {{
                        rankedTeams = tiedTeams;
                    }}
                    
                    const spotsRemaining = 3 - wildCards.length;
                    const teamsToAdd = rankedTeams.slice(0, spotsRemaining);
                    
                    teamsToAdd.forEach((t, idx) => {{
                        let qualification = 'Wild card';
                        
                        if (idx === 0 && tiebreakerInfo && tiedTeams.length > 1) {{
                            qualification = `Wild card (won tiebreaker: ${{tiebreakerInfo}})`;
                        }} else if (idx === 0 && tiedTeams.length > 2 && !tiebreakerInfo) {{
                            qualification = `Wild card (won ${{tiedTeams.length}}-team tiebreaker)`;
                        }}
                        
                        wildCards.push({{
                            team: t,
                            record: `${{stats[t].W}}-${{stats[t].L}}-${{stats[t].T}}`,
                            division: teamsInfo[t].division,
                            qualification: qualification,
                            divRecord: `${{stats[t].division_W}}-${{stats[t].division_L}}`,
                            confRecord: `${{stats[t].conference_W}}-${{stats[t].conference_L}}`
                        }});
                    }});
                    
                    currentIndex += teamsToAdd.length;
                }}
                
                const playoffTeamNames = new Set([
                    ...divisionWinners.map(d => d.team),
                    ...wildCards.map(w => w.team)
                ]);
                
                confTeams.forEach(team => {{
                    if (!playoffTeamNames.has(team)) {{
                        let reason = '';
                        const teamDiv = teamsInfo[team].division;
                        const divWinner = divisionWinners.find(dw => dw.division === teamDiv);
                        
                        if (divWinner && divWinner.team !== team) {{
                            if (Math.abs(stats[team].win_pct - stats[divWinner.team].win_pct) < 0.001) {{
                                const qualMatch = divWinner.qualification.match(/won tiebreaker: (.+)\\)/);
                                if (qualMatch) {{
                                    reason = `Lost division to ${{divWinner.team}} (${{qualMatch[1]}})`;
                                }} else {{
                                    reason = `Lost division to ${{divWinner.team}}`;
                                }}
                            }} else {{
                                const winDiff = stats[divWinner.team].W - stats[team].W;
                                reason = `${{winDiff}} game${{winDiff !== 1 ? 's' : ''}} behind ${{divWinner.team}} in division`;
                            }}
                        }}
                        
                        if (wildCards.length > 0) {{
                            const lastWC = wildCards[wildCards.length - 1];
                            const wcWinPct = stats[lastWC.team].win_pct;
                            
                            if (stats[team].win_pct < wcWinPct) {{
                                const winDiff = stats[lastWC.team].W - stats[team].W;
                                if (reason) reason += '; ';
                                reason += `${{winDiff}} game${{winDiff !== 1 ? 's' : ''}} behind wild card (${{lastWC.team}}: ${{lastWC.record}})`;
                            }} else if (Math.abs(stats[team].win_pct - wcWinPct) < 0.001) {{
                                if (reason) reason += '; ';
                                reason += `Lost wild card tiebreaker`;
                            }}
                        }}
                        
                        if (!reason) {{
                            reason = 'Insufficient record for playoffs';
                        }}
                        
                        eliminated[conf].push({{
                            team: team,
                            record: `${{stats[team].W}}-${{stats[team].L}}-${{stats[team].T}}`,
                            reason: reason,
                            divRecord: `${{stats[team].division_W}}-${{stats[team].division_L}}`,
                            confRecord: `${{stats[team].conference_W}}-${{stats[team].conference_L}}`
                        }});
                    }}
                }});
                
                results[conf] = [
                    ...divisionWinners.slice(0, 4),
                    ...wildCards
                ];
                
                for (let i = 0; i < results[conf].length; i++) {{
                    if (i < results[conf].length - 1) {{
                        const currentSeed = results[conf][i];
                        const nextSeed = results[conf][i + 1];
                        const reason = getSeedingTiebreaker(currentSeed.team, nextSeed.team, stats);
                        if (reason) {{
                            currentSeed.seedingReason = reason;
                        }}
                    }}
                }}
                
                if (results[conf].length > 0 && eliminated[conf].length > 0) {{
                    const lastSeed = results[conf][results[conf].length - 1];
                    
                    eliminated[conf].sort((a, b) => {{
                        if (stats[b.team].win_pct !== stats[a.team].win_pct) return stats[b.team].win_pct - stats[a.team].win_pct;
                        return stats[b.team].W - stats[a.team].W;
                    }});
                    
                    const firstEliminated = eliminated[conf][0];
                    const reason = getSeedingTiebreaker(lastSeed.team, firstEliminated.team, stats);
                    if (reason) {{
                        lastSeed.seedingReason = reason;
                    }}
                }}
            }});
            
            return {{ playoffs: results, eliminated }};
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
                    const seedLabel = `Seed ${{seedNum}}`;
                    
                    const divLabel = seed.division ? ` • ${{seed.division.replace(conf + ' ', '')}}` : '';
                    const teamLogo = teamsInfo[seed.team].logo_url;
                    
                    const seedDiv = document.createElement('div');
                    seedDiv.className = `seed-team ${{seedClass}}`;
                    
                    let seedingReasonHtml = '';
                    if (seed.seedingReason) {{
                        seedingReasonHtml = `<div class="tiebreaker-info" style="margin-top: 8px;">🏆 Seed ${{seedNum}}: ${{seed.seedingReason}}</div>`;
                    }}
                    
                    seedDiv.innerHTML = `
                        <div class="seed-header">
                            <span class="seed-badge">${{seedLabel}}</span>
                            <span class="team-record">${{seed.record}}</span>
                        </div>
                        <div class="team-name">
                            <img src="${{teamLogo}}" class="team-logo" alt="${{seed.team}}">
                            <span>${{seed.team}}${{divLabel}}</span>
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                            Div: ${{seed.divRecord}} | Conf: ${{seed.confRecord}}
                        </div>
                        <div class="qualification-info">✓ ${{seed.qualification || 'Qualified'}}</div>
                        ${{seedingReasonHtml}}
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
                            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                                Div: ${{team.divRecord}} | Conf: ${{team.confRecord}}
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
