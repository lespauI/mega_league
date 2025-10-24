# Metric Help Injector (Docs helper)

Script
- `scripts/add_metric_helps.py`

Purpose
- Post-process `docs/team_player_usage.html` to insert explanatory `metricHelp` strings for charts.

Inputs
- `docs/team_player_usage.html`

Outputs
- In-place updates to `docs/team_player_usage.html`

Notes
- Script currently references an absolute path. Prefer updating to project-relative paths before use.
- Not required for core analysis pipeline; convenience for enhancing chart tooltips.

Run (after path fix)
- `python3 scripts/add_metric_helps.py`

Acceptance Criteria
- Target charts in `team_player_usage.html` gain `metricHelp:` entries without breaking JSON-in-JS structures.

