# MEGA League NFL Stats Analysis

Comprehensive NFL statistics analysis and visualization system for the MEGA League, featuring playoff probability calculations, strength of schedule analysis, and interactive HTML reports.

## 📁 Project Structure

```
MEGA_neonsportz_stats/
├── scripts/              # Analysis scripts
│   ├── calc_sos_by_rankings.py       # Calculate SOS using team rankings
│   ├── calc_remaining_sos.py         # Calculate remaining schedule strength
│   ├── calc_playoff_probabilities.py # Calculate playoff chances with NFL tiebreakers
│   └── playoff_race_html.py          # Generate playoff race HTML visualization
├── docs/                 # GitHub Pages output (HTML, images)
│   ├── playoff_race.html           # Main playoff race visualization
│   ├── playoff_race_report.md      # Markdown report
│   └── [other visualization files]
├── output/               # Data processing results (CSV, JSON)
│   ├── ranked_sos_by_conference.csv
│   ├── remaining_sos_by_conference.csv
│   └── playoff_probabilities.json
├── MEGA_*.csv           # Source data files
└── README.md            # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- No external dependencies required (uses only standard library)

### Running the Full Analysis

To generate the complete playoff race analysis with probabilities:

```bash
# Navigate to project directory
cd /path/to/MEGA_neonsportz_stats

# Run the main playoff race generator
python3 scripts/playoff_race_html.py
```

This automatically:
1. Calculates playoff probabilities using NFL tiebreaker rules
2. Generates interactive HTML visualization
3. Creates markdown report

**Output files:**
- `docs/playoff_race.html` - Open in browser for full interactive visualization
- `docs/playoff_race_report.md` - Markdown summary
- `output/playoff_probabilities.json` - Raw probability data

## 📊 Individual Scripts

### 1. Calculate Strength of Schedule (Rankings-Based)

```bash
python3 scripts/calc_sos_by_rankings.py
```

**What it does:**
- Analyzes team rankings (offense, defense, overall)
- Computes strength scores for each team
- Calculates SOS for remaining and past games
- Considers conference standings

**Output:** `output/ranked_sos_by_conference.csv`

**Columns:**
- `team`, `conference`, `W`, `L`
- `remaining_games` - Games left in season
- `ranked_sos_avg` - Average strength of remaining opponents
- `past_ranked_sos_avg` - Average strength of past opponents
- `total_ranked_sos` - Combined strength score

### 2. Calculate Remaining SOS (Win Percentage-Based)

```bash
python3 scripts/calc_remaining_sos.py
```

**What it does:**
- Uses opponent win percentages to calculate SOS
- Simpler calculation than rankings-based method
- Provides alternative SOS metric

**Output:** `output/remaining_sos_by_conference.csv`

### 3. Calculate Playoff Probabilities

```bash
python3 scripts/calc_playoff_probabilities.py
```

**What it does:**
- Implements official NFL tiebreaker rules:
  - Head-to-head records
  - Division records
  - Conference records
  - Strength of Victory (SOV)
  - Strength of Schedule (SOS)
  - Points scored/allowed
- Determines division leaders
- Ranks Wild Card candidates
- Projects final records based on remaining SOS
- Calculates playoff probability for each team

**Output:** `output/playoff_probabilities.json`

**Probability Calculation:**

**For Division Leaders:**
- Base probability: 95-99%
- Adjusted by win cushion over closest rival

**For Wild Card Candidates:**
- Base probability by position: WC5=75%, WC6=60%, WC7=45%
- SOS advantage factor: `(avg_competitor_SOS - team_SOS) × 80`
- Win projection factor: `(projected_wins - cutoff) × 12`
- Conference record factor: `(conf_pct - 0.5) × 20`
- Final capped at 1-95%

### 4. Generate Playoff Race HTML

```bash
python3 scripts/playoff_race_html.py
```

**What it does:**
- Combines all data sources
- Generates interactive HTML visualization
- Creates markdown report
- Includes Russian-language analysis section

**Features:**
- Color-coded playoff seeding
- Division leaders (Seeds 1-4)
- Wild Card teams (Seeds 5-7)
- Bubble teams (>20% playoff chance)
- Long shots (<20% chance)
- SOS difficulty indicators
- Detailed Russian commentary on key races

## 📋 Required Data Files

The scripts expect these CSV files in the root directory:

- `MEGA_teams.csv` - Team information (names, divisions, conferences, records)
- `MEGA_games.csv` - Game results and schedule (status, scores, teams)
- `MEGA_rankings.csv` - Weekly team rankings (offense, defense, overall)

**Note:** These files are generated from your league's data source.

## 🔄 Typical Workflow

### Weekly Update Process

```bash
# 1. Update your MEGA_*.csv files with latest data

# 2. Calculate SOS using rankings method
python3 scripts/calc_sos_by_rankings.py

# 3. (Optional) Calculate SOS using win percentage method
python3 scripts/calc_remaining_sos.py

# 4. Generate complete playoff race analysis
python3 scripts/playoff_race_html.py

# 5. View results
open docs/playoff_race.html
```

### For GitHub Pages

The `docs/` folder is configured for GitHub Pages:

1. Push your changes to GitHub
2. Enable GitHub Pages in repository settings
3. Set source to `/docs` folder
4. Your visualizations will be available at `https://[username].github.io/[repo-name]/playoff_race.html`

## 📈 Understanding the Output

### Playoff Race HTML

**Color Coding:**
- **Blue** - Division Leaders (Seeds 1-4)
- **Green** - Wild Card teams (Seeds 5-7)
- **Yellow** - Bubble teams (>20% chance)
- **Red** - Long shots (<20% chance)

**SOS Indicators:**
- 🟢 **EASY** - SOS < 0.45 (easier remaining schedule)
- 🟡 **BALANCED** - SOS 0.45-0.55 (average difficulty)
- 🔴 **BRUTAL** - SOS > 0.55 (tougher remaining schedule)

### Probability JSON Structure

```json
{
  "TeamName": {
    "conference": "AFC",
    "division": "AFC North",
    "W": 10,
    "L": 3,
    "win_pct": 0.769,
    "conference_pct": 0.750,
    "division_pct": 0.833,
    "strength_of_victory": 0.520,
    "strength_of_schedule": 0.505,
    "playoff_probability": 95.0,
    "remaining_sos": 0.450,
    "remaining_games": 4
  }
}
```

## 🔧 Customization

### Adjusting Probability Weights

Edit `scripts/calc_playoff_probabilities.py`:

```python
# Line 289 - SOS advantage multiplier (default: 80)
sos_advantage = (avg_wc_sos - team_sos) * 80

# Line 293 - Win projection multiplier (default: 12)
wins_above_cutoff = (projected_wins - cutoff_win_level) * 12

# Line 295 - Conference record multiplier (default: 20)
conference_factor = (stats[team_name]['conference_pct'] - 0.5) * 20
```

### Changing Bubble Team Threshold

Edit `scripts/playoff_race_html.py` line 205:

```python
# Show teams with >20% playoff chance (default: 20)
wc_with_chances = [t for t in wc if t.get('playoff_chance', 0) > 20]
```

## 📝 Notes

- **Tiebreaker Rules:** The system implements official NFL tiebreaker rules in order
- **SOS Calculation:** Uses team rankings (offense/defense/overall) for more accurate strength assessment
- **Projections:** Win projections assume teams perform at level inversely proportional to opponent strength
- **Division Leaders:** Automatically receive 95-99% playoff probability
- **Conference Sorting:** All results are organized by AFC/NFC

## 🐛 Troubleshooting

### "FileNotFoundError: MEGA_teams.csv"

Ensure you're running scripts from the project root directory, or data files are in the correct location.

### "KeyError: 'homeTeam'" or similar

Check that your CSV files have the expected column names:
- `MEGA_games.csv`: `homeTeam`, `awayTeam`, `homeScore`, `awayScore`, `status`, `weekIndex`
- `MEGA_teams.csv`: `displayName`, `divisionName`, `conferenceName`, `totalWins`, `totalLosses`

### HTML file is empty or broken

Verify that:
1. `output/ranked_sos_by_conference.csv` exists and has data
2. `output/playoff_probabilities.json` was generated successfully
3. All scripts completed without errors

## 📄 License

This project is for personal/league use. Modify and distribute as needed.

## 🤝 Contributing

Feel free to modify the scripts for your league's specific needs. Common customizations:
- Adjust probability calculation weights
- Change visualization colors/styles
- Add additional stats to the HTML report
- Modify tiebreaker rules for custom leagues
