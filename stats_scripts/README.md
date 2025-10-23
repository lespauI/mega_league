# Team Statistics Visualizations

## Overview
This folder contains scripts and outputs for team-level statistical analysis and visualizations.

## What Was Built

### 1. Data Aggregation Script
**File**: `aggregate_team_stats.py`

Aggregates player-level statistics from MEGA CSV files into team-level metrics.

**Run it:**
```bash
cd /Users/lespaul/Downloads/MEGA_neonsportz_stats
python3 stats_scripts/aggregate_team_stats.py
```

**Output**: `stats_scripts/output/team_aggregated_stats.csv`
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
├── aggregate_team_stats.py      # Aggregation script
├── output/
│   └── team_aggregated_stats.csv # Generated team data
├── STATS_VISUALIZATION_PLAN.md  # Full plan and ideas
└── README.md                     # This file

../docs/
├── team_stats_explorer.html      # Interactive Win% explorer
└── team_stats_correlations.html  # 10 interesting correlations
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

team_aggregated_stats.csv ──> D3.js HTML Visualizations
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

Based on the plan in `STATS_VISUALIZATION_PLAN.md`:

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

See `STATS_VISUALIZATION_PLAN.md` for:
- Ultimate Graph Builder (both X and Y as dropdowns)
- Player-level drill-downs
- Time-based filtering (last 5 games, trends)
- More derived metrics
- Quadrant analysis overlays

## Usage

1. **Run aggregation** (if data changed):
   ```bash
   python3 stats_scripts/aggregate_team_stats.py
   ```

2. **View visualizations**:
   - Open `index.html` in browser
   - Click "Team Stats Explorer" or "Interesting Correlations"
   
3. **Serve locally** (optional, if paths don't resolve):
   ```bash
   python3 -m http.server 8000
   # Then open http://localhost:8000
   ```

## Dependencies

- **Python**: Standard library only (csv, pathlib, collections)
- **Browser**: Modern browser with JavaScript enabled
- **D3.js**: Loaded from CDN (https://cdn.jsdelivr.net/npm/d3@7)

No pandas, no npm, no build step required!

---

*Created: 2025-10-23*
