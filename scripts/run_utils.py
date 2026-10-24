#!/usr/bin/env python3
import sys
import subprocess
import os
import csv
import shutil
from pathlib import Path


def season_start_row(season_index, games_csv='MEGA_games.csv'):
    """Locate the requested CSV season without legacy export row offsets."""
    with open(games_csv, newline='', encoding='utf-8') as f:
        for index, row in enumerate(csv.DictReader(f), 1):
            if row.get('seasonIndex') == str(season_index) and row.get('stageIndex') == '1':
                return index
    raise ValueError(f'No regular-season games for seasonIndex={season_index}')


def publish_browser_data(season_index):
    """Publish only current artifacts; never read from historical archives."""
    destination = Path('docs/data')
    destination.mkdir(parents=True, exist_ok=True)
    season = season_index + 1
    sources = {
        'MEGA_teams.csv': 'MEGA_teams.csv',
        'MEGA_users.csv': 'MEGA_users.csv',
        'mega_elo.csv': 'mega_elo.csv',
        'output/playoff_probabilities.json': 'playoff_probabilities.json',
        f'output/sos/season{season}_elo.csv': f'season{season}_elo.csv',
        f'output/schedules/season{season}/all_schedules.json': f'schedules_season{season}.json',
        'output/ranked_sos_by_conference.csv': f'ranked_sos_by_conference_season{season}.csv',
    }
    for source, name in sources.items():
        if Path(source).is_file():
            shutil.copyfile(source, destination / name)


def run_script(script_name, description, optional=False, extra_args=None):
    """Run a Python script and print its status"""
    print("\n" + "="*80)
    print(f"Running: {description}")
    if optional:
        print("(Optional)")
    print("="*80)

    try:
        cmd = [sys.executable, script_name]
        if extra_args:
            cmd.extend(extra_args)
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            return True
        else:
            if optional:
                print(f"⚠ {description} skipped (missing dependencies)")
                return True
            else:
                print(f"✗ {description} failed with exit code {result.returncode}")
                return False

    except Exception as e:
        if optional:
            print(f"⚠ {description} skipped: {str(e)}")
            return True
        else:
            print(f"✗ Error running {description}: {str(e)}")
            return False
