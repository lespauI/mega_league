# Technical Specification: Season 2 Strength of Schedule (SoS) — ELO-Based

## Technical Context
- Language: Python 3.10+ (uses only standard library for data processing).
- Frontend: Static HTML with D3.js v7 (already used in `docs/sos_graphs.html`).
- Primary inputs in repo root:
  - `MEGA_games.csv` — combined seasons game schedule/results. Season 2 begins at row 287 (1-based, inclusive) per PRD.
  - `mega_elo.csv` — preseason ELO snapshot per team (semicolon-delimited; decimal comma to be normalized).
  - `MEGA_teams.csv` — team metadata (conference/division, logoId, displayName/teamName etc.).
- Outputs: written under `output/` (consistent with repo):
  - `output/schedules/season2/all_schedules.json` — per-team Season 2 schedules (home/away, opponents, dates).
  - `output/sos/season2_elo.csv` — league-wide ELO SoS table (sortable schema defined below).
  - `output/sos/season2_elo.json` — same content as JSON for UI.
- Config: script CLI flags with sane defaults per PRD:
  - `--season-number 2`, `--games-csv MEGA_games.csv`, `--season2-start-row 287`, `--elo-csv mega_elo.csv`, `--teams-csv MEGA_teams.csv`.
  - `--include-home-advantage false`, `--hfa-elo-points 0`.
  - `--index-scale zscore-mean100-sd15`.

## Technical Implementation Brief
- Create a new script `scripts/calc_sos_season2_elo.py` that:
  - Slices `MEGA_games.csv` starting at row `season2_start_row` (inclusive) to construct Season 2 schedules.
  - Builds per-team ordered schedule entries: `[{opponent, homeAway, date, gameId}]` (date from `scheduled_date_time` if present, else synthesize from `(seasonIndex, stageIndex, weekIndex)`), including both home and away games.
  - Parses `mega_elo.csv` (semicolon-delimited, decimal commas) into `Team -> ELO` mapping; whitespace trimmed; validates all 32 teams present.
  - Enriches each scheduled game with opponent ELO; computes for each team:
    - `games`: count of Season 2 games in the slice.
    - `avg_opp_elo`: arithmetic mean of opponent ELO across Season 2 games (each game weight = 1).
    - `league_avg_opp_elo`: league-wide average of `avg_opp_elo` across teams.
    - `plus_minus_vs_avg`: `avg_opp_elo - league_avg_opp_elo`.
    - `sos_index`: standardized index for charting: z-score of `avg_opp_elo` rescaled to mean 100, sd 15 (configurable; or raw if `none`).
    - `rank`: 1..N (hardest first, highest `avg_opp_elo`/`sos_index`).
    - `conference`, `division` from `MEGA_teams.csv` via `displayName`/`teamName` key matching.
  - Writes per-team schedules to `output/schedules/season2/all_schedules.json` and per-team files `output/schedules/season2/<Team>.json`.
  - Writes ELO SoS outputs to `output/sos/season2_elo.csv` and `output/sos/season2_elo.json`.
- Add optional HFA adjustment: if enabled, add/subtract `hfa_elo_points` from opponent ELO for home/away respectively before averaging.
- Frontend deliverables (new, static):
  - `docs/sos_season2_table.html` — sortable table with filters for Conference/Division (mirrors Playoff Chances controls), loads `output/sos/season2_elo.csv` and `MEGA_teams.csv` for logos.
  - `docs/sos_season2_bars.html` — bar charts by league, conference, and division using `season2_elo.csv`; look-and-feel matches last season SoS graphics (colors, fonts, tooltips, hover highlight). Structure mirrors `docs/sos_graphs.html` components and styling variables.

## Source Code Structure
- New script:
  - `scripts/calc_sos_season2_elo.py`
    - `read_games_season2(games_csv_path, start_row)` → list[dict] for rows >= `start_row`.
    - `build_schedules(games)` → dict[str team] -> list[ScheduleEntry].
    - `read_elo_map(elo_csv_path)` → dict[str team] -> float elo.
    - `read_team_meta(teams_csv_path)` → dict[str team] -> {conference, division, logoId}.
    - `compute_sos_elo(schedules, elo_map, team_meta, include_hfa, hfa_pts, scale_mode)` → list[SoSRow].
    - `write_schedules_json(schedules, out_dir)`; `write_outputs(rows, out_csv, out_json)`.
    - CLI `main()` parsing args and orchestrating calls.
- New verification helper:
  - `scripts/verify_sos_season2_elo.py` — checks counts, numeric ranges, rank consistency, cross-validates team coverage, and prints summary by conference/division.
- New docs:
  - `docs/sos_season2_table.html` — sortable table; filter controls; consistent styling with existing `docs/playoff_race.html` and `docs/sos_graphs.html`.
  - `docs/sos_season2_bars.html` — stacked/clustered bars per group; tooltip includes Team, Games, Avg Opp ELO, +/- vs Avg, Rank.

## Contracts
- Input contracts:
  - `MEGA_games.csv` (existing): expects columns `homeTeam, awayTeam, gameId, scheduled_date_time, seasonIndex, stageIndex, weekIndex` present; season 2 rows are taken from line `season2_start_row` to EOF.
  - `mega_elo.csv` (existing): semicolon-delimited with headers like `#;Team;START;;`. Contract for parser:
    - Column `Team` maps to `MEGA_teams.displayName`/`teamName`.
    - Column `START` parsed as float after replacing `,` with `.` and stripping spaces.
  - `MEGA_teams.csv` (existing): uses `displayName` or `teamName` as matching key; provides `conferenceName`, `divName`, `logoId`.
- Output contracts:
  - `output/schedules/season2/all_schedules.json`
    - `{ [team: string]: { team: string, conference: string, division: string, games: number, schedule: [{ opponent: string, homeAway: "H"|"A", date: string|null, gameId: string|number|null, oppElo: number|null }] } }`.
  - `output/sos/season2_elo.csv` and `.json` — rows with fields:
    - `team` (string), `games` (int), `avg_opp_elo` (float), `league_avg_opp_elo` (float), `plus_minus_vs_avg` (float), `sos_index` (float), `rank` (int), `conference` (string), `division` (string)
    - Optional: `logoId` (string|int) for UI convenience.
- CLI contract (script):
  - `python3 scripts/calc_sos_season2_elo.py [--games-csv PATH] [--teams-csv PATH] [--elo-csv PATH] [--season2-start-row N] [--include-home-advantage true|false] [--hfa-elo-points N] [--index-scale zscore-mean100-sd15|none] [--out-dir output]`.
- Frontend data loading contract:
  - `docs/sos_season2_table.html` and `docs/sos_season2_bars.html` load from relative paths: `../output/sos/season2_elo.csv` fallback to `output/sos/season2_elo.csv` (same loader helper pattern as `docs/sos_graphs.html`).

## Delivery Phases
1) Phase 1 — Schedule Builder (Season 2 slice)
   - Implement `read_games_season2` and `build_schedules` with `--season2-start-row` default 287.
   - Deliver `output/schedules/season2/all_schedules.json` and per-team JSONs.

2) Phase 2 — ELO SoS Computation
   - Implement `read_elo_map`, `read_team_meta`, `compute_sos_elo`, `write_outputs`.
   - Produce `output/sos/season2_elo.csv` and `output/sos/season2_elo.json` with complete schema and ranks.

3) Phase 3 — SoS Table UI
   - Add `docs/sos_season2_table.html`: sortable columns (Team, Games, Avg Opp ELO, +/- vs Avg, SoS Index, Rank), filter by Conference and Division (same controls as Playoff Chances), sticky header.
   - Wire logos via `MEGA_teams.csv.logoId` (use CDN `https://cdn.neonsportz.com/teamlogos/256/{logoId}.png` when present).

4) Phase 4 — SoS Graphics UI
   - Add `docs/sos_season2_bars.html`:
     - League view: bars by team sorted by `avg_opp_elo` (or `sos_index`).
     - Conference view: separate panels for AFC/NFC.
     - Division view: grid of 8 panels (one per division), sorted within each.
     - Tooltips: Team, Games, Avg Opp ELO, +/- vs Avg, Rank.
     - Hover highlight and consistent color system with last season (from `docs/sos_graphs.html`).

## Verification Strategy
- Common pre-requisites:
  - From repo root: `python3 --version` must be 3.10+.
  - No third-party Python deps required. D3 is loaded via CDN in HTML.

- Phase 1 verification (Schedule Builder):
  - Command: `python3 scripts/calc_sos_season2_elo.py --dry-run --season2-start-row 287 --out-dir output` (dry-run prints summary, still writes schedules).
  - Checks:
    - `output/schedules/season2/all_schedules.json` exists and includes keys for all teams found in `MEGA_teams.csv` (at least 32).
    - For a sample team (e.g., `Broncos`), the number of schedule entries equals the number of appearances in `MEGA_games.csv` rows >= 287.
  - Helper (new): `python3 scripts/verify_sos_season2_elo.py --check schedules` prints per-team game counts and flags mismatches.

- Phase 2 verification (ELO SoS):
  - Command: `python3 scripts/calc_sos_season2_elo.py --season2-start-row 287`.
  - Checks:
    - `output/sos/season2_elo.csv` and `.json` exist with required columns.
    - `rank` is a strict 1..N ordering by `avg_opp_elo` desc and ties are handled deterministically.
    - `league_avg_opp_elo` is identical for all rows and equals the mean of `avg_opp_elo` across teams.
    - `plus_minus_vs_avg` mean is ~0 (tolerance 1e-9).
  - Helper: `python3 scripts/verify_sos_season2_elo.py --check sos` asserts the above and prints top/bottom 5.

- Phase 3 verification (Table UI):
  - Serve: `python3 -m http.server 8000` and open `http://localhost:8000/docs/sos_season2_table.html` (agent can verify HTML loads and console has no 404s).
  - Checks:
    - Table populates with 32 rows and supports sorting by each column (verify by clicking header; visually check order changes; or via console `document.querySelectorAll('tbody tr').length`).
    - Conference/Division filters reduce row counts appropriately (compare to `MEGA_teams.csv` grouping).

- Phase 4 verification (Graphics UI):
  - Open `http://localhost:8000/docs/sos_season2_bars.html`.
  - Checks:
    - Bars render without JS errors; tooltips appear on hover; order reflects `rank` per view.
    - Switching views (league/conference/division) updates correctly and maintains styling consistent with `docs/sos_graphs.html`.

- MCP servers to assist verification:
  - `filesystem` — browse/read generated artifacts for structural checks.
  - `bash`/`process` — execute scripts and simple assertions (already available in CLI harness).
  - `http-server` (local) — serve static files for UI verification (`python3 -m http.server`).
  - `csv-inspector` (optional) — if available, to assert schemas and column types; otherwise covered by `verify_sos_season2_elo.py`.

- Helper scripts to generate in Phase 1:
  - `scripts/verify_sos_season2_elo.py`:
    - `--check schedules`: validates all teams present; counts of appearances per team in games slice match schedule length.
    - `--check sos`: validates schema, rank ordering, averages consistency, and prints summaries by conference/division.

- Sample input artifacts for verification:
  - `MEGA_games.csv` (in repo) — used directly; contains both seasons; Season 2 slice begins at row 287 (provided by user).
  - `mega_elo.csv` (in repo) — used directly; provides opponent ELO; parser handles semicolons/decimal commas.
  - `MEGA_teams.csv` (in repo) — used directly for conference/division and logos.

