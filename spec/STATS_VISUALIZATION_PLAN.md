# Team Statistics Visualization Plan

## Overview
This document outlines suggested statistics visualizations based on available MEGA CSV data files. The visualizations will follow the same scatter plot style as the SoS graphs, using D3.js with team logos, trend lines, and interactive tooltips.

---

## Data Sources
- **MEGA_passing.csv** - Passing statistics by team/player
- **MEGA_rushing.csv** - Rushing statistics by team/player
- **MEGA_receiving.csv** - Receiving statistics by team/player
- **MEGA_defense.csv** - Defensive statistics by team/player
- **MEGA_kicking.csv** - Kicking statistics by team/player
- **MEGA_punting.csv** - Punting statistics by team/player
- **MEGA_teams.csv** - Team metadata (logos, win/loss records, conference)
- **MEGA_rankings.csv** - Team rankings

---

## Suggested Visualizations

### 1. **Universal Win% Correlation Graph** (with Dropdowns)
**One interactive graph that replaces 10+ boring "X vs Win%" charts**

- **X-axis**: Team Win% (always)
- **Y-axis**: Dropdown selector with 20+ metrics:
  - TD Efficiency (TDs / Total Plays)
  - Pass Yards per Attempt
  - Rush Yards per Attempt
  - QB Rating
  - Interception Rate
  - Sack Rate
  - Turnover Differential
  - Defensive INTs
  - Defensive Sacks
  - Broken Tackles per Rush
  - YAC per Reception
  - 20+ Yard Plays per Game
  - Red Zone TD %
  - 3rd Down Conversion %
  - etc.
- **Purpose**: Let users explore what correlates with winning
- **Interactive**: Change Y-axis on the fly, see correlation strength

---

### 2. **Interesting Cross-Metric Correlations** 🔥

#### Graph 2.1: Interception Rate vs Opponent Rush Yards/Attempt
- **X-axis**: Opponent Rush Yards per Attempt (how well defense stops run)
- **Y-axis**: QB Interception Rate (passTotalInts / passTotalAtt)
- **Hypothesis**: Teams that can't stop the run force QBs into desperate passing = more INTs
- **Insight**: Bad run defense → QB pressure → mistakes

#### Graph 2.2: Pass Attempts vs Punts per Game
- **X-axis**: Pass Attempts per Game
- **Y-axis**: Punts per Game
- **Hypothesis**: Pass-heavy teams (losing, playing from behind) punt more
- **Insight**: Shows game script - winning teams run more, punt less

#### Graph 2.3: Sacks Allowed vs QB Interceptions
- **X-axis**: Sacks Taken per Game
- **Y-axis**: Interceptions Thrown per Game
- **Hypothesis**: Bad O-line protection → hurried throws → INTs
- **Insight**: Pass protection quality affects QB decision-making

#### Graph 2.4: Yards After Contact % vs Broken Tackles
- **X-axis**: YAC % (rushTotalYdsAfterContact / rushTotalYds * 100)
- **Y-axis**: Broken Tackles per Rush Attempt
- **Hypothesis**: Strong correlation - elusive RBs generate yards after contact
- **Insight**: Which teams have physical, tackle-breaking runners

#### Graph 2.5: Defensive INTs vs Offensive Interceptions Thrown
- **X-axis**: Defensive INTs (takeaways)
- **Y-axis**: Offensive INTs (giveaways)
- **Purpose**: Turnover balance visualization
- **Insight**: Teams in top-right = high-variance (both create and give up turnovers)

#### Graph 2.6: Completion % vs Average Depth of Target
- **X-axis**: Completion Percentage
- **Y-axis**: Avg Yards per Completion (aDOT proxy)
- **Hypothesis**: Lower completion % teams throw deeper
- **Insight**: Conservative vs aggressive passing philosophies

#### Graph 2.7: Rush Attempts vs Pass Yards per Attempt
- **X-axis**: Rush Attempts per Game
- **Y-axis**: Pass Yards per Attempt
- **Hypothesis**: Run-first teams = better play action = more yards/attempt
- **Insight**: Balanced offense unlocks passing efficiency

#### Graph 2.8: Sacks (Defense) vs Interceptions (Defense)
- **X-axis**: Team Defensive Sacks
- **Y-axis**: Team Defensive Interceptions
- **Purpose**: Pass rush vs coverage effectiveness
- **Insight**: Pressure creates turnovers, or coverage creates pressure?

#### Graph 2.9: 20+ Yard Plays vs Punts per Game
- **X-axis**: Explosive Plays (20+ yard gains) per Game
- **Y-axis**: Punts per Game
- **Hypothesis**: Big plays = fewer punts (sustained drives)
- **Insight**: Explosive offense reduces punting frequency

#### Graph 2.10: Red Zone TD % vs Field Position (Punt Avg)
- **X-axis**: Net Punt Average (field position weapon)
- **Y-axis**: Red Zone TD Percentage
- **Hypothesis**: Better field position → more RZ attempts → better scoring
- **Insight**: Special teams impact on scoring efficiency

---

### 3. **Game Strategy & Philosophy**

#### Graph 3.1: Pass/Run Ratio vs Trailing Time %
- **X-axis**: Pass/Rush Attempt Ratio
- **Y-axis**: Estimated time spent trailing (inverse of win%)
- **Purpose**: Shows if teams pass because they're losing or by design
- **Insight**: Chicken or egg - do you pass because you're behind?

#### Graph 3.2: Average Pass Depth vs Sacks Taken
- **X-axis**: Avg Yards per Completion (depth of passing)
- **Y-axis**: Sacks Taken per Game
- **Hypothesis**: Deep passing = more time in pocket = more sacks
- **Insight**: Risk/reward of downfield passing

#### Graph 3.3: Rush Attempts vs Time of Possession (proxy)
- **X-axis**: Rush Attempts per Game
- **Y-axis**: Total Plays per Game (proxy for TOP)
- **Purpose**: Ball control strategy
- **Insight**: Run-heavy teams control clock and pace

---

### 4. **Physical Play & Contact**

#### Graph 4.1: Broken Tackles vs Yards After Contact per Rush
- **X-axis**: Broken Tackles per Rush Attempt
- **Y-axis**: Average Yards After Contact per Rush
- **Purpose**: RB power vs elusiveness
- **Insight**: Some break tackles for small gains, others for big chunks

#### Graph 4.2: YAC (Receiving) vs Drop Rate
- **X-axis**: Yards After Catch per Reception
- **Y-axis**: Drop Rate (drops / targets)
- **Hypothesis**: Receivers focused on YAC may drop more (looking upfield early)
- **Insight**: Hands vs athleticism trade-off

#### Graph 4.3: Sacks (Defense) vs Tackles for Loss
- **X-axis**: Defensive Sacks
- **Y-axis**: Tackles for Loss (if available, or proxy with negative plays)
- **Purpose**: Overall defensive disruption
- **Insight**: Teams that get behind the line of scrimmage

---

### 5. **Efficiency & Risk**

#### Graph 5.1: Turnover Differential vs Point Differential
- **X-axis**: Turnover Margin (Takeaways - Giveaways)
- **Y-axis**: Points per Game Differential (Off PPG - Def PPG estimate)
- **Purpose**: How much do turnovers drive scoring margin?
- **Strong correlation expected**

#### Graph 5.2: Interception Rate vs Yards per Attempt
- **X-axis**: QB Interception Rate
- **Y-axis**: Yards per Pass Attempt
- **Hypothesis**: Aggressive QBs (high Y/A) throw more INTs
- **Insight**: Risk/reward in passing game

#### Graph 5.3: 3rd Down Attempts vs Punts
- **X-axis**: 3rd Down Attempts per Game (if available)
- **Y-axis**: Punts per Game
- **Purpose**: Conversion efficiency proxy
- **Insight**: More 3rd downs faced = more punts (poor 1st/2nd down efficiency)

---

### 6. **Defensive Pressure & QB Performance**

#### Graph 6.1: Opponent Sacks vs QB Rating Allowed
- **X-axis**: Defensive Sacks per Game
- **Y-axis**: QB Rating Allowed (opponent QB rating)
- **Hypothesis**: More pressure = lower QB rating against
- **Insight**: Pass rush impact on QB effectiveness

#### Graph 6.2: Defensive INTs vs Opponent Completion %
- **X-axis**: Opponent Completion Percentage
- **Y-axis**: Defensive Interceptions
- **Hypothesis**: Lower completion % → more contested throws → INTs
- **Insight**: Coverage forcing difficult throws

---

### 7. **Special Teams Impact**

#### Graph 7.1: Punt Frequency vs Defensive Field Position
- **X-axis**: Punts per Game
- **Y-axis**: Defensive INT Return Yards + Fumble Return Yards
- **Purpose**: Field position battle
- **Insight**: Punting team vs turnover return game

#### Graph 7.2: Net Punt Average vs Defensive Stops %
- **X-axis**: Net Punt Average (punting team)
- **Y-axis**: Defensive 3-and-outs % (proxy if available)
- **Purpose**: Complementary football - punter + defense
- **Insight**: Good punting + good defense = field position wins

---

## Technical Implementation Details

### Chart Structure
Each visualization should follow the `docs/sos_graphs.html` pattern:

1. **Scatter plot with team logos** (30x30px images)
2. **Linear trend line** (least-squares regression)
3. **Mean lines** (dashed horizontal and vertical)
4. **Color-coded backgrounds**:
   - Red square: Above trend line
   - Blue square: Below trend line
5. **Interactive tooltips** showing:
   - Team name
   - X-axis metric value
   - Y-axis metric value
   - Win%
   - Delta from trend line
6. **Conference filter** (ALL / AFC / NFC)
7. **Responsive D3.js implementation**

### Data Aggregation Required
Since CSV files contain player-level data, we need to:
1. **Aggregate by team**: Sum/average metrics per team
2. **Join with MEGA_teams.csv**: Get logos, win%, conference
3. **Calculate derived metrics**:
   - Rates (per attempt, per game)
   - Ratios (TD/INT, YAC%, etc.)
   - Differentials (turnover margin)

### File Structure
```
stats_scripts/
├── aggregate_team_stats.py          # Aggregate player data to team level
├── calculate_derived_metrics.py     # Calculate efficiency metrics
├── generate_offensive_graphs.html   # Graphs 1.x (Offensive)
├── generate_passing_graphs.html     # Graphs 2.x (Passing)
├── generate_rushing_graphs.html     # Graphs 3.x (Rushing)
├── generate_receiving_graphs.html   # Graphs 4.x (Receiving)
├── generate_defensive_graphs.html   # Graphs 5.x (Defensive)
├── generate_combined_graphs.html    # Graph 7.x (Combined)
├── output/
│   ├── team_aggregated_stats.csv
│   ├── team_offensive_metrics.csv
│   ├── team_defensive_metrics.csv
│   └── team_efficiency_metrics.csv
└── STATS_VISUALIZATION_PLAN.md      # This file
```

---

## Priority Visualizations (Start Here)

### Phase 1: Universal Win% Explorer + Top 3 Interesting Graphs
1. **Universal Win% Graph** (1 graph with dropdown for Y-axis - replaces 15+ boring graphs)
   - X-axis: Always Win%
   - Y-axis dropdown: All major metrics
   - Shows correlation strength for each metric
   - Interactive exploration tool

2. **Sacks Allowed vs QB Interceptions** (Graph 2.3)
   - Shows O-line impact on QB decisions
   - Non-obvious relationship

3. **Defensive INTs vs Offensive INTs** (Graph 2.5)
   - Turnover balance visualization
   - High-variance vs safe teams

4. **Pass Attempts vs Punts per Game** (Graph 2.2)
   - Game script indicator
   - Passing desperation vs design

### Phase 2: Cross-Metric Insights (5-7 graphs)
5. **Interception Rate vs Opponent Rush Defense** (Graph 2.1)
6. **Rush Attempts vs Pass Yards/Attempt** (Graph 2.7)
7. **Yards After Contact % vs Broken Tackles** (Graph 2.4)
8. **Turnover Differential vs Point Differential** (Graph 5.1)
9. **20+ Yard Plays vs Punts per Game** (Graph 2.9)

### Phase 3: Strategy & Philosophy (3-4 graphs)
10. **Completion % vs Average Depth of Target** (Graph 2.6)
11. **Average Pass Depth vs Sacks Taken** (Graph 3.2)
12. **Sacks (Defense) vs Interceptions (Defense)** (Graph 2.8)

---

## Example Metrics Formulas

```javascript
// TD Efficiency
td_per_attempt = (passTotalTDs + rushTotalTDs) / (passTotalAtt + rushTotalAtt)

// INT Rate
int_rate = passTotalInts / passTotalAtt * 100

// Sack Rate
sack_rate = passTotalSacks / (passTotalAtt + passTotalSacks) * 100

// Broken Tackle Rate
bt_rate = rushTotalBrokenTackles / rushTotalAtt

// Drop Rate
drop_rate = recTotalDrops / (recTotalCatches + recTotalDrops) * 100

// YAC Percentage
yac_pct = recTotalYdsAfterCatch / recTotalYds * 100

// Explosive Play Rate
explosive_rate = (rushTotal20PlusYds + recTotal20PlusYds) / total_plays * 100
```

---

## Interactive Features to Add

### 🎯 **ULTIMATE GOAL: One Master Graph with Full Control**
Instead of 20+ static graphs, build **1-2 master interactive graphs**:

#### **Graph Builder Mode**
- **X-axis dropdown**: Select any metric (40+ options)
- **Y-axis dropdown**: Select any metric (40+ options)
- **Conference filter**: ALL / AFC / NFC
- **Playoffs filter**: All teams / Playoff contenders only
- **Minimum games filter**: Only teams with 5+ games, 8+ games, etc.
- **Correlation display**: Show R² value for trend line strength
- **Preset buttons**: Quick-load interesting correlations
  - "QB Pressure Impact" → Sacks Allowed vs INTs
  - "Run Game Physics" → YAC% vs Broken Tackles
  - "Turnover Balance" → Def INTs vs Off INTs
  - etc.

This gives users **infinite combinations** to explore, not just our predefined graphs.

---

### Additional Features

1. **Toggle between views**:
   - All teams
   - AFC only
   - NFC only
   - Playoff teams only (5%-99.5%)
   - Division-specific views

2. **Statistical overlays**:
   - Show R² (correlation strength)
   - Show quartile lines (25%, 50%, 75%)
   - Toggle trend line on/off
   - Toggle mean lines on/off

3. **Player-level drill-down**:
   - Click team logo → modal with top contributors
   - Display QB, RB, WR leaders for that team
   - Compare player stats to league average

4. **Time-based filtering** (future):
   - Full season
   - Last 5 games (trends)
   - First half vs second half
   - Before/after bye week

5. **Export functionality**:
   - Download chart as PNG
   - Export filtered data as CSV
   - Share link with current selections

---

## Styling Guidelines

Match the existing SoS graphs styling:
- **Colors**: Red (#ef4444) for above trend, Blue (#0ea5e9) for below
- **Grid**: Light gray (#e8eaed)
- **Axes**: Medium gray (#9aa0a6)
- **Background**: White panels on light gray (#f7f7f7) page
- **Font**: System UI stack
- **Border radius**: 10px for panels, 6px for tooltips
- **Tooltips**: Dark background (rgba(0,0,0,.78)), white text

---

## Success Metrics

Each visualization should help answer:
1. **Is there a correlation?** (trend line slope)
2. **Which teams are outliers?** (far from trend/means)
3. **What's the league average?** (mean lines)
4. **Which conference is stronger?** (filter + compare)
5. **What drives wins?** (X = Win% shows predictive power)

---

## Next Steps

1. ✅ Define visualization plan (this document)
2. ⬜ Create Python aggregation script for team-level stats
3. ⬜ Generate derived metrics CSV files
4. ⬜ Build HTML/D3.js visualization (start with Phase 1)
5. ⬜ Add interactive features
6. ⬜ Deploy to docs/ folder
7. ⬜ Add to main index.html

---

*Document created: 2025-10-23*  
*Last updated: 2025-10-23*
