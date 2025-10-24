# Playoff Race Table (Interactive)

Script
- `scripts/playoff_race_table.py`

Purpose
- Generate an interactive double-column (AFC/NFC) HTML table with playoff/division/bye/SB probability badges, remaining SoS, and opponent ranks.

Inputs
- `output/playoff_probabilities.json`
- `output/ranked_sos_by_conference.csv`
- `MEGA_teams.csv` (division, conference, logoId)
- `MEGA_games.csv` (remaining opponents: `status == 1`)

Outputs
- `docs/playoff_race_table.html`

Behavior
- Groups teams by conference/division, sorts by win%.
- Displays remaining SoS badge (easy/balanced/brutal thresholds).
- Shows tooltips explaining probability calculations (RU localization present).
- Lists remaining opponents with week and current rank, color-coded by strength.

Run
- `python3 scripts/playoff_race_table.py`

Acceptance Criteria
- HTML written to `docs/playoff_race_table.html`.
- Each team row shows record, remaining SoS, 3 probability fields, SB heuristic.
- Opponent tooltip present when remaining games > 0.
- Logo URLs present when `logoId` available.

