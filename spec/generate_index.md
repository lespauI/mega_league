# Root Index Generator

Script
- `scripts/generate_index.py`

Purpose
- Build the root `index.html` with categorized links to `docs/` artifacts and optionally run aggregation scripts.

Inputs
- Files present in `docs/` (HTML/PNGs/MD/TXT)
- Optional: `stats_scripts/aggregate_team_stats.py`, `stats_scripts/aggregate_player_usage.py`

Outputs
- `index.html` (root)

Behavior
- Optionally runs aggregation scripts (if present) to refresh CSVs.
- Scans `docs/` and groups into sections: Reports & Visualizations, Playoff Race Images, Strength of Schedule Images, Documentation, Other Files.
- Renders a styled landing page linking to each file under `docs/`.

Run
- `python3 scripts/generate_index.py`

Acceptance Criteria
- `index.html` created/updated; console lists categories with counts.
- All `docs/` files (except `.DS_Store`, `index.html`, `CNAME`) appear in some category.

