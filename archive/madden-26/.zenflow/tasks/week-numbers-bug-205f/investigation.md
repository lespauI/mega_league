# Week Numbers Bug – Investigation

## Bug summary
- Playoff-related reports and tools (team scenario viewer, playoff race table/HTML, and derived markdown reports) display NFL week numbers off by one.
- Source CSV `MEGA_games.csv` uses `weekIndex` as zero-based (0–17), but UI surfaces treat it as if it were one-based, so upcoming games like `weekIndex = 14` appear as “Week 14” instead of “Week 15” (e.g. Cowboys vs Eagles case).

## Root cause analysis
- Data input:
  - `MEGA_games.csv` header includes `weekIndex`, and sample rows confirm values start at 0 for the first regular-season week and continue upward (e.g. Cowboys–Eagles scheduled game has `weekIndex = 14`).
  - `README.md` documents `weekIndex` as a required column but does not clarify that it is zero-based; in practice the CSV uses 0-based indexing.
- Processing:
  - `scripts/calc_playoff_probabilities.py::load_data` reads games and stores `week` directly from `weekIndex`:
    - `week: int(row['weekIndex']) if row['weekIndex'] else 0`
  - `scripts/team_scenario_report.py::calculate_game_probabilities` copies this `game['week']` straight into output:
    - `game_probs.append({'week': game['week'], ...})`
  - `scripts/generate_all_team_scenarios.py::build_team_scenarios_json` uses `calculate_game_probabilities` and then writes `week` as-is into `output/team_scenarios.json`.
  - `scripts/generate_team_scenario_html.py` embeds that JSON and renders the remaining schedule table with:
    - `Week ${g.week}` in the HTML template.
  - `scripts/playoff_race_table.py` and `scripts/playoff_race_html.py` read `MEGA_games.csv` and build `remaining_opponents` with:
    - `week = int(row.get('weekIndex', 0))`
    - Later, tooltips render remaining schedules with `Week {opp["week"]}: {opp["name"]}`.
- Output / UI:
  - `docs/team_scenarios.html` contains embedded `TEAM_DATA` with `remaining_games` entries like `"week": 13, 14, 15, 16, 17` for late-season games, matching raw `weekIndex` rather than human week numbers 14–18.
  - `docs/playoff_race_table.html` and `docs/playoff_race.html` show “Remaining Schedule” tooltips with “Week 13–17” labels that correspond directly to zero-based indices from `MEGA_games.csv`.
- Impact:
  - Any user-facing place that shows remaining games or schedules based on `weekIndex` is off by one week for all regular-season games.
  - Core simulation logic (Monte Carlo playoff simulations, tiebreakers, etc.) does not materially depend on the absolute values of `week`, so the bug is presentation-layer only.

## Affected components
- Data & simulation:
  - `scripts/calc_playoff_probabilities.py` (defines `games[i]['week']` from `weekIndex`).
  - `scripts/team_scenario_report.py` (`calculate_game_probabilities` produces `week` values passed through to reports/JSON).
- Scenario JSON and viewer:
  - `scripts/generate_all_team_scenarios.py` (`build_team_scenarios_json` includes `remaining_games[].week` taken from `game_probs`).
  - `output/team_scenarios.json` (generated artifact consumed by the viewer).
  - `scripts/generate_team_scenario_html.py` (renders `Week ${g.week}` from embedded JSON).
  - `docs/team_scenarios.html` (generated viewer page currently showing off-by-one weeks).
- Playoff race reports:
  - `scripts/playoff_race_table.py` (builds `remaining_opponents` with raw `weekIndex` and renders `Week {opp["week"]}` tooltips).
  - `scripts/playoff_race_html.py` (similarly builds and displays remaining schedule weeks).
  - `docs/playoff_race_table.html` and `docs/playoff_race.html` (generated artifacts with off-by-one “Week N” labels in Remaining Schedule tooltips).
- Likely unaffected / should remain as-is:
  - `scripts/week18_simulator.py`:
    - Reads `week = int(row['weekIndex'])` and explicitly selects `week18_games = [g for g in games if g['week'] == 17]`.
    - The UI is hardcoded as “Week 18 Playoff Simulator”, so it intentionally treats `weekIndex == 17` as Week 18; changing its internal week representation would risk breaking that selection logic.
  - Other analytics or validation code that uses `weekIndex` only for ordering or latest-week selection (e.g. `calc_sos_by_rankings.py`, `aggregate_rankings_stats.py`) and does not display the raw week number.

## Proposed solution
- General approach:
  - Treat `weekIndex` from CSV as a zero-based technical field and introduce a clear one-based “display week” wherever weeks are shown to users.
  - Apply the `+1` transformation at the presentation/data-output boundary, not inside core simulation logic that only needs a consistent ordering.
- Concrete changes (to be implemented in the next step):
  1. Team scenarios (JSON + HTML + markdown):
     - Update `scripts/team_scenario_report.py::calculate_game_probabilities` so that it emits a one-based week number, e.g. `display_week = game['week'] + 1`, and store `display_week` in the `week` field of each `game_probs` entry.
     - Because `build_team_scenarios_json` already consumes `game_probs`, this single change will:
       - Fix `output/team_scenarios.json` (`remaining_games[].week`).
       - Fix `docs/team_scenarios.html` once regenerated via `generate_all_team_scenarios.py` and `generate_team_scenario_html.py`.
       - Fix markdown reports produced by `team_scenario_report.py` that render `| {gp['week']} |` in their tables.
  2. Playoff race table and HTML:
     - In both `scripts/playoff_race_table.py` and `scripts/playoff_race_html.py`, adjust the construction of `remaining_opponents` so that stored week values are `week_index + 1`:
       - When reading `MEGA_games.csv`, compute `display_week = int(row.get('weekIndex', 0)) + 1` and store that in the `week` field of each opponent dict.
       - This preserves ordering (sorting by week still works) and corrects the human-readable labels used in tooltips (e.g. “Week 15: Cowboys vs Eagles”).
  3. Verification and regression checks:
     - Regenerate playoff outputs via `python3 scripts/run_all_playoff_analysis.py` after updating `.gitignore` (if needed) to ignore generated artifacts like `output/` and relevant `docs/` files.
     - Manually verify:
       - For a known example such as Cowboys vs Eagles, the team scenarios page now shows “Week 15 vs Eagles” instead of “Week 14 vs Eagles”.
       - Playoff race tooltips list remaining games with weeks 1–18 (no zero week; final week shown as 18 for `weekIndex == 17`).
     - Run existing Playwright E2E tests (`npm install` if necessary, then `npx playwright test`) to ensure that UI and probability formats remain valid.



## Implementation notes
- Updated `calculate_game_probabilities` in `scripts/team_scenario_report.py` to emit `weekIndex + 1` as the `week` field so team scenario markdown, JSON, and HTML now show human weeks 1–18.
- Updated `read_standings` in `scripts/playoff_race_table.py` and `scripts/playoff_race_html.py` to store remaining opponent weeks as `weekIndex + 1`, fixing Remaining Schedule tooltips in both playoff race views.
- Added regression test `scripts/tests/test_week_numbers.py` verifying that a remaining game with internal `week = 14` is surfaced as display week 15 for the team scenario reports.
- Ran `python3 scripts/tests/test_week_numbers.py` (passes) and `python3 scripts/run_all_playoff_analysis.py` (completes successfully, regenerating `output/team_scenarios.json`, `docs/playoff_race_table.html`, `docs/playoff_race.html`, and `docs/team_scenarios.html`).
- Attempted to run Playwright E2E test `npx playwright test tests/e2e/team_scenarios.spec.ts`, but it failed to install Playwright due to lack of network access to npm registry in this environment.
