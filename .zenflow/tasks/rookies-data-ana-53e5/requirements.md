# Feature Specification: Draft Class 2026 Analytics Page

## User Stories*

### User Story 1 - Generate draft class analytics
**Acceptance Scenarios**:
1. Given MEGA_players.csv and MEGA_teams.csv are present in the project root, When I run `python3 scripts/generate_draft_class_analytics.py --year 2026`, Then an HTML file is generated at `docs/draft_class_2026.html` containing KPIs, a Hidden spotlight, Round Hidden graphic, and team/position analytics.
2. Given a different output path is provided, When I run with `--out <path>`, Then the HTML is saved at the specified path and has the same contents/structure.

### User Story 2 - Review hidden elites (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Hidden Spotlight” section, Then I see rookies with dev traits 3 (X-Factor) and 2 (Superstar) only, each showing name, team, position, overall rating, and draft round/pick appended; dev tiers are masked in UI as “Hidden”.
2. Given the “Hidden Spotlight” section, When I scan the cards, Then the list is sorted by higher OVR and name deterministically within masked tier, and cards include logo if available.

### User Story 3 - Compare team draft outcomes (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Team draft quality — by Avg OVR” table, Then I see for each team the total rookie count, average OVR, best OVR, and counts of Hidden/Normal (Hidden = dev 1/2/3), sorted by higher Avg OVR, with centered headers/cells.
2. Given the generated page is open, When I view the “Most Hiddens — by team” table, Then teams are ranked by total Hiddens (dev 1/2/3) and I can see each team’s Hidden count, total rookies, and average OVR; I can sort by any column via header click.

### User Story 4 - Evaluate positional strength (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Position strength” table, Then I see for each position the total rookies, average OVR, and counts of Hidden/Normal, sorted by higher Avg OVR and then by total; I can sort by each column; layout is centralized.
2. Given the generated page is open, When I view the “Hidden-heavy positions” list, Then I see up to 6 positions with the most Hidden (dev > 0), breaking ties by position code.

### User Story 5 - Round Hidden distribution (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Round Hidden” section, Then I see a visual/table summary per team and round showing how many Hidden players were selected in each round for the class year.
2. Given the “Round Hidden” section, When I sort by a column, Then the ordering updates client-side without page reload.

---

## Requirements*

- Scope
  - Generate a static, self-contained HTML page that summarizes analytics for the 2026 draft class (rookieYear = 2026) from CSV data.
  - Focus on position, team, overall rating, and development trait mapping where 3 = X-Factor, 2 = Superstar, 1 = Star, 0 = Normal.
  - Primary audience is league managers seeking quick evaluation of the draft class quality and distribution.

- Data Sources
  - Players: `MEGA_players.csv` (filter by `rookieYear == 2026`).
  - Teams (optional, for logos): `MEGA_teams.csv`, mapping `displayName`/`nickName`/`teamName` to `logoId` for Neon logos.
  - Fields and fallbacks:
    - Overall: prefer `playerBestOvr`; fallback to `playerSchemeOvr` if missing; default 0 if both missing.
    - Name: prefer `fullName`, else `cleanName`, else `firstName` + `lastName`.
    - Team: use `team`; default `FA` if missing.
    - Position: use `position`; default `?` if missing.
    - Dev trait: `devTrait` with mapping {3: X-Factor, 2: Superstar, 1: Star, 0: Normal}. Non-mapped values treated as 0.

- Analytics and Presentation
  - KPIs: total rookies, average OVR, counts of Hidden and Normal, and Hidden share (Hidden / total).
  - Hidden Spotlight: grid of rookies with dev 3 or 2; show name, team, position, OVR, draft round/pick; dev tier masked as “Hidden”; deterministic sort.
  - Team Analytics: table sorted by avg OVR desc then team name; columns include Team (logo if available), # rookies, Avg OVR, Best OVR, Hidden, Normal; centered header/cells, sortable by any column.
  - Round Hidden: distribution of Hidden picks by round per team (class year scope), presented as a compact sortable table or graphic.
  - Most Hiddens: table ranking teams by Hidden count (dev 1/2/3) desc; includes Team, Hiddens, #, Avg OVR; clarifies this is based on current roster team field.
  - Position Analytics: table sorted by avg OVR desc, then total desc; columns include Pos, Total, Avg OVR, Hidden, Normal; sortable columns.
  - Hidden-heavy Positions: list of up to 6 positions with the most Hidden (dev > 0).
  - Styling: improved but simple, responsive layout with inline CSS; masked dev badges; basic accessibility (alt text for logos, readable contrasts).

- CLI & Automation
  - Script supports arguments: `--year`, `--players`, `--teams`, `--out`.
  - Default output path when `--out` is not provided: `docs/draft_class_<year>.html`.
  - Script prints a final summary: output path, rookies total, average OVR.

- Resilience & Data Quality
  - Gracefully handle missing files/columns and empty datasets; still generate a valid page with placeholders and zeroed metrics.
  - Ignore rows where overall cannot be parsed (treat as 0) and keep them in counts unless they fail rookieYear filter.
  - Robust conversion for numeric fields; treat invalid devTrait as 0.
  - Do not fail if team logos are missing; omit image.

- Performance & Compatibility
  - Pure Python 3.7+; standard library only; process typical Neon exports within seconds.
  - Output is a single static file compatible with GitHub Pages.

- Branding & Navigation
  - Page title: “Draft Class <year> — Analytics — MEGA League”.
  - [NEEDS CLARIFICATION: Should “MEGA League” be configurable for other leagues or kept as-is?]
  - [NEEDS CLARIFICATION: Should we add a backlink to `index.html` or main reports navigation?]

## Success Criteria*

- Functionality
  - Running `python3 scripts/generate_draft_class_analytics.py --year 2026` generates `docs/draft_class_2026.html` without errors.
  - The page contains: KPIs, Elites Spotlight, Team draft quality table, Most hiddens table, Position strength table, Elite-heavy positions list.
  - Dev trait labels and badge colors reflect the mapping (3=X-Factor, 2=Superstar, 1=Star, 0=Normal).

- Data Correctness
  - Rookie filtering uses `rookieYear == 2026`.
  - Overall rating is derived from `playerBestOvr` with `playerSchemeOvr` fallback.
  - Counts and averages in KPIs, team, and position sections match the computed set of rookies.
  - Teams and positions are correctly aggregated; logos appear where `logoId` exists and team name matches.

- UX & Presentation
  - Hidden Spotlight shows only dev 3/2 rookies (masked) and is correctly sorted deterministically; cards include draft round/pick.
  - Tables have centered headers/cells and support client-side sorting via header clicks (lightweight inline JS only).
  - The page loads without external CSS dependencies; includes a tiny inline JS sorter.

- Robustness
  - If `MEGA_teams.csv` is absent or lacks `logoId`, the page still renders (logos omitted).
  - If some rookies lack fields (e.g., missing name/position/team), safe fallbacks render without breaking layout.

---

Top Clarifications (please confirm):
1. Output location: keep default `docs/draft_class_<year>.html` and link from `index.html`, or standalone? [NEEDS CLARIFICATION]
2. Branding: should page title/branding use a configurable league name instead of “MEGA League”? [NEEDS CLARIFICATION]
3. FA handling: exclude `FA` rookies from team tables or include under `FA` bucket? [NEEDS CLARIFICATION]
4. Round Hidden visualization: prefer compact sortable table (current) or add a small bar chart? [NEEDS CLARIFICATION]
