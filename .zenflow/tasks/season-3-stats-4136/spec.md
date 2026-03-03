# Technical Specification: Season 3 Stats Update

## Difficulty: Medium

The MEGA CSVs have already been updated with Season 3 data (`MEGA_teams.csv` shows `seasonIndex: 2`). The core stats scripts are season-agnostic (they derive the season from MEGA_teams.csv). However, two playoff/game-analysis scripts have hardcoded `seasonIndex == 1` filters that must be updated to `== 2` before re-running the full pipeline.

---

## Technical Context

- **Language**: Python 3
- **No external dependencies** beyond stdlib (csv, json, pathlib, etc.)
- **Data flow**:
  1. MEGA CSVs (root-level) → input
  2. `stats_scripts/build_player_team_stints.py` → `output/player_team_stints.csv` (trade-aware per-player/team stints)
  3. `stats_scripts/aggregate_team_stats.py` → `output/team_aggregated_stats.csv`
  4. `stats_scripts/aggregate_player_usage.py` → `output/team_player_usage.csv`
  5. `stats_scripts/aggregate_rankings_stats.py` → `output/team_rankings_stats.csv`
  6. `scripts/calc_playoff_probabilities.py` → `output/playoff_probabilities.json`
  7. `scripts/playoff_race_table.py` → `docs/playoff_race_table.html`
  8. Other playoff/SoS/scenario scripts → various HTML and CSV outputs
  9. `scripts/generate_index.py` → `docs/index.html`

- **Season indexing**: Madden uses 0-based `seasonIndex` in game/ranking CSVs:
  - Season 1 = `seasonIndex: 0`
  - Season 2 = `seasonIndex: 1`
  - **Season 3 = `seasonIndex: 2`** ← current

---

## Root Cause

`MEGA_teams.csv` now reflects Season 3 (`seasonIndex: 2`). The stats scripts in `stats_scripts/` derive `seasonIndex` dynamically from `MEGA_teams.csv`, so they are self-updating. However, two scripts hardcode `seasonIndex != 1` to filter game/ranking data:

| File | Lines | Current value | Required value |
|------|-------|---------------|----------------|
| `scripts/calc_playoff_probabilities.py` | 45, 106 | `!= 1` | `!= 2` |
| `scripts/playoff_race_table.py` | 38, 106 | `!= 1` | `!= 2` |

---

## Source Code Changes

### Files to Modify

1. **`scripts/calc_playoff_probabilities.py`**
   - Line 45: `if int(row.get('seasonIndex', 0)) != 1:` → `!= 2`
   - Line 106: `if int(row.get('seasonIndex', 0)) != 1:` → `!= 2`

2. **`scripts/playoff_race_table.py`**
   - Line 38: `if int(row.get('seasonIndex', 0)) != 1:` → `!= 2`
   - Line 106: `if int(row.get('seasonIndex', 0)) != 1:` → `!= 2`

### Files with No Changes Required (Season-Agnostic)

- `stats_scripts/build_player_team_stints.py` — derives season from `MEGA_teams.csv`
- `stats_scripts/aggregate_team_stats.py` — uses stint layer, no season filter
- `stats_scripts/aggregate_player_usage.py` — uses stint layer, no season filter
- `stats_scripts/aggregate_rankings_stats.py` — uses `MEGA_rankings.csv` latest week per team
- `scripts/calc_sos_by_rankings.py` — `DEFAULT_SEASON_INDEX = 2` already set
- `scripts/calc_sos_season3_elo.py` — season-3-specific script, no change
- `scripts/calc_sos_season2_elo.py` — season-2 historical script, no change
- `scripts/generate_all_team_scenarios.py` — reads from MEGA_teams directly
- `scripts/playoff_race_html.py` — reads from playoff_race_table output
- `scripts/generate_index.py` — no season filtering

---

## Data Model / Interface Changes

None. All input/output CSV column schemas remain identical. The only change is which rows are selected from `MEGA_games.csv` and `MEGA_rankings.csv` (now `seasonIndex == 2` instead of `== 1`).

---

## Implementation Approach

1. Update the two hardcoded `seasonIndex` filters from `1` → `2`
2. Run the full pipeline: `python3 scripts/run_all.py` from the project root

The pipeline order in `run_all.py` is:
1. `stats_scripts/aggregate_team_stats.py`
2. `stats_scripts/aggregate_player_usage.py`
3. `stats_scripts/aggregate_rankings_stats.py`
4. `stats_scripts/build_player_team_stints.py`
5. `scripts/calc_sos_season2_elo.py`
6. `scripts/calc_sos_season3_elo.py`
7. `scripts/calc_sos_by_rankings.py`
8. `scripts/generate_all_team_scenarios.py` (includes playoff probabilities)
9. `scripts/playoff_race_table.py`
10. `scripts/playoff_race_html.py`
11. `scripts/generate_team_scenario_html.py`
12. `scripts/top_pick_race_analysis.py` (optional)
13. `scripts/generate_index.py`
14. `scripts/verify_trade_stats.py`

---

## Verification Approach

After the changes, run:
```bash
python3 scripts/run_all.py
```

**Expected outcomes:**
- `output/player_team_stints.csv` — stints with `seasonIndex: 2`
- `output/team_aggregated_stats.csv` — 32 teams, Season 3 totals
- `output/team_player_usage.csv` — 32 teams, Season 3 usage
- `output/team_rankings_stats.csv` — 32 teams with Season 3 rankings
- `output/playoff_probabilities.json` — Season 3 game data
- `docs/playoff_race_table.html` — Season 3 standings
- All other HTML outputs updated

**Spot-check verification:**
- Stints `seasonIndex` should be `2`, not `1`
- Rankings in `playoff_race_table.html` should reflect Season 3 data (18 weeks of season 3 games in MEGA_games.csv with `seasonIndex: 2`)
- `scripts/verify_trade_stats.py` should pass without errors
