## Task: Running scripts – avoid duplicate playoff simulations

- Updated `scripts/generate_all_team_scenarios.py` so the consolidated Monte Carlo run now also produces `output/playoff_probabilities.json`, using the same tiebreaker and probability‑capping logic as `calc_playoff_probabilities.py`.
- Adjusted orchestrators `scripts/run_all_playoff_analysis.py` and `scripts/run_all.py` to call `generate_all_team_scenarios.py` (once) instead of `calc_playoff_probabilities.py`, and to run it before `playoff_race_table.py` / `playoff_race_html.py`.
- Updated `spec/orchestration.md` and `scripts/README.md` to reflect the new pipeline order and to document `generate_all_team_scenarios.py` as part of the playoff toolchain.
- Ran `python3 scripts/generate_all_team_scenarios.py -n 1000` to verify that it now generates both `output/team_scenarios.json` and `output/playoff_probabilities.json` successfully.

