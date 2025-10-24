# Playoff Race Report (HTML + Markdown)

Script
- `scripts/playoff_race_html.py`

Purpose
- Produce a comprehensive HTML report embedding the interactive table and a Markdown summary of standings and key races.

Inputs
- `output/playoff_probabilities.json`
- `output/ranked_sos_by_conference.csv`
- `MEGA_teams.csv`, `MEGA_games.csv` (for remaining opponents/ranks)

Outputs
- `docs/playoff_race.html`
- `docs/playoff_race_report.md`

Behavior
- Builds per-conference playoff picture (leaders + WC + bubble) with SoS tags and remaining games.
- Embeds `playoff_race_table.html` via iframe; includes legend and analysis sections.
- Generates Markdown summary mirroring key highlights.

Run
- `python3 scripts/playoff_race_html.py`

Acceptance Criteria
- HTML and MD present in `docs/` and consistent with probability JSON.
- Division leaders match sort by win% and tiebreak-ready ordering.
- Sections render on mobile (table iframe height adjusts via postMessage).

