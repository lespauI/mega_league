# Technical Specification: Season 3 Playoff Chances

## Difficulty Assessment
**Medium** — The core logic is established; this is primarily adapting `seasonIndex` filters and output paths across several interdependent scripts.

---

## Technical Context

- **Language**: Python 3
- **Data source**: `MEGA_games.csv`, `MEGA_rankings.csv`, `MEGA_teams.csv`, `mega_elo.csv`
- **Season index mapping** (Madden MEGA league, 0-based):
  - `seasonIndex=0` → Season 1
  - `seasonIndex=1` → Season 2
  - `seasonIndex=2` → Season 3 *(target)*
- **Season 3 data confirmed**: 288 games (137 completed, 151 remaining as of now)

---

## Problem Statement

The playoff analysis pipeline was last run for Season 2 (`seasonIndex=1`). Three scripts have hardcoded `seasonIndex == 1` filters that must be updated to `seasonIndex == 2`. Additionally, the SoS intermediate CSV path has a mismatch: `calc_sos_by_rankings.py` already defaults to `seasonIndex=2` (outputs `output/ranked_sos_by_conference_season3.csv`), but downstream scripts (`playoff_race_table.py`, `playoff_race_html.py`) read from `output/ranked_sos_by_conference.csv` (no season suffix).

---

## Files to Modify

### 1. `scripts/calc_playoff_probabilities.py`
- **Lines 45, 106**: Change `seasonIndex != 1` → `seasonIndex != 2`
- These filters are in `load_rankings_data()` and `load_data()` respectively

### 2. `scripts/playoff_race_table.py`
- **Line 38**: Change `seasonIndex != 1` → `seasonIndex != 2` in `load_power_rankings()`
- **Line 112**: Change `output/ranked_sos_by_conference.csv` → `output/ranked_sos_by_conference_season3.csv` in `read_standings()` (or use the standard path, see orchestration fix below)

### 3. `scripts/playoff_race_html.py`
- **Line 39**: Change `output/ranked_sos_by_conference.csv` → `output/ranked_sos_by_conference_season3.csv` in `read_standings()` (or use the standard path, see orchestration fix below)

### 4. `scripts/run_all_playoff_analysis.py`
- Update the `calc_sos_by_rankings.py` call to pass `--season-index 2 --out-csv output/ranked_sos_by_conference.csv` as extra args. This:
  - Ensures `calc_sos_by_rankings.py` filters for Season 3
  - Outputs to the standard `output/ranked_sos_by_conference.csv` path that downstream scripts expect (no change needed to those scripts' read paths)

> **Design decision**: Rather than updating `ranked_sos_by_conference.csv` read paths in both `playoff_race_table.py` and `playoff_race_html.py`, we keep downstream scripts reading from `output/ranked_sos_by_conference.csv` and control the output path from the orchestrator. This is cleaner and consistent with the original season 2 pattern.

---

## Implementation Approach

With the design decision above, only 3 files need modification:

1. **`scripts/calc_playoff_probabilities.py`** — 2 filter changes (`!= 1` → `!= 2`)
2. **`scripts/playoff_race_table.py`** — 1 filter change (`!= 1` → `!= 2`)
3. **`scripts/run_all_playoff_analysis.py`** — Add `--season-index 2 --out-csv output/ranked_sos_by_conference.csv` args to `calc_sos_by_rankings.py` call

No new files need to be created. No new HTML pages need to be created — the existing `docs/playoff_race.html` and `docs/playoff_race_table.html` are regenerated in-place.

---

## Data Model / API / Interface Changes

- No schema changes
- `output/ranked_sos_by_conference.csv` will now contain Season 3 SoS data (previously Season 2)
- `output/playoff_probabilities.json` will now contain Season 3 probabilities
- `docs/playoff_race.html` and `docs/playoff_race_table.html` will now show Season 3 analysis
- `docs/team_scenarios/*.md` and `docs/team_scenarios.html` will now reflect Season 3

---

## Verification Steps

```bash
# 1. Run the full pipeline
cd /Users/lespaul/.zenflow/worktrees/season-3-playoff-chances-be7f
python3 scripts/run_all_playoff_analysis.py

# 2. Verify output contains Season 3 teams/standings
python3 -c "
import csv
with open('output/ranked_sos_by_conference.csv') as f:
    rows = list(csv.DictReader(f))
    print(f'SoS rows: {len(rows)}')
    print(rows[:2])
"

# 3. Spot-check playoff_probabilities.json
python3 -c "
import json
with open('output/playoff_probabilities.json') as f:
    data = json.load(f)
    print(list(data.items())[:3])
"

# 4. Confirm HTML outputs exist and are non-empty
ls -lh docs/playoff_race.html docs/playoff_race_table.html
```

No automated tests exist for these scripts; manual verification of outputs is the standard approach for this project.
