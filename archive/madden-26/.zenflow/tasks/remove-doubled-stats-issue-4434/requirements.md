# Remove Doubled Stats for Traded Players – PRD

## Context and Problem Statement

- The stats pipeline is built on flat CSV exports from the MEGA league:
  - Player‑level season stats by team: `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`, `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`.
  - Team‑level season context: `MEGA_teams.csv`, rankings in `MEGA_rankings.csv`, schedule in `MEGA_games.csv`, Elo in `mega_elo.csv`.
  - Roster and cap data: `MEGA_players.csv` and downstream exports in `output/team_rosters/*.csv` and `output/power_rankings_roster.csv`.
  - Stats outputs powering the dashboards: `output/team_aggregated_stats.csv`, `output/team_player_usage.csv`, `output/team_rankings_stats.csv`.
  - A placeholder for trade metadata: `MEGA_trades.csv` (header only today).
- Player stat CSVs already contain multiple rows for players who appeared on multiple teams in a season (e.g. Lamar Jackson has separate Browns and Ravens rows in passing and rushing).
- Roster/cap CSVs (`MEGA_players.csv` and `output/team_rosters/*.csv`) currently treat each player as belonging to a single “current” team and do not encode when that changed.
- As a result, traded players can conceptually distort:
  - Team‑level season stats (offense/defense/usage) when their season totals are implicitly attributed to the wrong team or to more than one team.
  - Player‑level stats views when it is unclear which portion of a player’s production belongs to each team.
  - Any correlation / rankings work that assumes “team season stats” correspond to the roster that actually played those snaps.
- Concrete example: Lamar Jackson played early‑season games for the Ravens and later games for the Browns. Current data/visualizations make it look like Cleveland “has Lamar from Week 1”, even though some or all of those stats actually occurred while he was on Baltimore.

**Goal:** Make the stats and visualizations trade‑aware so that:
- Team stats reflect only the production that happened while a player was actually on that team.
- Player stats clearly separate multi‑team seasons by team stint.
- Downstream dashboards (`team_stats_explorer`, `team_player_usage`, correlations, rankings) no longer double‑count or misattribute traded‑player production.

**Non‑goals (for this iteration):**
- Full per‑game or per‑snap history; we continue to work primarily with season‑aggregate CSVs.
- Automatic ingestion from external APIs beyond the existing CSV exports.
- Changing how the roster cap tool models trades as transactions (that is handled separately in `docs/roster_cap_tool`).

## Key User Stories and Acceptance Scenarios

### Story 1 – Team season stats are trade‑correct

As a league commissioner reviewing team performance,  
I want traded players’ pre‑trade stats to stay with their original team,  
so that season‑long efficiency metrics reflect what actually happened on the field.

- **Given** a player (e.g. Lamar Jackson) has stat rows for multiple teams in `MEGA_passing`/`MEGA_rushing` (Ravens and Browns),
  and Browns and Ravens have final records and yardage in `MEGA_teams.csv`,
- **When** I view the Browns’ season stats in `team_aggregated_stats.csv` or on `team_stats_explorer.html`,
- **Then** Browns passing/rushing/receiving/defensive totals should include only the subset of Lamar’s stats that correspond to his Browns stint,
  and **Then** Ravens totals should include only the subset that correspond to his Ravens stint,
  and **Then** Lamar’s season production should not be counted twice across the league.

### Story 2 – Player stats show clear multi‑team splits

As an analyst or fan looking at individual players,  
I want a traded player’s stats to be broken down by team,  
so that I can see how they performed for each team without guessing from context.

- **Given** a player appears under more than one team in the MEGA stat CSVs (e.g. `player__rosterId` appears with both Browns and Ravens),
- **When** I query or visualize that player’s stats (through CSVs or dashboards),
- **Then** I should see at least two distinct segments (e.g. “Lamar Jackson – Ravens” and “Lamar Jackson – Browns”),
  with games, yards, TDs, and other metrics consistent within each stint,
  and **Then** an optional “All teams” total is clearly labeled as a sum of those stints, not a separate team entry.

### Story 3 – Player usage distributions respect trades

As a user exploring `team_player_usage` (target shares, RB usage, etc.),  
I want usage metrics to be computed from the players who actually played for that team,  
so that a mid‑season addition does not retroactively change early‑season distributions.

- **Given** `output/team_player_usage.csv` is derived from `MEGA_receiving` and `MEGA_rushing`,
  and some players in those CSVs have rows for multiple teams,
- **When** I inspect Browns usage metrics (e.g. WR1 target share, RB1 rush share),
- **Then** only Browns‑stint rows for relevant players should participate in those shares,
  and **Then** those shares should align with the Browns’ per‑team totals in `team_aggregated_stats.csv`.

### Story 4 – Pipeline and data contracts are explicit about trades

As a developer extending the stats pipeline,  
I want a clear, documented contract for how traded players are represented,  
so that new scripts can be made trade‑safe by design.

- **Given** the project’s stat CSVs (`MEGA_*`, `output/*.csv`) and the new trade‑aware data model,
- **When** I add a new analysis script or visualization,
- **Then** I can rely on a documented canonical source for trade information (e.g. a populated `MEGA_trades.csv` or a derived `player_team_segments` CSV),
  and **Then** I can test that total league stats are not inflated by double‑counting multi‑team seasons.

## Functional Requirements

### Data modeling and trade representation

1. **Canonical traded‑player representation**
   - The system must have a single canonical source for in‑season team changes, either:
     - a populated `MEGA_trades.csv`, or
     - a new derived CSV (e.g. `output/player_team_segments.csv`) produced from existing data.
   - At minimum each trade/segment must encode: `player__rosterId`, `player__fullName`, `from_team`, `to_team`, `seasonIndex`, and the number of games played for each team; ideally also `weekIndex` of the trade.

2. **Multi‑team season segments**
   - For any player appearing under more than one `team__displayName` in the MEGA stat CSVs, the pipeline must treat each `(player__rosterId, team__displayName)` pair as a distinct “team stint”.
   - It must be possible to reconstruct, for each stint, consistent aggregates across passing, rushing, receiving, and defense (e.g. Lamar’s Browns rushing stats and Browns passing stats line up as a single stint).

3. **Roster vs stats separation**
   - `MEGA_players.csv` and roster exports may continue to treat `team` as the current team for cap/roster tools, but the stats pipeline must not rely on that field to determine where past production occurred.
   - Documentation must clarify that `team__displayName` in the MEGA stat CSVs is the authoritative team for that stat row.

### Aggregation and outputs

4. **Team aggregation is trade‑aware**
   - `stats_scripts/aggregate_team_stats.py` must aggregate per‑team totals using player‑team stints such that:
     - Each stat row contributes only to the team indicated in that row.
     - A player with multiple teams in a season contributes separately to each team’s row, without duplication of the same game stats.
   - League‑level integrity: summing key stats across `team_aggregated_stats.csv` (e.g. total pass yards) must match summing the same columns directly from the MEGA player stat CSVs, within rounding tolerances.

5. **Player usage is trade‑aware**
   - `stats_scripts/aggregate_player_usage.py` must compute target/rush shares and concentration metrics using only the players associated with that team in the receiving/rushing CSVs.
   - A player’s usage for their old team must not be included in the new team’s usage metrics and vice versa.

6. **Rankings and correlation inputs are consistent**
   - `output/team_rankings_stats.csv` must align with `team_aggregated_stats.csv` for core volume metrics (off/def yards, points, etc.), ensuring that ranking‑based pages use the same trade‑aware team numbers.
   - Any future correlation scripts must treat team season rows as trade‑correct by construction (no post‑hoc filtering).

7. **Optional “current‑roster” lens (stretch goal)**
   - It should be possible (via a flag or separate output CSV) to generate a view where each player’s full‑season stats are rolled up under their current team (e.g. for a “what if we had them all year?” perspective), distinct from the canonical “where did the stats actually happen?” view.

### Validation and diagnostics

8. **Multi‑team player report**
   - Provide a simple report (CSV or console) listing all players who appear for multiple teams in the MEGA stat CSVs, including per‑team games and key stats (yards, TDs).
   - This report will be used to spot‑check correctness for high‑impact trades like Lamar Jackson and Baker Mayfield.

9. **Invariance checks**
   - The pipeline must include checks (either assertions or a dedicated verification script) that:
     - per‑league totals from `team_aggregated_stats.csv` match the sum of MEGA player stat CSVs;
     - no player’s season totals are greater when summing across teams than when summing their raw MEGA stat rows.

10. **Backwards compatibility**
    - Existing consumers that only care about team‑level aggregates (e.g., SOS and ELO scripts using `team_aggregated_stats.csv`) must continue to work without changes, benefiting automatically from corrected stats.
    - File formats (`team_aggregated_stats.csv`, `team_player_usage.csv`, `team_rankings_stats.csv`) should remain stable where possible; any new columns must be additive and documented.

## Proposed Approaches (for review, not implementation yet)

These approaches are meant as design options to review before coding. The final implementation can choose one or combine elements.

### Approach A – Leverage existing stat splits as the source of truth

**Idea:** Treat the MEGA stat CSVs (passing, rushing, receiving, defense, etc.) as the canonical record of where production happened, and make sure all aggregation scripts and visualizations respect those splits.

- Identify multi‑team players by scanning MEGA stat CSVs for duplicated `player__rosterId` with different `team__displayName`.
- Treat each `(player__rosterId, team__displayName)` as a separate stint when aggregating team stats and player usage.
- Ensure no script infers team from `MEGA_players.team` when computing stats; always join via the team field embedded in the stat row.
- Optionally generate a small helper CSV (e.g. `output/player_team_stints.csv`) summarizing each stint (player, team, games, key stats) to power player‑centric UIs.

**Pros:**
- Uses data we already have; no new manual trade input required.
- Automatically handles any future in‑season trades as long as the export includes per‑team rows.
- Keeps the pipeline simple: aggregation is a pure sum over correctly labeled stat rows.

**Cons / Open questions:**
- We only know per‑team season totals and games, not the exact week of the trade; we cannot reconstruct weekly evolution without additional data.
- We need to confirm with league owners that the MEGA stat exports already split stats by team exactly the way they expect (the Lamar example suggests they do, but this should be validated).

### Approach B – Introduce explicit trade metadata

**Idea:** Use `MEGA_trades.csv` (or a new CSV) to explicitly record trades, including the week they occurred, and make trade handling a first‑class concept in stats scripts.

- Populate `MEGA_trades.csv` with one row per trade:
  - `tradeId`, `player__rosterId` (or player export ID), `fromTeam`, `toTeam`, `seasonIndex`, `weekIndex`, plus free‑text `details`.
- Derive player‑team stints by combining `MEGA_trades.csv` with the MEGA stat CSVs:
  - For example, if Lamar has “Ravens → Browns at week 5”, interpret his Ravens stat row as weeks 1–4 and his Browns stat row as weeks 5+.
- Optionally extend dashboards to support “pre‑trade vs post‑trade” comparisons or to show when major trades happened on timeline views.

**Pros:**
- Makes the notion of a trade and its timing explicit and queryable.
- Unlocks richer future features (e.g. “team performance before/after trade”, “impact of a deadline move”).

**Cons / Open questions:**
- Requires a reliable process to keep `MEGA_trades.csv` up to date (either automated export or manual maintenance).
- The week split implied by `gamesPlayed` vs `weekIndex` needs clear rules; current CSVs do not encode per‑game participation.

### Approach C – Hybrid: stat‑first now, trade metadata later

**Idea:** In the short term, fix double‑counting and mis‑attribution using Approach A (stat‑row splits), while designing `MEGA_trades.csv` and validation hooks so that richer trade modeling can be added later.

- Immediate steps:
  - Audit aggregation scripts (`aggregate_team_stats.py`, `aggregate_player_usage.py`, any others) to confirm they are purely stat‑row based and do not collapse multi‑team seasons.
  - Add the multi‑team player report and league‑level invariance checks.
  - Document expected behavior for traded players in `spec/stats_team_aggregation.md` and `spec/stats_player_usage.md`.
- Future steps:
  - Define the schema and maintenance process for `MEGA_trades.csv`.
  - Add optional “pre/post trade” views once reliable trade timing data is available.

**Pros:**
- Addresses the immediate correctness issue with minimal disruption.
- Creates a clear path for a richer trade model without blocking on new data.

**Cons:**
- Until `MEGA_trades.csv` is populated, we still cannot answer “stats through Week N at time of trade” type questions.

## Success Criteria

1. **No doubled production for traded players**
   - For any player with multiple teams in the season, the sum of their per‑team stats across all teams in MEGA stat CSVs must match the sum of their stats as seen through any team‑level output (e.g. aggregating `team_aggregated_stats.csv` back down to the player).
   - In particular, Lamar Jackson’s Browns and Ravens contributions should sum to his true season total, and league‑wide totals should not change when the trade‑aware logic is introduced.

2. **Consistent team metrics across all stats outputs**
   - For each team, core metrics (pass yards, rush yards, points for/against, turnovers) must be internally consistent between:
     - `MEGA_teams.csv` (where applicable),
     - `output/team_aggregated_stats.csv`,
     - and `output/team_rankings_stats.csv`.
   - Stats dashboards (`team_stats_explorer`, `team_stats_correlations`, `team_player_usage`, `rankings_explorer`) must all reflect the same corrected numbers.

3. **Clear player‑centric view of traded seasons**
   - For at least one known traded star (e.g. Lamar Jackson) and one secondary example (e.g. Baker Mayfield Jets → Buccaneers), we can:
     - Point to a machine‑readable representation of their per‑team stints.
     - Manually verify that team and player stats line up with expectations for those stints.

4. **Documented, testable contracts**
   - `spec/stats_team_aggregation.md` and `spec/stats_player_usage.md` are updated (in later steps) to describe trade handling rules.
   - A simple verification command (or script) is documented in the README to re‑run the stats pipeline and check invariants.

5. **User validation**
   - League stakeholders can look at a handful of traded players and teams they touched and confirm:
     - “This is now showing the right numbers for each team,” and
     - “I no longer see traded players implicitly counted as being on their new team from Week 1.”

