# Feature Specification: Roster-Based Power Rankings & Unit Strength Analysis


## User Stories*


### User Story 1 - Generate roster-based power rankings

**Acceptance Scenarios**:

1. Given league CSVs (`MEGA_players.csv`, `MEGA_teams.csv`) are present, When I run the CLI with default options, Then it produces `output/power_rankings_roster.csv` and `docs/power_rankings_roster.html` with team ranks, unit grades, and a strengths/weaknesses summary for all 32 teams.
2. Given teams have players with Superstar/X-Factor dev traits, When rankings are generated, Then the dev traits influence unit grades proportionally to player overall (low-OVR dev traits contribute minimally by design).


### User Story 2 - View team strengths and weaknesses

**Acceptance Scenarios**:

1. Given the HTML report is generated, When I open my team’s section, Then I see headline scores (overall power score, Offense/Defense unit grades) and a narrative explaining top strengths and weaknesses with key contributing players.
2. Given the report is loaded, When I interact with the team list (search/sort), Then I can quickly locate my team and compare its unit grades versus league average and top quartile benchmarks.


### User Story 3 - Compare teams across units

**Acceptance Scenarios**:

1. Given the HTML report includes charts, When I sort by a specific unit (e.g., Pass Coverage), Then teams reorder accordingly and the chart highlights the selected metric with league-average reference lines.
2. Given unit grades exist, When I open a team detail, Then I can see a compact radar/spider visualization for its major units (Off Pass, Off Run, Def Coverage, Pass Rush, Run Defense) and dev-trait composition.


### User Story 4 - Operate the pipeline repeatedly

**Acceptance Scenarios**:

1. Given the CLI accepts input/output paths and weights config, When I run it multiple times with the same inputs, Then outputs are deterministic and overwrite old outputs unless `--no-clobber` is specified.
2. Given I change weighting parameters, When I rerun, Then the new outputs reflect updated weights and the report documents the configuration used.

---

## Requirements*

- Scope and goals
  - Produce roster-based team power rankings independent of in-season statistics, focused on player overalls, position groups, line play attributes, and dev traits (Superstar/X-Factor) with sensible scaling.
  - Output both machine-readable CSV and a polished HTML report “in the same style as draft class analysis,” reusing CSS/card layout patterns and visual tone from `docs/draft_class_2026.html` and the charts style from `docs/rankings_explorer.html` where appropriate.
  - Provide high-signal insights; minimize misleading signals (e.g., a 66 OVR Superstar should not elevate a team in a meaningful way).

- Inputs
  - Required: `MEGA_players.csv` (player metadata, position, team, OVR, devTrait, ratings), `MEGA_teams.csv` (team IDs/names/abbrevs).
  - Optional/auxiliary for presentation only: team logos if available; other MEGA CSVs are not used for scoring in the initial version.

- Roster export and preparation
  - Export per-team roster CSVs to `output/team_rosters/<TEAM_ABBR>.csv` with key fields: id, team, position, playerBestOvr, devTrait, primary ratings relevant to unit scoring.
  - Split rosters into Offense, Defense, and Special Teams logical groups for calculation; persist as `output/team_rosters/<TEAM_ABBR>_O.csv`, `_D.csv`, `_ST.csv`.
  - Starter selection when no depth chart file is provided: derive starters by position typical counts and OVR (ties by relevant attribute). Example defaults:
    - Offense: 1 QB, 1 RB, 3 WR, 1 TE, 5 OL (LT, LG, C, RG, RT). FB optional if present.
    - Defense base: 2 CB, 1 FS, 1 SS, 2 EDGE (OLB/DE), 2 DT/IDL, 2 LB (MIKE/WILL). Adjust by best-available front7 composition if strict positions are scarce.
    - Special Teams: 1 K, 1 P; returners optional for display.
  - Handle position scarcity gracefully (warn and backfill from nearest roles with adjusted weight).

- Unit scoring (normalized 0–100 per unit)
  - Offense Passing: QB (accuracy short/mid/deep, throw power, under pressure, play action), WR/TE (route running, release, catch, spec catch), OL pass block (PBP, PBF, PB). Weights calibrated to prioritize QB and OL.
  - Offense Rushing: RB (carrying, break tackle, trucking/juke, speed/accel), OL run block (RBK, RBF, RBP), TE/FB run/lead block. Weights calibrated to prioritize OL then RB.
  - Defense Pass Coverage: CB/FS/SS (man, zone, press, play rec), LB coverage (zone/man/play rec) as secondary.
  - Defense Pass Rush: EDGE/DE/OLB/DT (FMV/PMV, block shed, finesse/power mix, strength/accel) with front-7 emphasis.
  - Defense Run Defense: DL/LB (tackle, block shed, pursuit, hit power) with safeties as secondary.
  - Optional Special Teams (configurable): K/P (accuracy/power). Default excluded from overall unless enabled.
  - Dev trait effect: multiplicative bonus scaled by OVR band to avoid over-weighting low-OVR dev players. Proposed defaults:
    - X-Factor: +10% if OVR ≥ 85; +5% if 80–84; +0% otherwise.
    - Superstar: +7% if OVR ≥ 85; +3% if 80–84; +0% otherwise.
    - Star/Normal: +0%.
  - Normalization: z-score or min–max within league to 0–100 per unit; publish method in report footer and include config snapshot.

- Overall power score
  - Default composite (configurable): 30% Off Pass, 20% Off Run, 30% Pass Coverage, 20% Pass Rush. Run Defense surfaced in report and narratives but excluded from default composite to keep 100% weighting focused on passing-era meta; can be toggled via CLI/config.
  - Generate league ranks for each unit and overall. Provide league-average and top-quartile benchmarks for context.

- Narratives and insights
  - For each team, auto-generate 2–4 bullet insights describing strongest unit(s), weakest unit(s), and key player contributors (name, position, OVR, dev) that drive those results.
  - Flag outliers (e.g., elite OL run block with average RB) with actionable interpretation.

- HTML report
  - Location: `docs/power_rankings_roster.html` (default; configurable via `--out-html`).
  - Style: reuse the CSS and card layout patterns from the draft class analysis page; use compact radar for 4 core units; bar charts for unit ranks; dev composition pills; search/sort UI similar to existing docs pages.
  - Include an “Assumptions & Method” section with weights, dev multipliers, and unit definitions.

- CSV outputs
  - `output/power_rankings_roster.csv`: one row per team with fields: team, overall_score, overall_rank, off_pass_score/rank, off_run_score/rank, def_cover_score/rank, def_rush_score/rank, def_run_score/rank, dev_counts (normal/star/ss/x), top_contributors (compact list), config_hash.
  - `output/team_rosters/*.csv` and split O/D/ST variants per team.

- CLI & configuration
  - Single entry script (e.g., `scripts/power_rankings_roster.py`) with args: `--players`, `--teams`, `--out-csv`, `--out-html`, `--export-rosters`, `--include-st`, `--weights-json`, `--dev-multipliers-json`, `--verbose`, `--no-clobber`.
  - Defaults baked-in; custom weights via JSON path or inline JSON.

- Quality, performance, and reliability
  - Deterministic outputs for the same inputs/config. Runtime under 3 seconds on typical hardware for 32 teams.
  - Clear warnings for missing data/positions; continue with best-effort backfills.
  - Unit-tested scoring functions where feasible; CLI smoke test to validate end-to-end generation.

- Out of scope (v1)
  - No usage of game stats, strength of schedule, win-loss records, or in-season injuries for scoring (presentation can show them if provided later).
  - No per-week deltas or time-series trends.

- Assumptions and open decisions
  - Dev trait multipliers follow the OVR-banded model above to neutralize low-OVR outliers.
  - Starter counts per unit follow standard formations; edge cases backfill from nearest-role players.
  - Composite weights prioritize passing-era impact; can be tuned by config.
  - Special Teams excluded from overall by default.
  - [NEEDS CLARIFICATION] Confirm default composite weights and whether Run Defense should be included in the overall by default.
  - [NEEDS CLARIFICATION] Confirm dev-trait OVR thresholds and bonus levels; proposed: thresholds at 80 and 85 OVR with +3/+7 (SS) and +5/+10 (X-Factor).
  - [NEEDS CLARIFICATION] Should we strictly adhere to existing depth charts if an authoritative depth chart file exists, or keep OVR-based starter selection for v1?
  - [NEEDS CLARIFICATION] Output paths and naming: `docs/power_rankings_roster.html` and `output/power_rankings_roster.csv` acceptable?
  - [NEEDS CLARIFICATION] Unit set and presentation: do we include OL pass/run as separate surfaced metrics or fold into Off Pass/Run only (current plan: fold into unit scoring but display OL sub-scores in team detail)?

## Success Criteria*

- Running `python3 scripts/power_rankings_roster.py --players MEGA_players.csv --teams MEGA_teams.csv` produces:
  - `output/power_rankings_roster.csv` with complete scores/ranks for all teams.
  - `docs/power_rankings_roster.html` styled consistently with draft class analysis, including searchable/sortable team list, per-team cards with radar/bar charts, and narratives.
- Low-OVR dev-trait players do not materially distort unit or overall ranks (verified by spot-checking teams with <80 OVR dev players).
- Team cards clearly articulate at least one strength and one weakness with named key contributors.
- Outputs are deterministic across runs given the same inputs and config; CLI prints config summary and paths to artifacts.
- The method section transparently documents unit definitions, weights, and dev multipliers used in the calculation.

