# Technical Specification: Player Contract Distribution Editor

## Technical Context
- Stack: Static web app under `docs/roster_cap_tool` using ES Modules (vanilla JS, no bundler)
- Language: JavaScript (ES2020+), HTML, CSS
- Data: CSV via PapaParse CDN, loaded at runtime
- State mgmt: Lightweight in‑memory store in `js/state.js` with pub/sub and selective localStorage for some per‑team settings
- Testing: Playwright config (`playwright.config.ts`) serves `http://127.0.0.1:8000` via `python3 -m http.server 8000`
- No backend/database; feature must be browser‑memory only

## Technical Implementation Brief
- Add a side‑drawer editor that opens when clicking a player in the Active Roster table. Drawer shows editable year‑by‑year Salary and Bonus fields.
- Values are typed in millions (e.g., 22.7 → $22.7M). Accept up to 2 decimals; display with 1–2 decimals, trimming trailing zeros.
- Default distribution: Even per‑year total = `(contractSalary + contractBonus) / contractLength`, with 50/50 split per year.
- Start year logic (from answers): Use current season as Year 1; if `contractYearsLeft` exists, `startYear = baseCalendarYear - (contractLength - contractYearsLeft)`. Only show remaining years from the current season forward.
- In‑memory storage only: Maintain `customContractsByPlayer` keyed by `player.id` with `{ [year: number]: { salary: number, bonus: number } }` in absolute USD (not millions). No localStorage.
- Auto‑save on edit; no Save button. Reset button restores default 50/50 and clears custom entry for that player.
- Scope: For this increment, the editor is UI‑only and does not alter cap math/projections. A follow‑up phase can add an optional cap math override.

## Source Code Structure
- docs/roster_cap_tool/js/
  - state.js
    - Add: ephemeral `customContractsByPlayer` map and getters/setters/reset
      - `getCustomContract(playerId)` → `{ [year]: { salary, bonus } } | null`
      - `setCustomContract(playerId, map)` → updates state and emits
      - `resetCustomContract(playerId)` → deletes entry and emits
  - ui/playerTable.js
    - Enhance Player cell (`.cell-player`) to open editor on click
    - Optional: Add “Contract Distribution” to Action select as secondary trigger
  - ui/modals/contractEditor.js (new)
    - `openContractEditor(player)` renders a `<dialog>` styled as a right‑side drawer
    - Renders year columns (calendar years) with Salary/Bonus numeric inputs (millions)
    - Live formatting preview (`$XX.XM`) next to each input
    - Footer actions: Reset (restores default), Close
    - Uses `enhanceDialog` from `ui/a11y.js`
  - css/styles.css
    - Add minimal drawer styles: `.drawer`, `.drawer--open`, layout grid for year columns, input adornments for “M” suffix
  - format.js (new, optional)
    - `fmtMoneyMillions(n)` → `$12.3M` with 1–2 decimals
    - `parseMillions(input)` → absolute dollars

## Contracts
- State shape additions (ephemeral; no persistence):
  - `state.customContractsByPlayer: { [playerId: string]: { [year: number]: { salary: number, bonus: number } } }`

- Public state API (to be added in `state.js`):
  - `getCustomContract(playerId: string): Record<number, { salary: number, bonus: number }> | null`
  - `setCustomContract(playerId: string, map: Record<number, { salary: number, bonus: number }>): void`
  - `resetCustomContract(playerId: string): void`

- Editor API:
  - `openContractEditor(player: Player): void`

- Utility contracts:
  - `computeStartYear(player: Player): number | null` — uses `getBaseCalendarYear()` and player `contractLength/contractYearsLeft`
  - `computeDefaultDistribution(player: Player): Record<number, { salary: number, bonus: number }>` — years = remaining years incl. current season; per‑year total = `(contractSalary + contractBonus)/contractLength`; salary = bonus = per‑year total × 0.5
  - `formatMillions(n: number): string` — `$12.3M`, `$12.75M` as appropriate
  - `toAbsoluteDollarsFromMillions(m: number|string): number`

Notes
- Year columns: Only render current season onward. If `contractYearsLeft` is 0 or missing, render nothing and show “No remaining years” state.
- Input units: `step=0.01`, min `0`, allow `''` while typing; coerce to number on blur.
- Auto‑save strategy: On input `input` or `change`, update the in‑memory map; re‑read on drawer open.
- Reset semantics: Clear map entry (delete key entirely) then re‑render defaults.

## Delivery Phases
1) Data + Utilities (no UI)
   - Add state map + getters/setters/reset in `state.js`
   - Add `computeStartYear`, `computeDefaultDistribution`, and formatting helpers
   - Verification: unit‑style smoke via Node console in browser devtools; no UI yet

2) Drawer UI (open/close + default render)
   - Implement `openContractEditor(player)` drawer with table scaffold
   - Wire click on player name to open editor
   - Render default 50/50 values using calendar year headers
   - Verification: manual run; ensure columns and defaults match player contract

3) Editing + Auto‑save + Formatting
   - Hook inputs to update `customContractsByPlayer` in dollars (parse millions)
   - Live display as `$XM` with 1–2 decimals
   - Reopen editor should reflect custom values
   - Verification: E2E spec asserts edits persist within session and UI updates in place

4) Reset
   - Add Reset button to clear map entry and restore defaults
   - Verification: E2E spec verifies Reset restores default values

5) Optional (separate PR): Cap math override
   - Introduce an optional “project with custom distribution” code path that reads the map for the player to compute base/proration per year (non‑breaking, feature‑flagged)
   - Keep out of initial scope to avoid coupling and circular deps

## Verification Strategy
- Local server: `npx playwright test` (already configured to serve `docs/`)
- Add a new Playwright test `tests/e2e/contract_editor.spec.ts` that validates:
  - Clicking a player row opens a drawer with year columns for remaining years
  - Default values per year equal `(total/years) × 0.5` for Salary and Bonus
  - Editing a cell updates the UI immediately and persists on reopen
  - Values display as `$XM` with 1–2 decimals (e.g., `$22.7M`, `$22.75M`)
  - Reset restores default distribution

Suggested selectors and test hooks
- Drawer root: `[data-testid="contract-editor"]`
- Year column headers: `[data-testid="ce-year"]` (text = 4‑digit year)
- Inputs: `[data-testid="ce-input-salary"][data-year="YYYY"]`, `[data-testid="ce-input-bonus"][data-year="YYYY"]`
- Reset button: `[data-testid="ce-reset"]`
- Close button: `[data-testid="ce-close"]`

Test outline (Playwright)
1. Navigate to `docs/roster_cap_tool/`, ensure Active Roster tab visible
2. Click first player name to open editor; expect drawer visible
3. Count year headers equals `contractYearsLeft` (when available)
4. Read first year’s Salary and Bonus formatted text; verify numbers ≈ `(total/len) * 0.5`
5. Edit first year Salary to `22.7` (millions); verify display shows `$22.7M` and persists after closing/reopening
6. Click Reset; verify values revert to defaults

MCP servers
- Not required. Verification uses existing Playwright config and local static server. Built‑in shell/filesystem access is sufficient.

Sample data/artifacts
- Use existing CSVs under `docs/roster_cap_tool/data/` and `MEGA_players.csv` fields (`contractSalary`, `contractBonus`, `contractLength`, `contractYearsLeft`, `capHit`)
- No additional artifacts needed

