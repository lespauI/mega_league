# Technical Specification: Playoff Race Update for Season 2

## Difficulty: Medium

The task involves modifying existing scripts to filter data by season index. The core Monte Carlo simulation logic remains unchanged, but data loading functions need season filtering.

## Technical Context

- **Language**: Python 3
- **Key Scripts**:
  - `scripts/calc_playoff_probabilities.py` - Monte Carlo simulation for playoff chances
  - `scripts/calc_sos_by_rankings.py` - Strength of Schedule calculation
- **Data Files**:
  - `MEGA_games.csv` - Game results (columns: seasonIndex, stageIndex, weekIndex, status)
  - `MEGA_rankings.csv` - Team rankings by season/week
  - `MEGA_teams.csv` - Team metadata (division, conference)

## Data Structure Analysis

### Season Index Mapping
- `seasonIndex=0` → Season 1 (completed)
- `seasonIndex=1` → Season 2 (current)

### Current State of Season 2
- Week 12 has pending games (status=1)
- We're currently at **Week 12** of Season 2 (not Week 13 as initially stated)
- Weeks 0-11 have completed games for Season 2
- Regular season: `stageIndex=1`, weeks 0-17

### Game Status Values
- `status=1` → Pending (not played)
- `status=2` → Completed (home team won indicator)
- `status=3` → Completed (away team won indicator)

## Current Issues

### 1. `calc_playoff_probabilities.py`
The `load_data()` function at line 8-44 loads ALL games without filtering by season:
```python
def load_data():
    # ... loads all games from MEGA_games.csv
    for row in reader:
        games.append({...})  # No seasonIndex filter
```

### 2. `calc_sos_by_rankings.py`
The `read_games_split()` function at line 94-112 loads ALL games:
```python
def read_games_split(games_csv_path):
    # ... loads all games without seasonIndex filter
```

The `read_latest_rankings()` function gets latest rankings per team but includes all seasons, which may cause incorrect strength scores for season 2.

## Implementation Approach

### Option A: Add Season Parameter (Recommended)
Add a `season_index` parameter to data loading functions, defaulting to season 2 (index=1).

### Files to Modify

1. **`scripts/calc_playoff_probabilities.py`**
   - Modify `load_data()` to filter games by `seasonIndex=1`
   - Filter `stageIndex=1` for regular season only

2. **`scripts/calc_sos_by_rankings.py`**
   - Modify `read_games_split()` to filter by `seasonIndex=1` and `stageIndex=1`
   - Modify `read_latest_rankings()` to filter rankings by `seasonIndex=1`

## Source Code Changes

### calc_playoff_probabilities.py

**`load_data()` function (lines 8-44)**:
- Add `season_index=1` filter when loading games
- Add `stage_index=1` filter for regular season only
- Change from:
  ```python
  for row in reader:
      games.append({...})
  ```
- To:
  ```python
  for row in reader:
      if int(row.get('seasonIndex', 0)) != 1:  # Season 2
          continue
      if int(row.get('stageIndex', 0)) != 1:  # Regular season
          continue
      games.append({...})
  ```

### calc_sos_by_rankings.py

**`read_games_split()` function (lines 94-112)**:
- Add season and stage filtering
- Change to filter `seasonIndex=1` and `stageIndex=1`

**`read_latest_rankings()` function (lines 64-91)**:
- Filter rankings to only include `seasonIndex=1`
- Get latest week rankings for season 2 only

## Verification Approach

1. **Pre-check**: Count games per season before changes
2. **Run Scripts**: Execute `python scripts/run_all_playoff_analysis.py`
3. **Verify Output**:
   - Check `output/playoff_probabilities.json` has reasonable values
   - Verify team records match season 2 standings
   - Confirm remaining games count matches expected (week 12-17)
4. **Manual Validation**: Compare team W-L records with MEGA_teams.csv for season 2

## Expected Outcomes

- Scripts should use only Season 2 data (seasonIndex=1)
- Playoff probabilities should reflect current Season 2 standings
- Remaining games should be weeks 12-17 (approximately 80-96 games total)
- Team records should match Season 2 data only

## Risks

- **Low**: Changes are localized to data filtering, core simulation logic unchanged
- **Medium**: Need to ensure rankings data for Season 2 exists (verified: yes)
