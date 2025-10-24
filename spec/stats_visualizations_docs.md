# Stats Visualizations (Docs)

Pages
- `docs/team_stats_explorer.html` — Interactive Win% vs metric explorer
- `docs/team_stats_correlations.html` — Preselected cross-metric correlations
- `docs/team_player_usage.html` — Player usage distributions and related outcomes
- `docs/rankings_explorer.html` — Rankings-focused visualizations
- `docs/stats_dashboard.html` — Hub linking to key dashboards
- `docs/sos_graphs.html` — SoS visuals

Purpose
- Provide interactive, D3.js-based (via CDN) exploration of team metrics and relationships.

Data
- Backed by CSVs in `output/` (e.g., `team_aggregated_stats.csv`, `team_player_usage.csv`, `team_rankings_stats.csv`).

Acceptance Criteria
- Pages render in modern browsers without local build steps.
- Team logos appear where implemented; trendlines/R² render for correlation charts.
- Filters (conference/metric selectors) update charts correctly.

