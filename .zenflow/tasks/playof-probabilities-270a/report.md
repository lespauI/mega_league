# Implementation Report: Playoff Probability Capping

## What Was Implemented

Added probability capping to the Monte Carlo playoff simulation in `scripts/calc_playoff_probabilities.py`:

1. **New `cap_probability` function** (lines 447-455): Caps simulation probabilities to avoid false certainty:
   - Returns raw probability if `remaining_games == 0` (season complete)
   - Caps 100% to 99.9% when games remain
   - Caps 0% to 0.1% when games remain
   - Passes through mid-range probabilities unchanged

2. **Applied capping in `main()`**: All three probability outputs (`playoff_probability`, `division_win_probability`, `bye_probability`) now use `cap_probability()` before rounding.

## How The Solution Was Tested

1. Ran the full script: `python3 scripts/calc_playoff_probabilities.py`
2. Verified output JSON contains no `100.0%` or `0.0%` values when remaining games > 0
3. Confirmed teams that previously would show 100% now display 99.9% (e.g., Bengals, Broncos)
4. Confirmed teams that previously would show 0% now display 0.1% (e.g., Jets, Ravens, Eagles, Cardinals)

## Results

Before:
- Teams with 1000/1000 simulation wins showed 100.0%
- Teams with 0/1000 simulation wins showed 0.0%

After:
- Top teams show 99.9% (capped)
- Bottom teams show 0.1% (capped)
- Mid-range probabilities unchanged

## Challenges

None significant. The implementation was straightforward as the `remaining_games` data was already available in the SOS data being loaded.
