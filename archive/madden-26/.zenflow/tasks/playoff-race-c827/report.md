# Implementation Report: ELO-Based Super Bowl Probability Calculation

## Overview

Updated the Super Bowl probability calculation to use a pure ELO-based tournament simulation approach, replacing the previous multi-factor formula that weighted win percentage, power rank, past strength of schedule, and quality of wins.

## What Was Implemented

### 1. ELO Data Integration
- Added `load_elo_ratings()` function in `playoff_race_table.py`
- Loads ELO ratings from `mega_elo.csv`
- Returns dictionary mapping team names to ELO ratings
- Handles missing teams with default ELO of 1200

### 2. New Calculation Function
- Implemented `calculate_superbowl_prob_elo()` function
- Uses standard ELO win probability formula: `1 / (1 + 10^((opp_elo - team_elo) / 400))`
- Calculates playoff field average ELO for each conference
- Applies home field advantage as +25 ELO boost
- Simulates tournament (3-4 games based on seeding)
- Multiplies by playoff probability
- Caps maximum at 45% (SB_PROB_MAX constant)

### 3. Updated Table Generation
- Modified `read_standings()` to load and pass ELO data
- Updated `create_html_table()` to use new ELO-based function
- Builds list of playoff contenders' ELOs per conference
- Replaced old multi-factor calculation with ELO-only approach

### 4. Tooltip Updates
- Rewrote `get_superbowl_tooltip()` function
- Displays team's ELO rating
- Explains ELO-based tournament simulation methodology
- Shows relative strength vs playoff field
- Removed references to old weighting factors

## How the Solution Was Tested

### Automated Testing
- Verified ELO win probability formula with known values (1300 vs 1200 = ~64% win probability)
- Confirmed script runs without errors
- Validated data loading and parsing

### Manual Verification
- Generated `docs/playoff_race_table.html`
- Inspected all team probabilities
- Verified tooltips display correctly
- Compared manual calculations with output
- Checked differentiation between teams with similar records but different ELOs

## Results

### Top Teams by Super Bowl Probability

| Team | Record | ELO | SB Probability | Notes |
|------|--------|-----|----------------|-------|
| Broncos | 11-2 | 1310 | 20.2% | Highest in league |
| Giants | 11-1-1 | 1269 | 17.0% | Second highest |
| Browns | 11-3 | 1247 | 5.3% | Lower despite similar record to Broncos |
| Patriots | 9-4 | 1255 | 3.3% | Mid-tier playoff team |
| Bills | 9-5 | 1205 | 2.6% | Lower than Patriots due to lower ELO |

### Key Findings

**ELO-Based Differentiation Works as Expected:**
- Broncos (ELO 1310) have 20.2% SB probability
- Browns (ELO 1247) have only 5.3% despite similar 11-3 record vs Broncos' 11-2
- This demonstrates the formula correctly prioritizes team strength (ELO) over record alone

**Formula Validation:**
- Win probability calculations match expected ELO formula output
- Home field advantage (+25 ELO) appropriately boosts probabilities
- Playoff probability multiplier correctly scales down teams with low playoff chances
- 45% cap prevents unrealistic probabilities

## Challenges Encountered

### 1. Data Consistency
- Ensured team name matching between standings and ELO data
- Default ELO of 1200 handles any missing teams

### 2. Home Field Advantage Modeling
- Applied consistent +25 ELO boost for home games
- Accounts for higher seeds getting home field advantage in playoffs

### 3. Conference-Specific Calculations
- Calculated separate playoff field averages for AFC and NFC
- Ensures teams are compared against their actual competition

## Technical Details

### ELO Win Probability Formula
```
P(win) = 1 / (1 + 10^((opponent_elo - team_elo) / 400))
```

### Tournament Simulation
- **Wildcard teams**: 3 wins needed (WC → Div → Conf → SB)
- **Bye teams**: 2 wins needed (Div → Conf → SB)
- Each game probability calculated against playoff field average ELO
- Home field advantage applied based on seeding

### Final Calculation
```
sb_prob = tournament_prob × playoff_prob
sb_prob = min(sb_prob, SB_PROB_MAX)  # Cap at 45%
```

## Conclusion

The ELO-based approach successfully replaced the multi-factor formula, providing a cleaner and more defensible methodology. The new calculation:
- ✅ Properly differentiates teams based on strength (ELO)
- ✅ Accounts for playoff probability
- ✅ Handles seeding advantages (byes, home field)
- ✅ Produces logical, verifiable results
- ✅ Provides clear explanations in tooltips

The implementation is complete, tested, and deployed.
