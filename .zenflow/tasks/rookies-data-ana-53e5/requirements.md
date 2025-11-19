# Feature Specification: Draft Class 2026 Analytics Page

## User Stories*

### User Story 1 - Generate draft class analytics
**Acceptance Scenarios**:
1. Given MEGA_players.csv and MEGA_teams.csv are present in the project root, When I run `python3 scripts/generate_draft_class_analytics.py --year 2026`, Then an HTML file is generated at `docs/draft_class_2026.html` containing KPIs, an elites spotlight, and team/position analytics.
2. Given a different output path is provided, When I run with `--out <path>`, Then the HTML is saved at the specified path and has the same contents/structure.

### User Story 2 - Review elite rookies (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Elites Spotlight” section, Then I see rookies with dev traits 3 (X-Factor) and 2 (Superstar) only, each showing name, team, position, overall rating, and a dev badge.
2. Given the “Elites Spotlight” section, When I scan the cards, Then the list is sorted by dev (X-Factor above Superstar), then by higher OVR, then by name.

### User Story 3 - Compare team draft outcomes (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Team draft quality — by Avg OVR” table, Then I see for each team the total rookie count, average OVR, best OVR, and counts of each dev tier (XF/SS/Star/Normal) sorted by higher Avg OVR.
2. Given the generated page is open, When I view the “Most hiddens (XF+SS+S) — by team” table, Then teams are ranked by total hiddens (XF + SS + Star) and I can see each team’s hidden count, total rookies, and average OVR.

### User Story 4 - Evaluate positional strength (manager)
**Acceptance Scenarios**:
1. Given the generated page is open, When I view the “Position strength” table, Then I see for each position the total rookies, average OVR, and counts of dev tiers (XF/SS/Star/Normal), sorted by higher Avg OVR and then by total.
2. Given the generated page is open, When I view the “Elite-heavy positions” list, Then I see up to 6 positions with the most elites (XF + SS), breaking ties by Star count and then position code.

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
  - KPIs: total rookies, average OVR, counts of X-Factors, Superstars, Stars, and the elite share (XF+SS count and percentage).
  - Elites Spotlight: grid of rookies with dev 3 or 2; show name, team, position, OVR, and a badge for dev tier; sorted by dev desc, OVR desc, name asc; include team logo if available.
  - Team Analytics: table sorted by avg OVR desc then team name; columns include Team (with logo if available), # rookies, Avg OVR, Best OVR, XF, SS, Star, Normal.
  - Most Hiddens: table ranking teams by (XF + SS + Star) desc; includes Team, Hiddens, #, Avg OVR; clarifies this is based on current roster team field.
  - Position Analytics: table sorted by avg OVR desc, then total desc; columns include Pos, Total, Avg OVR, XF, SS, Star, Normal.
  - Elite-heavy Positions: list of up to 6 positions with the most elites (XF + SS), tie-broken by Star count then position code.
  - Styling: lightweight, responsive grid layout, inline CSS; clear badges for dev tiers; basic accessibility (alt text for logos, readable contrasts).

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
  - Elites Spotlight shows only XF and SS rookies and is correctly sorted (dev desc → OVR desc → name asc).
  - Tables are readable on desktop and reasonably usable on smaller screens.
  - The page loads without external JS or CSS dependencies.

- Robustness
  - If `MEGA_teams.csv` is absent or lacks `logoId`, the page still renders (logos omitted).
  - If some rookies lack fields (e.g., missing name/position/team), safe fallbacks render without breaking layout.

---

Top Clarifications (please confirm):
1. Output location: keep default `docs/draft_class_<year>.html` and link from `index.html`, or standalone? [NEEDS CLARIFICATION]
2. Branding: should page title/branding use a configurable league name instead of “MEGA League”? [NEEDS CLARIFICATION]
3. Interactivity: is a static page sufficient, or do you want basic client-side sorting/filtering? (Current scope: static) [NEEDS CLARIFICATION]
4. Data fields: confirm `playerBestOvr` then `playerSchemeOvr` fallback is correct for OVR; any preference to exclude `FA` rookies from team tables? [NEEDS CLARIFICATION]
5. Additional metrics: include draft metadata (round/pick from `MEGA_draft.csv`) or keep out of scope for this iteration? [NEEDS CLARIFICATION]

