# Technical Specification: Playoff Probability Capping

## Task Difficulty: **Easy**

A straightforward fix to cap Monte Carlo simulation results to avoid showing 100% or 0% when not mathematically certain.

## Technical Context

- **Language**: Python 3
- **File**: `scripts/calc_playoff_probabilities.py`
- **Dependencies**: csv, json, random (stdlib only)

## Problem Analysis

The current Monte Carlo simulation (`calculate_playoff_probability_simulation`) runs 1000 simulations and calculates:
```python
playoff_probability = (playoff_count / num_simulations) * 100
```

This can result in 100% or 0% probabilities when:
- All 1000 simulations result in the same outcome
- The true probability is very high/low but not mathematically certain

**Current behavior**: Teams like Broncos show 99.8%, Browns show 99.9%, but could show 100.0% if lucky in all simulations.

## Implementation Approach

### Option Selected: Probability Capping

Add a cap to simulation-based probabilities:
- **Maximum**: 99.9% (unless mathematically clinched)
- **Minimum**: 0.1% (unless mathematically eliminated)

This is simpler than full mathematical elimination/clinching detection and addresses the user's core concern.

### Mathematical Certainty Detection (Simplified)

For a team to be mathematically clinched:
- They need to make playoffs in ALL possible remaining game outcomes
- This requires exhaustive analysis which is expensive

For simplicity, we'll use a heuristic:
- **Clinched if remaining_games == 0** and currently in playoff position
- **Eliminated if remaining_games == 0** and currently out of playoff position
- Otherwise, cap at 99.9%/0.1%

## Source Code Changes

### File: `scripts/calc_playoff_probabilities.py`

**Change 1**: Add probability capping function (lines ~440-445)

```python
def cap_probability(raw_probability, is_mathematically_certain=False):
    """Cap simulation probabilities to avoid false 100%/0%."""
    if is_mathematically_certain:
        return raw_probability
    if raw_probability >= 100:
        return 99.9
    if raw_probability <= 0:
        return 0.1
    return raw_probability
```

**Change 2**: Update `calculate_playoff_probability_simulation` return (lines ~437-445)

Apply capping to the returned probabilities, checking if there are remaining games.

**Change 3**: Update `main()` to pass remaining_games info for capping decision.

## Data Model / API Changes

None. Output JSON format remains the same.

## Verification Approach

1. Run the script: `python3 scripts/calc_playoff_probabilities.py`
2. Check `output/playoff_probabilities.json`:
   - No team should have exactly 100.0% unless season is complete
   - No team should have exactly 0.0% unless season is complete
   - Values like 99.8%, 99.9% are expected for top teams
   - Values like 0.1%, 0.2% are expected for eliminated-looking teams

## Edge Cases

- **Season complete**: If no remaining games, use raw 100%/0%
- **Very high/low probabilities**: Cap at 99.9%/0.1% respectively
- **Mid-range probabilities**: No change needed
