# Technical Specification: Roster-Based Power Rankings & Unit Strength Analysis

## Technical Context

- **Language**: Python 3 (>=3.10, matching existing scripts).
- **Runtime**: Command-line scripts invoked via `python3` from the project root.
- **Primary dependencies**: Standard library only, consistent with existing tools:
  - `argparse`, `csv`, `json`, `math`, `statistics`, `collections`, `dataclasses`, `typing`, `os`, `pathlib`, `hashlib`, `html`.
- **Data inputs** (existing in repo root):
  - `MEGA_players.csv` – player metadata, including `team`, `position`, `playerBestOvr`, `playerSchemeOvr`, `devTrait`, and detailed ratings.
  - `MEGA_teams.csv` – team metadata, including `teamId`, `displayName`, `nickName`, `teamName`, `abbrev`, `logoId`, conference/division fields, possibly a `rank` column.
- **Data outputs**:
  - CSV: `output/power_rankings_roster.csv`.
  - HTML: `docs/power_rankings_roster.html`.
  - Intermediate CSVs: `output/team_rosters/*.csv` and split O/D/ST variants.
- **Existing patterns to reuse**:
  - CSV reading, normalization, dev-trait handling, and per-team aggregation patterns from `scripts/generate_draft_class_analytics.py`.
  - HTML generation style (inline HTML + CSS classes, no external templating engine) from scripts like `scripts/playoff_race_table.py` and the existing page `docs/draft_class_2026.html`.
  - Documentation layout and navigation from `docs/rankings_explorer.html` and `docs/stats_dashboard.html`.


## Technical Implementation Brief

Implement a deterministic, CSV-driven pipeline that:

1. **Loads and normalizes roster data** from `MEGA_players.csv` and `MEGA_teams.csv` into typed Python structures.
2. **Exports per-team roster CSVs** (full roster, then split into offense/defense/special teams) to feed both debugging and future tooling.
3. **Computes unit scores** (Off Pass, Off Run, Def Coverage, Pass Rush, Run Defense, optional Special Teams) using position-aware rating weights and dev-trait multipliers that scale only for high-OVR dev players.
4. **Computes overall power scores and ranks** for each team based on configurable composite weights over unit scores.
5. **Writes a machine-readable CSV** summarizing all team scores, ranks, dev-trait distributions, and core configuration metadata.
6. **Renders a self-contained HTML report** that:
   - Reuses the visual style of the draft class analytics page (cards, typography, color scheme).
   - Provides sortable/searchable team lists.
   - Provides per-team cards with radar-style unit visualization and bar charts mirroring the feel of `rankings_explorer.html`.
   - Includes short, automatically generated textual narratives about strengths/weaknesses and key players.
7. **Exposes a CLI** (`scripts/power_rankings_roster.py`) with sensible defaults and options for overriding inputs and weights.

No new third-party dependencies are required. Complex logic (scoring, narrative generation) should live in pure functions to ease testing and reuse.


## Source Code Structure

New and modified files (focus for implementation):

- `scripts/power_rankings_roster.py`
  - Main CLI entry point.
  - Responsible for:
    - Parsing arguments.
    - Invoking the roster-export pipeline.
    - Invoking scoring and ranking functions.
    - Writing `output/power_rankings_roster.csv`.
    - Rendering `docs/power_rankings_roster.html`.
  - Should follow the structure used in `scripts/generate_draft_class_analytics.py`: helpers at top, `main(argv: list[str] | None)` + `if __name__ == "__main__":` guard.

- `scripts/power_rankings_roster_utils.py` (new helper module; optional but recommended)
  - Shared utilities to avoid bloating the main script:
    - CSV reading/writing helpers (wrapper around `csv.DictReader` and `csv.DictWriter`).
    - `safe_int`, `safe_float` style functions mirroring those in `generate_draft_class_analytics.py`.
    - Dev trait mapping constants and helpers.
    - Position normalization and unit assignment helpers.
    - Rating key selection for positions/units.
  - If a separate module is not desired, these helpers can live inside `power_rankings_roster.py`; the contracts below remain the same.

- `docs/power_rankings_roster.html`
  - Generated artifact; **not** hand-edited.
  - Follows patterns from `docs/draft_class_2026.html` and `docs/rankings_explorer.html`:
    - Top-level header and intro text.
    - Controls (search input, sort dropdowns, metric selector).
    - League overview section (league-average lines, quartile bands).
    - Team cards grid or table with mini charts.
  - Inline `<script>` and `<style>` blocks (or references to existing CSS if there’s a shared stylesheet) to remain self-contained.

- `output/team_rosters/` (directory, generated at runtime)
  - `output/team_rosters/<TEAM_ABBR>.csv` – full normalized roster.
  - `output/team_rosters/<TEAM_ABBR>_O.csv` – offensive starters/rotation.
  - `output/team_rosters/<TEAM_ABBR>_D.csv` – defensive starters/rotation.
  - `output/team_rosters/<TEAM_ABBR>_ST.csv` – special teams.

- `spec/power_rankings_roster.md` (optional future documentation)
  - If needed, a user-facing doc summarizing the methodology, linking to the generated HTML.

The implementation should avoid touching existing scripts unless a clear reuse/refactor is beneficial (e.g., copying known-good helpers) to minimize regression risk.


## Contracts

### Data contracts

**Players input row** (from `MEGA_players.csv`, as consumed by the pipeline):

- Required fields (must handle missing gracefully with warnings):
  - `id` (string/int, unique player ID).
  - `team` (team display name or abbrev; used to join with teams table).
  - `position` (e.g., `QB`, `HB`, `WR`, `TE`, `LT`, `MLB`, `CB`, `FS`, `SS`, `K`, `P`).
  - `playerBestOvr` (primary OVR; fallback to `playerSchemeOvr` if missing).
  - `devTrait` (categorical, expected in {'3', '2', '1', '0'} for X-Factor, Superstar, Star, Normal respectively; map unknowns to '0').
- Commonly used rating fields (must be read if present; missing values treated as sensible defaults like league average or 0):
  - **QB**: `throwAccShortRating`, `throwAccMidRating`, `throwAccDeepRating`, `throwPowerRating`, `throwUnderPressureRating`, `playActionRating`, `awareRating`, `speedRating`.
  - **RB**: `speedRating`, `accelRating`, `agilityRating`, `breakTackleRating`, `truckRating`, `jukeMoveRating`, `spinMoveRating`, `carryRating`, `bCVRating`.
  - **WR/TE**: `catchRating`, `cITRating`, `specCatchRating`, `routeRunShortRating`, `routeRunMedRating`, `routeRunDeepRating`, `releaseRating`, `speedRating`.
  - **OL**: `passBlockRating`, `passBlockPowerRating`, `passBlockFinesseRating`, `runBlockRating`, `runBlockPowerRating`, `runBlockFinesseRating`, `impactBlockRating`, `strengthRating`, `awareRating`.
  - **Front 7**: `powerMovesRating`, `finesseMovesRating`, `blockShedRating`, `pursuitRating`, `tackleRating`, `hitPowerRating`, `strengthRating`, `accelRating`.
  - **Coverage**: `manCoverageRating`, `zoneCoverageRating`, `pressRating`, `playRecRating`, `speedRating`, `changeOfDirectionRating`.

These match (or closely mirror) keys already referenced in `scripts/generate_draft_class_analytics.py`.

**Teams input row** (from `MEGA_teams.csv`):

- Required fields:
  - `teamId` (string/int) – internal ID.
  - `displayName` – primary display name (used in UI).
  - `nickName` / `teamName` – alternatives for logo mapping; used where present.
  - `abbrev` – used for short ID and file naming (`<TEAM_ABBR>.csv`).
  - `logoId` – numeric string for logo URL generation (if used).
- Optional fields (used when present):
  - `conferenceName`, `divisionName`, `rank` (existing overall rankings for context in the report, but not used in scoring).

**Exported team roster CSV** (`output/team_rosters/<TEAM_ABBR>.csv`):

- One row per player assigned to the team.
- Columns (explicitly defined):
  - `team_abbrev` (string, from `MEGA_teams.csv.abbrev`).
  - `team_name` (string, `displayName`).
  - `player_id` (from `id`).
  - `player_name` (best-effort full name, using fields like `fullName`, `cleanName`, `firstName` + `lastName`, mirroring draft analytics script).
  - `position` (raw position from players CSV).
  - `ovr` (int, normalized OVR used for scoring).
  - `dev` (string in {'3','2','1','0'}).
  - `normalized_pos` (internal normalized position class, e.g., `QB`, `RB`, `WR`, `TE`, `OL`, `DE`, `DT`, `LB`, `CB`, `S`, `K`, `P`).
  - Selected rating fields used in scoring (e.g., `throwAccShortRating`, `passBlockRating`, `runBlockRating`, etc.).

**Split roster CSVs** (`output/team_rosters/<TEAM_ABBR>_O.csv`, `_D.csv`, `_ST.csv`):

- Same schema as full roster CSV.
- Only players designated to that unit (starters + key rotational backups).
- Additional column `unit_role` (e.g., `starter`, `depth`, `specialist`) to make splits explicit.

**Power rankings CSV** (`output/power_rankings_roster.csv`):

- One row per team.
- Columns:
  - Identification:
    - `team_abbrev`, `team_name`, `conference`, `division`.
  - Overall scores & ranks:
    - `overall_score` (float, 0–100), `overall_rank` (1–32, 1 = best).
  - Unit scores & ranks:
    - `off_pass_score`, `off_pass_rank`.
    - `off_run_score`, `off_run_rank`.
    - `def_coverage_score`, `def_coverage_rank`.
    - `def_pass_rush_score`, `def_pass_rush_rank`.
    - `def_run_score`, `def_run_rank`.
    - Optionally: `st_score`, `st_rank` if special teams included.
  - Dev-trait composition:
    - `dev_xfactor_count`, `dev_superstar_count`, `dev_star_count`, `dev_normal_count`.
  - Roster context:
    - `avg_ovr`, `max_ovr` (team-wide).
  - Narrative fields (for quick text reuse in HTML):
    - `top_strengths` (short text or pipe-separated bullet labels).
    - `top_weaknesses`.
    - `key_players` (compact representation, e.g., `QB J. Allen (95 XF); LT T. Armstead (92 SS)`).
  - Configuration:
    - `config_hash` (short hash of weights/dev multipliers for reproducibility).
    - `weights_json` (optional text field with a compact JSON string or omitted for brevity).


### Functional contracts (Python interfaces)

The following are suggested function signatures; exact names can vary slightly as long as behavior is equivalent.

- `def read_players(path: str) -> list[dict]:`
  - Reads `MEGA_players.csv` and returns normalized dict rows.
  - Applies `safe_int`/`safe_float` on numeric fields and dev-trait normalization.
  - Logs warnings (to stderr) for missing required columns but does not crash.

- `def read_teams(path: str) -> list[dict]:`
  - Reads `MEGA_teams.csv` and returns normalized rows with `team_id`, `team_name`, `abbrev`, `logo_id`.

- `def build_team_index(teams: list[dict]) -> dict[str, dict]:`
  - Returns mapping from team key (prefer `abbrev`, fallback to normalized `displayName`) to team row.

- `def normalize_player_row(raw: dict, team_index: dict[str, dict]) -> dict:`
  - Produces the canonical internal player representation with fields noted above.
  - Resolves `team_abbrev` via `team_index`.

- `def export_team_rosters(players: list[dict], teams: list[dict], out_dir: str, *, split_units: bool = True) -> None:`
  - Groups players by team and writes full roster CSVs and, if `split_units`, `_O`, `_D`, `_ST` CSVs.
  - Implements starter selection heuristics from the PRD (position counts and OVR-based tie-breaking).
  - Prints summary to stdout (number of players per team, any teams with significant shortages at key positions).

- `def assign_unit(position: str) -> str:`
  - Returns one of `"O"`, `"D"`, `"ST"`, or `"?"` for unknown.
  - Uses normalized positions (e.g., OL, RB, WR → `"O"`; LB, CB, S, DE, DT → `"D"`; K, P → `"ST"`).

- `def score_unit(team_players: list[dict], unit: str, config: ScoringConfig) -> float:`
  - Computes a raw numeric score for a unit based on:
    - Weighted averages of relevant ratings per position group.
    - Positional importance weights (e.g., QB weight > WR/TE; OL weight high for both pass and run units).
    - Dev multipliers applied as multiplicative boosts, scaled by OVR band.
  - Returns an unnormalized raw score; separate function handles normalization across league.

- `def normalize_unit_scores(raw_scores: dict[str, float], method: str = "zscore") -> dict[str, float]:`
  - Accepts mapping `{team_abbrev: raw_score}`.
  - If `method == "zscore"`, maps to a 0–100 league distribution.
  - If `method == "minmax"`, rescales min→0, max→100.
  - Returns normalized scores in 0–100.

- `def compute_overall_score(units: dict[str, float], weights: dict[str, float]) -> float:`
  - Computes weighted sum of normalized unit scores.
  - Default weights per PRD: `off_pass=0.30`, `off_run=0.20`, `def_coverage=0.30`, `def_pass_rush=0.20`.
  - Run Defense can be optionally folded into the composite if enabled by config.

- `def generate_team_narrative(team_metrics: dict, league_context: dict) -> dict[str, str]:`
  - Input: per-team metrics (scores, ranks, dev counts) and league-level stats (league averages, quartiles).
  - Output:
    - `"strengths"`: human-readable sentences/bullets.
    - `"weaknesses"`: human-readable sentences/bullets.
    - Optionally `"summary"` string.
  - Logic highlights: best and worst units by percentile, standout players, and notable imbalances (e.g., elite OL + mediocre RB → “OL-driven rushing upside if RB room steps up”).

- `def write_power_rankings_csv(path: str, teams_metrics: list[dict]) -> None:`
  - Writes `output/power_rankings_roster.csv` with columns described above.

- `def render_html_report(path: str, teams_metrics: list[dict], config: dict, league_context: dict) -> None:`
  - Generates complete HTML report.
  - Uses inline JSON serialization (`<script id="data-json" type="application/json">…`) or JS arrays to drive charts and interactivity.
  - References or embeds CSS classes consistent with `docs/draft_class_2026.html`.

- `def main(argv: list[str] | None = None) -> int:`
  - CLI entry: parse args, orchestrate reading, scoring, CSV writing, and HTML rendering.


### CLI contract

New CLI: `python3 scripts/power_rankings_roster.py [options]`

- **Positional/required**:
  - None strictly required if defaults exist; otherwise:
    - `--players MEGA_players.csv` (default: `MEGA_players.csv`).
    - `--teams MEGA_teams.csv` (default: `MEGA_teams.csv`).

- **Options**:
  - `--players PATH` – path to players CSV.
  - `--teams PATH` – path to teams CSV.
  - `--out-csv PATH` – default `output/power_rankings_roster.csv`.
  - `--out-html PATH` – default `docs/power_rankings_roster.html`.
  - `--export-rosters` – if provided, export per-team roster CSVs (on by default; provide `--no-export-rosters` to skip if needed).
  - `--rosters-dir PATH` – default `output/team_rosters`.
  - `--include-st` – include special teams unit in calculation and output.
  - `--weights-json PATH_OR_INLINE` – JSON mapping for composite weights and/or unit-level attribute weights.
  - `--dev-multipliers-json PATH_OR_INLINE` – JSON mapping for dev multipliers by dev tier and OVR band.
  - `--normalization {zscore,minmax}` – choose normalization method.
  - `--no-clobber` – if target outputs exist, abort instead of overwrite.
  - `--verbose` / `-v` – more detailed console logs about missing data and scoring details.


## Delivery Phases

Define incremental, end-to-end-testable milestones.

### Phase 1 – Roster extraction & basic plumbing

- Implement:
  - `read_players`, `read_teams`, `build_team_index`, `normalize_player_row`.
  - `export_team_rosters` with full roster CSVs only (no unit splits yet).
  - Bare-bones CLI wiring to run the export.
- Deliverables:
  - `scripts/power_rankings_roster.py` capable of reading inputs and writing `output/team_rosters/<TEAM_ABBR>.csv`.
  - No unit scoring; no HTML yet.

### Phase 2 – Unit assignment, splits, and scoring

- Implement:
  - `assign_unit` and starter-selection heuristics.
  - Unit split exports: `_O`, `_D`, `_ST`.
  - `score_unit`, `normalize_unit_scores`, `compute_overall_score`.
  - Construction of per-team metrics + ranks.
- Deliverables:
  - Fully populated `output/power_rankings_roster.csv` with unit scores/ranks and overall scores/ranks.
  - Roster exports including unit splits, conforming to schema.

### Phase 3 – HTML report (basic)

- Implement:
  - `render_html_report` rendering:
    - A league table listing all teams with overall and unit scores.
    - Basic search (text filter) and sort controls (overall and by unit score).
    - Static bar charts or simple JS-driven charts for overall and at least one unit metric, visually aligned with `rankings_explorer.html`.
  - Minimal narratives: 1–2 simple sentences based on best/worst unit.
- Deliverables:
  - `docs/power_rankings_roster.html` generated and visually usable (even if not fully polished).

### Phase 4 – Advanced visualization & narratives

- Implement:
  - Radar/spider-style unit visualization (Off Pass, Off Run, Def Coverage, Pass Rush, Run Defense) per team.
  - Dev-trait composition indicators (chips/badges; counts of XF/SS/Star/Normal).
  - Richer narratives using multiple heuristics (outliers, balance, heavy dev concentration in certain units).
  - Methodology/config panel detailing weights, normalization, and dev multipliers.
- Deliverables:
  - Enhanced `docs/power_rankings_roster.html` whose UX and style are on par with draft class analysis and rankings explorer experiences.


## Verification Strategy

The verification strategy should rely on **repeatable commands** and, where necessary, **helper scripts** and **MCP servers** that make CSV/HTML inspection easier for an automated coding agent.

### Common verification commands

- Base generation (default paths):
  - `python3 scripts/power_rankings_roster.py --players MEGA_players.csv --teams MEGA_teams.csv`
- Custom output paths (smoke check):
  - `python3 scripts/power_rankings_roster.py --players MEGA_players.csv --teams MEGA_teams.csv --out-csv output/test_power_rankings.csv --out-html docs/test_power_rankings.html`

These should complete without errors and print a short summary of what was generated.


### Phase-by-phase verification

**Phase 1 – Roster extraction**

- Steps for coding agent:
  1. Run the base generation command.
  2. Confirm that `output/team_rosters/` exists and contains exactly one CSV per team in `MEGA_teams.csv` (by `abbrev`).
     - Use a command like `ls output/team_rosters` and `wc -l output/team_rosters/*.csv`.
  3. Inspect a small sample file to ensure schema matches contract (e.g., `head -n 5 output/team_rosters/BUF.csv`).
- Helper script to create (early in implementation):
  - `scripts/verify_power_rosters_basic.py`:
    - Reads `MEGA_teams.csv` and counts teams.
    - Compares against the number of `output/team_rosters/*.csv` files.
    - Verifies a minimal set of columns is present (`team_abbrev`, `player_id`, `position`, `ovr`, `dev`).
    - Exits with non-zero code on mismatch, printing helpful diagnostics.

**Phase 2 – Unit scoring**

- Steps for coding agent:
  1. Re-run the CLI with default inputs.
  2. Confirm `output/power_rankings_roster.csv` exists and has 32 rows (or number of teams in inputs) plus header.
     - Use `wc -l output/power_rankings_roster.csv`.
  3. Inspect a sample row and verify presence of all score and rank columns.
  4. Confirm ranks are a permutation of `1..N` with no duplicates for each of the rank columns.
- Helper script to create:
  - `scripts/verify_power_rankings_roster_csv.py`:
    - Loads `output/power_rankings_roster.csv`.
    - Checks expected header columns.
    - Validates numeric ranges (0–100) for score columns.
    - Ensures ranks are unique and within 1..N.
    - Optionally, spot-checks normalization: max score approximately 100, min close to 0.

**Phase 3 – HTML report (basic)**

- Steps for coding agent:
  1. Re-run CLI ensuring HTML generation is enabled.
  2. Confirm `docs/power_rankings_roster.html` exists and is non-trivially sized (e.g., `> 10 KB`).
  3. Grep the file to ensure that:
     - All team names appear at least once.
     - Key CSS classes used in other docs pages (e.g., those visible in `docs/draft_class_2026.html`) also appear.
     - Essential UI elements (search input, metric dropdown) are present.
- Helper script to create:
  - `scripts/verify_power_rankings_roster_html.py`:
    - Opens the HTML file and checks for presence of specific markers:
      - `<table` or card container for teams.
      - JS data blob or JSON with team metrics.
      - Basic controls (e.g., an element with id or class for search).
    - Optionally, parse with `html.parser` or `BeautifulSoup` *if* such a dependency is acceptable; otherwise, use simple string checks.

**Phase 4 – Visualizations & narratives**

- Steps for coding agent:
  1. Generate HTML after full feature implementation.
  2. Confirm that each team card includes:
     - A radar/spider representation (e.g., a `<canvas>` or SVG with 5-unit axes) or a reasonable visual equivalent.
     - Dev-trait composition indicators (XF/SS/Star/Normal counts) for the team.
     - Text segments corresponding to strengths/weaknesses.
  3. Optionally, compare a few teams with obvious roster strengths (e.g., teams with many X-Factors and high OL ratings) to ensure ranks qualitatively make sense.
- Helper script to create:
  - Extend `scripts/verify_power_rankings_roster_html.py` or add a new mode:
    - Ensures that each team in CSV has a corresponding HTML section or card.
    - Validates that narrative text blocks are present and non-empty for each team.


### MCP servers for verification

To make verification easier for an automated agent, the following MCP servers are recommended:

- **Filesystem MCP** (or equivalent):
  - For reading/writing generated CSV and HTML artifacts.
  - Enables structured inspection of `output/` and `docs/` directories.

- **Shell/Terminal MCP**:
  - To run `python3` commands, `ls`, `wc`, `head`, and verification scripts.
  - Essential for end-to-end CLI invocation.

- **Python evaluation MCP** (optional but useful):
  - To run ad-hoc Python snippets for inspecting CSV contents, checking distributions, and verifying scoring logic in isolation.

- **CSV analysis MCP** (optional):
  - Provides higher-level operations on CSV files (filter, aggregate, compute correlations) to cross-check that unit/overall scores correlate sensibly with OVR and dev-trait counts.

These servers complement the project’s own verification scripts and allow a coding agent to perform rich validations without modifying the core code.


### Sample input artifacts

- **Real league data (preferred)**:
  - `MEGA_players.csv` and `MEGA_teams.csv` in the repo root.
  - Used for primary verification; must be present and up to date.

- **Synthetic mini-datasets (for fast tests)**:
  - The coding agent may generate small CSVs (e.g., 4 teams, 5–10 players each) to validate edge cases:
    - Extremely top-heavy dev distributions.
    - Teams missing key positions (no true LT, only generic `OL`).
    - Teams with low-OVR dev players to ensure multipliers are negligible.
  - These synthetic inputs can live under `fixtures/` or `.zenflow/tasks/.../fixtures/` and be used in targeted verification commands.

- **Online discovery**:
  - Not required; all core verification can use local MEGA CSVs or generated fixtures.

Where sample inputs are generated, the spec expects the coding agent to include small helper generators (simple Python scripts under `scripts/` or the task artifacts directory) so that these fixtures can be recreated deterministically.

