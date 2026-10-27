#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DOCS_DIR = ROOT_DIR / "docs"
SITE_MANIFEST_PATH = DOCS_DIR / "site_manifest.json"
BUILD_MANIFEST_PATH = ROOT_DIR / "output" / "build_manifest.json"
try:
    from cycle_context import CycleContext
except ImportError:  # imported as a package from tests
    from scripts.cycle_context import CycleContext

try:
    from mega.pipeline.manifests import validate_browser_data
except ModuleNotFoundError:  # direct script invocation puts scripts/ first on sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from mega.pipeline.manifests import validate_browser_data

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
        'sos_season1.html': 'Season 1 strength of schedule using the supplied ELO ratings',
        'sos_graphs_season1.html': 'Season 1 rankings-based schedule analysis',
        'playoff_race.html': 'Playoff race visualization and analysis',
        'playoff_race_table.html': 'Detailed playoff race table',
        'week18_simulator.html': 'Interactive Week 18 playoff simulator for the active snapshot',
        'team_scenarios.html': '🎲 Monte Carlo Playoff Scenarios - Interactive team-by-team simulation analysis with probability distributions',
        'sos_graphs.html': 'Visual analysis of team schedules and difficulty',
        'sos_season2.html': 'Season 2 SoS — combined sortable table and bar charts',
        'sos_season3.html': 'Season 3 SoS — combined sortable table and bar charts',
        'sos_season2_table.html': 'Season 2 SoS — sortable table with conference/division filters',
        'sos_season2_bars.html': 'Season 2 SoS — bar charts by league, conference, division',
        'sos_graphs_season3.html': 'Season 3 SoS visualizations (graphs)',
        'sos_season4.html': 'Season 4 SoS — combined sortable table and bar charts',
        'sos_graphs_season4.html': 'Season 4 SoS visualizations (graphs)',
        'stats_dashboard.html': '🏠 Main Stats Hub - Access all team analytics visualizations from one place',
        'team_stats_explorer.html': '📊 Interactive Win% correlation explorer with 20+ team metrics',
        'team_stats_correlations.html': '🔍 35 cross-metric correlation graphs revealing strategic insights',
        'team_elo_correlations.html': '⚡ 15 ELO-based correlation charts analyzing team ratings vs performance metrics',
        'team_player_usage.html': '👥 25 player usage graphs (target distribution + performance impact: INTs, sacks, efficiency, TDs)',
        'trade_dashboard.html': '🔁 Trades & multi-team players dashboard (team impact + per-player stint splits)',
        'rankings_explorer.html': '🎯 12 strategic ranking visualizations (offensive/defensive balance, pass/rush philosophy, efficiency patterns)',
        'draft_class_2026.html': 'Draft class 2026 overview and scouting dashboard',
        'draft_class_2026_nointro.html': 'Draft class 2026 overview (no intro)',
        'draft_class_2027.html': 'Draft class 2027 overview and scouting dashboard',
        'draft_class_2028.html': 'Draft class 2028 — final-season analytics (day-1 impact lens)',
        'draft_class_2028_nointro.html': 'Draft class 2028 overview (no intro)',
        'draft_rounds_1_7_2028.html': 'Draft class 2028 — round-by-round recap (rounds 1-7)',
        'draft_mock_2028.md': 'Draft 2028 mock analysis (Russian) — pick-by-pick final-season verdicts',
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
    if not DOCS_DIR.exists() or not SITE_MANIFEST_PATH.is_file():
        return {}

    site_manifest = json.loads(SITE_MANIFEST_PATH.read_text(encoding="utf-8"))
    try:
        build_manifest = json.loads(BUILD_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        build_manifest = {}
    try:
        import_metadata = json.loads((DOCS_DIR / "data" / "import_metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        import_metadata = {}
    active_season = import_metadata.get("seasonNumber")
    try:
        current_snapshot = CycleContext.from_file(DOCS_DIR / "data" / "import_metadata.json", ROOT_DIR).snapshot_id
    except (OSError, ValueError):
        current_snapshot = None
    browser_manifest_matches = True
    browser_data = None
    browser_manifest_path = DOCS_DIR / "data" / "data_manifest.json"
    if browser_manifest_path.is_file():
        try:
            browser_data = validate_browser_data(ROOT_DIR)
        except (OSError, ValueError):
            browser_manifest_matches = False
    snapshot_matches = bool(
        current_snapshot
        and build_manifest.get("snapshotId") == current_snapshot
        and browser_manifest_matches
    )

    categories = {"Reports & Visualizations": [], "Documentation": []}
    for entry in site_manifest.get("pages", []):
        filename = entry.get("path", "")
        if not filename or not (DOCS_DIR / filename).is_file():
            continue
        if entry.get("feature") and entry["feature"] not in import_metadata.get("enabledFeatures", []):
            continue
        if entry.get("seasonScoped"):
            match = re.search(r"season(\d+)", filename)
            if not match or active_season is None or int(match.group(1)) != int(active_season):
                continue
        required_data = entry.get("requiresData", [])
        if required_data and (
            not browser_manifest_matches
            or not browser_data
            or any(key not in browser_data.get("data", {}) for key in required_data)
        ):
            continue
        requirements = entry.get("requires", [])
        if requirements:
            artifacts = build_manifest.get("artifacts", {})
            if not snapshot_matches:
                continue
            if any(
                path not in artifacts
                or not (ROOT_DIR / path).is_file()
                or _sha256(ROOT_DIR / path) != artifacts[path]
                for path in requirements
            ):
                continue
        category = "Documentation" if entry.get("kind") == "reference" else "Reports & Visualizations"
        categories[category].append(filename)

    return {key: sorted(files) for key, files in categories.items() if files}


def _sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

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

def main():
    # An archived cycle intentionally has no active exports. Do not create
    # misleading empty aggregates or advertise dashboards until data arrives.
    required_inputs = ('MEGA_teams.csv', 'MEGA_games.csv', 'MEGA_players.csv')
    missing_inputs = [name for name in required_inputs if not (ROOT_DIR / name).is_file()]
    categories = {}
    if missing_inputs:
        sections = ['''        <div class="section">
            <h2>Madden 27 — awaiting league data</h2>
            <p>The Madden 26 league data and reports have been archived.
            Current dashboards will be available after the new league exports
            are imported and the analysis is generated.</p>
            <div class="resource-list">
                <a href="README.md" class="resource-item">
                    <div class="resource-title">Madden 27 setup</div>
                    <div class="resource-desc">Data imports and calculation settings for the new cycle</div>
                </a>
                <a href="archive/madden-26/README.md" class="resource-item">
                    <div class="resource-title">Madden 26 archive</div>
                    <div class="resource-desc">Historical data and reports from the previous game</div>
                </a>
            </div>
        </div>''']
        print('Awaiting active exports: ' + ', '.join(missing_inputs))
    else:
        categories = categorize_files()
        sections = []
        for category, files in categories.items():
            sections.append(generate_section(category, files))
        metadata_path = DOCS_DIR / 'data/import_metadata.json'
        if metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            season = int(metadata['seasonNumber'])
            week = int(metadata['completedThroughWeek'])
            elo_week = int(metadata['eloSourceWeek'])
            sections.insert(0, f'''        <div class="section">
            <h2>Madden 27 · Season {season} · Through Week {week}</h2>
            <p>ELO ratings: Week {elo_week}, used with the current league exports.</p>
            <p><a href="docs/data/MEGA_users.csv">Team / GM / NeonSportz user list</a> ·
            <a href="docs/data/mega_elo.csv">ELO ratings</a> ·
            <a href="docs/data/elo_week8.png">Supplied ELO source</a></p>
        </div>''')
    
    html_content = HTML_TEMPLATE.format(sections='\n        \n'.join(sections))
    html_content = '\n'.join(line.rstrip() for line in html_content.splitlines()) + '\n'
    
    output_path = ROOT_DIR / "index.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nGenerated index.html in root with {sum(len(files) for files in categories.values())} files from docs/")
    for category, files in categories.items():
        print(f"  {category}: {len(files)} files")

if __name__ == "__main__":
    main()
