# MEGA League NFL Stats Analysis

Comprehensive NFL statistics analysis and visualization system for the MEGA League, featuring playoff probability calculations, strength of schedule analysis, draft pick race tracking, and interactive HTML reports.

## 📁 Project Structure

```
MEGA_neonsportz_stats/
├── scripts/                           # Analysis scripts
│   ├── run_all_playoff_analysis.py   # 🚀 RUN THIS - Executes all scripts
│   ├── calc_sos_by_rankings.py       # Calculate SOS using team rankings
│   ├── calc_remaining_sos.py         # Calculate remaining schedule strength
│   ├── calc_playoff_probabilities.py # Calculate playoff chances with Monte Carlo simulation
│   ├── playoff_race_table.py         # Generate interactive playoff race table
│   ├── playoff_race_html.py          # Generate full playoff race HTML report
│   ├── top_pick_race_analysis.py     # Generate draft pick race analysis
│   └── generate_index.py             # Generate index.html for GitHub Pages
├── docs/                              # GitHub Pages output (HTML, images)
│   ├── playoff_race.html             # Full playoff race report with embedded table
│   ├── playoff_race_table.html       # Interactive playoff race table
│   └── playoff_race_report.md        # Markdown report
├── output/                            # Data processing results
│   ├── ranked_sos_by_conference.csv  # SOS calculations
│   ├── playoff_probabilities.json    # Playoff probability data
│   └── draft_race/                   # Draft pick analysis
├── MEGA_*.csv                         # Source data files (from Neon Export)
├── index.html                         # GitHub Pages landing page
└── README.md                          # This file
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.7+**
- **No external dependencies required** for core functionality (uses only standard library)

### Step 1: Export Data from Neon Sports

1. Use the **Neon Export** feature to download your league data
2. Place the CSV files in the project root directory
3. **Important:** CSV files have a prefix with your league name (e.g., `MEGA_teams.csv`)
   - If your league name is different, either:
     - Rename your files to match: `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_rankings.csv`
     - Or update the CSV import paths in the scripts to match your league name

### Step 2: Run All Analysis Scripts

```bash
# Navigate to project directory
cd /path/to/MEGA_neonsportz_stats

# Run the complete analysis pipeline
python3 scripts/run_all_playoff_analysis.py
```

This single command automatically:
1. ✅ Calculates strength of schedule (SOS)
2. ✅ Calculates playoff probabilities using Monte Carlo simulation
3. ✅ Generates interactive playoff race table
4. ✅ Generates full playoff race HTML report
5. ✅ Generates draft pick race analysis

**Output files:**
- `docs/playoff_race.html` - Full playoff analysis report (open in browser)
- `docs/playoff_race_table.html` - Interactive playoff race table
- `docs/playoff_race_report.md` - Markdown summary
- `output/playoff_probabilities.json` - Raw probability data
- `output/draft_race/draft_race_report.md` - Draft pick race analysis

## 📊 Individual Scripts

### 1. Run All Analysis (Recommended)

```bash
python3 scripts/run_all_playoff_analysis.py
```

**What it does:**
- Executes all analysis scripts in the correct order
- Provides progress updates and error handling
- Generates complete playoff and draft analysis

**Output:** All files listed in Quick Start section

### 2. Calculate Strength of Schedule (Rankings-Based)

```bash
python3 scripts/calc_sos_by_rankings.py
```

**What it does:**
- Analyzes team rankings (offense, defense, overall)
- Computes strength scores for each team based on multiple metrics
- Calculates SOS for remaining and past games
- Considers conference standings

**Output:** `output/ranked_sos_by_conference.csv`

**Columns:**
- `team`, `conference`, `W`, `L`
- `remaining_games` - Games left in season
- `ranked_sos_avg` - Average strength of remaining opponents
- `past_ranked_sos_avg` - Average strength of past opponents
- `total_ranked_sos` - Combined strength score

### 3. Calculate Remaining SOS (Win Percentage-Based)

```bash
python3 scripts/calc_remaining_sos.py
```

**What it does:**
- Uses opponent win percentages to calculate SOS
- Simpler calculation than rankings-based method
- Provides alternative SOS metric

**Output:** `output/remaining_sos_by_conference.csv`

### 4. Calculate Playoff Probabilities

```bash
python3 scripts/calc_playoff_probabilities.py
```

**What it does:**
- Runs **Monte Carlo simulation** (1000 iterations) to calculate playoff probabilities
- Implements official NFL tiebreaker rules:
  - Head-to-head records
  - Division records
  - Conference records
  - Strength of Victory (SOV)
  - Strength of Schedule (SOS)
  - Points scored/allowed
- Determines division leaders and Wild Card candidates
- Calculates playoff probability, division win probability, and bye probability for each team

**Output:** `output/playoff_probabilities.json`

**Probability Calculation:**
- Uses Monte Carlo simulation to project remaining games
- Win probability based on: 70% team win percentage + 30% SOS
- Simulates 1000 seasons to determine playoff outcomes
- Applies NFL tiebreaker rules to determine final seeding

### 5. Generate Playoff Race Table

```bash
python3 scripts/playoff_race_table.py
```

**What it does:**
- Creates interactive double-column table (AFC/NFC side-by-side)
- Shows playoff probabilities, division win chances, bye probabilities
- Displays remaining opponents with team logos
- Color-coded SOS indicators
- Responsive design for mobile and desktop

**Output:** `docs/playoff_race_table.html`

**Features:**
- Team logos from Neon Sports CDN
- Hover tooltips with detailed probability explanations
- Color-coded playoff seeding
- Remaining schedule with opponent rankings

### 6. Generate Playoff Race HTML Report

```bash
python3 scripts/playoff_race_html.py
```

**What it does:**
- Combines all data sources into comprehensive HTML report
- Embeds playoff race table
- Includes Russian-language analysis section
- Generates markdown report

**Output:** `docs/playoff_race.html`, `docs/playoff_race_report.md`

**Features:**
- Full playoff race analysis
- Embedded interactive table
- Detailed commentary on key races
- SOS difficulty indicators

### 7. Generate Draft Pick Race Analysis

### 8. Generate Draft Pick Race Analysis

```bash
python3 scripts/top_pick_race_analysis.py
```

**What it does:**
- Analyzes bottom teams for draft pick order
- Projects final records based on remaining SOS
- Identifies tank battles and draft position risks

**Output:** `output/draft_race/draft_race_report.md`

**Features:**
- Top 16 draft picks projection
- SOS impact on draft position
- Tank battle analysis

### 9. Generate Index Page

```bash
python3 scripts/generate_index.py
```

**What it does:**
- Creates landing page for GitHub Pages
- Categorizes all generated files
- Provides easy navigation to all reports

**Output:** `index.html`

## 📋 Required Data Files

The scripts expect these CSV files in the root directory (exported from Neon Sports):

- `MEGA_teams.csv` - Team information (names, divisions, conferences, records, logos)
- `MEGA_games.csv` - Game results and schedule (status, scores, teams, weeks)
- `MEGA_rankings.csv` - Weekly team rankings (offense, defense, overall)

**Important Notes:**
- Files must have your league name as prefix (e.g., `MEGA_teams.csv`)
- If your league name is different, rename files or update script imports
- Export fresh data from Neon Sports before each analysis run

**Required Columns:**

`MEGA_teams.csv`:
- `displayName`, `teamName`, `divisionName`, `conferenceName`
- `totalWins`, `totalLosses`, `rank`, `logoId`

`MEGA_games.csv`:
- `homeTeam`, `awayTeam`, `homeScore`, `awayScore`
- `status` (1=scheduled, 2=in progress, 3=final)
- `weekIndex`, `seasonIndex`, `stageIndex`

`MEGA_rankings.csv`:
- `team`, `rank`, `prevRank`
- `ptsForRank`, `ptsAgainstRank`
- `offTotalYdsRank`, `offPassYdsRank`, `offRushYdsRank`
- `defTotalYdsRank`, `defPassYdsRank`, `defRushYdsRank`
- `weekIndex`, `seasonIndex`, `stageIndex`

## 🔄 Typical Workflow

### Weekly Update Process

```bash
# 1. Export latest data from Neon Sports
#    - Use Neon Export feature
#    - Download teams, games, and rankings CSV files
#    - Place in project root directory

# 2. Run complete analysis pipeline
python3 scripts/run_all_playoff_analysis.py

# 3. View results
open docs/playoff_race.html

# 4. (Optional) Generate index page for GitHub Pages
python3 scripts/generate_index.py
```

### For GitHub Pages

The `docs/` folder is configured for GitHub Pages:

1. Run `python3 scripts/generate_index.py` to create landing page
2. Push your changes to GitHub
3. Enable GitHub Pages in repository settings
4. Set source to **root** folder (index.html) or `/docs` folder
5. Your site will be available at `https://[username].github.io/[repo-name]/`

## 📈 Understanding the Output

### Playoff Race Table (playoff_race_table.html)

**Color Coding:**
- **Blue** - Division Leaders (Seeds 1-4)
- **Green** - Wild Card teams (Seeds 5-7)
- **Yellow** - Bubble teams (>20% chance)
- **Gray** - Eliminated teams

**SOS Indicators:**
- 🟢 **EASY** - SOS < 0.45 (easier remaining schedule)
- 🟡 **BALANCED** - SOS 0.45-0.55 (average difficulty)
- 🔴 **BRUTAL** - SOS > 0.55 (tougher remaining schedule)

**Probability Columns:**
- **Playoff %** - Chance to make playoffs (Monte Carlo simulation)
- **Div Win %** - Chance to win division
- **Bye %** - Chance to get first-round bye (#1 seed)
- **SB %** - Super Bowl probability estimate

**Hover Tooltips:**
- Hover over any probability to see detailed calculation explanation
- Tooltips explain Monte Carlo methodology and factors

### Playoff Race HTML Report (playoff_race.html)

**Features:**
- Embedded interactive playoff race table
- Detailed analysis of key playoff races
- Russian-language commentary section
- SOS difficulty analysis
- Division race breakdowns

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
    "division_win_probability": 87.5,
    "bye_probability": 23.4,
    "remaining_sos": 0.450,
    "remaining_games": 4
  }
}
```

## 🔧 Customization

### Adjusting Monte Carlo Simulation

Edit `scripts/calc_playoff_probabilities.py`:

```python
# Number of simulations (default: 1000)
NUM_SIMULATIONS = 1000

# Win probability formula weights
# win_prob = (team_win_pct * 0.7) + ((1 - opponent_sos) * 0.3)
TEAM_STRENGTH_WEIGHT = 0.7
SOS_WEIGHT = 0.3
```

### Changing League Name Prefix

If your league name is not "MEGA", update CSV file paths in all scripts:

```python
# Change from:
with open('MEGA_teams.csv', 'r', encoding='utf-8') as f:

# To (example for "MYLIGA"):
with open('MYLIGA_teams.csv', 'r', encoding='utf-8') as f:
```

Or simply rename your exported CSV files to match `MEGA_*.csv` format.

## 📝 Notes

- **Monte Carlo Simulation:** Uses 1000 simulations to calculate realistic playoff probabilities
- **Tiebreaker Rules:** Implements official NFL tiebreaker rules in order (H2H, division, conference, SOV, SOS, points)
- **SOS Calculation:** Uses team rankings (offense/defense/overall) for more accurate strength assessment than simple win percentage
- **Win Probability:** Based on 70% team strength + 30% opponent SOS
- **Division Leaders:** Calculated via simulation, not automatically assigned high probabilities
- **Conference Sorting:** All results organized by AFC/NFC for easy comparison
- **Team Logos:** Automatically fetched from Neon Sports CDN using logoId from teams CSV

## 🐛 Troubleshooting

### "FileNotFoundError: MEGA_teams.csv"

**Solution:**
- Ensure you're running scripts from the project root directory
- Verify CSV files are in the root directory (not in subdirectories)
- Check that files are named correctly: `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_rankings.csv`
- If your league name is different, rename files or update script imports

### "KeyError: 'homeTeam'" or similar column errors

**Solution:**
Check that your CSV files have the expected column names:

`MEGA_games.csv`:
- Required: `homeTeam`, `awayTeam`, `homeScore`, `awayScore`, `status`, `weekIndex`

`MEGA_teams.csv`:
- Required: `displayName`, `divisionName`, `conferenceName`, `totalWins`, `totalLosses`, `rank`, `logoId`

`MEGA_rankings.csv`:
- Required: `team`, `rank`, `ptsForRank`, `ptsAgainstRank`, various yards ranks

### HTML file is empty or broken

**Solution:**
1. Verify `output/ranked_sos_by_conference.csv` exists and has data
2. Verify `output/playoff_probabilities.json` was generated successfully
3. Check that all scripts completed without errors
4. Run `python3 scripts/run_all_playoff_analysis.py` to regenerate all files

 

### Probabilities seem incorrect

**Solution:**
- Verify your CSV data is up-to-date from Neon Sports
- Check that game statuses are correct (1=scheduled, 2=in progress, 3=final)
- Ensure team records (W/L) match actual standings
- Review `output/playoff_probabilities.json` for detailed probability data

## 📄 License

This project is for personal/league use. Modify and distribute as needed.

## 🤝 Contributing

Feel free to modify the scripts for your league's specific needs. Common customizations:

**Probability Calculations:**
- Adjust Monte Carlo simulation count (default: 1000)
- Change win probability formula weights
- Modify tiebreaker rules for custom leagues

**Visualization:**
- Change color schemes in HTML/CSS
- Adjust SOS thresholds (easy/balanced/brutal)
- Customize team logo sources
- Add additional stats columns

**Analysis:**
- Add custom metrics (strength of victory, point differential, etc.)
- Create new visualization types
- Implement different playoff formats
- Add historical trend analysis

## 🆘 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify your CSV files match the required format
3. Review script output for specific error messages
4. Ensure you're using Python 3.7+

## 📊 Script Execution Order

When running scripts individually (not using `run_all_playoff_analysis.py`):

1. **First:** `calc_sos_by_rankings.py` - Generates SOS data
2. **Second:** `calc_playoff_probabilities.py` - Generates probability data
3. **Third:** `playoff_race_table.py` - Generates interactive table
4. **Fourth:** `playoff_race_html.py` - Generates full report
5. **Optional:** `top_pick_race_analysis.py` - Draft analysis
6. **Optional:** `generate_index.py` - GitHub Pages landing page

---

## 🎓 New to Python or GitHub?

**👉 See [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) for step-by-step instructions!**

The beginner guide includes:
- How to install Python
- How to download and run this project
- How to publish to GitHub Pages
- How to embed in Neon Sports news articles
- Common questions and troubleshooting
