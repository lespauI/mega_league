# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: 1e4477fd-e9b4-433a-8a2d-41cdf583f774 -->

**Difficulty**: Medium

See `spec.md` for full specification.

**Summary**: Scripts need to filter by `seasonIndex=1` (Season 2) to use correct data. Currently they load all games from all seasons.

---

### [x] Step: Update calc_playoff_probabilities.py
<!-- chat-id: 2d2433a3-159c-401f-889f-ebfbc52693ad -->

Modify `load_data()` function to filter games by:
- `seasonIndex=1` (Season 2)
- `stageIndex=1` (Regular season only)

**Verification**: Run script and confirm team records match Season 2 data.

**Completed**: Added filters at lines 23-26 to skip games where `seasonIndex != 1` or `stageIndex != 1`. Verified: 272 Season 2 games loaded (179 completed, 93 pending).

---

### [x] Step: Update calc_sos_by_rankings.py
<!-- chat-id: c2d7faf8-64cc-444f-af8e-da57b1be8c1e -->

Modify data loading functions:
1. `read_games_split()` - filter by seasonIndex=1 and stageIndex=1
2. `read_latest_rankings()` - filter rankings by seasonIndex=1

**Verification**: Run script and confirm SoS data is for Season 2.

**Completed**: Added filters at lines 73-76 in `read_latest_rankings()` to skip non-Season 2 rankings. Added filters at lines 102-105 in `read_games_split()` to filter by seasonIndex=1 and stageIndex=1. Verified: Script outputs Season 2 data with 6 remaining games per team.

---

### [x] Step: Run Full Analysis & Verify
<!-- chat-id: 24af5dfe-394d-47d4-91f7-af4c829ef3f3 -->

1. Run `python scripts/run_all_playoff_analysis.py`
2. Verify output files are generated correctly
3. Manually validate team records against Season 2 standings
4. Confirm remaining games count is correct (weeks 12-17)

**Completed**: All scripts ran successfully. Verified:
- 272 Season 2 regular season games (180 completed, 92 pending in weeks 12-17)
- Team records match raw CSV data (e.g., Broncos 9-2, Browns 9-2, Bengals 9-3)
- Remaining games per team correctly calculated (5-6 games each)
- Output files generated: playoff_probabilities.json, playoff_race.html, playoff_race_table.html

---

### [x] Step: Write Report
<!-- chat-id: 204f374f-61e2-4fd4-bc58-ec0fa3086566 -->

Document what was implemented, how it was tested, and any issues encountered in `report.md`.

**Completed**: Created `report.md` documenting all changes to `calc_playoff_probabilities.py` and `calc_sos_by_rankings.py`, verification results, and testing approach.

### [x] Step: Run scripts to recalculate probabilities
<!-- chat-id: b1239893-eaca-45ee-8f80-b597b91ce8a6 -->

Run scripts for season 2 and check the data is correct, and we dont have any bugs

**Completed**: Ran `python3 scripts/run_all_playoff_analysis.py` successfully. Verified:
- 272 Season 2 regular season games (179 completed, 92 pending in weeks 12-17)
- Team records match raw CSV data (Broncos 9-2, Browns 9-2, Bengals 9-3)
- All output files generated: playoff_probabilities.json, playoff_race.html, playoff_race_table.html, draft_race files
