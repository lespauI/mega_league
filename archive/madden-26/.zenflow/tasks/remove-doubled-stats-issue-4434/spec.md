# Technical Specification – Trade‑Aware Team & Player Stats

## 1. Technical Context

- **Language & Runtime**
  - Python 3 CLI scripts using only the standard library (`csv`, `pathlib`, `collections`, etc.).
- **Primary Stats Scripts**
  - `stats_scripts/aggregate_team_stats.py`
    - Aggregates player‑level CSVs into `output/team_aggregated_stats.csv` (one row per team).
  - `stats_scripts/aggregate_player_usage.py`
    - Aggregates player receiving/rushing by team into `output/team_player_usage.csv`.
  - `stats_scripts/aggregate_rankings_stats.py`
    - Joins team stats, rankings, and Elo into `output/team_rankings_stats.csv`.
  - Orchestration via `scripts/run_all_stats.py`.
- **Key Inputs**
  - Player stats (season aggregates by team):
    - `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`,
      `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`.
  - Team context:
    - `MEGA_teams.csv` (records, conference/division, cap, schemes, etc.).
    - `MEGA_rankings.csv`, `mega_elo.csv`.
  - Roster / cap:
    - `MEGA_players.csv` (one “current team” per player; includes `last_updated`).
    - Per‑team roster exports in `output/team_rosters/*.csv`.
  - Games schedule:
    - `MEGA_games.csv` (home/away, scores, `seasonIndex`, `weekIndex`).
  - Trades:
    - `MEGA_trades.csv` – header only today (`tradeId,teamA,teamB,draftPicksA,draftPicksB,approved,season,details,created`).
- **Current Outputs Used by Dashboards**
  - `output/team_aggregated_stats.csv` → `team_stats_explorer`, correlations.
  - `output/team_player_usage.csv` → `team_player_usage` views.
  - `output/team_rankings_stats.csv` → `team_rankings_stats` dashboards.
  - `output/team_rosters/*.csv`, `output/power_rankings_roster.csv` → roster‑driven visuals.

## 2. Current Behavior & Observed Trade Issues

### 2.1 How Aggregation Works Today

- `aggregate_team_stats.py`
  - Loads `MEGA_*` stat CSVs and `MEGA_teams.csv`.
  - Builds `teams_map` keyed by `teams['displayName']` (e.g. `"Browns"`, `"Ravens"`).
  - For each team name:
    - Filters player stat rows with `row['team__displayName'] == team`.
    - Sums volume fields (attempts, yards, TDs, INTs, sacks, tackles, etc.).
    - Derives rates (e.g. `pass_yds_per_att`, `sack_rate`) and per‑game metrics
      using win/loss/tie counts from `MEGA_teams.csv`.
- `aggregate_player_usage.py`
  - Uses `MEGA_receiving.csv`, `MEGA_rushing.csv`, plus `MEGA_teams` and
    `output/team_aggregated_stats.csv`.
  - For each team (`teams['displayName']`):
    - Filters receiving/rushing rows where `team__displayName == team`.
    - Computes target/rush shares by position, HHI concentration, WR1/2/3, RB1/2, styles, etc.

### 2.2 Data Shape for Traded Players

From the 2026 example data:

- **Multi‑team stat rows**
  - Lamar Jackson (`player__rosterId = 553387273`) appears for both Browns and Ravens:
    - `MEGA_passing.csv` has:
      - `11:Browns, ... Lamar Jackson, gamesPlayed=8, passTotalAtt=119, ...`
      - `44:Ravens, ... Lamar Jackson, gamesPlayed=8, passTotalAtt=161, ...`
    - `MEGA_rushing.csv` has:
      - `57:Browns, ... Lamar Jackson, gamesPlayed=8, rushTotalAtt=6, ...`
      - `224:Ravens, ... Lamar Jackson, gamesPlayed=8, rushTotalAtt=8, ...`
  - Other traded players (e.g. Baker Mayfield) show similar multi‑team stat rows.
- **Team naming mismatch**
  - In `MEGA_teams.csv`:
    - `displayName` is `"Browns"`, `"Ravens"`, etc. (no numeric prefix).
  - In stat CSVs:
    - `team__displayName` is sometimes prefixed with an index, e.g. `"11:Browns"`, `"44:Ravens"`.
    - Other teams (e.g. `49ers`) have plain names with no prefix.
  - Current aggregators compare `team__displayName` directly to `displayName`, so:
    - Prefixed rows like `"11:Browns"` will **not match** `"Browns"` and will be silently dropped from aggregation.
- **Roster vs stats**
  - `MEGA_players.csv` encodes a single current `team` per player and a `last_updated` timestamp.
    - Lamar’s current team appears as Browns in this file.
  - `output/team_rosters/*.csv` are roster snapshots; Lamar currently appears under Ravens there.
  - Neither roster export currently encodes **when** the team changed or how season stats should be split.

### 2.3 Conceptual Problem to Fix

From the PRD and data review:

- Traded players can:
  - Appear under multiple teams in the stat CSVs.
  - Be shown as belonging to a single “current team” in `MEGA_players` and roster exports.
- Without explicit trade handling:
  - Team‑level stats can appear to give a traded player’s full season production to their final team (“Lamar on CLE from Week 1”), depending on how the underlying MEGA export is built.
  - League‑wide totals can be distorted if a player’s production is effectively counted for more than one team in roll‑ups or correlations.
  - Player‑centric views do not clearly show “Ravens stint vs Browns stint”.
- We **do not** have per‑game stat CSVs, and `MEGA_trades.csv` is currently empty (header only),
  so we must:
  - Treat per‑team rows in `MEGA_*` stat CSVs as the canonical record of “where production belongs”.
  - Avoid inferring or retroactively moving stats using `MEGA_players.team` or roster exports.

## 3. Chosen High‑Level Approach

We adopt a **hybrid, stat‑first trade model** (PRD “Approach C”) with these concrete decisions:

1. **Canonical team normalization**
   - Introduce a consistent “team key” so that stats rows like `"11:Browns"` are correctly attributed to `"Browns"`.
   - Apply the same normalization everywhere we join across CSVs.
2. **Player‑team stint summary (derived)**
   - Treat each `(player__rosterId, canonicalTeam)` pair in stat CSVs as a **stint**.
   - Build a small derived CSV `output/player_team_stints.csv` summarizing season totals by stint to power:
     - Trade sanity checks.
     - Player‑centric UI for multi‑team seasons.
3. **Trade‑aware aggregation**
   - Keep **team stats** and **usage** aggregation fundamentally stat‑row based (no roster re‑assignment).
   - Ensure that:
     - All relevant stat rows are included (via normalized team keys).
     - Multi‑team players’ production is only counted for the team named on each stat row.
4. **Validation & invariants**
   - Add a verification step to:
     - Identify multi‑team players and emit a small report for human review.
     - Check league‑wide invariants (e.g. per‑team sums across stints vs team outputs).
5. **Future‑proofing for explicit trades**
   - Design `MEGA_trades.csv` schema and wiring points so that, once populated, we can:
     - Attach `seasonIndex` / `weekIndex` for each trade.
     - Optionally expose “pre‑trade vs post‑trade” views without changing the base stat contracts.

This keeps the immediate change minimal and safe (relying on existing per‑team stat rows),
while giving us clear extension points for richer trade modeling later.

## 4. Implementation Approach (Referencing Existing Code)

### 4.1 Canonical Team Keys

**Goal:** Ensure all scripts use a shared, normalized notion of team identity so that:
- `"Browns"` and `"11:Browns"` are treated as the same team.
- All joins and aggregations operate on this canonical key.

**Normalization rule**

- Define a pure helper function (e.g. `normalize_team_display(name: str) -> str`):
  - Trim whitespace.
  - Strip any leading numeric index plus colon: `^\d+:(.+)` → `\1`.
  - Return the cleaned display name (e.g. `"11:Browns"` → `"Browns"`).
- Define a reusable mapping between:
  - `canonical_team_name` (e.g. `"Browns"`)
  - `team_abbrev` from `MEGA_teams.csv` (e.g. `"CLE"`), when needed.

**Usage changes**

- `stats_scripts/aggregate_team_stats.py`
  - When building `teams_map`, normalize `t['displayName']` to `canonical_team`.
  - When filtering stat rows (passing/rushing/etc.), normalize `row['team__displayName']`
    and compare against `canonical_team`.
- `stats_scripts/aggregate_player_usage.py`
  - Same canonicalization logic for `teams_map` and stat row filtering.
- `stats_scripts/aggregate_rankings_stats.py`
  - Ensure joins between `MEGA_teams`, rankings CSVs, and `output/team_aggregated_stats.csv`
    use either:
    - `team_abbrev` when possible, or
    - the same `canonical_team_name` mapping.

**Expected impact**

- Previously dropped rows (due to prefixes) will now contribute correctly.
- Team stats and usage metrics will be based on the full set of stat rows, including traded players.

### 4.2 Player‑Team Stint Summary (`output/player_team_stints.csv`)

**Goal:** Provide a simple, machine‑readable representation of traded players’
multi‑team seasons and support Story 2 (“Player stats show clear multi‑team splits”).

**New script**

- Add `stats_scripts/build_player_team_stints.py`:
  - Inputs:
    - `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`,
      `MEGA_defense.csv`, `MEGA_punting.csv`, `MEGA_kicking.csv`.
    - `MEGA_teams.csv` for season/team context (e.g., conference, `seasonIndex`).
  - Output:
    - `output/player_team_stints.csv`
      - One row per `(seasonIndex, canonicalTeam, player__rosterId)`.
      - Suggested columns (initial, additive only):
        - Identity:
          - `seasonIndex`
          - `team` (canonical display name, e.g. `"Browns"`)
          - `team_abbrev` (e.g. `"CLE"`)
          - `player__rosterId`
          - `player__fullName`
          - `player__position`
        - Basic playing time:
          - `gamesPlayed_passing`, `gamesPlayed_rushing`, `gamesPlayed_receiving`,
            `gamesPlayed_defense` (raw from each CSV; may be equal across teams for traded players).
        - Aggregated stats by phase:
          - Passing volume: `passTotalAtt`, `passTotalComp`, `passTotalYds`, `passTotalTDs`, `passTotalInts`, `passTotalSacks`.
          - Rushing volume: `rushTotalAtt`, `rushTotalYds`, `rushTotalTDs`, `rushTotalFum`, `rushTotal20PlusYds`, `rushTotalYdsAfterContact`.
          - Receiving volume: `recTotalCatches`, `recTotalYds`, `recTotalTDs`, `recTotalDrops`, `recTotalYdsAfterCatch`.
          - Defensive volume: `defTotalTackles`, `defTotalSacks`, `defTotalInts`, `defTotalForcedFum`, `defTotalFumRec`, `defTotalTDs`.
        - Simple derived flags:
          - `multi_team_season` (boolean per player across all teams).
  - Implementation patterns:
    - Reuse `load_csv` and `safe_float` helpers from existing scripts, or centralize them in a small shared module if appropriate.
    - Use `normalize_team_display` for all team keys.

**Usage**

- For this task:
  - Use `player_team_stints.csv` as:
    - A report to verify how traded players have been split across teams.
    - A source for downstream dashboards that want per‑team player stats.
- Later:
  - This table can be extended with trade metadata once `MEGA_trades.csv` is populated.

### 4.3 Trade‑Aware Team Aggregation

**Goal:** Ensure that team‑level stats in `output/team_aggregated_stats.csv`:
- Include all relevant per‑team stat rows.
- Attribute production only to the team listed on each stat row.
- Respect multi‑team seasons without double‑counting.

**Changes to `aggregate_team_stats.py`**

1. **Canonical team filtering**
   - Replace direct equality checks:
     - `p.get('team__displayName') == team`
   - With normalized comparison:
     - `normalize_team_display(p.get('team__displayName', '')) == canonical_team`.
2. **Avoid relying on `gamesPlayed` from player rows for multi‑team metrics**
   - Today, some per‑game metrics use fields like `passAvgYdsPerGame` from the player CSVs.
   - For traded players, `gamesPlayed` appears constant across teams (e.g., 8 games for both Ravens and Browns),
     so these **per‑player averages are not trustworthy for trade splits**.
   - Specification:
     - Continue to compute **team games** from `MEGA_teams.csv` win/loss/tie counts.
     - For QB rating and similar rate stats, rely only on:
       - Volume fields (`passTotalAtt`, `passTotalComp`, `passTotalYds`, `passTotalTDs`, `passTotalInts`, `passTotalSacks`).
       - Ignore per‑player `passAvgYdsPerGame` and similar “Avg per game” fields where splitting is ambiguous.
3. **Consistency with `player_team_stints` (read‑only)**
   - After canonicalization, we **do not** need to re‑aggregate from `player_team_stints.csv` for team stats
     (to avoid redundant work).
   - However, we define a contract:
     - For any team T and stat type S (e.g., passing yards),
       the sum over `player_team_stints` rows for team T and S must approximately equal
       the aggregated value in `team_aggregated_stats.csv` (see invariants in 4.5).

### 4.4 Trade‑Aware Player Usage Aggregation

**Goal:** Ensure `output/team_player_usage.csv` respects trades by:
- Including only stat rows for players while they are on the given team (via team key).
- Providing correct multi‑team distributions and surfacing top targets/rushers by stint.

**Changes to `aggregate_player_usage.py`**

1. **Canonical team filtering**
   - Same `normalize_team_display` logic as `aggregate_team_stats.py`.
2. **Usage metrics remain stat‑row based**
   - For each team, compute:
     - `wr_target_share`, `te_target_share`, `rb_target_share`.
     - WR1/2/3, TE1, RB1/RB2, concentration metrics, and usage styles.
   - Since computations already operate on stat rows filtered by team, once canonicalization is applied,
     multi‑team players will contribute only where their stat rows say they played.
3. **Optional integration with `player_team_stints.csv` (non‑breaking)**
   - For future UI enhancements (not required to fix double counting now):
     - Expose additional columns in `team_player_usage.csv` referencing
       `player_team_stints` (e.g., `top_target_multi_team_flag`).
   - For this iteration, we keep `team_player_usage.csv` schema compatible and only fix team key handling.

### 4.5 Trade Validation & Invariants

**Goal:** Detect and prevent subtle double‑counting or mis‑attribution issues,
and provide a human‑reviewable list of traded players.

**New verification script**

- Add `scripts/verify_trade_stats.py`:
  - Inputs:
    - `MEGA_passing.csv`, `MEGA_rushing.csv`, `MEGA_receiving.csv`.
    - `output/team_aggregated_stats.csv`.
    - `output/player_team_stints.csv`.
  - Responsibilities:
    1. **Identify multi‑team players**
       - Group by `player__rosterId` and collect distinct `canonicalTeam`s.
       - Emit `output/traded_players_report.csv` with:
         - `player__rosterId`, `player__fullName`, list of teams, key volume stats per team.
    2. **Check team aggregation consistency**
       - For each team and each core offensive/defensive stat:
         - Sum player‑level values from `player_team_stints.csv`.
         - Compare to the corresponding value in `team_aggregated_stats.csv`.
         - Allow a small tolerance for rounding / missing edge cases; log discrepancies.
    3. **League‑wide sanity check**
       - Optionally compute league totals by summing:
         - `team_aggregated_stats` across all teams, and
         - `player_team_stints` across all teams.
       - Flag if they diverge beyond a small tolerance.

**Contracts**

- A player’s stat line for team T is only counted once for team T in all downstream aggregations.
- For a traded player:
  - The per‑team rows captured in `player_team_stints.csv` represent the authoritative split.
  - Team output CSVs must be consistent with these splits.

### 4.6 Future: Explicit Trade Metadata (`MEGA_trades.csv`)

**Not required for this iteration**, but we define the future shape:

- Extend `MEGA_trades.csv` to include:
  - `tradeId`
  - `player__rosterId`
  - `fromTeam`, `toTeam` (canonical display or team abbrevs)
  - `seasonIndex`, `weekIndex`
  - `details` (free text)
- Later integrations:
  - Join `player_team_stints.csv` with `MEGA_trades.csv` so each stint knows:
    - Whether it is pre‑trade or post‑trade.
  - Expose optional “pre‑trade vs post‑trade” metrics in:
    - Future dashboard CSVs (e.g., `team_trade_impacts.csv`).

## 5. Source Code Structure Changes

Planned changes (no code yet, design only):

- **New shared helpers (optionally a small module)**
  - Location: `stats_scripts/` (e.g., `stats_common.py`).
  - Functions:
    - `load_csv(path: Path) -> list[dict]`
    - `safe_float(value, default=0.0) -> float`
    - `normalize_team_display(name: str) -> str`
  - Existing scripts can import these instead of duplicating logic.

- **New script**
  - `stats_scripts/build_player_team_stints.py`
    - Generates `output/player_team_stints.csv`.

- **New verification script**
  - `scripts/verify_trade_stats.py`
    - Generates `output/traded_players_report.csv`.

- **Modified scripts**
  - `stats_scripts/aggregate_team_stats.py`
    - Use canonical team keys; avoid ambiguous per‑player per‑game averages where they conflict with trade splits.
  - `stats_scripts/aggregate_player_usage.py`
    - Use canonical team keys.
  - `stats_scripts/aggregate_rankings_stats.py`
    - Ensure joins are keyed by canonical team / team abbrev consistently.
  - `scripts/run_all_stats.py`
    - Optionally append:
      - `stats_scripts/build_player_team_stints.py`
      - `scripts/verify_trade_stats.py`
    - Or, at minimum, document these as separate follow‑up commands.

All changes are **additive or backward‑compatible** at the CSV schema level
(we only add new outputs and rely on existing output filenames for existing dashboards).

## 6. Data Model / Interface Contracts

### 6.1 Existing CSVs

- **Inputs** (`MEGA_*`, `mega_elo.csv`) remain unchanged.
- **Outputs**
  - `output/team_aggregated_stats.csv`
  - `output/team_player_usage.csv`
  - `output/team_rankings_stats.csv`
  - Remain structurally compatible; values become:
    - More complete (due to canonicalization).
    - Trade‑aware (no mis‑assignment of rows to “current team”).

### 6.2 New CSVs

- `output/player_team_stints.csv`
  - One row per `(seasonIndex, canonicalTeam, player__rosterId)`.
- `output/traded_players_report.csv`
  - Subset of `player_team_stints` for players with `multi_team_season = True`,
    plus convenience columns for human review.

These CSVs are read‑only from the perspective of existing dashboards
and can be adopted incrementally by new views.

## 7. Delivery Phases / Milestones

**Phase 1 – Canonicalization & Stint Summary**
- Implement `normalize_team_display` and update:
  - `aggregate_team_stats.py`
  - `aggregate_player_usage.py`
  - (and, as needed) `aggregate_rankings_stats.py`.
- Implement `build_player_team_stints.py` and generate `output/player_team_stints.csv`.
- Manually verify a few multi‑team players (e.g. Lamar Jackson, Baker Mayfield)
  using the new stints CSV.

**Phase 2 – Verification & Regression Safety Nets**
- Implement `scripts/verify_trade_stats.py`.
- Add invariants:
  - Team‑level sums from `player_team_stints` ≈ `team_aggregated_stats`.
  - League‑level sums consistent across inputs/outputs.
- Integrate verification into the recommended workflow:
  - e.g., document `python3 scripts/run_all_stats.py` followed by
    `python3 scripts/verify_trade_stats.py` in `README.md` and/or `spec` docs.

**Phase 3 – Optional Trade Metadata Integration (Future)**
- Define and populate `MEGA_trades.csv` outside this task.
- Extend `player_team_stints.csv` to reference `tradeId` and pre/post‑trade flags.
- Add optional CSVs and dashboard views focused on trade impacts.

## 8. Verification Approach

- **Core commands**
  - `python3 stats_scripts/aggregate_team_stats.py`
  - `python3 stats_scripts/aggregate_player_usage.py`
  - `python3 stats_scripts/aggregate_rankings_stats.py`
  - `python3 stats_scripts/build_player_team_stints.py`
  - `python3 scripts/verify_trade_stats.py`
  - Or end‑to‑end via `python3 scripts/run_all_stats.py` plus the new verification step.

- **Checks aligned with PRD success criteria**
  1. **No doubled production for traded players**
     - Use `verify_trade_stats.py` to confirm that for each multi‑team player,
       the sum of stint stats matches their representation in team outputs,
       and that league‑wide totals are stable.
  2. **Consistent team metrics across outputs**
     - Cross‑check `team_aggregated_stats.csv` with
       `output/team_rankings_stats.csv` for key offensive/defensive metrics.
  3. **Clear player‑centric view**
     - Inspect `output/player_team_stints.csv` for Lamar Jackson and Baker Mayfield,
       ensuring that each team stint is present and logically consistent.
  4. **Documentation hooks**
     - Later steps will update `spec/stats_team_aggregation.md`
       and `spec/stats_player_usage.md` to include trade rules and
       reference the new verification script.

