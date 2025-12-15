# MEGA League NFL Stats Analysis

Comprehensive NFL statistics analysis and visualization system for the MEGA League, featuring playoff probability calculations, strength of schedule analysis, draft pick race tracking, and interactive HTML reports.

## 📁 Project Structure

```
MEGA_neonsportz_stats/
├── scripts/                           # Analysis scripts
│   ├── run_all.py                    # 🚀 Full pipeline (SoS S2 + playoff + stats + index)
│   ├── run_all_playoff_analysis.py   # Playoff + draft race pipeline
│   ├── run_all_stats.py              # Stats-only pipeline (team/player usage + rankings joins)
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

## 🧭 Architecture at a Glance

At a high level, the project is split into four domains. Each domain has clear CSV inputs, one or more orchestrator scripts, data outputs, and user-facing HTML pages:

| Domain               | Inputs CSVs                                                                                                                                  | Orchestrators / core scripts                                                                                                  | Outputs (data)                                                                                                         | Key HTML pages                                                                                               |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Playoff + draft race | `MEGA_teams.csv`, `MEGA_games.csv`, `MEGA_rankings.csv`                                                                                      | `scripts/run_all_playoff_analysis.py`, `scripts/calc_sos_by_rankings.py`, `scripts/calc_playoff_probabilities.py`, `scripts/top_pick_race_analysis.py` | `output/ranked_sos_by_conference.csv`, `output/playoff_probabilities.json`, `output/draft_race/draft_race_report.md` | `docs/playoff_race.html`, `docs/playoff_race_table.html`                                                    |
| Stats aggregation    | `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`, `MEGA_teams.csv` | `scripts/run_all_stats.py`, `stats_scripts/aggregate_team_stats.py`, `stats_scripts/aggregate_player_usage.py`, `stats_scripts/aggregate_rankings_stats.py` | `output/team_aggregated_stats.csv`, `output/team_player_usage.csv`, `output/team_rankings_stats.csv`, `output/player_team_stints.csv` | `docs/team_stats_explorer.html`, `docs/team_stats_correlations.html`, `docs/stats_dashboard.html`           |
| SoS Season 2 (ELO)   | `MEGA_games.csv`, `MEGA_teams.csv`, `mega_elo.csv`                                                                                           | `scripts/run_all.py`, `scripts/calc_sos_season2_elo.py`                                                                       | `output/sos/season2_elo.csv`, `output/sos/season2_elo.json`                                                          | `docs/sos_season2.html`, `docs/sos_graphs.html`                                                              |
| Roster / cap         | `MEGA_players.csv`, `MEGA_teams.csv`                                                                                                        | `scripts/power_rankings_roster.py`, `scripts/calc_team_y1_cap.py`, `scripts/tools/sync_data_to_docs.sh`                      | `output/power_rankings_roster.csv`, `output/cap_tool_verification.json`                                              | `docs/roster_cap_tool/index.html`, `docs/power_rankings_roster.html`, `docs/power_rankings_roster_charts.html` |

For a tour of the dashboards and which scripts power each HTML page, see `docs/README.md`.

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
# Choose one of the canonical workflows below
```

**Canonical workflows:**

- **Full pipeline (SoS Season 2 + playoff/draft + stats + index)**

  ```bash
  python3 scripts/run_all.py
  ```

- **Playoff + draft race only**

  ```bash
  python3 scripts/run_all_playoff_analysis.py
  ```

  This playoff + draft workflow automatically:
  1. ✅ Calculates strength of schedule (SOS)
  2. ✅ Calculates playoff probabilities using Monte Carlo simulation
  3. ✅ Generates interactive playoff race table
  4. ✅ Generates full playoff race HTML report
  5. ✅ Generates draft pick race analysis

- **Stats only (team/player usage + rankings joins)**

  ```bash
  python3 scripts/run_all_stats.py
  ```

- **Season 2 SoS only (ELO-based)**

  ```bash
  python3 scripts/calc_sos_season2_elo.py --season2-start-row 287
  ```

  See the “Season 2 Strength of Schedule (ELO)” section below for additional options and flags.
You can run any of these from the project root; they share the same CSV inputs.

### Step 3: Generate Trade-Aware Team & Player Stats (Recommended)

To regenerate all team and player stats, including trade-aware splits for multi-team players:

```bash
python3 scripts/run_all_stats.py
```

This will:
- Build `output/team_aggregated_stats.csv` (team stats, using canonical team keys).
- Build `output/team_player_usage.csv` (team usage distribution, trade-aware).
- Build `output/team_rankings_stats.csv` (team stats + rankings/ELO joins).
- Build `output/player_team_stints.csv` (one row per player/team/season stint).

For validation and a human-reviewable view of traded players, run:

```bash
python3 scripts/verify_trade_stats.py
```

This verification step:
- Writes `output/traded_players_report.csv` (multi-team players and their per-team stat lines).
- Checks invariants between `player_team_stints.csv` and `team_aggregated_stats.csv` to guard against doubled or mis-attributed production for traded players.

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

## 🗓️ Season 2 Strength of Schedule (ELO)

This pipeline computes Season 2 Strength of Schedule (SoS) using opponent ELO ratings, writes CSV/JSON artifacts, and provides interactive HTML views (table and bar charts).

### Inputs
- `MEGA_games.csv` — full schedule; Season 2 starts at row 287 (data rows, header excluded)
- `MEGA_teams.csv` — team metadata (conference, division, logoId)
- `mega_elo.csv` — team ELO snapshot (semicolon `;` delimited; decimal commas)

### Run SoS (ELO) Calculation

```bash
# Default run (starts at row 287 and writes outputs under ./output)
python3 scripts/calc_sos_season2_elo.py --season2-start-row 287

# Common options
python3 scripts/calc_sos_season2_elo.py \
  --games-csv MEGA_games.csv \
  --teams-csv MEGA_teams.csv \
  --elo-csv mega_elo.csv \
  --season2-start-row 287 \
  --include-home-advantage false \
  --hfa-elo-points 55 \
  --index-scale zscore-mean100-sd15 \
  --out-dir output
```

Artifacts produced:
- `output/schedules/season2/all_schedules.json` — per-team schedules (with opponent/homeAway/date)
- `output/sos/season2_elo.csv` — SoS table for Season 2
- `output/sos/season2_elo.json` — SoS rows for Season 2

### Verify Artifacts

```bash
# Validate schedules schema and counts
python3 scripts/verify_sos_season2_elo.py --check schedules

# Validate SoS table schema, rank ordering, and league averages
python3 scripts/verify_sos_season2_elo.py --check sos
```

### View UI Pages

```bash
# From repo root, serve docs locally
python3 -m http.server 8000

# Then open in your browser (combined page with tabs):
http://localhost:8000/docs/sos_season2.html
```

Logos are loaded via Neon Sports CDN using `logoId` from `MEGA_teams.csv`.

### One‑Command Pipeline (optional)

```bash
python3 scripts/run_all.py
```

This runs the end‑to‑end analysis and regenerates `index.html` with links to the new SoS pages. Open `index.html` from the repo root or visit `http://localhost:8000/index.html` if using the local server.

## Draft Class Analytics

- Purpose: Generate an analytics-focused HTML report for a given rookie draft class (e.g., 2026) using `MEGA_players.csv` and, optionally, `MEGA_teams.csv` for logos.

- Usage
  - Minimal (defaults paths and output):
    - `python3 scripts/generate_draft_class_analytics.py --year 2026`
  - Explicit paths and output file:
    - `python3 scripts/generate_draft_class_analytics.py --year 2026 --players MEGA_players.csv --teams MEGA_teams.csv --out docs/draft_class_2026.html`

- Arguments
  - `--year <int>`: Required draft class year (e.g., 2026)
  - `--players <path>`: Players CSV path; default `MEGA_players.csv`
  - `--teams <path>`: Teams CSV path; default `MEGA_teams.csv` (optional, only used for logos)
  - `--out <path>`: Output HTML path; default `docs/draft_class_<YEAR>.html` (parent dir is created)
  - `--league-prefix <str>`: Optional suffix added to `<title>` (default: `MEGA League`)
  - `--title <str>`: Optional full page `<title>` override

- Output
  - Generates `docs/draft_class_<YEAR>.html` (e.g., `docs/draft_class_2026.html`) with:
    - KPIs: Total rookies, Avg OVR, XF%, SS%, Star%, Normal%; plus an “Elites share” bar where Elites = XF + SS
    - Grading badges for XF% (target ≥ 10%) and SS% (target ≥ 15%): labels “On-target”, “Near-target”, or “Below-target” with classes `grade-on`, `grade-near`, `grade-below`
    - Elites Spotlight (title exactly: “Elites Spotlight”) featuring only X‑Factor and Superstar players; Stars are excluded. Player cards include visible dev badges and show draft round and pick appended to OVR (e.g., `OVR 85 round 1 pick 8`)
    - Team draft quality table (Avg OVR, Best OVR, and dev distribution columns XF/SS/Star/Normal)
    - Position strength table with dev distribution columns XF/SS/Star/Normal
    - Dual rounds view:
      - “Hit = XF/SS/Star” (non‑Normal) by round and team
      - “Hit = Elites (XF/SS)” by round and team
      - Notes/footers clarify definitions and that displays may be limited to first 10 rounds
    - Most elites leaderboard (title: “Most elites (XF+SS) — by team”) where elites = XF + SS
  - Team logos appear when `MEGA_teams.csv` provides a resolvable `logoId`; renders fine without it.
  - Dev trait handling: raw data uses `3 = X‑Factor (XF)`, `2 = Superstar (SS)`, `1 = Star`, `0 = Normal`; UI renders explicit dev badges (no masking).

- Visual badges and classes
  - Rendering helper: badges appear as `<span class="dev-badge dev-<tier>">Label</span>`
  - CSS classes used: `.dev-xf`, `.dev-ss`, `.dev-star`, `.dev-norm`
  - Grading badges: `.grade`, `.grade-on`, `.grade-near`, `.grade-below`

- Tables and Interactivity
  - All analytics tables have centered headers and cells
  - Click any column header to sort ascending/descending (client-side, no dependencies)
  - Updated headers include the four dev columns: `XF`, `SS`, `Star`, `Normal`

- Verification
  - Generate for 2026:
    - `python3 scripts/generate_draft_class_analytics.py --year 2026 --players MEGA_players.csv --teams MEGA_teams.csv --out docs/draft_class_2026.html`
  - Quick checks:
    - `test -s docs/draft_class_2026.html`
    - `rg -n "Draft Class 2026 — Analytics Report" docs/draft_class_2026.html`
    - `rg -n "Elites Spotlight" docs/draft_class_2026.html`
    - `rg -n "class=\"dev-(xf|ss|star|norm)\"" docs/draft_class_2026.html`
    - `rg -n "class=\"grade-(on|near|below)\"" docs/draft_class_2026.html`
    - `rg -n "Most elites \(XF\+SS\) — by team" docs/draft_class_2026.html`
    - `rg -n "Team.*\|.*XF.*\|.*SS.*\|.*Star.*\|.*Normal" docs/draft_class_2026.html`
    - `rg -n "Position.*\|.*XF.*\|.*SS.*\|.*Star.*\|.*Normal" docs/draft_class_2026.html`
    - `rg -n "Hit = XF/SS/Star" docs/draft_class_2026.html`
    - `rg -n "Hit = Elites \(XF/SS\)" docs/draft_class_2026.html`
    - `! rg -n "__[A-Z_]+__" docs/draft_class_2026.html`
  - Sanity compare rookies count vs CSV:
    - `python3 - << 'PY'\nimport csv;rows=[r for r in csv.DictReader(open('MEGA_players.csv',newline='',encoding='utf-8')) if str(r.get('rookieYear'))=='2026'];print(len(rows))\nPY`
    - `rg -o "<b>Total rookies</b><span>(\\d+)" -r "$1" -N docs/draft_class_2026.html`
  - Verifier script (recommended):
    - `python3 scripts/verify_draft_class_analytics.py 2026 --players MEGA_players.csv --teams MEGA_teams.csv --html docs/draft_class_2026.html`
  - Smoke test (end-to-end):
    - `bash scripts/smoke/smoke_generate_draft_2026.sh`

Additional checks (optional):
- Ensure dual rounds sections exist:
  - `rg -n "Hit = XF/SS/Star" docs/draft_class_2026.html`
  - `rg -n "Hit = Elites \(XF/SS\)" docs/draft_class_2026.html`
- Ensure sortable headers are present:
  - `rg -n "data-sort" docs/draft_class_2026.html`

Notes:
- If `MEGA_teams.csv` is missing, the page still renders without logos.

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

# 2. Run one of the canonical pipelines
#    - Full pipeline (SoS S2 + playoff/draft + stats + index)
python3 scripts/run_all.py
#    - Playoff + draft race only
# python3 scripts/run_all_playoff_analysis.py
#    - Stats only (team & player usage)
# python3 scripts/run_all_stats.py
#    - Season 2 SoS only (ELO-based)
# python3 scripts/calc_sos_season2_elo.py --season2-start-row 287

# 3. View results (see docs/README.md for more dashboards)
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

## 💸 Roster Cap Management Tool (Spotrac‑style)

Interactive, Spotrac‑inspired salary cap manager for Madden that lets you manage rosters and see real‑time cap impact for releases, trades (quick), extensions, conversions, and free‑agent signings.

Quick start (local):

```bash
# 1) Ensure fresh CSVs exist at repo root
ls MEGA_players.csv MEGA_teams.csv

# 2) Sync CSVs into GitHub Pages data folder
bash scripts/tools/sync_data_to_docs.sh

# 3) Serve locally and open the tool
python3 -m http.server 8000
open http://localhost:8000/docs/roster_cap_tool/

# Optional: browser smoke tests
open http://localhost:8000/docs/roster_cap_tool/test.html
```

GitHub Pages:
1. Commit/push `docs/roster_cap_tool/` (including `data/MEGA_players.csv` and `data/MEGA_teams.csv`)
2. In Settings → Pages, set Source to `/docs`
3. Visit `https://<username>.github.io/<repo>/docs/roster_cap_tool/`

Docs and references:
- Usage guide: `docs/roster_cap_tool/USAGE.md`
- Madden cap rules reference: `spec/Salary Cap Works in Madden.md`
- Data sync script: `scripts/tools/sync_data_to_docs.sh`
- Smoke page: `docs/roster_cap_tool/test.html`
- Cap math verification: `scripts/verify_cap_math.py` (writes `output/cap_tool_verification.json`)

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

## 🧑‍💻 Developer Guide

This section is for league commissioners and contributors who want to extend the project safely or run automated tests.

### Environment Setup

- **Python:** 3.7+ (3.10+ recommended). Core scripts use only the standard library.
- **Node.js (optional):** 18+ recommended, required only for the roster cap tool Playwright E2E tests.
- **Playwright (optional):** Installed via npm (see below) for browser automation.

### Running Python Unit Tests

- Run the full test suite:

  ```bash
  python3 -m unittest
  ```

- Run just the roster power rankings tests (fast smoke test for `scripts/power_rankings_roster.py`):

  ```bash
  python3 -m unittest tests/test_power_rankings_roster.py
  ```

  These tests validate:
  - Normalization helpers (`normalize_unit_scores`)
  - Overall score weighting (`compute_overall_score`)
  - Team metrics and ranking logic (`build_team_metrics`)
  - HTML report generation (`render_html_report`) including the sortable table helper

### Roster Cap Tool – Playwright E2E Tests

End-to-end tests for the Spotrac-style cap tool live under `tests/e2e/` and exercise real browser flows (release, trade, signing, extensions, conversions, year context, etc.).

From the repo root:

```bash
# 1) Install Node dev dependencies
npm install

# 2) Install Playwright browsers & system deps
npm run pw:install

# 3) Run the full E2E suite (headless)
npm run test:e2e

# 4) Run a focused subset (recommended for day-to-day work)
npm run test:e2e -- --grep cap
```

What happens:
- Playwright starts `python3 -m http.server 8000` from the repo root.
- Tests hit `http://127.0.0.1:8000/docs/roster_cap_tool/`.
- CSVs are read from `docs/roster_cap_tool/data/` (sync with `bash scripts/tools/sync_data_to_docs.sh`).

For more details, see `tests/e2e/README.md`. Some tests may fail if the local data or HTML diverges from the expectations baked into the fixtures.

### Where to Add New Scripts

Use these conventions when extending analysis:

- **Orchestrators / pipelines:**  
  - Add new end-to-end runners under `scripts/` (e.g., `run_all_<something>.py`).  
  - Reuse existing ones where possible: `scripts/run_all.py`, `scripts/run_all_playoff_analysis.py`, `scripts/run_all_stats.py`.
- **Analysis scripts:**  
  - Put single-purpose analysis that reads `MEGA_*.csv` under `scripts/`.  
  - Put stats-focused aggregations that feed stats dashboards under `stats_scripts/` (see `stats_scripts/README.md`).
- **Verifiers & smoke tests:**  
  - Add `verify_*.py` validators at the top level of `scripts/`.  
  - Add shell-based smoke tests under `scripts/smoke/`.  
  - Add dev/test helpers (Node/Playwright, small JS utilities) under `scripts/tests/`.  
  - Small maintenance utilities belong in `scripts/tools/`.

Whenever you add a new script that generates CSV/JSON or HTML:
- Update the **“Architecture at a Glance”** table near the top of this README (which domain it belongs to, what inputs/outputs it uses).
- Update `scripts/README.md` with a short description and category.
- If it powers a dashboard, also update `docs/README.md` under the relevant domain table.

### Adding New Dashboards / Visualizations

- Place new HTML pages under `docs/` (or a subfolder).  
- Source data should live under `output/` (for CSV/JSON) or `docs/roster_cap_tool/data/` for cap tool–style apps.
- Link new dashboards from:
  - `index.html` (landing page for GitHub Pages),
  - `docs/README.md` (so it shows up in the domain tables),
  - Optionally `docs/tools_guide.html` if it’s a user-facing tool.

When wiring a new visualization:
- Decide which orchestrator regenerates its backing data (`run_all.py`, `run_all_stats.py`, `run_all_playoff_analysis.py`, or a new `run_all_*`).
- Document that command in this README under the relevant domain and in `docs/README.md`.

---

## 🎓 New to Python or GitHub?

**👉 See [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) for step-by-step instructions!**

The beginner guide includes:
- How to install Python
- How to download and run this project
- How to publish to GitHub Pages
- How to embed in Neon Sports news articles
- Common questions and troubleshooting
