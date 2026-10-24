# Feature Specification: Season 2 Strength of Schedule (SoS) Calculation and Visualization


## User Stories*


### User Story 1 - Compute SoS for each team in Season 2

**Acceptance Scenarios**:

1. **Given** the combined `_games` CSV and the `mega_elo` ratings, **When** the SoS job runs for Season 2, **Then** it builds and stores each team’s Season 2 schedule using rows starting at 287 and onward.
2. **Given** the Season 2 schedules are built, **When** the SoS computation runs with the configured ELO snapshot and weighting, **Then** each team receives a SoS value and rank, persisted as artifacts for downstream use.

---

### User Story 2 - Explore league-wide SoS table

**Acceptance Scenarios**:

1. **Given** SoS results exist, **When** a user opens the SoS view, **Then** they see a sortable table of all teams with columns for Team, Games, Avg Opponent ELO, SoS Index, +/- vs League Avg, and Rank.
2. **Given** the SoS table is displayed, **When** the user filters by Division or Conference (same controls as Playoff Chances), **Then** the table updates to show matching teams and preserves sort state.

---

### User Story 3 - Visualize SoS by Division and Conference

**Acceptance Scenarios**:

1. **Given** SoS results exist, **When** a user switches to Division or Conference view, **Then** they see the SoS visualization matching last season’s SoS graphic style (e.g., ranked bars per team) for the selected grouping.
2. **Given** the visualization is displayed, **When** the user hovers or taps on a team, **Then** a tooltip shows the team’s SoS details (SoS Index, Avg Opp ELO, games) and the team is highlighted.

---

## Requirements*

- Scope
  - Calculate SoS for all teams for Season 2 only, using the combined `_games` CSV where Season 2 begins at row 287 (inclusive).
  - Persist per-team Season 2 schedules and per-team SoS outputs for reuse by UI and analytics.

- Inputs
  - `_games` CSV containing both prior season and Season 2 games.
    - Season 2 rows start at 287 (inclusive) in the combined file.
    - Required columns (min): date, home_team, away_team, conference/division (or joinable via team metadata), game_id (if available).
  - `mega_elo` dataset with current opponent ratings.
    - A single snapshot is used for pre-season SoS unless a rolling mode is explicitly enabled (see Configuration).

- Processing
  - Build Season 2 schedules: for each team, parse all Season 2 games (rows >=287) and generate the ordered list of opponents with home/away flags and dates.
  - Join ELO: enrich each scheduled game with the opponent’s `mega_elo` rating from the configured snapshot.
  - Compute SoS per team (default decisions):
    - Base metric: average of opponents’ ELO across all scheduled games for Season 2.
    - Weight: each game counts equally (1 per game). Double-headers count as separate games if present in `_games`.
    - Home/away: no home-field adjustment by default; a configurable adjustment can be enabled later.
    - Normalization: compute league-average opponent ELO and report a “SoS +/– vs Avg” (team Avg Opp ELO minus league average). Also compute a standardized SoS Index (e.g., z-score scaled to mean 100, sd 15) for ranking and charting.
    - Rank: rank teams by hardest schedule (highest Avg Opp ELO or highest SoS Index).
  - Aggregations
    - Division and Conference views: provide the same team-level SoS metrics scoped and filterable by division and conference, mirroring Playoff Chances controls.

- Outputs
  - Data artifacts
    - Stored per-team schedules for Season 2.
    - Per-team SoS results including: team_id, games, Avg Opponent ELO, SoS Index, +/- vs league avg, rank, conference, division.
    - Export formats: JSON and CSV for downstream consumption.
  - UI: SoS Table
    - Sortable by all visible columns (Team, Games, Avg Opp ELO, SoS Index, +/- vs Avg, Rank).
    - Filters: Conference and Division, consistent with Playoff Chances UX (same controls/placement).
  - UI: SoS Graphics
    - League-wide and group (Division/Conference) bar charts matching last season’s SoS style (colors, fonts, labeling) with tooltips and highlighting.

- Configuration
  - `season_number`: integer (default 2).
  - `games_csv_path`: path to `_games` CSV.
  - `season2_start_row`: integer (default 287; inclusive).
  - `mega_elo_path`: path to ratings snapshot.
  - `sos.include_home_advantage`: boolean (default false). If true, apply a configurable HFA offset.
  - `sos.hfa_elo_points`: integer (default 0). Positive values make away games harder, home games easier.
  - `sos.index.scale`: choose between `zscore-mean100-sd15` (default) or `none`.

- Non‑functional
  - Deterministic, idempotent runs with the same inputs/config yield identical outputs.
  - Runtime completes within typical CI/CD job time for the dataset size (minutes, not hours).
  - Clear logging: number of teams processed, games per team, any missing ELO joins, final ranks.
  - Backward-compatible: does not alter last season’s artifacts; Season 2 outputs stored separately.

- Assumptions (informed defaults to enable progress)
  - Row 287 is the first Season 2 data row (header not counted as a data row).
  - Use a single `mega_elo` snapshot taken at (or designated as) Season 2 start for all opponents.
  - No home/away adjustment initially; can be toggled later via config if desired.
  - Division and conference metadata is available via `_games` or a joinable teams reference.
  - Visual style mirrors last season’s SoS assets; component structure aligns with existing Playoff Chances filters.

## Success Criteria*

- Data completeness and correctness
  - 100% of teams have Season 2 schedules built from `_games` rows >=287.
  - 99%+ of scheduled opponent games resolve to a `mega_elo` rating (with any misses logged and reported).
  - League average and per-team SoS metrics compute without errors and produce a stable rank order.

- UX behavior
  - SoS table loads within 2 seconds on typical hardware and supports sorting on all columns.
  - Conference/Division filters mirror Playoff Chances behavior and preserve sort state.
  - Charts render with last season’s SoS style; tooltips show Team, Avg Opp ELO, SoS Index, +/- vs Avg.

- Operability
  - A single command or CI job parameter runs the SoS pipeline for Season 2 and writes outputs to distinct artifacts.
  - Logs clearly identify inputs, configuration, counts, and any data-quality warnings.
  - Re-running with the same inputs produces identical artifacts (hash-stable).

