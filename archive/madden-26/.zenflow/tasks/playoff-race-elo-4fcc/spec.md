# Technical Specification: Integrate ELO into Playoff Probability Simulations

## Difficulty Assessment
**Medium** — Moderate complexity with a clear scope, but requires careful calibration of weight factors and integration with existing formulas.

---

## Technical Context

- **Language**: Python 3
- **Key File**: `scripts/calc_playoff_probabilities.py`
- **Data Source**: `mega_elo.csv` (team ELO ratings, range ~1060–1310)
- **Related Code**: `scripts/calc_sos_season2_elo.py` has `normalize_team_name()` and `read_elo_map()` utilities

---

## Problem Statement

Current game simulation in `simulate_remaining_games()` uses:
- 70% win percentage (from W-L record)
- 20% past SoS
- 10% SoV (Strength of Victory)

**Issue**: Win percentage is based on record only, not accounting for true team strength. A team at 2-0 who beat weak opponents appears stronger than a 1-1 team who beat a powerhouse. ELO ratings provide a better measure of "true skill."

---

## Implementation Approach

### 1. Load ELO Data

Add a function to load ELO ratings from `mega_elo.csv`:

```python
def load_elo_data():
    """Load team ELO ratings from mega_elo.csv."""
    elo_map = {}
    with open('mega_elo.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = row.get('Team', '').strip()
            elo_str = row.get('Week 14+', '')
            if team and elo_str:
                try:
                    elo_map[team] = float(elo_str)
                except ValueError:
                    continue
    return elo_map
```

### 2. Integrate ELO into Win Probability Calculation

Modify `simulate_remaining_games()` to use ELO-based expected win probability:

**ELO Formula** (standard chess/sports ELO):
```
expected_score = 1 / (1 + 10^((opponent_elo - team_elo) / 400))
```

### 3. Updated Rating Formula

Replace the current formula:
```python
# Current (lines 319-328)
home_rating = (
    home_win_pct * 0.70 +
    home_past_sos * 0.20 +
    home_sov * SOV_WEIGHT
)
```

With a blended approach incorporating ELO:
```python
# Proposed weights
ELO_WEIGHT = 0.50      # ELO is primary skill indicator
WIN_PCT_WEIGHT = 0.25  # Record still matters
SOS_WEIGHT = 0.15      # Past schedule difficulty
SOV_WEIGHT = 0.10      # Quality of victories
```

The ELO component is converted to a 0-1 scale for blending:
```python
elo_normalized = (elo - 1000) / 400  # Maps 1000=0.0, 1200=0.5, 1400=1.0
elo_normalized = max(0, min(1, elo_normalized))  # Clamp to [0,1]
```

### 4. Constants

Add new constants at top of file:
```python
ELO_WEIGHT = 0.50
WIN_PCT_WEIGHT = 0.25
SOS_WEIGHT = 0.15
# SOV_WEIGHT already exists at 0.10
```

---

## Source Code Changes

### Files Modified
- `scripts/calc_playoff_probabilities.py`

### Key Changes

| Location | Change |
|----------|--------|
| Lines 1-20 | Add `ELO_WEIGHT`, `WIN_PCT_WEIGHT`, `SOS_WEIGHT` constants |
| New function | Add `load_elo_data()` function |
| `load_data()` | Call `load_elo_data()` and store in `teams_info` |
| `simulate_remaining_games()` | Update rating calculation to include ELO |
| `main()` | Update print statements to reflect new formula |

---

## Data Model Changes

### `teams_info` dictionary
Add `elo` key per team:
```python
teams_info[team] = {
    ...
    'elo': 1200.0  # From mega_elo.csv
}
```

### Output JSON
Add `elo` field to `output/playoff_probabilities.json`:
```json
{
  "Broncos": {
    "elo": 1310.08,
    ...
  }
}
```

---

## Verification Approach

1. **Unit Test**: Check ELO loading returns 32 teams with values in expected range
2. **Smoke Test**: Run simulation and verify:
   - High ELO teams (Broncos ~1310) have higher playoff probabilities
   - Low ELO teams (Cardinals ~1064) have lower probabilities
3. **Existing Tests**: Run `python3 scripts/calc_playoff_probabilities.py` and verify JSON output
4. **Lint**: Run any existing lint commands

---

## Edge Cases

- **Missing ELO**: Default to 1200 (league average) if team not in `mega_elo.csv`
- **ELO Extremes**: Cap normalized ELO to [0, 1] range
- **Team Name Matching**: Use exact match first; strip whitespace for robustness
