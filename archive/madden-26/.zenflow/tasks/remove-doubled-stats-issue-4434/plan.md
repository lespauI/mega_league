# New feature

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Requirements
<!-- chat-id: cc556460-2ecd-438e-a87d-a5784169ad75 -->

Create a Product Requirements Document (PRD) based on the feature description.

1. Review existing codebase to understand current architecture and patterns
2. Analyze the feature definition and identify unclear aspects
3. Ask the user for clarifications on aspects that significantly impact scope or user experience
4. Make reasonable decisions for minor details based on context and conventions
5. If user can't clarify, make a decision, state the assumption, and continue

Save the PRD to `{@artifacts_path}/requirements.md` with:
- User stories with acceptance scenarios (Given/When/Then)
- Functional requirements
- Success criteria

### [x] Step: Technical Specification
<!-- chat-id: 907cab45-cdde-49b7-b8b6-c428547818c2 -->

Create a technical specification based on the PRD in `{@artifacts_path}/requirements.md`.

1. Review existing codebase architecture and identify reusable components
2. Define the implementation approach

Save to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach referencing existing code patterns
- Source code structure changes
- Data model / API / interface changes
- Delivery phases (incremental, testable milestones)
- Verification approach using project lint/test commands

### [x] Step: Planning
<!-- chat-id: 6cb523bf-eaf3-4bdc-a169-c08099b5b76b -->

Create a detailed implementation plan based on `{@artifacts_path}/spec.md`.

1. Break down the work into concrete tasks
2. Each task should reference relevant contracts and include verification steps
3. Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function) or too broad (entire feature).

If the feature is trivial and doesn't warrant full specification, update this workflow to remove unnecessary steps and explain the reasoning to the user.

Save to `{@artifacts_path}/plan.md`.

### [x] Step: Phase 1 – Canonical team helper and aggregator updates
<!-- chat-id: 866a8cd4-3f11-460f-978f-f378df97e9c6 -->

Implement the shared helpers and make all primary stats aggregators trade-aware via canonical team keys, as described in `{@artifacts_path}/spec.md` (sections 4.1, 4.3, 4.4, 5).

1. Add a shared helper module (e.g. `stats_scripts/stats_common.py`) exposing:
   - `load_csv(path) -> list[dict]`
   - `safe_float(value, default=0.0) -> float`
   - `normalize_team_display(name: str) -> str` that:
     - Strips whitespace.
     - Removes any leading numeric index and colon from team display names (e.g. `"11:Browns"` → `"Browns"`).
2. Update `stats_scripts/aggregate_team_stats.py` to:
   - Build team maps using canonical team names.
   - Filter player stat rows by `normalize_team_display(row['team__displayName'])`.
   - Rely on volume stats (attempts, yards, TDs, INTs, sacks, etc.) and team games from `MEGA_teams.csv` instead of per-player "per game" averages for multi-team players.
3. Update `stats_scripts/aggregate_player_usage.py` to:
   - Use the same canonical team normalization when grouping receiving/rushing rows.
   - Keep usage metrics stat-row based so multi-team players are only counted for the teams in their stat rows.
4. Update `stats_scripts/aggregate_rankings_stats.py` (as needed) to:
   - Join `MEGA_teams`, `mega_elo.csv`, `MEGA_rankings.csv`, and `output/team_aggregated_stats.csv` using canonical team display names and/or stable team abbreviations.
5. Verification:
   - Run `python3 stats_scripts/aggregate_team_stats.py`.
   - Run `python3 stats_scripts/aggregate_player_usage.py`.
   - Run `python3 stats_scripts/aggregate_rankings_stats.py`.
   - Spot-check a few teams (including ones with known traded players like Lamar Jackson and Baker Mayfield) to confirm:
     - All expected teams appear.
     - Offensive/defensive volumes align with the underlying MEGA stat CSVs.

### [x] Step: Phase 1 – Build player_team_stints summary
<!-- chat-id: ff2f0416-a5fe-4260-afdb-52c7db8d5775 -->

Create a canonical, per-team/per-player stint summary to support trade-aware views and future validation, as defined in `{@artifacts_path}/spec.md` section 4.2 and data contracts in section 6.2.

1. Implement `stats_scripts/build_player_team_stints.py` that:
   - Reads `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`.
   - Uses `normalize_team_display` to derive a canonical team key.
   - Aggregates stats into one row per `(seasonIndex, canonicalTeam, player__rosterId)` with:
     - Identity columns (seasonIndex, team display, team abbrev, player__rosterId, player__fullName, player__position).
     - Phase-specific volume stats as outlined in the spec (passing, rushing, receiving, defensive).
     - A derived `multi_team_season` flag based on whether the player appears for multiple teams in the season.
   - Writes `output/player_team_stints.csv`.
2. Ensure the script reuses helpers from `stats_common.py` (CSV loading, safe float parsing, team normalization).
3. Verification:
   - Run `python3 stats_scripts/build_player_team_stints.py`.
   - Open `output/player_team_stints.csv` and:
     - Confirm that players with a single team have one row per season.
     - Confirm that multi-team players (e.g. Lamar Jackson, Baker Mayfield) have one row per team with reasonable per-team volumes.

### [x] Step: Phase 2 – Trade verification script and traded-players report
<!-- chat-id: 7c805276-08db-418c-b01e-96d7a927dc64 -->

Add verification tooling to detect multi-team players and enforce invariants between player-level and team-level stats, following `{@artifacts_path}/spec.md` section 4.5 and PRD validation criteria.

1. Implement `scripts/verify_trade_stats.py` that:
   - Reads `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv` using shared helpers.
   - Reads `output/team_aggregated_stats.csv` and `output/player_team_stints.csv`.
2. Multi-team player report:
   - Group by `player__rosterId` (and season) to find players with stats for multiple canonical teams.
   - Emit `output/traded_players_report.csv` including:
     - `player__rosterId`, `player__fullName`, list of teams, and key volume stats per team.
3. Invariant checks:
   - For each team and core stat (e.g. pass yards, rush yards, TDs):
     - Sum values from `player_team_stints.csv` and compare to `output/team_aggregated_stats.csv`, allowing a small tolerance.
   - Optionally check league-wide totals by summing across all teams from both sources.
   - Log discrepancies with enough detail to debug (team, stat name, expected vs actual).
4. Verification:
   - Run `python3 scripts/verify_trade_stats.py` after regenerating stats.
   - Inspect `output/traded_players_report.csv` to confirm known traded players are present with correct teams.
   - Ensure no invariants fail for the current dataset, or document and triage any intentional exceptions.

### [x] Step: Phase 2 – Orchestration and documentation updates
<!-- chat-id: 24b806e1-ac2a-43de-99cf-7a2260e2a22d -->

Wire the new trade-aware tools into the standard stats pipeline and document their usage, referencing `{@artifacts_path}/spec.md` sections 5 and 8 and the PRD success criteria.

1. Update `scripts/run_all_stats.py` to:
   - Invoke `stats_scripts/build_player_team_stints.py` after the core aggregation scripts.
   - Optionally invoke `scripts/verify_trade_stats.py` at the end, or clearly document it as a recommended follow-up command.
2. Update stats-related specs and docs:
   - Amend `spec/stats_team_aggregation.md` and `spec/stats_player_usage.md` (or their equivalents) to describe:
     - Canonical team normalization rules.
     - How traded-player stats are split across teams.
     - The role of `player_team_stints.csv` and `traded_players_report.csv`.
   - Update `README.md` (or relevant docs) with:
     - The recommended pipeline: `python3 scripts/run_all_stats.py` followed by `python3 scripts/verify_trade_stats.py`.
     - A short explanation of how to use `output/player_team_stints.csv` and `output/traded_players_report.csv` for manual validation.
3. Verification:
   - Run the full pipeline via `python3 scripts/run_all_stats.py` (and the verification script, if integrated).
   - Confirm all expected CSV outputs are generated without errors.
   - Spot-check documentation against actual script behavior and CLI usage.

### [x] Step: Fixes
<!-- chat-id: e2c79d80-26ad-4742-8ac2-37bdcc85f701 -->

I see you evaluate traded players correctly thats grate, but when i looking into the stats graps, for example into Turnover Balance — Defensive INTs vs Offensive INTs i still can see ambigeous stats of doubled ints for Ravens And Browns, you must update the calculation and remove ambigeous stats for every our statistical calculations
