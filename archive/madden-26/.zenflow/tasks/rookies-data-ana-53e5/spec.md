# Technical Specification: Draft Class 2026 Analytics HTML

## Technical Context
- Language: Python 3.8+ (standard library only)
- Runtime: CLI script invoked via `python3`
- Primary inputs:
  - `MEGA_players.csv` (Neon export)
  - `MEGA_teams.csv` (Neon export, optional; used for logo mapping)
- Primary output:
  - `docs/draft_class_<YEAR>.html` (e.g., `docs/draft_class_2026.html`)
- Static assets:
  - Team logos via Neon Sports CDN: `https://cdn.neonsportz.com/teamlogos/256/<logoId>.png`
- Existing code to leverage: `scripts/generate_draft_class_analytics.py`

## Technical Implementation Brief
- Reuse and harden `scripts/generate_draft_class_analytics.py` to generate an analytics-focused HTML page for a specified draft year (2026 initially).
- Rookie selection: filter rows where `rookieYear == <YEAR>` from `MEGA_players.csv`.
- Player snapshot fields: name, team, position, overall (OVR), development trait (devTrait). Dev masking in UI: dev 3/2/1 => Hidden, 0 => Normal. Keep raw values for analytics.
- OVR computation: prefer `playerBestOvr`; fallback to `playerSchemeOvr`; default 0 if missing/invalid.
- Hidden spotlight: display only X-Factor and Superstar rookies (dev in {3,2}) as cards, but mask tier as “Hidden”; sort deterministically (OVR desc, then name); include draft round/pick appended to OVR line.
- Team analytics: aggregate per current team (from players CSV) with counts, average OVR, best OVR, and masked dev distribution (Hidden/Normal); sort by avg OVR desc, then team name; table is client-side sortable by any header.
- Position analytics: aggregate per position with counts, average OVR, and masked dev distribution; sort by avg OVR desc, count desc, pos name; client-side sortable.
- KPIs: totals, average OVR, counts of Hidden and Normal, Hidden share (Hidden/total as percentage).
- Round Hidden: compute per-team counts of Hidden rookies by draft round (from `draftRound` in `MEGA_players.csv`), render as compact sortable table/graphic.
- Team logos: build a map from `MEGA_teams.csv` using `displayName`, `nickName`, `teamName` -> `logoId`. If `MEGA_teams.csv` missing, skip logos gracefully.
- Output HTML: self-contained document with improved CSS and a tiny inline JS for client-side sorting; ensure all template placeholders are resolved.
- CLI parameters:
  - `--year <int>` (required)
  - `--players <path>` default `MEGA_players.csv`
  - `--teams <path>` default `MEGA_teams.csv`
  - `--out <path>` default `docs/draft_class_<YEAR>.html`
- Robustness: tolerate missing/empty fields, unknown devTrait values (treat as `0`), missing teams (render as `FA`).
  - Round/pick derivation uses `draftRound` and `draftPick` fields if present; omit gracefully if missing.

## Source Code Structure
- `scripts/generate_draft_class_analytics.py`
  - `read_csv(path) -> list[dict]`: CSV reader returning list of dict rows.
  - `safe_int(v, default=None) -> Optional[int]`: parse-to-int helper.
  - `build_team_logo_map(teams_rows) -> dict[str,str]`: map team name variants to logoId.
  - `gather_rookies(players, year) -> list[dict]`: filter and normalize rookies rows with fields: `id, name, team, position, ovr, dev`.
  - `compute_analytics(rows) -> dict`: aggregates: totals, average OVR, dev counts, per-team stats, per-position stats.
  - `badge_for_dev(dev) -> str`: HTML badge for dev tier.
  - `generate_html(year, rows, analytics, team_logo_map) -> str`: build full HTML string using inline CSS and placeholders.
  - `main()`: CLI arg parsing, file IO, generation, and printing summary.
- Helper scripts to be added for verification (see Verification Strategy):
  - `scripts/verify_draft_class_analytics.py`
  - `scripts/smoke/smoke_generate_draft_2026.sh`

## Contracts
- Data contracts (inputs):
- `MEGA_players.csv` must contain the following headers (present in Neon exports):
  - `rookieYear`, `playerBestOvr`, `playerSchemeOvr`, `devTrait`, `position`, `team`
  - Player name fields: at least one of `fullName`, `cleanName`, or both `firstName`/`lastName`.
  - For spotlight and round distribution (optional but used when present): `draftRound`, `draftPick`.
  - `MEGA_teams.csv` (optional) headers used:
    - `logoId`, and any of `displayName`, `nickName`, `teamName` for mapping.
- Dev trait mapping:
  - Raw: `3` => `X-Factor`, `2` => `Superstar`, `1` => `Star`, `0` (or unknown) => `Normal`.
  - Masked in UI: `3/2/1` => `Hidden`, `0` => `Normal`.
- CLI interface (script contract):
  - Invocation: `python3 scripts/generate_draft_class_analytics.py --year <YYYY> [--players P] [--teams T] [--out OUT]`
  - Output path must be creatable; parent directory is created if missing.
- Output HTML contract:
  - Contains KPIs, Hidden spotlight cards (dev 3/2 masked), Round Hidden section, team table, Most Hiddens leaderboard, position table, Hidden-heavy positions list.
  - No unresolved placeholders of form `__PLACEHOLDER__` remain in final HTML.
  - Logos appear when `logoId` is resolvable via teams file.
  - Tables have centered headers/cells and support client-side sorting by header click.

## Delivery Phases
1. Baseline generation (MVP)
   - Ensure script generates `docs/draft_class_2026.html` from current `MEGA_players.csv` and `MEGA_teams.csv`.
   - Validate rookie filter, OVR fallback, dev mapping, and basic aggregates.
2. Verification helpers
   - Add `scripts/verify_draft_class_analytics.py` to compute expected totals from CSV and assert presence in HTML.
   - Add `scripts/smoke/smoke_generate_draft_2026.sh` to run end-to-end generation + verification.
3. Resilience and UX polish
   - Improve error messages for missing files/columns and add exit codes.
   - Add `--league-prefix` override or auto-detection (optional) if non-MEGA files are used in other environments.
   - Document usage in `README.md` (new section for Draft Class Analytics).
4. Optional analytics extensions
   - Flags to filter view (e.g., `--min-dev 1`), or output JSON summary alongside HTML.
   - Add small bar chart for Round Hidden if desired beyond the sortable table.

## Verification Strategy
- Built-in validation commands (no external deps):
  - Generate for 2026:
    - `python3 scripts/generate_draft_class_analytics.py --year 2026 --players MEGA_players.csv --teams MEGA_teams.csv --out docs/draft_class_2026.html`
  - Quick checks:
    - `test -s docs/draft_class_2026.html`
    - `rg -n "Draft Class 2026 — Analytics Report" docs/draft_class_2026.html`
    - Ensure no unresolved placeholders:
      - `! rg -n "__[A-Z_]+__" docs/draft_class_2026.html`
  - Sanity compare counts vs CSV (shell one-liners):
    - Rookies in CSV: `python3 - << 'PY'\nimport csv;import sys;rows=[r for r in csv.DictReader(open('MEGA_players.csv',newline='',encoding='utf-8')) if str(r.get('rookieYear'))=='2026'];print(len(rows))\nPY`
    - Compare to HTML KPI Total: `rg -o "<b>Total rookies</b><span>(\\d+)" -r "$1" -N docs/draft_class_2026.html`
    - Dev counts (XF/SS/Star/Normal): use the helper verifier below for robust checks.
  - Presence of Round Hidden section and sort hooks:
    - `rg -n "Round Hidden" docs/draft_class_2026.html`
    - `rg -n "data-sort" docs/draft_class_2026.html`

- Helper scripts to add (Phase 2):
  - `scripts/verify_draft_class_analytics.py`:
    - Reads `MEGA_players.csv` and recomputes:
      - total rookies `rookieYear==<YEAR>`
      - counts for `devTrait` in {3,2,1,0}
      - average OVR (best, fallback scheme)
    - Parses generated HTML and asserts:
      - KPI values (Total, Avg OVR, Hidden, Normal, Hidden share) match recomputed values (with small float tolerance for Avg and percent).
      - No placeholders remain.
      - If teams file present, at least one `<img class="logo"` exists.
      - Hidden Spotlight cards include round/pick when available.
    - Exit non-zero and print diffs when mismatches occur.
  - `scripts/smoke/smoke_generate_draft_2026.sh`:
    - Runs generation for 2026 and then `verify_draft_class_analytics.py 2026`.
    - Returns non-zero on failure; prints locations of outputs.

- MCP servers recommended for agent verification:
  - Filesystem MCP (read/write paths, list files) — to validate artifacts exist and inspect outputs.
  - Shell/Process MCP (run commands) — to execute Python scripts and shell checks end-to-end.
  - HTTP/Fetch MCP (optional) — to probe a few Neon logo URLs for 200 status if network is available.
  - Git MCP (optional) — to diff and stage changes in a review workflow.

- Sample input artifacts:
  - `MEGA_players.csv` and `MEGA_teams.csv` are already present in the repo (provided by user export). No additional fixtures required.
  - If running in a different league context: user must provide corresponding `*_players.csv` and `*_teams.csv` (must be provided by the user; agent cannot discover online reliably).

---

Notes on potential bug surfaces to check/fix during implementation:
- Robust name derivation: prefer `fullName`, then `cleanName`, then `firstName + lastName` with whitespace-trim handling.
- Team name mismatches between players and teams (e.g., `team` vs `displayName`): logo mapping should consider `displayName`, `nickName`, and `teamName` variants; fall back gracefully when not found.
- Numeric parsing: guard against empty strings in OVR/dev fields; default dev outside {0,1,2,3} to `0`.
- Sorting ties: ensure deterministic sorting using secondary keys (e.g., team name on equal averages).
