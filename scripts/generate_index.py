#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DOCS_DIR = ROOT_DIR / "docs"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MEGA League Stats & Analysis</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; 
            color: #333; 
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 20px; 
            padding: 40px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); 
        }}
        h1 {{ 
            text-align: center; 
            color: #1e293b; 
            margin-bottom: 15px; 
            font-size: 2.5em; 
        }}
        .subtitle {{ 
            text-align: center; 
            color: #64748b; 
            margin-bottom: 40px; 
            font-size: 1.1em; 
        }}
        .section {{ 
            margin-bottom: 35px; 
        }}
        .section h2 {{ 
            color: #0f172a; 
            margin-bottom: 20px; 
            padding-bottom: 10px; 
            border-bottom: 3px solid #3b82f6; 
            font-size: 1.5em;
        }}
        .resource-list {{ 
            display: flex; 
            flex-direction: column; 
            gap: 12px; 
        }}
        .resource-item {{ 
            background: #f8fafc; 
            border-radius: 10px; 
            padding: 20px; 
            border-left: 5px solid #3b82f6; 
            transition: transform 0.2s, box-shadow 0.2s; 
            text-decoration: none;
            display: block;
        }}
        .resource-item:hover {{ 
            transform: translateX(5px); 
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .resource-title {{ 
            font-size: 1.2em; 
            font-weight: bold; 
            color: #1e293b; 
            margin-bottom: 5px; 
        }}
        .resource-desc {{ 
            color: #64748b; 
            font-size: 0.95em; 
        }}
        .footer {{ 
            text-align: center; 
            margin-top: 40px; 
            padding-top: 20px; 
            border-top: 1px solid #e2e8f0; 
            color: #94a3b8; 
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>MEGA League Stats & Analysis</h1>
        <p class="subtitle">Fantasy Football Analytics & Reports</p>
        
{sections}
        
        <div class="footer">
            MEGA League Statistics & Analysis Hub
        </div>
    </div>
</body>
</html>
"""

def get_file_description(filename):
    descriptions = {
        'playoff_race_w15.html': 'Current playoff standings, seeding, and race analysis',
        'playoff_race.html': 'Playoff race visualization and analysis',
        'playoff_race_table.html': 'Detailed playoff race table',
        'sos_graphs.html': 'Visual analysis of team schedules and difficulty',
        'sos_season2.html': 'Season 2 SoS — combined sortable table and bar charts',
        'sos_season2_table.html': 'Season 2 SoS — sortable table with conference/division filters',
        'sos_season2_bars.html': 'Season 2 SoS — bar charts by league, conference, division',
        'stats_dashboard.html': '🏠 Main Stats Hub - Access all team analytics visualizations from one place',
        'team_stats_explorer.html': '📊 Interactive Win% correlation explorer with 20+ team metrics',
        'team_stats_correlations.html': '🔍 34 cross-metric correlation graphs revealing strategic insights',
        'team_player_usage.html': '👥 25 player usage graphs (target distribution + performance impact: INTs, sacks, efficiency, TDs)',
        'rankings_explorer.html': '🎯 12 strategic ranking visualizations (offensive/defensive balance, pass/rush philosophy, efficiency patterns)',
        'afc_race.png': 'AFC playoff standings and race visualization',
        'afc_compl.png': 'AFC season completion metrics',
        'nfc_race.png': 'NFC playoff standings and race visualization',
        'nfc_compl.png': 'NFC season completion metrics',
        'Tot_sos.png': 'Overall league strength of schedule visualization',
        'Afc_total_sos.png': 'AFC conference strength of schedule breakdown',
        'nfc_total.png': 'NFC conference strength of schedule breakdown',
        'playoff_race_analysis.md': 'Detailed analysis of playoff scenarios and race dynamics',
        'playoff_race_report.md': 'Playoff race summary report',
        'nfl_playoff_tie.txt': 'Reference document for playoff tiebreaker scenarios',
    }
    return descriptions.get(filename, f'{filename}')

def format_title(filename):
    name = Path(filename).stem
    name = name.replace('_', ' ').replace('-', ' ')
    return ' '.join(word.capitalize() for word in name.split())

def categorize_files():
    if not DOCS_DIR.exists():
        return {}
    
    categories = {
        'Reports & Visualizations': [],
        'Playoff Race Images': [],
        'Strength of Schedule Images': [],
        'Documentation': [],
        'Other Files': []
    }
    
    for file in sorted(DOCS_DIR.iterdir()):
        if file.name in ['.DS_Store', 'index.html', 'CNAME']:
            continue
        
        filename = file.name
        
        if filename.endswith('.html'):
            categories['Reports & Visualizations'].append(filename)
        elif 'race' in filename.lower() and filename.endswith('.png'):
            categories['Playoff Race Images'].append(filename)
        elif 'compl' in filename.lower() and filename.endswith('.png'):
            categories['Playoff Race Images'].append(filename)
        elif 'sos' in filename.lower() and filename.endswith('.png'):
            categories['Strength of Schedule Images'].append(filename)
        elif filename.endswith(('.md', '.txt')):
            categories['Documentation'].append(filename)
        else:
            categories['Other Files'].append(filename)
    
    return {k: v for k, v in categories.items() if v}

def generate_section(title, files):
    items = []
    for filename in files:
        resource_title = format_title(filename)
        resource_desc = get_file_description(filename)
        items.append(f"""                <a href="docs/{filename}" class="resource-item">
                    <div class="resource-title">{resource_title}</div>
                    <div class="resource-desc">{resource_desc}</div>
                </a>""")
    
    section = f"""        <div class="section">
            <h2>{title}</h2>
            <div class="resource-list">
{chr(10).join(items)}
            </div>
        </div>"""
    
    return section

def run_aggregation_script():
    """Run the team stats aggregation scripts to generate CSV data."""
    scripts = [
        ("stats_scripts/aggregate_team_stats.py", "Team stats"),
        ("stats_scripts/aggregate_player_usage.py", "Player usage")
    ]
    
    for script_rel, name in scripts:
        script_path = ROOT_DIR / script_rel
        if script_path.exists():
            print(f"Running {name} aggregation script...")
            try:
                result = subprocess.run(
                    ["python3", str(script_path)],
                    cwd=str(ROOT_DIR),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"✓ {name} aggregated successfully")
                else:
                    print(f"⚠ {name} aggregation warning: {result.stderr}")
            except Exception as e:
                print(f"⚠ Could not run {name} aggregation: {e}")
        else:
            print(f"⚠ {name} aggregation script not found, skipping")

def main():
    run_aggregation_script()
    
    categories = categorize_files()
    
    sections = []
    for category, files in categories.items():
        sections.append(generate_section(category, files))
    
    html_content = HTML_TEMPLATE.format(sections='\n        \n'.join(sections))
    
    output_path = ROOT_DIR / "index.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nGenerated index.html in root with {sum(len(files) for files in categories.values())} files from docs/")
    for category, files in categories.items():
        print(f"  {category}: {len(files)} files")

if __name__ == "__main__":
    main()
