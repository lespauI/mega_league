#!/usr/bin/env python3
import os
import json

def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from calc_playoff_probabilities import load_data
    teams_info, _, _ = load_data()
    
    afc_teams = sorted([t for t in teams_info if teams_info[t]['conference'] == 'AFC'])
    nfc_teams = sorted([t for t in teams_info if teams_info[t]['conference'] == 'NFC'])
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Team Playoff Scenarios - Monte Carlo Analysis</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #718096;
            font-size: 1.1em;
        }
        
        .selector-container {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        .selector-label {
            display: block;
            color: #2d3748;
            font-weight: 600;
            font-size: 1.1em;
            margin-bottom: 12px;
        }
        
        .team-select {
            width: 100%;
            padding: 12px 16px;
            font-size: 1.1em;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            background: white;
            cursor: pointer;
            transition: all 0.3s ease;
            color: #2d3748;
        }
        
        .team-select:hover {
            border-color: #667eea;
        }
        
        .team-select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .content-container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            min-height: 400px;
        }
        
        .loading {
            text-align: center;
            padding: 60px 20px;
            color: #718096;
            font-size: 1.2em;
        }
        
        .error {
            text-align: center;
            padding: 60px 20px;
            color: #e53e3e;
            font-size: 1.1em;
        }
        
        #report-content h1 {
            color: #2d3748;
            border-bottom: 3px solid #667eea;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        
        #report-content h2 {
            color: #4a5568;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }
        
        #report-content h3 {
            color: #667eea;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        #report-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }
        
        #report-content table th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        #report-content table td {
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        #report-content table tr:hover {
            background: #f7fafc;
        }
        
        #report-content ul {
            margin: 15px 0;
            padding-left: 25px;
        }
        
        #report-content li {
            margin: 8px 0;
            color: #4a5568;
            line-height: 1.6;
        }
        
        #report-content strong {
            color: #2d3748;
        }
        
        #report-content hr {
            border: none;
            border-top: 2px solid #e2e8f0;
            margin: 30px 0;
        }
        
        #report-content p {
            line-height: 1.8;
            color: #4a5568;
            margin: 12px 0;
        }
        
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
            
            .content-container {
                padding: 20px;
            }
            
            #report-content table {
                font-size: 0.85em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏈 NFL Team Playoff Scenarios</h1>
            <p>Monte Carlo simulation analysis of playoff probabilities and potential outcomes</p>
        </div>
        
        <div class="selector-container">
            <label class="selector-label" for="team-select">Select Your Team:</label>
            <select id="team-select" class="team-select">
                <option value="">-- Choose a team --</option>
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
        
        <div class="content-container">
            <div id="report-content" class="loading">
                Select a team above to view their playoff scenario analysis
            </div>
        </div>
    </div>
    
    <script>
        const teamSelect = document.getElementById('team-select');
        const reportContent = document.getElementById('report-content');
        
        teamSelect.addEventListener('change', async function() {
            const teamFile = this.value;
            
            if (!teamFile) {
                reportContent.innerHTML = '<div class="loading">Select a team above to view their playoff scenario analysis</div>';
                return;
            }
            
            reportContent.innerHTML = '<div class="loading">Loading scenario analysis...</div>';
            
            try {
                const response = await fetch(`team_scenarios/${teamFile}.md`);
                
                if (!response.ok) {
                    throw new Error('Report not found');
                }
                
                const markdown = await response.text();
                const html = marked.parse(markdown);
                reportContent.innerHTML = html;
                
                reportContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } catch (error) {
                reportContent.innerHTML = '<div class="error">Error loading team report. Please try again.</div>';
                console.error('Error loading report:', error);
            }
        });
    </script>
</body>
</html>
'''
    
    with open('docs/team_scenarios.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✓ Generated docs/team_scenarios.html")

if __name__ == "__main__":
    main()
