# Draft Pick Race Analysis

Script
- `scripts/top_pick_race_analysis.py`

Purpose
- Rank bottom teams by record and remaining SoS for draft order insights; output a Markdown report.

Inputs
- `output/ranked_sos_by_conference.csv`
- `MEGA_teams.csv`

Outputs
- `output/draft_race/draft_race_report.md`

Behavior
- Collates all teams with win%, remaining games, remaining SoS.
- Sorts by win_pct asc and secondary by remaining SoS desc; provides tiers (Top 3 / Top 10 / 11–16).
- Includes “SOS impact” commentary blocks.

Run
- `python3 scripts/top_pick_race_analysis.py`

Acceptance Criteria
- Markdown file generated with ordered sections and per-team lines.
- Values match inputs; easier remaining schedules flagged appropriately.

