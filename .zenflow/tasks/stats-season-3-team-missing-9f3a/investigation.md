# Investigation: Stats Season 3 — Missing Teams

## Bug Summary
Some teams are missing from stats dashboards. Specifically, Seattle Seahawks ("Sea") is not visible in the "Rush Yards per Attempt vs Win%" scatter chart.

## Root Cause Analysis

The filter causing missing teams is in **two HTML dashboard files**:

### 1. `docs/team_stats_explorer.html` — line 125
```javascript
const data = rows.filter(d => 
  Number.isFinite(+d.win_pct) && 
  Number.isFinite(+d[metricKey]) &&
  +d.win_pct >= 0.005 && +d.win_pct <= 0.995   // ← BUG: excludes perfect/winless records
);
```

### 2. `docs/sos_graphs.html` — line 123
```javascript
data = rows.filter(d => Number.isFinite(+d[cfg.key]) && Number.isFinite(+d[xKey]) && +d[xKey] >= 0.005 && +d[xKey] <= 0.995);
```

The filter `win_pct >= 0.005 && win_pct <= 0.995` was likely added to prevent scatter plot distortion when all teams have the same X value (if a season had only 1 game played), but in the current season (Season 3), some teams have perfect or zero records:

## Affected Teams (currently in Season 3 data)

| Team      | Record | win_pct | Status       |
|-----------|--------|---------|--------------|
| Seahawks  | 9-0    | 1.0     | EXCLUDED (>=0.995) |
| Cardinals | 0-9    | 0.0     | EXCLUDED (<=0.005) |
| Jets      | 0-8    | 0.0     | EXCLUDED (<=0.005) |

**3 out of 32 teams** are missing from all scatter plots in `team_stats_explorer.html` and win%-based scatter plots in `sos_graphs.html`.

## Non-Affected Files
- `docs/team_stats_correlations.html` — no extreme win_pct filter ✓
- `docs/team_elo_correlations.html` — no extreme win_pct filter ✓
- `docs/rankings_explorer.html` — no extreme win_pct filter ✓
- `docs/team_player_usage.html` — no extreme win_pct filter ✓
- `docs/matchup_gameplan.html` — no extreme win_pct filter ✓

## Data Verification
All 32 teams are present in `output/team_aggregated_stats.csv` with valid data. The bug is purely in the HTML rendering filters.

Seahawks have valid data: `rush_yds_per_att = 5.43`, `win_pct = 1.0` — both finite, but `win_pct = 1.0` fails the `<= 0.995` check.

## Proposed Solution
Remove the `win_pct >= 0.005 && win_pct <= 0.995` bounds check from both files. Keep only the `Number.isFinite()` guard, which is the correct way to exclude teams with missing/null data.

### Fix 1: `docs/team_stats_explorer.html` (line 122-126)
**Before:**
```javascript
const data = rows.filter(d => 
  Number.isFinite(+d.win_pct) && 
  Number.isFinite(+d[metricKey]) &&
  +d.win_pct >= 0.005 && +d.win_pct <= 0.995
);
```
**After:**
```javascript
const data = rows.filter(d => 
  Number.isFinite(+d.win_pct) && 
  Number.isFinite(+d[metricKey])
);
```

### Fix 2: `docs/sos_graphs.html` (line 123)
**Before:**
```javascript
data = rows.filter(d => Number.isFinite(+d[cfg.key]) && Number.isFinite(+d[xKey]) && +d[xKey] >= 0.005 && +d[xKey] <= 0.995);
```
**After:**
```javascript
data = rows.filter(d => Number.isFinite(+d[cfg.key]) && Number.isFinite(+d[xKey]));
```

## Implementation Notes

Both fixes applied:
1. `docs/team_stats_explorer.html` line 122–125: removed `+d.win_pct >= 0.005 && +d.win_pct <= 0.995` condition
2. `docs/sos_graphs.html` line 123: removed `+d[xKey] >= 0.005 && +d[xKey] <= 0.995` condition

Seahawks (win_pct=1.0), Cardinals (win_pct=0.0), and Jets (win_pct=0.0) will now appear in all scatter plots. No automated tests exist in this project (static HTML/JS dashboards); fix verified by code inspection.

## Edge Cases & Side Effects
- **No regression risk**: Removing the filter only adds back teams. Charts may display points at `x=0` or `x=1.0`, which are valid data points.
- **X-axis scaling**: Charts use `d3.min/d3.max` to compute axis domains with padding, so extreme values will be handled gracefully.
- **Trend line**: Including undefeated/winless teams in regression will slightly affect R² values, but will make analysis more accurate.
- **Season progression**: As the season continues and more teams get mixed records, this filter would auto-resolve itself mid-season — but for teams at extremes it will always be a problem.
