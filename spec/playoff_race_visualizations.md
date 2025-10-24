# Playoff Race Visualizations (Optional)

Script
- `scripts/playoff_race_analysis.py` (requires `matplotlib`)

Purpose
- Generate PNG charts for playoff standings and bubble analysis, plus Markdown summary.

Inputs
- `output/ranked_sos_by_conference.csv`
- `MEGA_teams.csv`

Outputs
- `output/playoff_race/afc_playoff_race.png`
- `output/playoff_race/nfc_playoff_race.png`
- `output/playoff_race/afc_bubble.png`
- `output/playoff_race/nfc_bubble.png`
- `output/playoff_race/playoff_race_report.md`

Behavior
- Creates bar and scatter plots indicating seed status (leaders/WC/bubble/out) and remaining SoS.
- Adds visual thresholds and legends; saves to `output/playoff_race/`.

Run
- `python3 scripts/playoff_race_analysis.py`

Acceptance Criteria
- All PNGs saved without errors when `matplotlib` installed.
- Teams/labels correspond to `ranked_sos_by_conference.csv` ordering.

