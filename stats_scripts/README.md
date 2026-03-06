# Team Statistics Visualizations

## Overview
This folder contains scripts and outputs for team-level statistical analysis and visualizations.

## What Was Built

### 1. Data Aggregation & Pipeline
**File**: `aggregate_team_stats.py` (run via `scripts/run_all_stats.py`)

Aggregates player-level statistics from MEGA CSV files into team-level metrics.

**Recommended entry point (from project root):**
```bash
python3 scripts/run_all_stats.py
```

This pipeline builds:
- `output/team_aggregated_stats.csv` – team-level stats and efficiency metrics.
- `output/team_player_usage.csv` – team usage distributions.
- `output/team_rankings_stats.csv` – rankings + stats joins for correlation work.
- `output/player_team_stints.csv` – trade-aware season stints per player/team.

You can still run the team aggregation script directly if needed:
```bash
python3 stats_scripts/aggregate_team_stats.py
```

**Output (team aggregation)**: `output/team_aggregated_stats.csv`
- 32 teams
- 71 metrics including:
  - Offensive stats (passing, rushing, receiving)
  - Defensive stats (sacks, INTs, tackles)
  - Efficiency metrics (YPA, completion%, TD rates)
  - Derived stats (turnover differential, explosive plays)

### 2. Interactive Visualizations

#### 📊 Team Stats Explorer
**File**: `docs/team_stats_explorer.html`
**URL**: Open `index.html` → "Team Stats Explorer"

**Features**:
- X-axis: Always Win%
- Y-axis: Dropdown with 22 metrics
- Interactive exploration of what correlates with winning
- R² correlation strength display
- Conference filter (ALL/AFC/NFC)

**Key Metrics Available**:
- Pass/Rush Yards per Attempt
- QB Rating
- Interception Rate
- Turnover Differential
- TD per Play
- Sacks (offense & defense)
- Explosive Plays
- And 15 more...

#### 🔬 Interesting Correlations
**File**: `docs/team_stats_correlations.html`
**URL**: Open `index.html` → "Interesting Correlations"

**Features**:
- 10 pre-selected non-obvious correlations
- Each graph has an insight/hypothesis
- Shows cross-metric relationships, not just "X vs Win%"

**Example Graphs**:
1. **O-Line Protection vs QB Turnovers** - Do sacks cause INTs?
2. **Turnover Balance** - Defensive INTs vs Offensive INTs
3. **Pass Volume vs Punting** - Are teams passing because they're losing?
4. **Physical Running** - YAC% vs Broken Tackles
5. **Turnover Margin vs Wins** - Most predictive single stat
6. **Passing Philosophy** - Completion% vs Depth of Target
7. **Run Game Impact** - Rush attempts vs Pass efficiency
8. **Pass Rush vs Coverage** - What creates turnovers?
9. **Explosive Plays** - Big plays vs Punting frequency
10. **Game Script** - Pass/Run ratio vs Wins

## File Structure

```
stats_scripts/
├── aggregate_team_stats.py        # Team stats aggregation
├── aggregate_player_usage.py      # Usage distributions
├── aggregate_rankings_stats.py    # Rankings + stats join
├── build_player_team_stints.py    # Trade-aware stints builder
└── README.md                      # This file

spec/
├── STATS_VISUALIZATION_PLAN.md    # Full plan and ideas
├── RANKINGS_VISUALIZATION_PLAN.md # Rankings-focused visualization ideas
└── CORRELATION_IDEAS.md           # Extra correlation concepts

../output/
├── team_aggregated_stats.csv      # Team stats (input to most dashboards)
├── team_player_usage.csv          # Usage metrics (backing team_player_usage.html)
├── team_rankings_stats.csv        # Rankings + stats (backing rankings_explorer.html)
└── player_team_stints.csv         # Trade-aware stints (backing trade_dashboard.html)

../docs/
├── team_stats_explorer.html       # Interactive Win% explorer
├── team_stats_correlations.html   # 10 interesting correlations
└── stats_dashboard.html           # Hub page linking stats tools
```

## How It Works

### Data Flow
```
MEGA_passing.csv  ─┐
MEGA_rushing.csv  ─┤
MEGA_receiving.csv─┤
MEGA_defense.csv  ─┼──> aggregate_team_stats.py ──> team_aggregated_stats.csv
MEGA_punting.csv  ─┤
MEGA_teams.csv    ─┘

output/team_aggregated_stats.csv ──> docs/team_stats_explorer.html, docs/team_stats_correlations.html
```

### Visualization Style
- Same look-and-feel as SoS graphs
- Team logos as data points (30x30px)
- Red squares = above trend
- Blue squares = below trend
- Trend line with R² correlation
- Interactive tooltips
- Conference filtering

## Key Insights

Based on the plan in `../spec/STATS_VISUALIZATION_PLAN.md`:

### Strong Correlations (R² > 0.5)
- Turnover Differential vs Win%
- Pass Efficiency vs Win%

### Interesting Non-Obvious Relationships
- **Sacks Allowed → QB INTs**: Bad O-line forces hurried throws
- **Run Attempts → Pass Efficiency**: Run game unlocks play-action
- **Explosive Plays → Fewer Punts**: Big plays sustain drives

### Strategic Insights
- **Turnover Margin** is the single best predictor of wins
- **Pass-heavy teams** often punt more (game script: trailing)
- **High completion% + low YPC** = dink-and-dunk offense
- **Low completion% + high YPC** = vertical passing attack

## Future Enhancements

See `../spec/STATS_VISUALIZATION_PLAN.md` for:
- Ultimate Graph Builder (both X and Y as dropdowns)
- Player-level drill-downs
- Time-based filtering (last 5 games, trends)
- More derived metrics
- Quadrant analysis overlays

## Usage

1. **Run the full stats pipeline (recommended)**:
   ```bash
   python3 scripts/run_all_stats.py
   ```

2. **(Optional) Run a single aggregation script**:
   ```bash
   python3 stats_scripts/aggregate_team_stats.py
   python3 stats_scripts/aggregate_player_usage.py
   python3 stats_scripts/aggregate_rankings_stats.py
   python3 stats_scripts/build_player_team_stints.py
   ```

3. **View visualizations**:
   - Open `index.html` in browser
   - Click "Team Stats Explorer" or "Interesting Correlations" (or open `docs/stats_dashboard.html`)
   
4. **Serve locally** (optional, if paths don't resolve):
   ```bash
   python3 -m http.server 8000
   # Then open http://localhost:8000
   ```

## Further Reading & Design Docs

For deeper background and future ideas, see:
- `../spec/STATS_VISUALIZATION_PLAN.md` – full plan for team stats visualizations.
- `../spec/RANKINGS_VISUALIZATION_PLAN.md` – concepts for rankings-focused charts and dashboards.
- `../spec/CORRELATION_IDEAS.md` – additional cross-metric correlation ideas.

## Dependencies

- **Python**: Standard library only (csv, pathlib, collections)
- **Browser**: Modern browser with JavaScript enabled
- **D3.js**: Loaded from CDN (https://cdn.jsdelivr.net/npm/d3@7)

No pandas, no npm, no build step required!

---

*Created: 2025-10-23*
