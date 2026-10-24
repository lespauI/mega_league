# PRD: Matchup Gameplan Advisor

## 1. Context and Goals

The project already provides:
- Playoff race simulations and strength of schedule analysis.
- Draft pick race and power rankings.
- Team-level stat explorers, cross-metric correlations, and win% analysis.
- Trade-aware stats, player usage breakdowns, and a roster/cap scenario tool.

All of these tools are excellent for league-wide analysis, roster planning, and long-term strategy. What is missing is a **matchup-focused, gameplan-oriented view**: a way to answer the question:

> “Given my next opponent, how should I gameplan this week using all the stats we’ve already computed?”

This PRD defines a new feature: a **Matchup Gameplan Advisor** that turns the existing CSV outputs into **actionable, opponent-specific scouting reports and gameplan suggestions**.

Primary goals:
- Help a user quickly understand **where they have edges or weaknesses** versus a specific opponent.
- Translate raw stats into **concrete strategic levers** (e.g., “lean into deep passing”, “protect the ball”, “force them into 3rd-and-long”).
- Re-use existing CSV outputs (team stats, rankings, usage, schedules) rather than adding new data sources.

Assumptions:
- We continue working with season-level and game-level aggregates (not play-by-play).
- Upcoming or hypothetical matchups can be selected via team dropdowns (no need to model a full week schedule UI initially).
- Existing CSVs such as `output/team_aggregated_stats.csv`, `output/team_player_usage.csv`, `output/team_rankings_stats.csv`, `MEGA_games.csv`, and `MEGA_rankings.csv` are available and up to date.

## 2. Target Users

- **League Commissioners / Owners**
  - Want competitive but balanced games and tools that drive smarter decision-making in the league.
- **Team GMs / Coaches (human users of the league)**
  - Need a quick, visual way to scout an opponent and plan their weekly strategy.
- **Content Creators / Streamers**
  - Want narrative-ready material (“strength vs strength showdown”, “can this offense exploit that weak run defense?”).

## 3. User Stories with Acceptance Scenarios

### Story 1: Quick Matchup Overview

As a GM/coach,  
I want to select my team and an opponent  
so that I can instantly see a high-level summary of the matchup.

**Acceptance Criteria (Given/When/Then):**
- Given that team stats CSVs are generated and available,  
  When I open the Matchup Gameplan Advisor page,  
  Then I see two dropdowns (My Team, Opponent Team) populated with all 32 team names.

- Given that I have selected both a “My Team” and “Opponent Team”,  
  When the matchup loads,  
  Then I see a **summary panel** showing:
  - Win% for both teams.
  - Offensive and defensive efficiency ranks (overall).
  - A simple “edge meter” or text summary (e.g., “Overall edge: Slight advantage to YOU / THEM / Even”).

- Given that no team is selected in one of the dropdowns,  
  When I attempt to view the matchup,  
  Then I see an inline message prompting me to choose both teams, and no matchup metrics are shown yet.

### Story 2: Offensive vs Defensive Strengths and Weaknesses

As a GM/coach,  
I want to see how my offense matches up against the opponent’s defense  
so that I can identify where to attack and what to avoid.

**Acceptance Criteria:**
- Given that I have selected My Team and Opponent Team,  
  When the matchup is displayed,  
  Then I see a section titled **“Your Offense vs Their Defense”** with:
  - Key offensive metrics for my team (e.g., pass_yds_per_att, rush_yds_per_att, yds_per_play, red_zone_td_pct, turnover_rate).
  - Key defensive metrics for the opponent (e.g., pass_yds_allowed_per_att, rush_yds_allowed_per_att, yds_per_play_allowed, red_zone_td_allowed_pct, takeaways_per_game).
  - A clear visual comparison for at least:
    - **Passing efficiency vs pass defense.**
    - **Rushing efficiency vs run defense.**
    - **Turnover tendencies (giveaways vs takeaways).**

- Given that metric definitions exist in `output/team_aggregated_stats.csv` / `output/team_rankings_stats.csv`,  
  When the matchup loads,  
  Then offensive and defensive values are pulled directly from those CSVs (no manual input required).

### Story 3: Defensive Gameplan View

As a GM/coach,  
I want to see how my defense matches up against the opponent’s offense  
so that I can understand what I need to stop.

**Acceptance Criteria:**
- Given a selected matchup,  
  When I scroll or navigate to **“Your Defense vs Their Offense”**,  
  Then I see:
  - Opponent offensive strengths (e.g., strong passing, elite rushing, explosive plays per game).
  - My defensive counters (e.g., sack rate, rush yards allowed per attempt, INT rate).

- Given that the existing CSVs already encode various offensive and defensive metrics,  
  When the feature computes matchup text,  
  Then it uses thresholds or league medians to label things as **“Strength”, “Weakness”, or “Neutral”** for each side.

### Story 4: Usage & Tendencies Insights

As a GM/coach,  
I want to understand how concentrated or spread my opponent’s offense is  
so that I can tailor matchups (e.g., double a WR1 or focus on RBBC).

**Acceptance Criteria:**
- Given `output/team_player_usage.csv` exists,  
  When I view a matchup,  
  Then I see a **Tendencies/Usage** section that includes:
  - Opponent pass_distribution_style and rush_distribution_style.
  - Names of their top receiving threats (WR1/WR2/TE1) and primary backs (RB1/RB2), where available.
  - A concise text summary such as:
    - “They funnel targets to WR1 (45% share).”
    - “RBBC backfield with two backs in the 30–40% range.”

- Given this tendencies panel,  
  When I view my own team in the same matchup,  
  Then I also see the same style/tendencies summary for my offense, to compare philosophies.

### Story 5: Suggested Strategic Focus Areas

As a GM/coach,  
I want the tool to suggest 3–5 clear strategic focus points  
so that I can turn stats into actionable gameplan ideas.

**Acceptance Criteria:**
- Given both teams and all relevant CSVs are available,  
  When the matchup is displayed,  
  Then I see a **“Suggested Gameplan Focus”** list with 3–5 bullet items such as:
  - “Attack their weak run defense: you are +0.8 YPC vs league average, they allow +0.5 YPC.”
  - “Avoid high-risk passing: you throw INTs at a top-5 rate, and they generate above-average takeaways.”
  - “Lean into play-action/deep shots if explosive passes are a relative strength.”

- Given large gaps in one metric (e.g., big difference in turnover differential, sack rate, explosive plays),  
  When the suggestions are generated,  
  Then at least one bullet calls out each **major mismatch**.

### Story 6: Recent Form / Momentum (Optional v1.1)

As a GM/coach,  
I want to see how both teams have performed in the last N games  
so that I can understand momentum instead of just season-long stats.

**Acceptance Criteria:**
- Given that `MEGA_games.csv` includes per-game results and team identifiers,  
  When I toggle a **“Last 4 Games”** or similar filter,  
  Then key metrics (e.g., win%, points for/against, yards per play) update to reflect only that window.

- Given this recent-form view,  
  When either team has notably outperformed their season averages,  
  Then the UI highlights them as “trending up” or “trending down” in relevant areas.

## 4. Functional Requirements

### 4.1 Data Inputs

- The feature SHALL re-use existing CSV outputs:
  - `output/team_aggregated_stats.csv` for core team efficiency and counting stats.
  - `output/team_player_usage.csv` for usage concentration, positional splits, and key player names.
  - `output/team_rankings_stats.csv` and/or `MEGA_rankings.csv` for rankings and ELO-type ratings.
  - `MEGA_games.csv` for win/loss records and (optionally) recent form windows.
- The feature SHALL NOT require manual data entry or external APIs.

### 4.2 Matchup Selection and State

- The UI SHALL provide:
  - A “My Team” dropdown.
  - An “Opponent Team” dropdown.
- The UI MAY default “My Team” to a commonly-used team or first alphabetically.
- The feature SHALL display a clear empty state when either dropdown is unselected.
- The feature SHALL update all panels when either selection changes.

### 4.3 Metrics and Comparisons

- For **each team** in the matchup, the tool SHALL compute or display:
  - Overall win%.
  - Points scored/allowed per game (if available).
  - Offensive metrics: pass yards/attempt, rush yards/attempt, yards/play, red zone TD%, turnover rate, explosive plays per game (where available).
  - Defensive metrics: same categories but against.
  - Turnover differential and sack rates (offense and defense).
- The tool SHALL compute **relative differences** (team vs opponent and vs league median/average if available).
- The tool SHALL label strong/weak areas with at least:
  - Strength categories: “Major Strength”, “Moderate Strength”, “Neutral”, “Weakness”.
  - Visual cues (e.g., colored badges or arrows).

### 4.4 Usage & Tendencies Panel

- The tool SHALL summarize offensive usage for **both teams** using `team_player_usage.csv`:
  - Pass/rush distribution style labels.
  - Target concentration (e.g., WR1 share, top3_share).
  - RB usage style (Bellcow vs RBBC).
- Where player names are available, the tool SHALL surface key names (WR1, TE1, RB1) alongside usage stats.
- If data is missing for a particular team, the tool SHALL display a graceful fallback message (e.g., “Usage data not available for this team”).

### 4.5 Suggestions Engine

- The feature SHALL implement a simple **rule-based suggestion engine** (initially, no ML is required) that:
  - Reads mismatches in key metrics (e.g., +X delta in YPC vs YPC allowed, turnover differential gaps, sack rate gaps).
  - Converts these mismatches into human-readable recommendations.
- Recommendations SHALL be phrased in **action-oriented language**, ideally grouped under 2–3 headings such as “Attack”, “Protect”, “Defend”.
- The engine SHALL produce at least 3 suggestions per matchup when sufficient data exists.

### 4.6 Presentation and UX

- The feature SHALL be exposed as an HTML page under `docs/` (e.g., `docs/matchup_gameplan.html`) and linked from `index.html` or `docs/stats_dashboard.html`.
- The layout SHOULD align visually with existing dashboards:
  - Light, card-based UI.
  - Responsive (desktop first, but not broken on mobile).
  - Clear section headers: Overview, Offense vs Defense, Defense vs Offense, Tendencies, Suggestions.
- Performance:
  - All data SHOULD load from static CSV and JS (no backend required).
  - Initial load time SHOULD be comparable to existing dashboards.

## 5. Non-Functional Requirements

- **Performance:**  
  - Page load (including CSV loading and initial render) SHOULD complete within ~2 seconds in a typical browser when hosted via GitHub Pages or similar static hosting.

- **Maintainability:**  
  - The feature SHOULD reuse existing CSV parsing utilities and chart/DOM helpers where possible (e.g., shared JS utilities in `docs` or `scripts` already used by dashboards).
  - Configuration (e.g., which metrics to highlight) SHOULD be data-driven where feasible so that new metrics can be added without major code changes.

- **Robustness:**  
  - The UI SHOULD handle missing or partial data gracefully and surface clear messages instead of breaking.
  - If a CSV fails to load, a non-blocking error notice SHOULD be displayed with guidance (e.g., “Run `python3 scripts/run_all_stats.py` to regenerate stats.”).

## 6. Success Criteria

The Matchup Gameplan Advisor is considered successful if:

1. **Usability**
   - Users can select any two teams and see a coherent scouting report without reading raw CSVs.
   - GMs/coaches report (informally) that the tool helps them make at least one concrete strategic adjustment per week.

2. **Adoption**
   - The feature is linked from the main `index.html` or stats dashboard and becomes part of the regular pre-game workflow for at least some users in the league.

3. **Data Reuse**
   - The tool leverages **existing CSV outputs** (team stats, rankings, usage) without introducing fragile or one-off data pipelines.

4. **Expansion Potential**
   - The design leaves clear hooks for future enhancements, such as:
     - Toggling recent-form windows (last 4/6 games).
     - Visual matchup “heatmaps” across all teams in a given week.
     - More advanced suggestion rules or ML-based recommendations.

If these criteria are met, this feature will turn the rich statistical backbone of the project into a highly practical, matchup-level decision aid for users.

