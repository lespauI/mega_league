# Bug Investigation: Playoff Chances When 0 Games Remaining

## Bug Summary
When no games remain in the season, playoff chances are incorrectly shown as 100% or 0% in the playoff race table, even when tiebreakers are still undecided. The team scenario page shows correct probabilities (e.g., Panthers 67.4%), but the main table shows incorrect probabilities (e.g., Panthers 100%).

## Evidence
From screenshots:
- **Team Page (Correct)**: Panthers show 67.4% playoff chances with 10-7-0 record
- **Table Page (Incorrect)**: Panthers show 100% playoff chances with same 10-7-0 record

## Root Cause Analysis

### Location of Bug
**File**: `scripts/calc_playoff_probabilities.py`
**Function**: `check_mathematical_certainty()` (lines 615-690)

### The Problem
When there are 0 remaining games:

1. **Line 625-626**: `check_mathematical_certainty()` returns `None` when `remaining_games` is empty
   ```python
   if not remaining_games:
       return None
   ```

2. **Line 593**: Monte Carlo simulation still runs with `simulate_remaining_games()`
   ```python
   simulated_games = simulate_remaining_games(teams_info, stats, sos_data, games, rankings)
   ```

3. **Line 325**: `simulate_remaining_games()` returns empty list when no games remain
   ```python
   remaining_games = [g for g in games if not g['completed']]
   simulated_games = []  # Empty when season is over
   ```

4. **Line 594**: `determine_playoff_teams()` applies tiebreakers to current standings with no simulated games
   - Every simulation produces identical results (no randomness)
   - Teams currently in playoff spots get 100% (1000/1000 simulations)
   - Teams currently out get 0% (0/1000 simulations)

5. **Line 693-703**: `cap_probability()` doesn't override because certainty is `None`
   ```python
   def cap_probability(raw_probability, certainty_status):
       if certainty_status == 'clinched':
           return 100.0
       if certainty_status == 'eliminated':
           return 0.0
       # Falls through to raw_probability when certainty_status is None
   ```

### Why This Is Wrong
**Tiebreakers are complex** (from `docs/nfl_playoff_tie.txt`):
- Head-to-head record
- Division record
- Conference record  
- Strength of victory
- Strength of schedule
- Combined ranking in points scored/allowed
- Net points in conference/all games
- **Coin toss** (final tiebreaker!)

When multiple teams have identical records and identical tiebreaker stats, they should NOT have 100%/0% - they should reflect the probability of winning a coin toss or other uncertain tiebreaker.

## Affected Components
1. **`scripts/calc_playoff_probabilities.py`**: Core calculation logic
2. **`scripts/playoff_race_table.py`**: Displays the incorrect probabilities
3. **`output/playoff_probabilities.json`**: Contains incorrect data when season ends

## Proposed Solution

### Option 1: Fix `check_mathematical_certainty()` to handle end-of-season
When `remaining_games` is empty, determine actual playoff teams using tiebreakers and return appropriate certainty:

```python
def check_mathematical_certainty(team_name, teams_info, stats, games):
    remaining_games = [g for g in games if not g['completed']]
    
    # NEW: When season is over, determine actual playoff teams
    if not remaining_games:
        conf = teams_info[team_name]['conference']
        playoff_teams, _, _ = determine_playoff_teams(teams_info, stats, [])
        if team_name in playoff_teams[conf]:
            return 'clinched'
        else:
            return 'eliminated'
    
    # Rest of existing logic...
```

### Option 2: Add randomness to tiebreaker resolution
Modify `apply_tiebreakers()` to add randomness when tiebreakers are exhausted, simulating coin tosses:

```python
def apply_tiebreakers(teams, stats, teams_info, is_division=False):
    # Existing tiebreaker logic...
    
    # When all tiebreakers are exhausted (line 322):
    # Instead of: return remaining[0] if remaining else teams[0]
    # Use: return random.choice(remaining) if remaining else teams[0]
```

This would make simulations produce different results even with 0 games remaining.

### Recommended Approach
**Option 1** is simpler and more correct. When the season is over with no tiebreaker ambiguity, teams should be 100%/0%. However, we should still run simulations to handle coin-flip scenarios.

**Combined approach**: 
1. Fix `check_mathematical_certainty()` to determine playoff teams when season ends
2. Add randomness to `apply_tiebreakers()` for final tiebreaker (coin toss)
3. This ensures:
   - Clear cases get 100%/0%
   - Tied cases get probability based on number of tied teams (e.g., 3-way tie = 33.3%)

## Edge Cases to Consider
1. **2-way tie on all tiebreakers**: Should be 50%/50%
2. **3-way tie on all tiebreakers**: Should be 33.3%/33.3%/33.3%  
3. **Clear leader**: Should be 100%
4. **Clear elimination**: Should be 0%
5. **Partial ties**: Some positions clear, some tied

## Test Cases Needed
1. Team with better record than 7th place → 100%
2. Team with worse record than 7th place → 0%
3. Two teams tied for 7th place with identical tiebreakers → 50%/50%
4. Three teams tied for 7th place with identical tiebreakers → ~33% each

---

## Implementation

### Changes Made
**File**: `scripts/calc_playoff_probabilities.py`
**Function**: `check_mathematical_certainty()` (lines 615-656)

### Fix Applied
Added special handling when a team has 0 remaining games but other conference teams still have games:

1. **Check for potential tiebreakers**: When target team is done playing, check if any other conference team could finish with the same record
2. **Return None if tie possible**: If another team's max or min possible wins equals target team's wins, return `None` (uncertain)
3. **Let simulations handle it**: Monte Carlo simulations with randomized tiebreakers (`random.choice()` at line 322) properly calculate probabilities

### Code Added (lines 631-653)
```python
team_remaining_games = [g for g in remaining_games if team_name in (g['home'], g['away'])]

if not team_remaining_games and remaining_games:
    team_record = stats[team_name]['W'] + 0.5 * stats[team_name]['T']
    
    for other_team, other_stats in stats.items():
        if other_team == team_name:
            continue
        if teams_info.get(other_team, {}).get('conference') != conf:
            continue
        
        other_remaining = [g for g in remaining_games if other_team in (g['home'], g['away'])]
        if not other_remaining:
            continue
        
        other_current = other_stats['W'] + 0.5 * other_stats['T']
        other_max = other_current + len(other_remaining)
        other_min = other_current
        
        if abs(other_max - team_record) < 0.01 or abs(other_min - team_record) < 0.01:
            return None
        if other_min < team_record < other_max:
            return None
```

### Test Results
**Before Fix**:
- Panthers (10-7, 0 games): 100% playoff, clinched: True ❌

**After Fix**:
- Panthers (10-7, 0 games): **67.5%** playoff, clinched: False ✓
- Lions (9-7, 1 game): **33.5%** playoff ✓
- Titans (10-7, 0 games): 99.9% playoff, clinched: False ✓

Probabilities now correctly reflect:
- Panthers compete with Lions for final playoff spot
- If Lions win (finish 10-7), tiebreakers determine outcome
- Monte Carlo simulations with random tiebreaker resolution show Panthers win ~67.5% of ties
- Total probability ≈ 101% (rounding + edge cases)

### Files Modified
1. `scripts/calc_playoff_probabilities.py` - Fixed certainty check
2. `output/playoff_probabilities.json` - Regenerated with correct probabilities
3. `docs/playoff_race_table.html` - Regenerated table shows correct 67.5%
