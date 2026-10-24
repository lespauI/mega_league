# Technical Spec: Matchup Gameplan Advisor

## Technical Context

- **Runtime / Stack**
  - Static HTML + vanilla JS, rendered in the browser.
  - `d3@7` loaded from CDN (same pattern as `docs/team_stats_explorer.html`, `docs/team_player_usage.html`, `docs/trade_dashboard.html`).
  - No bundler, no backend; all data comes from CSV files and is processed client‑side.
- **Primary Data Sources**
  - `output/team_rankings_stats.csv` – canonical per‑team row combining rankings, ELO, record, and many team metrics.
  - `output/team_aggregated_stats.csv` – detailed efficiency and rate stats for offense/defense (yards per play, turnover metrics, sack rates, explosive plays, etc.).
  - `output/team_player_usage.csv` – pass/rush distribution, usage concentration, and key player names (WR1/TE1/RB1/RB2 plus styles).
  - `MEGA_games.csv` – per‑game results used for recent‑form windows (v1.1).
- **Existing Conventions to Reuse**
  - CSV loading helper `tryCsv([...])` with multiple relative search paths.
  - Team logos via `logoId` → `https://cdn.neonsportz.com/teamlogos/256/${logoId}.png`.
  - Card/panel UI, `details`/`summary` panels, and responsive container styling from existing docs pages.

## Implementation Approach

### 1. Data Loading & Normalization

- Implement a `tryCsv` helper in the new page, identical in behavior to existing docs pages:
  - For each CSV, attempt `../output/...`, then `output/...`, then `/output/...` (and for MEGA CSVs: `../MEGA_*.csv`, `MEGA_*.csv`, `/MEGA_*.csv`).
  - Surface a friendly inline error message if a CSV fails to load, with guidance to run `python3 scripts/run_all_stats.py`.
- Load and normalize data into an in‑memory model:
  - Use `output/team_rankings_stats.csv` as the primary index; for each row, build a base `TeamProfile` keyed by `team` (canonical display name).
  - Left‑join:
    - `output/team_aggregated_stats.csv` on `team` to attach detailed offense/defense efficiency fields (e.g., `pass_yds_per_att`, `rush_yds_per_att`, `yds_per_play`, `td_per_play`, `turnover_diff`, `explosive_plays_per_game`, `def_sacks_per_game`, `pass_ints_per_game`, `sacks_allowed_per_game`).
    - `output/team_player_usage.csv` on `team` to attach usage/tendencies fields (e.g., `pass_distribution_style`, `rush_distribution_style`, `wr1_name`, `wr1_share`, `te1_name`, `rb1_name`, `rb1_share`, `rb2_name`, `rb2_share`, `top3_share`, `rbbc`).
  - Compute league‑level aggregates used for labeling strengths/weaknesses:
    - League mean/median and standard deviation for core offensive metrics (e.g., `pass_yds_per_att`, `rush_yds_per_att`, `yds_per_play`, `td_per_play`, `turnover_diff`, `explosive_plays_per_game`).
    - League mean/median for defensive impact metrics (e.g., `def_sacks_per_game`, `def_ints_per_game`, `ptsAgainstPg`, `defYdsPerPt` if available).
  - Store precomputed z‑scores/percentiles for each team/metric so matchup logic is simple and fast at interaction time.

### 2. Team Profile & Matchup Model

- Define an internal JS shape (not TypeScript, but consistent structure) for `TeamProfile`:
  - Identity/context: `name`, `conference`, `division`, `logoUrl`, `rank`, `eloIndex`, `win_pct`, `ptsForPg`, `ptsAgainstPg`.
  - Offense metrics (season‑long): `pass_yds_per_att`, `rush_yds_per_att`, `yds_per_play`, `td_per_play`, `turnover_diff`, `pass_ints_per_game`, `sacks_allowed_per_game`, `explosive_plays_per_game`, red‑zone proxy fields if available.
  - Defense metrics (season‑long): `def_sacks_per_game`, `def_ints_per_game`, `ptsAgainstPg`, yards‑per‑point allowed, total yards allowed per game, plus any existing defensive efficiency columns from `team_rankings_stats`.
  - Usage/tendencies: `pass_distribution_style`, `rush_distribution_style`, `wr1_name`, `wr1_share`, `wr2_name`, `wr3_name`, `top3_share`, `te1_name`, `rb1_name`, `rb1_share`, `rb2_name`, `rb2_share`, `rbbc`.
- Derive `MatchupViewModel` at selection time:
  - Given `myTeam` and `oppTeam` keys, produce:
    - Overview metrics for both teams.
    - A derived comparison block for:
      - `myOffense` vs `theirDefense`.
      - `myDefense` vs `theirOffense`.
      - Tendencies/usage for both sides.
    - A list of `Suggestion` objects (`{ category: 'Attack' | 'Protect' | 'Defend', severity: 'major' | 'moderate', text }`).

### 3. UI Layout & Interaction

- Create a new page `docs/matchup_gameplan.html` with:
  - Header: title, short explanation (“Select any two teams to generate a scouting report and suggested gameplan.”).
  - Controls:
    - `My Team` `<select>` populated with unique `team` values from rankings CSV, sorted alphabetically.
    - `Opponent Team` `<select>` with the same options.
    - Optional v1.1 toggle: radio buttons or a small dropdown for time window (`Full season`, `Last 4 games`).
  - Panels (using `details.panel > summary` + body pattern from other docs pages):
    - **Matchup Overview**:
      - Two side‑by‑side mini‑cards (“You” vs “Opponent”) showing logo, record, win%, overall rank, `eloIndex`, points for/against per game.
      - A simple “edge meter” or textual label derived from weighted differences in `eloIndex`, `win_pct`, and `netPtsPg`:
        - Map the numeric differential to “Major edge YOU/THEM”, “Slight edge YOU/THEM”, or “Even”.
    - **Your Offense vs Their Defense**:
      - Tabular or bullet comparison for:
        - Passing: `pass_yds_per_att` vs an opponent pass‑defense proxy (e.g., how far they are above/below league median in `ptsAgainstPg`, `defYdsPerPt`, or any pass‑defense specific columns present).
        - Rushing: `rush_yds_per_att` vs run‑defense proxy.
        - Explosiveness: `explosive_plays_per_game` vs league median and their defensive sacks/INT rates.
        - Turnovers: your `pass_ints_per_game` and `total_turnovers` vs their `def_ints_per_game` and `total_takeaways`.
      - Display strength/weakness badges for each axis based on combined z‑scores.
    - **Your Defense vs Their Offense**:
      - Symmetric layout focusing on:
        - Opponent passing and rushing efficiency vs your defensive counters (`def_sacks_per_game`, `def_ints_per_game`, `ptsAgainstPg`, explosive plays allowed proxies).
        - High‑level labels (e.g., “elite passing”, “below‑avg rushing”, “bend‑but‑don’t‑break red zone”).
    - **Tendencies & Usage**:
      - For each team, a compact summary:
        - Offense style chips: `pass_distribution_style`, `rush_distribution_style`.
        - Top threats: WR1/WR2/WR3 + TE1 names with target shares, RB1/RB2 with rush shares, and whether the backfield is `Bellcow` vs `RBBC`.
        - Short narrative lines (e.g., “They funnel 45% of targets to WR1”, “RBBC with two backs in the 30–40% range”).
    - **Suggested Gameplan Focus**:
      - 3–5 bullet items from the rule‑based suggestion engine (see below).
- Interaction behavior:
  - When either dropdown changes:
    - If both teams are selected, recompute and re‑render all sections.
    - If one or both are empty, show an empty state message instead of matchup metrics.
  - Keep all logic in a single `render()` function that:
    - Initializes the page.
    - Sets up event listeners.
    - Delegates to small helper functions (`buildOverview`, `buildOffenseVsDefense`, `buildDefenseVsOffense`, `buildTendencies`, `buildSuggestions`).

### 4. Rule‑Based Suggestions Engine

- Implement a pure JS function `computeSuggestions(myProfile, oppProfile, leagueStats)` that returns an array of suggestion objects.
- Core rule types:
  - **Attack Weaknesses**
    - If `(my.rush_yds_per_att - leagueMedian.rush_yds_per_att)` is strongly positive **and** opponent’s run‑defense proxy is significantly worse than median, add a “run‑focused attack” suggestion.
    - If `(my.pass_yds_per_att - leagueMedian.pass_yds_per_att)` is strongly positive **and** opponent is below average in INTs/sacks, add a “lean into deep/efficient passing” suggestion.
  - **Protect the Ball / QB**
    - If `my.pass_ints_per_game` is high and opponent `def_ints_per_game` is high, add a “protect the ball, avoid high‑risk throws” suggestion.
    - If `sacks_allowed_per_game` is high vs league and opponent `def_sacks_per_game` is high, add “protect the QB: quick game, max protect, rollouts”.
  - **Defensive Priorities**
    - If opponent passing efficiency is very high vs your pass‑defense proxies, add “prioritize coverage: limit explosive passes, disguise coverages”.
    - If opponent rushing efficiency is high and your rush defense is weak, add “sell out vs run on early downs”.
  - **Usage‑Driven Suggestions**
    - High `wr1_share` and `top3_share` with a single standout WR1 → “bracket WR1, force QB to progressions 2/3”.
    - Extreme TE usage → “respect TE up the seam / middle of field”.
    - RBBC vs bellcow → different run‑fit and sub‑package suggestions.
- Rule implementation details:
  - Use standardized thresholds: e.g., z‑score ≥ +1.0 as “major strength”, ≤ −1.0 as “major weakness”.
  - Each suggestion includes:
    - A short label (e.g., “Attack weak run defense”).
    - One sentence contextualizing numerical differences using formatted numbers (YPC deltas, turnover gaps).
    - A category (`Attack`, `Protect`, `Defend`) for grouping in the UI.

### 5. Recent Form / Momentum (v1.1)

- Optional, behind a small UI toggle:
  - When “Last 4 games” is active:
    - Filter `MEGA_games.csv` to games involving each selected team.
    - Take the most recent N games per team (based on `seasonIndex`, `weekIndex`, and/or `gameId` ordering).
    - Derive a simplified set of recent‑form metrics:
      - Recent win% (wins / games in window).
      - Average points for/against.
      - Net points per game.
    - Adjust overview section to show both season‑long and recent metrics, and flag when recent form is notably better/worse than season baseline (e.g., ±0.15 in win% or ±7 net points per game).
  - Initial version can limit recent‑form impact to the overview panel; later iterations could feed it into suggestions as well.

## Source Code Structure Changes

- **New page**
  - `docs/matchup_gameplan.html`
    - Self‑contained HTML + JS (no separate JS file, consistent with most existing docs).
    - Includes:
      - Shared base styles (container, panel, info blocks) adapted from `team_stats_explorer.html` / `team_player_usage.html`.
      - CSV loader, data normalization, and `render()` logic.
      - DOM nodes for team dropdowns, panels, and suggestion list.
- **Existing pages updated**
  - `docs/stats_dashboard.html`
    - Add a new `stat-card` in the grid linking to `matchup_gameplan.html`, with copy that emphasizes weekly matchup scouting and gameplan advice.
  - `index.html`
    - If it already links to the stats dashboards, add a simple text/link entry for “Matchup Gameplan Advisor”, or reuse the pattern used for other docs pages.
- **No changes** to:
  - Python aggregation scripts in `stats_scripts/` (all required metrics already exist or are derivable).
  - E2E Playwright test harness, at least in the first iteration.

## Data Model / Interface Details

- **Team Identity / Join Keys**
  - Use the `team` column (canonical display name) as the join key across all CSVs (`team_rankings_stats`, `team_aggregated_stats`, `team_player_usage`).
  - Preserve `conference` and `division` from rankings CSV for possible future filters (e.g., “show only AFC teams”).
- **League Statistics Helper**
  - Implement a small helper object `leagueStats` that:
    - Stores per‑metric `mean`, `median`, `stdDev`.
    - Provides helper functions like `strengthLabel(teamMetric, metricName)` → `{ label: 'Major Strength' | 'Moderate Strength' | 'Neutral' | 'Weakness', zScore }`.
- **DOM / Interaction Contract**
  - Expose stable IDs for testing and manual QA:
    - `#my-team-select`, `#opp-team-select`, `#matchup-overview`, `#offense-vs-defense`, `#defense-vs-offense`, `#tendencies`, `#suggestions`.
  - All re‑rendering should be idempotent: calling `renderMatchup()` with the same teams twice should clear and rebuild child nodes to avoid duplicate content.

## Delivery Phases

1. **Phase 1 – Data & Overview**
   - Implement CSV loading, `TeamProfile` normalization, and league aggregates.
   - Render the basic page skeleton, team dropdowns, and the Matchup Overview panel (win%, ELO, simple edge text).
   - Validate that all teams load correctly and basic comparisons are sane.
2. **Phase 2 – Matchup Panels & Tendencies**
   - Implement “Your Offense vs Their Defense” and “Your Defense vs Their Offense” sections using season‑long stats.
   - Implement the Tendencies/Usage panel based on `team_player_usage.csv`.
   - Add strength/weakness labels and visual badges based on league z‑scores.
3. **Phase 3 – Suggestions Engine**
   - Implement and tune the rule‑based `computeSuggestions` function.
   - Hook suggestions into the UI with grouped categories and clear wording.
   - Iterate on thresholds using a few known “interesting” matchups (e.g., extreme run teams vs weak run defenses).
4. **Phase 4 – Recent Form (Optional v1.1)**
   - Wire the recent‑form toggle, derive last‑N metrics from `MEGA_games.csv`, and surface them in the overview.
   - Optionally add a “Trending up / down” indicator where recent form significantly diverges from season averages.

## Verification Approach

- **Data Preconditions**
  - Ensure stats outputs are up to date:
    - `python3 scripts/run_all_stats.py` – regenerate all `output/*.csv`, including `team_aggregated_stats.csv`, `team_rankings_stats.csv`, and `team_player_usage.csv`.
  - Optionally run targeted verifiers (not required for this feature but useful for sanity):
    - `python3 scripts/verify_team_rosters_export.py`
    - `python3 scripts/verify_power_rankings_roster_csv.py`
- **Manual Functional Checks**
  - Open `docs/matchup_gameplan.html` via a static server (e.g., `python3 -m http.server`) and:
    - Confirm both dropdowns are populated with 32 teams.
    - Select several different matchups and verify:
      - Overview metrics (win%, ELO, record) match `team_rankings_stats.csv`.
      - Offense/defense metrics align directionally with known strong/weak teams.
      - Tendencies panel reflects player usage patterns from `team_player_usage.csv`.
      - Suggestion bullets are generated and reference actual statistical mismatches.
    - Check browser console for errors and verify all CSVs loaded successfully.
- **Automated Tests (where practical)**
  - Run Playwright E2E suite to ensure no regressions in existing tooling:
    - `npm install` (once, if not already installed).
    - `npm run test:e2e` – existing tests primarily cover the roster cap tool, but this ensures dependencies and environment remain healthy.
  - Future enhancement: add a minimal Playwright smoke test that:
    - Opens `docs/matchup_gameplan.html`.
    - Selects a known matchup via the dropdowns.
    - Asserts that suggestions and key sections render without errors.

