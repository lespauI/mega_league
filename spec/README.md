# MEGA League Project Specs

This folder contains concise specifications for each feature in the MEGA League NFL Stats Analysis project. Each spec outlines purpose, inputs, outputs, behavior, run commands, and acceptance criteria.

Scope covers scripts in `scripts/` and `stats_scripts/`, generated HTML/MD assets in `docs/`, and orchestration entries.

Index:
- spec/data_inputs.md — CSV inputs and required columns
- spec/sos_by_rankings.md — Strength of Schedule (rankings-based)
- spec/sos_remaining_winpct.md — Remaining SoS (win% based)
- spec/playoff_probabilities.md — Monte Carlo playoff probabilities
- spec/playoff_race_table.md — NYT-style playoff race table
- spec/playoff_race_report.md — Playoff race HTML + MD report
- spec/playoff_race_visualizations.md — Playoff PNG visuals (optional)
- spec/draft_pick_race.md — Draft pick race analysis
- spec/generate_index.md — Root index generator
- spec/stats_team_aggregation.md — Team stats aggregation
- spec/stats_player_usage.md — Player usage aggregation
- spec/stats_rankings_aggregation.md — Rankings + team stats aggregation
- spec/orchestration.md — End-to-end runners
 - spec/stats_visualizations_docs.md — Stats dashboards in docs/
 - spec/add_metric_helps.md — Docs helper script

Conventions:
- Run scripts from repo root (`os.getcwd()` expectations)
- Inputs live in repo root as `MEGA_*.csv`
- Primary outputs: `output/` (data) and `docs/` (HTML/visuals)
