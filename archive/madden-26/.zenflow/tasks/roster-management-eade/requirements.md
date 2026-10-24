# Feature Specification: Madden Roster Cap Management Tool

## User Stories*

### User Story 1 - Switch Teams and View Cap Summary
As a user, I can select any NFL team and immediately see a persistent cap summary panel showing original cap, current cap, cap spent, cap space, and gain/loss from my actions.

**Acceptance Scenarios**:
1. Given the dashboard is loaded, When I pick a team from the Team Selector, Then the Cap Summary updates to that team’s `capRoom`, `capSpent`, and `capAvailable` with a progress bar for `capSpent / capRoom`.
2. Given I switch between multiple teams, When I return to a previously viewed team in the same session, Then the last computed cap values for that team persist until I reset or reload the session.

---

### User Story 2 - Manage Active Roster with Real-Time Cap Impact
As a user, I can release or trade a player from the Active Roster and see real-time cap impact before confirming.

**Acceptance Scenarios**:
1. Given a player row in Active Roster, When I choose Action → Release, Then a confirmation modal shows Dead Cap Hit (`capReleasePenalty`), Cap Savings (`capReleaseNetSavings`), and New Cap Space (`capAvailable + capReleaseNetSavings`).
2. Given I confirm Release, When the action completes, Then the player is removed from the Active Roster, the team’s `capSpent` and `capAvailable` update, and the Cap Summary reflects a net Gain/Loss indicator.

---

### User Story 3 - Simulate Trades
As a user, I can simulate a trade to see dead money impact and update the roster accordingly.

**Acceptance Scenarios**:
1. Given a player row, When I choose Action → Trade → Quick Simulate, Then the player is removed from the team and the full `capReleasePenalty` is applied immediately to cap figures (using provided dataset values) and the Cap Summary updates.
2. Given I open Action → Trade → Custom Trade (Phase 2), When I construct a trade with outgoing player/picks and incoming player/picks, Then I can see cap impacts for each team and validate that both teams remain under the cap before “Apply Simulation”.

---

### User Story 4 - Sign Free Agents with Offer Builder
As a user, I can make offers to free agents and preview Year 1 cap hit and remaining cap before confirming.

**Acceptance Scenarios**:
1. Given a free agent row, When I click Make Offer, Then an offer modal pre-fills Years (`desiredLength`), Annual Salary (`desiredSalary`), and Signing Bonus (`desiredBonus`) and shows Year 1 Cap Hit = Salary + (Bonus ÷ min(Years, 5)).
2. Given the offer is below 90% of the desired terms, When I attempt to confirm, Then I see a warning and the accept action is blocked unless I confirm override (configurable) or improve the offer to meet the rule.
3. Given `capAvailable < Year1CapHit`, When I try to confirm signing, Then the action is blocked with an error message explaining insufficient cap space.
4. Given the offer is accepted, When I confirm, Then the player moves to the Active Roster, `isFreeAgent` becomes false, `capSpent` and `capAvailable` update, and the Cap Summary refreshes.

---

### User Story 5 - Extensions and Conversions
As a user, I can extend contracts or convert salary to bonus and preview multi-year cap impacts.

**Acceptance Scenarios**:
1. Given a player with `contractYearsLeft ≤ 2`, When I choose Action → Extension, Then I can set Years (1–7), Total Salary, and Signing Bonus, and see New Cap Hit = (New Total Salary + New Bonus) ÷ New Contract Length (MVP simplification; see Requirements) with before/after comparison.
2. Given a player with high `capHit`, When I choose Action → Conversion, Then I can convert part of base salary to a signing bonus, see reduced current-year cap hit and projected future-year increases, and confirm to apply changes to cap figures and player contract fields.

---

### User Story 6 - Tabbed Roster Views and Filters
As a user, I can navigate across Active Roster, Injured Reserve, Dead Money, Draft Picks, and Free Agents with contextual columns and filters.

**Acceptance Scenarios**:
1. Given the tabbed navigation, When I switch tabs, Then the table updates using the appropriate filters (Active: `isFreeAgent=false` AND `team=selectedTeam`; Free Agents: `isFreeAgent=true`) and columns per tab spec.
2. Given the Injured Reserve tab, When I filter by injury status, Then only IR players matching the filter are shown with their cap implications, if present in dataset.

---

## Requirements*

### Scope
- Build a Spotrac-style web interface to manage Madden rosters with immediate, accurate cap impact visualization using provided CSVs (`MEGA_players.csv`, `MEGA_teams.csv`).
- Always-on Cap Summary Panel shows: Original Cap Total (`capRoom` from team), Current Cap Total (same as Original for season view), Cap Spent (`capSpent`), Cap Space (`capAvailable`), and Cap Gain/Loss from user actions.
- Roster Management UI with tabs: Active Roster, Injured Reserve, Dead Money, Draft Picks, Free Agents.
- Player table columns (desktop):
  - Row # (by descending `capHit` per team)
  - Player identity: `firstName`, `lastName`, `position`, `age`, `height`, `weight` with position badge
  - 2025 Cap (`capHit`)
  - Dead Cap Hit (Release) (`capReleasePenalty`)
  - Dead Cap Hit (Trade) (same as release penalty in dataset unless specified otherwise)
  - Contract (`contractLength`, `contractSalary`)
  - Free Agent Year (`contractYearsLeft`, computed FA year)
  - Action dropdown: Release, Trade, Extension, Conversion (contextual availability)

### Data Integration
- Source files: `MEGA_players.csv`, `MEGA_teams.csv`.
- Join: Players → Teams on `players.team = teams.abbrName`.
- Filters:
  - Active Roster: `isFreeAgent=false` AND `team=selectedTeam`
  - Free Agents: `isFreeAgent=true`
  - Re-sign candidates: `contractYearsLeft = 0` OR `reSignStatus != 0`
- Time context: use `seasonIndex` and `weekIndex` as display metadata; core calculations assume current-season snapshot.

### Calculations and Rules
- Reference: spec/Salary Cap Works in Madden.md (Madden in-game logic primer).
- Cap Summary:
  - Cap Space = `capAvailable`
  - Cap Spent = `capSpent`
  - Progress bar = `capSpent / capRoom`
  - Gain/Loss indicator = net delta from initial session load for the selected team
- Releases (use dataset):
  - Dead Money = `capReleasePenalty`
  - Cap Savings = `capReleaseNetSavings`
  - New Cap Space (preview) = `current capAvailable + capReleaseNetSavings`
- Trades (Quick Simulate):
  - Remove player, apply `capReleasePenalty` immediately; savings follow `capReleaseNetSavings` semantics if provided for trade, else treat as release-equivalent for MVP.
- Free Agent Offer Builder:
  - Year 1 Cap Hit = `Annual Salary + (Signing Bonus ÷ min(Years, 5))`
  - Validate: block if `capAvailable < Year1CapHit`
  - Warning if offer < 90% of desired: acceptance may be blocked or require explicit confirmation (configurable – see Clarifications).
- Extensions (MVP simplification):
  - New Cap Hit (simplified) = `(New Total Salary + New Bonus) ÷ New Contract Length`
  - Show Cap Impact = `New Cap Hit - Old Cap Hit`
  - Note: Advanced mode (Phase 2) adopts Madden 5-year bonus proration and salary distribution tables for multi-year projections per salary cap guide.
- Conversions:
  - Convert portion of current-year base salary to signing bonus; reduce current year’s cap hit; distribute converted amount over remaining years up to 5 via `converted ÷ min(remainingYears, 5)`.

### UI/UX
- Spotrac-inspired design with color coding:
  - Green = savings/positive deltas
  - Red = dead money/penalties
  - Yellow = warnings/low cap space
  - Blue = extensions/modifications
- Sticky Financial Summary panel with real-time updates and progress bar.
- Player cards/rows include badges and hover tooltips for contract breakdowns.
- Responsive behavior:
  - Desktop: full table columns
  - Tablet: collapsible contract details
  - Mobile: card-based layout with swipe actions (Release/Trade/Offer)

### Non-Functional
- In-memory scenario state; no backend required for MVP.
- Performance: Changes apply instantly (<100ms UI update on typical roster sizes), virtualize long tables where needed.
- Persistence (MVP): optional localStorage save/restore of a single scenario per team. [Assumption]
- Accessibility: keyboard navigation for tables and modals; color contrast aligned with WCAG AA.

### Phase 2 (Advanced)
- Multi-year projections (3–5 seasons) honoring Madden bonus proration max (5 years) and dataset fields.
- Multi-team Trade Analyzer with cap calculation validation for all involved teams.
- Contract comparables by position (league averages, median, highlight over/underpaid).
- Scenario Planning: what-if stacks, save/load multiple scenarios, compare side-by-side.

### Assumptions
- Use `capReleasePenalty` and `capReleaseNetSavings` as authoritative for dead money and savings; no additional split-year modeling in MVP beyond these fields.
- For Trade (Quick Sim), treat penalty equivalent to release if no trade-specific fields are present.
- Year 1 Cap Hit for Free Agents uses 5-year bonus proration max per Madden rules from the guide.
- Draft Picks tab in MVP is informational; rookie reserve is noted but not enforced as a separate lock unless data available. [Assumption]

### [NEEDS CLARIFICATION]
1. Free Agent acceptance rule: Should offers below 90% be strictly blocked (hard rule) or allowed with explicit “lowball” confirmation? This impacts UX and simulation realism.
2. Persistence scope: Should scenarios auto-save per team to localStorage (MVP) or remain session-only until Phase 2? Affects user flow and data model.
3. Trade (Quick) vs Release: If dataset provides different `capReleaseNetSavings` for trades, should we prefer those values, or assume release-equivalent for MVP? Impacts cap math accuracy.
4. Draft Picks/Rookie Reserve: Should the tool enforce a rookie reserve buffer (blocking signings that encroach), or be advisory only in MVP? Impacts validation logic.
5. Seasonal context: Should we expose “pre/post June 1” style splits or keep to dataset-provided penalties only for MVP? Affects education vs simulation fidelity.

## Success Criteria*
- Cap Summary updates instantly after each action and matches expected values computed from dataset fields and formulas described above.
- Release/Trade modals display Dead Money, Cap Savings, and New Cap Space accurately; confirming applies roster and cap changes correctly.
- Free Agent signing validates cap availability, warns on <90% offers per configured rule, and on success moves player to Active Roster and updates cap figures.
- Extension and Conversion flows show before/after cap comparisons and apply simplified MVP rules correctly; updated values reflect in Cap Summary and player rows.
- Tabbed navigation filters data correctly (Active vs Free Agents) and sorts by `capHit` by default, with consistent responsive layouts across desktop/tablet/mobile breakpoints.
