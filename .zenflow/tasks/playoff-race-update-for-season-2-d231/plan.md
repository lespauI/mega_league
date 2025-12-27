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

### [ ] Step: Update calc_playoff_probabilities.py

Modify `load_data()` function to filter games by:
- `seasonIndex=1` (Season 2)
- `stageIndex=1` (Regular season only)

**Verification**: Run script and confirm team records match Season 2 data.

---

### [ ] Step: Update calc_sos_by_rankings.py

Modify data loading functions:
1. `read_games_split()` - filter by seasonIndex=1 and stageIndex=1
2. `read_latest_rankings()` - filter rankings by seasonIndex=1

**Verification**: Run script and confirm SoS data is for Season 2.

---

### [ ] Step: Run Full Analysis & Verify

1. Run `python scripts/run_all_playoff_analysis.py`
2. Verify output files are generated correctly
3. Manually validate team records against Season 2 standings
4. Confirm remaining games count is correct (weeks 12-17)

---

### [ ] Step: Write Report

Document what was implemented, how it was tested, and any issues encountered in `report.md`.
