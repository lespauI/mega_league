# Technical Specification: Playoff Probability Capping with Mathematical Certainty Detection

## Task Difficulty: **Medium**

Requires proper mathematical certainty detection (clinched/eliminated) plus capping for simulation results.

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

**User's concern**: 100% should only appear when mathematically clinched (e.g., 12-3 team that makes playoffs even if they lose all remaining games).

## Implementation Approach

### Two-Part Solution

1. **Mathematical Certainty Detection**: Determine if a team is truly clinched or eliminated
2. **Probability Capping**: Cap simulation results at 99.9%/0.1% when NOT mathematically certain

### Mathematical Certainty Detection

**Clinched (100%)**: Team makes playoffs even in worst-case scenario
- Simulate: Team loses ALL remaining games, every other team wins ALL their remaining games
- If team still makes playoffs → mathematically clinched

**Eliminated (0%)**: Team can't make playoffs even in best-case scenario
- Simulate: Team wins ALL remaining games, every other team loses ALL their remaining games
- If team still misses playoffs → mathematically eliminated

This reuses the existing `determine_playoff_teams()` function with deterministic game outcomes.

## Source Code Changes

### File: `scripts/calc_playoff_probabilities.py`

**Change 1**: Add function to check mathematical clinching (~line 417)

```python
def check_mathematical_certainty(team_name, teams_info, stats, games):
    """
    Check if team is mathematically clinched or eliminated.
    Returns: 'clinched', 'eliminated', or None
    """
    remaining_games = [g for g in games if not g['completed']]
    if not remaining_games:
        return None  # Season complete, use actual result
    
    conf = teams_info[team_name]['conference']
    
    # Worst case: team loses all, others win all
    worst_case_games = []
    for game in remaining_games:
        home, away = game['home'], game['away']
        if team_name in (home, away):
            winner = away if home == team_name else home
            loser = team_name
        else:
            winner = home  # Arbitrary, just needs consistency
            loser = away
        worst_case_games.append({'home': home, 'away': away, 'winner': winner, 'loser': loser})
    
    playoff_teams, _, _ = determine_playoff_teams(teams_info, stats, worst_case_games)
    if team_name in playoff_teams[conf]:
        return 'clinched'
    
    # Best case: team wins all, others lose all
    best_case_games = []
    for game in remaining_games:
        home, away = game['home'], game['away']
        if team_name in (home, away):
            winner = team_name
            loser = away if home == team_name else home
        else:
            winner = home  # Arbitrary
            loser = away
        best_case_games.append({'home': home, 'away': away, 'winner': winner, 'loser': loser})
    
    playoff_teams, _, _ = determine_playoff_teams(teams_info, stats, best_case_games)
    if team_name not in playoff_teams[conf]:
        return 'eliminated'
    
    return None
```

**Change 2**: Add probability capping function

```python
def cap_probability(raw_probability, certainty_status):
    """Cap simulation probabilities unless mathematically certain."""
    if certainty_status == 'clinched':
        return 100.0
    if certainty_status == 'eliminated':
        return 0.0
    if raw_probability >= 100:
        return 99.9
    if raw_probability <= 0:
        return 0.1
    return raw_probability
```

**Change 3**: Update `main()` to use certainty detection and capping

Apply `check_mathematical_certainty()` for each team, then apply `cap_probability()` to simulation results.

## Data Model / API Changes

None. Output JSON format remains the same.

## Verification Approach

1. Run the script: `python3 scripts/calc_playoff_probabilities.py`
2. Check `output/playoff_probabilities.json`:
   - 100.0% only for mathematically clinched teams
   - 0.0% only for mathematically eliminated teams
   - 99.9% max for very likely but not clinched teams
   - 0.1% min for very unlikely but not eliminated teams

## Edge Cases

- **Season complete**: No remaining games → use raw 100%/0%
- **Clinched team**: Show 100.0% regardless of simulation result
- **Eliminated team**: Show 0.0% regardless of simulation result
- **High probability (99-100%)**: Cap at 99.9% if not clinched
- **Low probability (0-1%)**: Cap at 0.1% if not eliminated
