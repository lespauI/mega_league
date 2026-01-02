# Implementation Report: Enhanced Playoff Probability Calculation

## What Was Implemented

Enhanced the Monte Carlo simulation in `scripts/calc_playoff_probabilities.py` with four new factors:

### 1. Home Field Advantage (+2%)
- Slight boost for home team reflecting Madden crowd noise effects
- Applied via `HOME_FIELD_ADVANTAGE = 0.02`

### 2. Win Streak Bonus/Penalty (+/-3%)
- Teams with 3+ consecutive wins get +3% probability boost
- Teams with 3+ consecutive losses get -3% penalty
- Uses `winLossStreak` column from `MEGA_teams.csv`
- Handles unsigned byte encoding (values >127 converted to negative)

### 3. Divisional Game Regression (15%)
- Divisional matchups regress 15% toward 50-50
- Reflects that division rivals know each other well, creating more unpredictable outcomes

### 4. Strength of Victories Rating (10% of rating)
- Uses `MEGA_rankings.csv` power rankings to evaluate quality of defeated opponents
- Teams that beat higher-ranked opponents get higher SOV rating
- Formula: `1.0 - (avg_defeated_rank - 1) / 31`

### Rating Formula
```
Base rating: 70% win_pct + 20% past_sos + 10% sov_rating
Then apply: +2% home field, +/-3% streak bonus, 15% divisional regression
```

## Bug Fixes (Post-Review)

### 1. Unsigned Byte Conversion for Win/Loss Streak
The `winLossStreak` column uses unsigned byte encoding (0-255). Values >127 represent negative streaks:
- 255 = -1 (one game loss streak)
- 254 = -2 (two game loss streak)

**Fix**: Added conversion `if streak > 127: streak = streak - 256`

### 2. Win Streak Bonus Scaling
Originally the streak bonus was diluted to 0.3% instead of 3% due to incorrect scaling through the rating system.

**Fix**: Applied streak modifier directly to probability after base calculation:
```python
home_prob += get_streak_modifier(home_streak)
home_prob -= get_streak_modifier(away_streak)
```

## Files Modified

| File | Changes |
|------|---------|
| `scripts/calc_playoff_probabilities.py` | Added 5 constants, 4 helper functions, modified `load_data()`, `simulate_remaining_games()`, `calculate_playoff_probability_simulation()`, `main()` |

## How It Was Tested

1. Ran full simulation with 1000 iterations: `python3 scripts/calc_playoff_probabilities.py -n 1000`
2. Verified all 32 teams processed successfully
3. Output saved to `output/playoff_probabilities.json`
4. Probabilities within expected [0-100] range

## Test Results

Script completed in ~16 seconds for 1000 simulations. Sample output:

**AFC Top 5**: Bengals (100%), Broncos (100%), Jaguars (100%), Browns (99.8%), Bills (90.2%)

**NFC Top 5**: Giants (99.9%), Seahawks (99.2%), Cowboys (95.6%), Saints (77.8%), Rams (74.5%)

## Configuration Constants

All adjustments are tunable at the top of the file:
```python
HOME_FIELD_ADVANTAGE = 0.02      # 2%
WIN_STREAK_THRESHOLD = 3
WIN_STREAK_BONUS = 0.03          # 3%
DIVISIONAL_REGRESSION = 0.15     # 15%
SOV_WEIGHT = 0.10                # 10%
```
