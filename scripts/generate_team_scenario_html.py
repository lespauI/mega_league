#!/usr/bin/env python3
import os
import json

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from calc_playoff_probabilities import load_data
    teams_info, _, _ = load_data()
    
    afc_teams = sorted([t for t in teams_info if teams_info[t]['conference'] == 'AFC'])
    nfc_teams = sorted([t for t in teams_info if teams_info[t]['conference'] == 'NFC'])
    
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
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Playoff Scenarios - Monte Carlo Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #2563eb;
            --secondary: #7c3aed;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #1e293b;
            --gray-50: #f8fafc;
            --gray-100: #f1f5f9;
            --gray-200: #e2e8f0;
            --gray-300: #cbd5e1;
            --gray-600: #475569;
            --gray-700: #334155;
            --gray-800: #1e293b;
            --gray-900: #0f172a;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 24px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            color: white;
        }
        
        .header h1 {
            font-size: 3em;
            font-weight: 800;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .selector-container {
            background: white;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.15);
        }
        
        .selector-label {
            display: block;
            color: var(--gray-800);
            font-weight: 700;
            font-size: 1.2em;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .team-select {
            width: 100%;
            padding: 16px 20px;
            font-size: 1.2em;
            font-weight: 600;
            border: 3px solid var(--gray-200);
            border-radius: 12px;
            background: var(--gray-50);
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            color: var(--gray-800);
        }
        
        .team-select:hover {
            border-color: var(--primary);
            background: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
        }
        
        .team-select:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
        }
        
        .stats-overview {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-left: 5px solid var(--primary);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        
        .stat-label {
            font-size: 0.9em;
            color: var(--gray-600);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .stat-value {
            font-size: 2.5em;
            font-weight: 800;
            color: var(--gray-900);
            line-height: 1;
        }
        
        .stat-sublabel {
            font-size: 0.85em;
            color: var(--gray-500);
            margin-top: 4px;
        }
        
        .content-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
        }
        
        .content-card {
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .chart-container {
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 24px;
        }
        
        .chart-title {
            font-size: 1.5em;
            font-weight: 700;
            color: var(--gray-800);
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 3px solid var(--gray-200);
        }
        
        canvas {
            max-height: 400px;
        }
        
        .loading {
            text-align: center;
            padding: 100px 20px;
            color: var(--gray-600);
            font-size: 1.3em;
        }
        
        .loading::after {
            content: '...';
            animation: dots 1.5s steps(4, end) infinite;
        }
        
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }
        
        .error {
            text-align: center;
            padding: 100px 20px;
            color: var(--danger);
            font-size: 1.2em;
            font-weight: 600;
        }
        
        #report-content h1 {
            color: var(--gray-900);
            font-size: 2.5em;
            font-weight: 800;
            border-bottom: 4px solid var(--primary);
            padding-bottom: 20px;
            margin-bottom: 32px;
        }
        
        #report-content h2 {
            color: var(--gray-800);
            font-size: 1.8em;
            font-weight: 700;
            margin-top: 48px;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--gray-200);
        }
        
        #report-content h3 {
            color: var(--primary);
            font-size: 1.4em;
            font-weight: 600;
            margin-top: 28px;
            margin-bottom: 16px;
        }
        
        #report-content table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 24px 0;
            font-size: 0.95em;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border-radius: 12px;
            overflow: hidden;
        }
        
        #report-content table th {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 16px;
            text-align: left;
            font-weight: 700;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        #report-content table td {
            padding: 14px 16px;
            border-bottom: 1px solid var(--gray-200);
            background: white;
        }
        
        #report-content table tr:last-child td {
            border-bottom: none;
        }
        
        #report-content table tr:hover td {
            background: var(--gray-50);
        }
        
        #report-content ul {
            margin: 20px 0;
            padding-left: 28px;
        }
        
        #report-content li {
            margin: 12px 0;
            color: var(--gray-700);
            line-height: 1.8;
        }
        
        #report-content strong {
            color: var(--gray-900);
            font-weight: 700;
        }
        
        #report-content hr {
            border: none;
            border-top: 2px solid var(--gray-200);
            margin: 40px 0;
        }
        
        #report-content p {
            line-height: 1.9;
            color: var(--gray-700);
            margin: 16px 0;
        }
        
        .probability-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.9em;
        }
        
        .prob-high {
            background: #dcfce7;
            color: #166534;
        }
        
        .prob-medium {
            background: #fef3c7;
            color: #92400e;
        }
        
        .prob-low {
            background: #fee2e2;
            color: #991b1b;
        }
        
        @media (max-width: 768px) {
            body {
                padding: 12px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .content-card, .chart-container {
                padding: 20px;
            }
            
            #report-content table {
                font-size: 0.8em;
            }
            
            .stat-card {
                padding: 16px;
            }
            
            .stat-value {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏈 NFL Playoff Scenarios</h1>
            <p>Monte Carlo simulation analysis • 10,000 iterations per team • Real-time probability modeling</p>
        </div>
        
        <div class="selector-container">
            <label class="selector-label" for="team-select">🎯 Select Your Team</label>
            <select id="team-select" class="team-select">
                <option value="">-- Choose a team to analyze --</option>
                <optgroup label="AFC">
'''
    
    for team in afc_teams:
        safe_filename = team.replace(' ', '_').replace('/', '_')
        html += f'                    <option value="{safe_filename}">{team}</option>\n'
    
    html += '''                </optgroup>
                <optgroup label="NFC">
'''
    
    for team in nfc_teams:
        safe_filename = team.replace(' ', '_').replace('/', '_')
        html += f'                    <option value="{safe_filename}">{team}</option>\n'
    
    html += '''                </optgroup>
            </select>
        </div>
        
        <div id="stats-overview" class="stats-overview" style="display: none;"></div>
        
        <div id="charts-container" style="display: none;">
            <div class="chart-container">
                <h2 class="chart-title">📊 Record Distribution</h2>
                <canvas id="recordChart"></canvas>
            </div>
            <div class="chart-container">
                <h2 class="chart-title">🎯 Playoff Probabilities</h2>
                <canvas id="probChart"></canvas>
            </div>
        </div>
        
        <div class="content-card">
            <div id="report-content" class="loading">
                Select a team above to view their playoff scenario analysis
            </div>
        </div>
    </div>
    
    <script>
        const TEAM_COLORS = ''' + json.dumps(team_colors) + ''';
        
        const teamSelect = document.getElementById('team-select');
        const reportContent = document.getElementById('report-content');
        const statsOverview = document.getElementById('stats-overview');
        const chartsContainer = document.getElementById('charts-container');
        let recordChart = null;
        let probChart = null;
        
        function getTeamColor(teamName) {
            return TEAM_COLORS[teamName] || '#2563eb';
        }
        
        function createStatsCards(data) {
            const lines = data.split('\\n');
            let playoffProb = '0%', divisionProb = '0%', byeProb = '0%';
            let currentRecord = '0-0-0';
            
            lines.forEach(line => {
                if (line.includes('**Make Playoffs:**')) {
                    playoffProb = line.match(/\\*\\*Make Playoffs:\\*\\* ([\\d.]+)%/)?.[1] + '%' || '0%';
                }
                if (line.includes('**Win Division:**')) {
                    divisionProb = line.match(/\\*\\*Win Division:\\*\\* ([\\d.]+)%/)?.[1] + '%' || '0%';
                }
                if (line.includes('**Earn Bye:**')) {
                    byeProb = line.match(/\\*\\*Earn Bye:\\*\\* ([\\d.]+)%/)?.[1] + '%' || '0%';
                }
                if (line.includes('**Current Record:**')) {
                    currentRecord = line.match(/\\*\\*Current Record:\\*\\* ([\\d-]+)/)?.[1] || '0-0-0';
                }
            });
            
            const teamName = teamSelect.options[teamSelect.selectedIndex].text;
            const teamColor = getTeamColor(teamName);
            
            statsOverview.innerHTML = `
                <div class="stat-card" style="border-left-color: ${teamColor}">
                    <div class="stat-label">Current Record</div>
                    <div class="stat-value">${currentRecord}</div>
                </div>
                <div class="stat-card" style="border-left-color: #10b981">
                    <div class="stat-label">Playoff Chances</div>
                    <div class="stat-value">${playoffProb}</div>
                </div>
                <div class="stat-card" style="border-left-color: #8b5cf6">
                    <div class="stat-label">Division Title</div>
                    <div class="stat-value">${divisionProb}</div>
                </div>
                <div class="stat-card" style="border-left-color: #f59e0b">
                    <div class="stat-label">First Round Bye</div>
                    <div class="stat-value">${byeProb}</div>
                </div>
            `;
            statsOverview.style.display = 'grid';
        }
        
        function parseTableData(markdown) {
            const lines = markdown.split('\\n');
            const records = [];
            const frequencies = [];
            const playoffProbs = [];
            
            let inTable = false;
            lines.forEach(line => {
                if (line.includes('## All Scenario Outcomes')) {
                    inTable = true;
                    return;
                }
                if (inTable && line.startsWith('|') && !line.includes('Final Record') && !line.includes('---')) {
                    const parts = line.split('|').map(p => p.trim()).filter(p => p);
                    if (parts.length >= 4) {
                        records.push(parts[0]);
                        const freq = parseInt(parts[1].replace(/,/g, ''));
                        frequencies.push(freq);
                        const playoffProb = parseFloat(parts[3].replace('%', ''));
                        playoffProbs.push(playoffProb);
                    }
                }
                if (inTable && line.includes('---') && line.includes('##')) {
                    inTable = false;
                }
            });
            
            return { records: records.slice(0, 10), frequencies: frequencies.slice(0, 10), playoffProbs: playoffProbs.slice(0, 10) };
        }
        
        function createCharts(markdown) {
            const data = parseTableData(markdown);
            const teamName = teamSelect.options[teamSelect.selectedIndex].text;
            const teamColor = getTeamColor(teamName);
            
            if (recordChart) recordChart.destroy();
            if (probChart) probChart.destroy();
            
            const recordCtx = document.getElementById('recordChart').getContext('2d');
            recordChart = new Chart(recordCtx, {
                type: 'bar',
                data: {
                    labels: data.records,
                    datasets: [{
                        label: 'Frequency',
                        data: data.frequencies,
                        backgroundColor: teamColor + 'CC',
                        borderColor: teamColor,
                        borderWidth: 2,
                        borderRadius: 8,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            padding: 12,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#e2e8f0' },
                            ticks: { font: { size: 12, weight: '600' } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 12, weight: '600' } }
                        }
                    }
                }
            });
            
            const probCtx = document.getElementById('probChart').getContext('2d');
            probChart = new Chart(probCtx, {
                type: 'line',
                data: {
                    labels: data.records,
                    datasets: [{
                        label: 'Playoff Probability %',
                        data: data.playoffProbs,
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderColor: '#10b981',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            padding: 12,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            callbacks: {
                                label: (context) => `Playoff Chance: ${context.parsed.y.toFixed(1)}%`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#e2e8f0' },
                            ticks: {
                                callback: (value) => value + '%',
                                font: { size: 12, weight: '600' }
                            }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 12, weight: '600' } }
                        }
                    }
                }
            });
            
            chartsContainer.style.display = 'block';
        }
        
        teamSelect.addEventListener('change', async function() {
            const teamFile = this.value;
            
            if (!teamFile) {
                reportContent.innerHTML = '<div class="loading">Select a team above to view their playoff scenario analysis</div>';
                statsOverview.style.display = 'none';
                chartsContainer.style.display = 'none';
                return;
            }
            
            reportContent.innerHTML = '<div class="loading">Loading scenario analysis</div>';
            statsOverview.style.display = 'none';
            chartsContainer.style.display = 'none';
            
            try {
                const response = await fetch(`team_scenarios/${teamFile}.md`);
                
                if (!response.ok) {
                    throw new Error('Report not found');
                }
                
                const markdown = await response.text();
                createStatsCards(markdown);
                createCharts(markdown);
                
                const html = marked.parse(markdown);
                reportContent.innerHTML = html;
                
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } catch (error) {
                reportContent.innerHTML = '<div class="error">⚠️ Error loading team report. Please try again.</div>';
                console.error('Error loading report:', error);
            }
        });
    </script>
</body>
</html>
'''
    
    with open('docs/team_scenarios.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✓ Generated docs/team_scenarios.html with enhanced design and charts")

if __name__ == "__main__":
    main()
