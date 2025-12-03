# Feature Specification: Player Contract Distribution Editor


## User Stories*


### User Story 1 - Edit Year-by-Year Distribution

As a roster manager, I want to customize year-by-year salary and bonus allocations for a player’s contract so I’m not constrained to the default equal split.

**Acceptance Scenarios**:

1. Given a roster view showing players with contract metadata (playerId, total amount, term in years, start year), When I click a player, Then a contract distribution editor opens showing a table with a column per contract year and editable Salary and Bonus for each year.
2. Given the editor opens with no prior custom data for that player, When it renders, Then default values are pre-filled as: per-year allotment = total/years, and per-year Salary = per-year allotment × 0.5, per-year Bonus = per-year allotment × 0.5.
3. Given the editor is open, When I edit any Salary or Bonus cell, Then the UI updates immediately, values are formatted as currency like $22.7M (millions with 1 decimal), and the in-memory store for that player is updated.
4. Given I have custom values saved in-memory for a player, When I reopen the editor for that player in the same session, Then the table loads and displays the custom values instead of defaults.
5. Given I have modified values so that the sum across years does not equal the contract total, When the editor displays, Then the UI still accepts and shows the values (no blocking validation or auto-adjustment) and the state remains saved in-memory.
6. Given the editor shows custom values, When I click Reset, Then all years revert to the default 50/50 distribution (per-year allotment split evenly between Salary and Bonus) and any custom in-memory values for the player are cleared.

---

## Requirements*

- Trigger
  - Clicking a player entry in the roster opens the Contract Distribution Editor. The exact clickable target may be the row or name; the implementation should use the existing roster interaction pattern.

- Editor Surface
  - Modal or side drawer that overlays the roster without navigation away. Must provide a clear Close action. Closing the editor does not discard in-memory changes already made.

- Table Layout
  - Columns: one per contract year (e.g., 2026, 2027, … startYear + years − 1).
  - Fields per column: Salary (editable), Bonus (editable).
  - Header shows the year label as a 4-digit year.
  - Inputs accept numeric entry; formatting applied as currency on blur or input where practical.

- Defaults and Calculations
  - Per-year base = total / years.
  - Default Salary per year = base × 0.5; Default Bonus per year = base × 0.5.
  - Internal values stored as absolute dollars (number). Display values formatted as millions with 1 decimal (e.g., $22.7M). Rounding: display rounds to 1 decimal place; underlying value preserves full precision.
  - No constraints or normalization on totals; do not auto-balance other years when one cell changes.

- Editing Behavior
  - Changes reflect immediately in the UI and in the in-memory store.
  - Reopening the editor in the same session shows previously edited values for that player.
  - No cross-field validation; fields are independent.

- Reset Behavior
  - “Reset” button restores the default 50/50 distribution for the current player and clears any custom values stored for that player.

- In-Memory Storage
  - Structure: Map<playerId, { [year: number]: { salary: number; bonus: number } }>
  - Lifetime: runtime only; cleared on page reload. Survives route changes within the SPA/session.

- Formatting
  - Display values as currency in millions with one decimal place (e.g., $49.5M). Use standard rounding to one decimal place for display only.

- Accessibility and Usability
  - Keyboard-editable inputs; tab order should follow year/field order.
  - Visual focus states on inputs and actionable buttons.

- Out of Scope
  - Persisting to server/database.
  - Enforcing totals to equal contract total or validating sum distribution.
  - Advanced pro-rating rules, cap mechanics, or derived summaries.

## Success Criteria*

- Clicking a player reliably opens the editor with a table of years (correct year labels based on start year and term).
- Default values per year are set to (total/years) × 0.5 for Salary and Bonus.
- Editing any cell updates the UI immediately and is reflected in the in-memory store keyed by playerId and year.
- Values display as currency in millions with 1 decimal (e.g., $22.7M), with display rounding that does not alter stored precision.
- Reset restores the default 50/50 split for the current player and clears custom data for that player from memory.
- Custom distributions are preserved while the session remains active and are shown when the editor is reopened.
- No validation prevents the user from entering distributions that do not sum to the contract total.
