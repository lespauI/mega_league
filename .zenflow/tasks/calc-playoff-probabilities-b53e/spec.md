# Technical Specification: Enhanced Playoff Probability Calculation

## Task Difficulty: **Medium**

The task involves enhancing an existing Monte Carlo simulation with additional factors. The codebase is well-structured with clear patterns, making the implementation straightforward but requiring careful tuning of probability adjustments.

---

## Technical Context

- **Language**: Python 3
- **Dependencies**: Standard library only (csv, json, random, argparse, collections)
- **Key Files**:
  - `scripts/calc_playoff_probabilities.py` - Main simulation script (692 lines)
  - `MEGA_rankings.csv` - Team power rankings by week (1314 rows)
  - `MEGA_games.csv` - Game schedule and results
  - `MEGA_teams.csv` - Team metadata (division, conference)

---

## Current Implementation Analysis

### How It Works Now

The `simulate_remaining_games()` function (lines 241-307) calculates win probability using:

```python
home_rating = (home_win_pct * 0.7) + (home_past_sos * 0.3)
away_rating = (away_win_pct * 0.7) + (away_past_sos * 0.3)
home_prob = home_rating / (home_rating + away_rating)
home_prob = max(0.25, min(0.75, home_prob))  # Capped at 25-75%
```

### Current Limitations

1. **No home field advantage** - Both teams are treated equally regardless of venue
2. **No momentum/form consideration** - Recent win streak has no impact
3. **No divisional rivalry factor** - Divisional games treated same as any other game
4. **Limited opponent quality tracking** - Only uses overall past SoS, not quality of specific wins

---

## Proposed Improvements

### 1. Home Field Advantage (Slight)

**Rationale**: In Madden, home team has slight advantages (crowd noise affects snap counts, play calling). Should be small (~2-3%) compared to real NFL (~3-5%).

**Implementation**:
```python
HOME_FIELD_ADVANTAGE = 0.02  # 2% boost for home team
home_prob = home_prob + HOME_FIELD_ADVANTAGE
```

### 2. Win Streak Bonus

**Rationale**: Teams on hot streaks (3+ consecutive wins) often have momentum and confidence.

**Implementation**:
- Track `winLossStreak` from `MEGA_teams.csv` column (positive = wins, negative = losses)
- Apply bonus for streaks ≥3 wins: `+0.03` (3%)
- Apply penalty for streaks ≤-3 losses: `-0.03` (3%)

```python
WIN_STREAK_THRESHOLD = 3
WIN_STREAK_BONUS = 0.03

def get_streak_modifier(team_streak):
    if team_streak >= WIN_STREAK_THRESHOLD:
        return WIN_STREAK_BONUS
    elif team_streak <= -WIN_STREAK_THRESHOLD:
        return -WIN_STREAK_BONUS
    return 0.0
```

### 3. Divisional Game Adjustment

**Rationale**: Division games are always tough battles - underdogs perform better, favorites can slip. This creates more variance.

**Implementation**:
- Detect divisional matchups by comparing `divisionName`
- Apply regression toward 50%: reduce gap between favorite and underdog

```python
DIVISIONAL_REGRESSION = 0.15  # Move 15% toward 50-50

if is_divisional_game:
    home_prob = home_prob + (0.5 - home_prob) * DIVISIONAL_REGRESSION
```

### 4. Strength of Victories Factor

**Rationale**: Teams that beat strong opponents should be rewarded more than teams with easy schedules.

**Data Source**: `MEGA_rankings.csv` contains weekly power rankings (`rank` column, 1-32).

**Implementation**:
- Calculate average rank of defeated opponents
- Teams with lower average (beat higher-ranked teams) get a bonus
- Weight: 10% of rating calculation

```python
def calculate_sov_rating(team, stats, rankings_data):
    defeated = stats[team]['defeated_opponents']
    if not defeated:
        return 0.5
    ranks = [get_latest_rank(opp, rankings_data) for opp in defeated]
    avg_rank = sum(ranks) / len(ranks)
    # Normalize: rank 1 = 1.0, rank 32 = 0.0
    return 1.0 - (avg_rank - 1) / 31
```

**New Rating Formula**:
```python
# Base rating: 70% win_pct + 20% past_sos + 10% sov_rating
home_rating = (
    home_win_pct * 0.70 +
    home_past_sos * 0.20 +
    home_sov_rating * 0.10
)
# Then apply adjustments directly to probability:
# +2% home field, +/-3% streak bonus, 15% divisional regression
```

---

## Source Code Changes

### Files to Modify

| File | Changes |
|------|---------|
| `scripts/calc_playoff_probabilities.py` | Add new factors to `simulate_remaining_games()`, load rankings data |

### New Constants (top of file)

```python
HOME_FIELD_ADVANTAGE = 0.02
WIN_STREAK_THRESHOLD = 3
WIN_STREAK_BONUS = 0.03
DIVISIONAL_REGRESSION = 0.15
```

### New Functions to Add

1. `load_rankings_data()` - Parse `MEGA_rankings.csv` and get latest rank per team
2. `get_streak_modifier(streak)` - Calculate win/loss streak bonus/penalty
3. `calculate_sov_rating(team, stats, rankings)` - Quality of victories metric
4. `is_divisional_game(home, away, teams_info)` - Check if teams in same division

### Modified Functions

1. `load_data()` - Also load `winLossStreak` from `MEGA_teams.csv`
2. `simulate_remaining_games()` - Apply all new factors

---

## Data Model Changes

### `teams_info` dictionary - add:
```python
teams_info[team] = {
    ...
    'win_streak': int(row.get('winLossStreak', 0)),  # NEW
    'current_rank': get_latest_rank(team, rankings)   # NEW
}
```

### `stats` dictionary - add:
```python
stats[team] = {
    ...
    'sov_rating': float,  # NEW: 0.0-1.0 based on defeated opponent rankings
}
```

---

## Configuration & Tuning

All adjustment constants will be defined at the top of the file for easy tuning:

```python
# === PROBABILITY ADJUSTMENT CONSTANTS ===
HOME_FIELD_ADVANTAGE = 0.02      # Home team bonus (2%)
WIN_STREAK_THRESHOLD = 3          # Minimum streak for bonus
WIN_STREAK_BONUS = 0.03           # Streak bonus (3%)
DIVISIONAL_REGRESSION = 0.15      # Divisional games regress 15% toward 50-50
SOV_WEIGHT = 0.10                 # Weight for strength of victories in rating
FORM_WEIGHT = 0.10                # Weight for current form in rating
```

---

## Verification Approach

1. **Unit Test**: Verify each modifier returns expected values for edge cases
2. **Run Script**: `python3 scripts/calc_playoff_probabilities.py -n 1000`
3. **Validate Output**: Check `output/playoff_probabilities.json` for:
   - All 32 teams present
   - Probabilities in [0, 100] range
   - Division leaders have higher probabilities
   - Hot streak teams show improved chances vs baseline
4. **Compare**: Run before/after to see impact of changes

---

## Implementation Steps

1. Add constants and helper functions for new factors
2. Extend `load_data()` to include win streak and rankings data
3. Create `calculate_sov_rating()` function using `MEGA_rankings.csv`
4. Modify `simulate_remaining_games()` to apply all adjustments
5. Update print statements to document new features
6. Test with full simulation run

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Over-adjustment causing unrealistic probabilities | Keep all modifiers small (2-3%) and test thoroughly |
| Rankings data format issues | Validate column names, handle missing data gracefully |
| Performance impact from loading rankings | Load once at startup, cache latest ranks per team |
