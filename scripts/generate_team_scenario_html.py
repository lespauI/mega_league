#!/usr/bin/env python3
import os
import json

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    with open('output/team_scenarios.json', 'r', encoding='utf-8') as f:
        team_data = json.load(f)
    
    teams_by_conference = {'AFC': [], 'NFC': []}
    for team_name, info in team_data['teams'].items():
        teams_by_conference[info['conference']].append(team_name)
    
    afc_teams = sorted(teams_by_conference['AFC'])
    nfc_teams = sorted(teams_by_conference['NFC'])
    
    team_colors = {
        '49ers': '#AA0000', 'Bears': '#0B162A', 'Bengals': '#FB4F14', 'Bills': '#00338D',
        'Broncos': '#FB4F14', 'Browns': '#311D00', 'Buccaneers': '#D50A0A', 'Cardinals': '#97233F',
        'Chargers': '#0080C6', 'Chiefs': '#E31837', 'Colts': '#002C5F', 'Commanders': '#5A1414',
        'Cowboys': '#003594', 'Dolphins': '#008E97', 'Eagles': '#004C54', 'Falcons': '#A71930',
        'Giants': '#0B2265', 'Jaguars': '#006778', 'Jets': '#125740', 'Lions': '#0076B6',
        'Packers': '#203731', 'Panthers': '#0085CA', 'Patriots': '#002244', 'Raiders': '#000000',
        'Rams': '#003594', 'Ravens': '#241773', 'Saints': '#D3BC8D', 'Seahawks': '#002244',
        'Steelers': '#FFB612', 'Texans': '#03202F', 'Titans': '#0C2340', 'Vikings': '#4F2683'
    }
    
    team_logos = {
        '49ers': 'SF', 'Bears': 'CHI', 'Bengals': 'CIN', 'Bills': 'BUF',
        'Broncos': 'DEN', 'Browns': 'CLE', 'Buccaneers': 'TB', 'Cardinals': 'ARI',
        'Chargers': 'LAC', 'Chiefs': 'KC', 'Colts': 'IND', 'Commanders': 'WAS',
        'Cowboys': 'DAL', 'Dolphins': 'MIA', 'Eagles': 'PHI', 'Falcons': 'ATL',
        'Giants': 'NYG', 'Jaguars': 'JAX', 'Jets': 'NYJ', 'Lions': 'DET',
        'Packers': 'GB', 'Panthers': 'CAR', 'Patriots': 'NE', 'Raiders': 'LV',
        'Rams': 'LAR', 'Ravens': 'BAL', 'Saints': 'NO', 'Seahawks': 'SEA',
        'Steelers': 'PIT', 'Texans': 'HOU', 'Titans': 'TEN', 'Vikings': 'MIN'
    }
    
    num_simulations = team_data.get('num_simulations', 10000)
    generated_at = team_data.get('generated_at', '')
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Playoff Scenarios - Monte Carlo Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --primary: #2563eb;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --gray-50: #f8fafc;
            --gray-100: #f1f5f9;
            --gray-200: #e2e8f0;
            --gray-600: #475569;
            --gray-800: #1e293b;
            --gray-900: #0f172a;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: var(--gray-800);
            border-radius: 12px;
            padding: 32px;
            margin-bottom: 20px;
            color: white;
            position: relative;
        }}
        
        .header h1 {{
            font-size: 2em;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        
        .header p {{
            opacity: 0.8;
        }}
        
        .back-button {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9em;
            transition: background 0.2s;
            margin-bottom: 16px;
        }}
        
        .back-button:hover {{
            background: rgba(255, 255, 255, 0.2);
        }}
        
        .selector-container {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .selector-label {{
            display: block;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--gray-800);
        }}
        
        .team-select {{
            width: 100%;
            padding: 12px 16px;
            font-size: 1.1em;
            border: 2px solid var(--gray-200);
            border-radius: 8px;
            background: var(--gray-50);
            cursor: pointer;
        }}
        
        .team-select:focus {{
            outline: none;
            border-color: var(--primary);
        }}
        
        .team-header {{
            display: flex;
            align-items: center;
            gap: 16px;
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .team-logo {{
            width: 64px;
            height: 64px;
            object-fit: contain;
        }}
        
        .team-info h2 {{
            font-size: 1.5em;
            color: var(--gray-900);
        }}
        
        .team-info .subtitle {{
            color: var(--gray-600);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid var(--primary);
        }}
        
        .stat-label {{
            font-size: 0.85em;
            color: var(--gray-600);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: 700;
            color: var(--gray-900);
        }}
        
        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: var(--gray-800);
            margin-bottom: 16px;
        }}
        
        canvas {{
            max-height: 350px;
        }}
        
        .content-card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .section-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: var(--gray-800);
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--gray-200);
        }}
        
        .games-table, .outcomes-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
        }}
        
        .games-table th, .outcomes-table th {{
            background: var(--gray-100);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.9em;
            color: var(--gray-700);
        }}
        
        .games-table td, .outcomes-table td {{
            padding: 12px;
            border-bottom: 1px solid var(--gray-200);
        }}
        
        .games-table tr:hover td, .outcomes-table tr:hover td {{
            background: var(--gray-50);
        }}
        
        .prob-high {{ color: #059669; font-weight: 600; }}
        .prob-medium {{ color: #d97706; font-weight: 600; }}
        .prob-low {{ color: #dc2626; font-weight: 600; }}
        
        .outcome-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .outcome-W {{ background: #dcfce7; color: #166534; }}
        .outcome-L {{ background: #fee2e2; color: #991b1b; }}
        .outcome-T {{ background: #fef3c7; color: #92400e; }}
        
        .placeholder {{
            text-align: center;
            padding: 60px 20px;
            color: var(--gray-600);
        }}
        
        .hidden {{ display: none !important; }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.5em; }}
            .stat-value {{ font-size: 1.5em; }}
            .team-header {{ flex-direction: column; text-align: center; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="playoff_race_table.html" class="back-button">
                ← Back to Playoff Race
            </a>
            <h1>NFL Playoff Scenarios</h1>
            <p>Monte Carlo simulation analysis - {num_simulations:,} iterations - Generated {generated_at[:10] if generated_at else 'recently'}</p>
        </div>
        
        <div class="selector-container">
            <label class="selector-label" for="team-select">Select Your Team</label>
            <select id="team-select" class="team-select">
                <option value="">-- Choose a team to analyze --</option>
                <optgroup label="AFC">
'''
    
    for team in afc_teams:
        html += f'                    <option value="{team}">{team}</option>\n'
    
    html += '''                </optgroup>
                <optgroup label="NFC">
'''
    
    for team in nfc_teams:
        html += f'                    <option value="{team}">{team}</option>\n'
    
    html += '''                </optgroup>
            </select>
        </div>
        
        <div id="team-header" class="team-header hidden"></div>
        
        <div id="stats-grid" class="stats-grid hidden"></div>
        
        <div id="charts-section" class="hidden">
            <div class="chart-container">
                <h3 class="chart-title">Record Distribution</h3>
                <canvas id="recordChart"></canvas>
            </div>
            <div class="chart-container">
                <h3 class="chart-title">Playoff Probability by Record</h3>
                <canvas id="probChart"></canvas>
            </div>
        </div>
        
        <div class="content-card">
            <div id="content-placeholder" class="placeholder">
                Select a team above to view their playoff scenario analysis
            </div>
            <div id="team-content" class="hidden"></div>
        </div>
    </div>
    
    <script>
        const TEAM_DATA = ''' + json.dumps(team_data['teams'], indent=None) + ''';
        const TEAM_COLORS = ''' + json.dumps(team_colors) + ''';
        const TEAM_LOGOS = ''' + json.dumps(team_logos) + ''';
        
        let recordChart = null;
        let probChart = null;
        
        function getTeamColor(teamName) {
            return TEAM_COLORS[teamName] || '#2563eb';
        }
        
        function getTeamLogoUrl(teamName) {
            const abbr = TEAM_LOGOS[teamName];
            return abbr ? `https://a.espncdn.com/i/teamlogos/nfl/500/${abbr}.png` : '';
        }
        
        function getProbClass(prob) {
            if (prob >= 50) return 'prob-high';
            if (prob >= 20) return 'prob-medium';
            return 'prob-low';
        }
        
        function renderTeamHeader(teamName, data) {
            const header = document.getElementById('team-header');
            const logoUrl = getTeamLogoUrl(teamName);
            
            header.innerHTML = `
                <img src="${logoUrl}" alt="${teamName}" class="team-logo" onerror="this.style.display='none'">
                <div class="team-info">
                    <h2>${teamName}</h2>
                    <div class="subtitle">${data.division} - ${data.current_record}</div>
                </div>
            `;
            header.classList.remove('hidden');
        }
        
        function renderStats(teamName, data) {
            const grid = document.getElementById('stats-grid');
            const teamColor = getTeamColor(teamName);
            const probs = data.overall_probabilities;
            
            grid.innerHTML = `
                <div class="stat-card" style="border-left-color: ${teamColor}">
                    <div class="stat-label">Current Record</div>
                    <div class="stat-value">${data.current_record}</div>
                </div>
                <div class="stat-card" style="border-left-color: #10b981">
                    <div class="stat-label">Playoff Chances</div>
                    <div class="stat-value">${probs.playoff.toFixed(1)}%</div>
                </div>
                <div class="stat-card" style="border-left-color: #8b5cf6">
                    <div class="stat-label">Win Division</div>
                    <div class="stat-value">${probs.division.toFixed(1)}%</div>
                </div>
                <div class="stat-card" style="border-left-color: #f59e0b">
                    <div class="stat-label">First Round Bye</div>
                    <div class="stat-value">${probs.bye.toFixed(1)}%</div>
                </div>
            `;
            grid.classList.remove('hidden');
        }
        
        function renderCharts(teamName, data) {
            const section = document.getElementById('charts-section');
            const teamColor = getTeamColor(teamName);
            
            const outcomes = data.record_outcomes.slice(0, 10);
            const records = outcomes.map(o => o.record);
            const frequencies = outcomes.map(o => o.frequency);
            const playoffProbs = outcomes.map(o => o.playoff_pct);
            
            if (recordChart) recordChart.destroy();
            if (probChart) probChart.destroy();
            
            recordChart = new Chart(document.getElementById('recordChart'), {
                type: 'bar',
                data: {
                    labels: records,
                    datasets: [{
                        label: 'Frequency',
                        data: frequencies,
                        backgroundColor: teamColor + 'CC',
                        borderColor: teamColor,
                        borderWidth: 1,
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true },
                        x: { grid: { display: false } }
                    }
                }
            });
            
            probChart = new Chart(document.getElementById('probChart'), {
                type: 'line',
                data: {
                    labels: records,
                    datasets: [{
                        label: 'Playoff %',
                        data: playoffProbs,
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderColor: '#10b981',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: '#10b981'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } },
                        x: { grid: { display: false } }
                    }
                }
            });
            
            section.classList.remove('hidden');
        }
        
        function renderContent(teamName, data) {
            const content = document.getElementById('team-content');
            const placeholder = document.getElementById('content-placeholder');
            
            let gamesHtml = '';
            data.remaining_games.forEach(g => {
                const location = g.is_home ? 'vs' : '@';
                gamesHtml += `
                    <tr>
                        <td>Week ${g.week}</td>
                        <td>${location} ${g.opponent}</td>
                        <td class="${getProbClass(g.win_prob)}">${g.win_prob.toFixed(1)}%</td>
                        <td class="${getProbClass(g.loss_prob)}">${g.loss_prob.toFixed(1)}%</td>
                    </tr>
                `;
            });
            
            let outcomesHtml = '';
            data.record_outcomes.forEach(o => {
                const exampleStr = o.example_outcomes.map(e => 
                    `<span class="outcome-badge outcome-${e.outcome}">${e.outcome}</span> ${e.is_home ? 'vs' : '@'} ${e.opponent}`
                ).join(', ');
                
                outcomesHtml += `
                    <tr>
                        <td><strong>${o.record}</strong></td>
                        <td>${o.frequency} (${o.percentage.toFixed(1)}%)</td>
                        <td class="${getProbClass(o.playoff_pct)}">${o.playoff_pct.toFixed(1)}%</td>
                        <td class="${getProbClass(o.division_pct)}">${o.division_pct.toFixed(1)}%</td>
                        <td class="${getProbClass(o.bye_pct)}">${o.bye_pct.toFixed(1)}%</td>
                    </tr>
                `;
            });
            
            content.innerHTML = `
                <h3 class="section-title">Remaining Games (${data.game_count} games)</h3>
                <table class="games-table">
                    <thead>
                        <tr>
                            <th>Week</th>
                            <th>Opponent</th>
                            <th>Win %</th>
                            <th>Loss %</th>
                        </tr>
                    </thead>
                    <tbody>${gamesHtml}</tbody>
                </table>
                
                <h3 class="section-title">All Scenario Outcomes</h3>
                <table class="outcomes-table">
                    <thead>
                        <tr>
                            <th>Final Record</th>
                            <th>Frequency</th>
                            <th>Playoff %</th>
                            <th>Division %</th>
                            <th>Bye %</th>
                        </tr>
                    </thead>
                    <tbody>${outcomesHtml}</tbody>
                </table>
                
                <h3 class="section-title">Most Likely Outcome</h3>
                <p><strong>${data.most_likely.record}</strong> - Occurs in ${data.most_likely.percentage.toFixed(1)}% of simulations (${data.most_likely.frequency} times)</p>
            `;
            
            content.classList.remove('hidden');
            placeholder.classList.add('hidden');
        }
        
        function hideAll() {
            document.getElementById('team-header').classList.add('hidden');
            document.getElementById('stats-grid').classList.add('hidden');
            document.getElementById('charts-section').classList.add('hidden');
            document.getElementById('team-content').classList.add('hidden');
            document.getElementById('content-placeholder').classList.remove('hidden');
        }
        
        document.getElementById('team-select').addEventListener('change', function() {
            const teamName = this.value;
            
            if (!teamName || !TEAM_DATA[teamName]) {
                hideAll();
                return;
            }
            
            const data = TEAM_DATA[teamName];
            renderTeamHeader(teamName, data);
            renderStats(teamName, data);
            renderCharts(teamName, data);
            renderContent(teamName, data);
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        
        const urlParams = new URLSearchParams(window.location.search);
        const teamFromUrl = urlParams.get('team');
        if (teamFromUrl && TEAM_DATA[teamFromUrl]) {
            const selectElement = document.getElementById('team-select');
            selectElement.value = teamFromUrl;
            selectElement.dispatchEvent(new Event('change'));
        }
    </script>
</body>
</html>
'''
    
    os.makedirs('docs', exist_ok=True)
    with open('docs/team_scenarios.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Generated docs/team_scenarios.html with embedded data for {len(team_data['teams'])} teams")

if __name__ == "__main__":
    main()
