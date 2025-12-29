# Orchestration & End-to-End Runs

Scripts
- `scripts/run_all.py` — Complete pipeline (team stats, player usage, SoS, playoff, draft, index)
- `scripts/run_all_playoff_analysis.py` — Playoff-focused subset
- `scripts/run_all_stats.py` — Stats-focused subset

Purpose
- Provide one-command entry points that execute scripts in the correct order with basic status logging.

Sequences
- run_all.py
  1) stats_scripts/aggregate_team_stats.py
  2) stats_scripts/aggregate_player_usage.py
  3) stats_scripts/aggregate_rankings_stats.py
  4) stats_scripts/build_player_team_stints.py
  5) scripts/calc_sos_season2_elo.py
  6) scripts/calc_sos_by_rankings.py
  7) scripts/generate_all_team_scenarios.py
  8) scripts/playoff_race_table.py
  9) scripts/playoff_race_html.py
 10) scripts/generate_team_scenario_html.py
 11) scripts/top_pick_race_analysis.py (optional, matplotlib required for visuals)
 12) scripts/generate_index.py
 13) scripts/verify_trade_stats.py

- run_all_playoff_analysis.py
  1) scripts/calc_sos_by_rankings.py
  2) scripts/generate_all_team_scenarios.py
  3) scripts/playoff_race_table.py
  4) scripts/playoff_race_html.py
  5) scripts/generate_team_scenario_html.py
  6) scripts/top_pick_race_analysis.py (optional, matplotlib required for visuals)

- run_all_stats.py
  1) stats_scripts/aggregate_team_stats.py
  2) stats_scripts/aggregate_player_usage.py
  3) stats_scripts/aggregate_rankings_stats.py
  4) stats_scripts/build_player_team_stints.py
  5) scripts/generate_index.py
  6) scripts/verify_trade_stats.py

Run
- `python3 scripts/run_all.py`
- `python3 scripts/run_all_playoff_analysis.py`
- `python3 scripts/run_all_stats.py`

Acceptance Criteria
- Sequence executes in order; failures logged with clear status.
- Expected outputs appear (see individual specs) given valid CSV inputs.
- Optional steps do not fail the run if dependencies are missing.
