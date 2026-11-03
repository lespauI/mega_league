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
- Runs 10,000 shared regular-season and postseason simulations; ordered seeds 1–7, one bye per conference, Wild Card 2/7, 3/6, 4/5, then reseeding through the conference finals; the Super Bowl game itself is not simulated.
- Uses the shared 70% performance Win% / 30% past SoS match model with a postseason home odds multiplier `10**(75/400)` (equivalent to +75 ELO), retaining the 25–75% bounds. Super Bowl appearance probability is the share of simulated conference titles (100% per conference, 200% league-wide), without floors/caps or a second playoff multiplier.
- Shows tooltips explaining probability calculations (RU localization present).
- Lists remaining opponents with week and current rank, color-coded by strength.

Run
- `python3 scripts/playoff_race_table.py`

Acceptance Criteria
- HTML written to `docs/playoff_race_table.html`.
- Each team row shows record, remaining SoS, 3 probability fields, simulated probability of reaching the Super Bowl.
- Opponent tooltip present when remaining games > 0.
- Logo URLs present when `logoId` available.

