# Strength of Schedule — Rankings-Based

Script
- `scripts/calc_sos_by_rankings.py`

Purpose
- Compute remaining and past strength of schedule (SoS) using normalized team performance rankings.

Inputs
- `MEGA_rankings.csv` — latest ranking per team used to compute a strength score
- `MEGA_games.csv` — to split remaining vs past opponents (`status` 1 vs 2/3)
- `MEGA_teams.csv` — team metadata (conference, W/L)

Outputs
- `output/ranked_sos_by_conference.csv` with columns:
  - team, conference, W, L, remaining_games
  - ranked_sos_avg, ranked_sos_sum
  - past_ranked_sos_avg, total_ranked_sos

Behavior
- Normalizes ranks to 0..1 where higher is stronger (offense/defense/overall blended).
- Builds opponent lists for remaining and past games; averages opponents’ strength.
- Sorts by conference and desc remaining average in output.

Run
- `python3 scripts/calc_sos_by_rankings.py`

Acceptance Criteria
- Output exists at `output/ranked_sos_by_conference.csv`.
- Each team has `remaining_games` equal to count of `status == 1` matchups.
- Columns present and numeric fields parse as floats/ints.
- Conferences align with `MEGA_teams.csv`.

