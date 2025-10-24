# Playoff Probabilities (Monte Carlo)

Script
- `scripts/calc_playoff_probabilities.py`

Purpose
- Estimate playoff, division win, and first-round bye probabilities per team via Monte Carlo simulation of remaining games.

Inputs
- `MEGA_teams.csv` — division, conference
- `MEGA_games.csv` — schedule/results with `status`
- `output/ranked_sos_by_conference.csv` — for past/remaining SoS context

Outputs
- `output/playoff_probabilities.json` keyed by team with fields:
  - conference, division, W, L, win_pct, conference_pct, division_pct
  - strength_of_victory, strength_of_schedule
  - playoff_probability, division_win_probability, bye_probability
  - remaining_sos, remaining_games, past_sos

Behavior
- Builds team stats from completed games (W/L/T, H2H, conference/division splits, SoV/SOS).
- Simulates remaining games with win prob from 70% team win% + 30% past SoS (capped 25–75%).
- Applies NFL-like tiebreakers: H2H → Division% (if applicable) → Conference% → SoV → SoS.
- Determines 7 playoff teams per conference (4 division winners + 3 WCs) and bye team (#1 seed).
- Repeats for 1000 simulations per team; converts counts to probabilities.

Run
- `python3 scripts/calc_playoff_probabilities.py`

Acceptance Criteria
- `output/playoff_probabilities.json` exists and parses as JSON.
- All teams in `MEGA_teams.csv` present and assigned to correct conference/division.
- Probability values within [0,100], one bye team per conference detectable by max `bye_probability`.
- Uses prior SoS CSV; warn/guard if file missing.

