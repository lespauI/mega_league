# Strength of Schedule — Remaining (Win% Based)

Script
- `scripts/calc_remaining_sos.py`

Purpose
- Compute remaining vs past SoS using opponent win percentages.

Inputs
- `MEGA_teams.csv` — computes win_pct per team from W/L/T (or uses `winPct`)
- `MEGA_games.csv` — remaining vs past games (`status` 1 vs 2/3)

Outputs
- `output/remaining_sos_by_conference.csv` with columns:
  - team, conference, W, L, remaining_games
  - sos_avg, sos_sum, past_sos_avg, total_sos

Behavior
- Aggregates opponent `win_pct` for remaining and past games.
- Sorts by conference and desc remaining `sos_avg`.

Run
- `python3 scripts/calc_remaining_sos.py`

Acceptance Criteria
- Output exists at `output/remaining_sos_by_conference.csv`.
- `win_pct` computed when not provided (from W/L/T).
- Numeric columns present and valid.

