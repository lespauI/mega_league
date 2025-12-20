# Depth Management Tool – Technical Specification

## 1. Technical Context

- **Runtime / stack**
  - Static HTML page under `docs/depth_chart/index.html`.
  - Native ES modules (`type="module"`) with plain browser DOM APIs.
  - CSV parsing via PapaParse loaded from CDN.
  - No bundler or framework; everything runs client-side.
- **Shared data**
  - Teams and players come from the same CSVs as the cap tool:
    - `docs/roster_cap_tool/data/MEGA_teams.csv`
    - `docs/roster_cap_tool/data/MEGA_players.csv`
  - Normalization logic already reused from `docs/roster_cap_tool/js/validation.js`.
- **Related tools for reference**
  - Cap tool state and models in `docs/roster_cap_tool/js/state.js` and `docs/roster_cap_tool/js/models.js`.
  - Contextual contract helpers in `docs/roster_cap_tool/js/context.js`.
  - Modal / a11y patterns in `docs/roster_cap_tool/js/ui/modals/*` and `docs/roster_cap_tool/js/ui/a11y.js`.
  - E2E tests: `tests/e2e/depth_chart.spec.ts`.

The depth chart tool will stay independent of the cap tool UI, but will share:

- CSV normalization (`normalizeTeamRow`, `normalizePlayerRow`).
- Player model fields (id, team, position, OVR, contract fields).

## 2. High-Level Design

Transform the read-only depth chart into an interactive, per-team depth management tool:

1. **Shared player model**
   - Make depth chart players use the same normalized player shape as the cap tool (including `id`, `contractLength`, `contractYearsLeft`, salary/bonus fields, `isFreeAgent`).
2. **Depth plan data layer**
   - Introduce a per-team **Depth Plan** model that represents, for each position slot and depth index (1–4), what occupies that slot:
     - Existing roster player.
     - Free-agent player assigned to the team.
     - Placeholder acquisition (`Draft R1`, `Draft R2`, `Trade`, `FA`).
   - Persist plans and roster edits to `localStorage` so they survive reloads.
3. **Roster edit model**
   - Track lightweight roster edits as diffs from baseline CSV:
     - Player moved between teams (trade).
     - Player moved to/from free-agent pool (cut/sign).
   - Derive current rosters and FA pool on the fly from baseline + edits.
4. **Interactive UI**
   - Replace the single tabular view with:
     - **Offense field layout** (OL row, QB behind C, HB offset right, WR1/WR2 wide left/right, TE next to RT).
     - **Defense field layout** (safeties deep, LBs mid, DTs+EDGEs down, CBs wide).
     - **Special teams strip** (K, P, LS).
   - Each position card shows up to four depth rows with:
     - Player name + OVR or placeholder label.
     - Acquisition tag.
     - Contract summary + FA-at-end-of-season marker where applicable.
   - Clicking a depth cell opens a small slot editor to:
     - Assign an existing roster player.
     - Search and assign a free agent.
     - Set placeholder acquisition type (`Draft R1`, `Draft R2`, `Trade`, `FA`).
     - Clear the slot.
   - Optional side panel listing roster + FA pool for quick edits.
5. **CSV export**
   - Add an “Export CSV” control that flattens the current team’s depth plan into rows suitable for spreadsheets.

All state remains client-side and independent from the cap tool’s own state/scenario system.

## 3. Source Code Structure & Changes

### 3.1 Existing depth chart entry / wiring

- `docs/depth_chart/index.html`
  - Currently renders header with team selector and a single `#depth-chart-grid` container.
  - Loads styles from `docs/depth_chart/css/styles.css`.
  - Boots `docs/depth_chart/js/main.js`.
- `docs/depth_chart/js/main.js`
  - Loads teams/players via `js/csv.js`.
  - Initializes state via `js/state.js`.
  - Mounts `ui/teamSelector` and `ui/depthChart`, re-mounting on every state change.
- `docs/depth_chart/js/state.js`
  - Minimal global state: `{ selectedTeam, teams, players }`.
  - `getTeamPlayers()` returns current team’s non-FA players.
- `docs/depth_chart/js/ui/depthChart.js`
  - Defines `DEPTH_CHART_SLOTS` and `POSITION_GROUPS`.
  - Computes per-slot players purely from current roster (no persistence or editing).
  - Renders seven position-group tables in a grid.

### 3.2 CSV loading and normalization

- `docs/depth_chart/js/csv.js` currently:
  - Uses PapaParse to load CSVs.
  - Delegates validation to `../../roster_cap_tool/js/validation.js`.
  - Returns **stripped** player objects (no `id` or contract fields).

**Change:** extend `loadPlayers` to keep the full normalized player model:

- Include at least:
  - `id`, `firstName`, `lastName`, `position`, `team`, `isFreeAgent`, `isOnIR`, `yearsPro`.
  - OVRs: `playerBestOvr`, `playerSchemeOvr`.
  - Contract / cap fields: `contractSalary`, `contractBonus`, `contractLength`, `contractYearsLeft`, `capHit`, `capReleasePenalty`, `capReleaseNetSavings`, `desiredSalary`, `desiredBonus`, `desiredLength`, `reSignStatus`.
- Optionally add a helper field the depth chart will use:
  - `ovr` (preferred OVR value, derived from `playerBestOvr`/`playerSchemeOvr`).

This ensures the depth tool and cap tool share a compatible player schema.

### 3.3 Depth chart state and persistence

Update `docs/depth_chart/js/state.js` to support:

- **State shape (new fields)**
  - `baselinePlayers: Player[]` – immutable snapshot from CSV, normalized.
  - `players: Player[]` – derived from `baselinePlayers` + `rosterEdits` (for convenience).
  - `rosterEdits: Record<string, { team?: string; isFreeAgent?: boolean }>` – diffs by player `id`.
  - `depthPlansByTeam: Record<string, DepthPlan>` – depth plans by team abbreviation.
  - (Existing) `selectedTeam`, `teams`, and pub/sub `listeners` remain.

- **Types (conceptual; implemented via JSDoc)**

  ```js
  /**
   * @typedef {'existing' | 'faPlayer' | 'draftR1' | 'draftR2' | 'trade' | 'faPlaceholder'} AcquisitionType
   *
   * @typedef {Object} DepthSlotAssignment
   * @property {string} slotId        // e.g. 'QB', 'WR1'
   * @property {number} depthIndex    // 1..4
   * @property {AcquisitionType} acquisition
   * @property {string=} playerId     // for existing / faPlayer
   * @property {string=} placeholder  // human label for placeholder (Draft R1, Trade, FA)
   *
   * @typedef {Object} DepthPlan
   * @property {string} teamAbbr
   * @property {Record<string, Array<DepthSlotAssignment>>} slots
   */
  ```

- **Derived getters**
  - `getState()` / `setState()` unchanged in shape but extended:
    - `initState({ teams, players })`:
      - Normalize teams/players (using existing team normalization).
      - Set `baselinePlayers` and `players`.
      - Load any persisted `rosterEdits` and `depthPlansByTeam` from `localStorage` and apply them.
  - `getTeamPlayers()`:
    - Use `players` array (already including roster edits).
    - Filter on `team === selectedTeam` and `!isFreeAgent`.
  - `getFreeAgents()`:
    - Return all players where `isFreeAgent === true`.
  - `getDepthPlanForSelectedTeam()`:
    - Return existing plan from `depthPlansByTeam[selectedTeam]`, or lazily initialize from baseline roster.

- **Roster edit helpers**
  - `applyRosterEdits(baselinePlayers, rosterEdits) => Player[]`
    - Patterned after cap tool’s `applyRosterEdits` but simplified:
      - For each baseline player, apply `team` and/or `isFreeAgent` overrides if present.
  - `setRosterEdit(playerId, patch)`
    - Merge patch into `rosterEdits`.
    - Recompute `players` via `applyRosterEdits`.
    - Persist `rosterEdits` to `localStorage`.
  - `resetTeamRosterAndPlan(teamAbbr)`
    - Remove roster edits that affect the given team (either players traded out or into that team).
    - Recompute `players`.
    - Rebuild that team’s `DepthPlan` from baseline auto-depth (see below).
    - Persist updates.

- **Depth plan helpers**
  - `buildInitialDepthPlanForTeam(teamAbbr, players) => DepthPlan`
    - Use the same auto-assignment logic as the current read-only chart:
      - For each `DEPTH_CHART_SLOT`, compute eligible players and sort by OVR.
      - Apply WR/CB/EDGE/DT splits exactly as today via `split` property.
      - Generate `DepthSlotAssignment` entries of type `existing` for up to `slot.max` players, filling depth indices 1..4.
  - `ensureDepthPlanForTeam(teamAbbr)`
    - If no plan in memory, try to load from `localStorage`, else generate via `buildInitialDepthPlanForTeam`.
  - `updateDepthSlot({ teamAbbr, slotId, depthIndex, assignment })`
    - Update the entry in `depthPlansByTeam`, preserving other slots.
    - If `assignment` references a `playerId`, also:
      - Update that player’s `team` / `isFreeAgent` via `setRosterEdit` (for trades / signings).
      - Remove that `playerId` from any other depth plans/slots (so a player isn’t accidentally shown on two teams unless explicitly allowed).
    - Persist updated depth plans.
  - `clearDepthSlot({ teamAbbr, slotId, depthIndex })`
    - Set the slot entry to `null` or remove it, and persist.

- **LocalStorage schema**
  - Keys are scoped to this tool and versioned:
    - `depthChartPlanner.v1.rosterEdits` → `{ [playerId]: { team?: string; isFreeAgent?: boolean } }`.
    - `depthChartPlanner.v1.depthPlans` → `{ [teamAbbr]: DepthPlanSerializable }`.
  - `DepthPlanSerializable` mirrors `DepthPlan` but removes derived fields as needed.

### 3.4 UI components

New and updated modules:

- **Updated** `docs/depth_chart/js/ui/depthChart.js`
  - Switch from 7 generic tables to a game-like formation layout:
    - Offense, Defense, Special Teams sections.
    - Each position represented as a card positioned on a “field”.
  - Render from the `DepthPlan` instead of recomputing from players on each mount.
  - Display:
    - Position label.
    - Up to four depth rows, showing:
      - Player or placeholder label.
      - OVR (for players).
      - Acquisition tag.
      - Contract summary + FA-at-end-of-season indicator (icon or text).
  - Attach click handlers on each depth row to open the slot editor.
  - Add global controls for:
    - “Reset to baseline” (per team).
    - “Export CSV”.

- **New** `docs/depth_chart/js/ui/slotEditor.js`
  - Responsible for the popup / panel when a depth cell is clicked.
  - Input props:
    - `{ slotId, depthIndex }` and current assignment (if any).
  - UI options:
    - **Current roster tab** – list of eligible current-team players for that position.
    - **Free agents tab** – list of eligible FAs for that position, with:
      - Text search by name.
      - Optional OVR min/max filter.
    - **Placeholders** – buttons for `Draft R1`, `Draft R2`, `Trade`, `FA`.
    - “Clear slot” action.
  - Actions call back into state via `updateDepthSlot` and `setRosterEdit` as needed.
  - Uses simple in-DOM overlay (e.g., absolutely-positioned panel anchored near the clicked cell) instead of `<dialog>` for now.

- **New (optional but recommended)** `docs/depth_chart/js/ui/rosterPanel.js`
  - Sidebar panel with two lists:
    - Current team roster (with position, name, OVR, contract summary, FA marker).
    - Free-agent pool (filterable by position and search text).
  - Interactions:
    - “Cut to FA” button on roster rows → `setRosterEdit(playerId, { isFreeAgent: true, team: '' })` and clear from depth plan.
    - “Sign to team” button on FA rows → assign to selected team (not necessarily to a depth slot).
    - Optional “Trade to…” dropdown to reassign team and clear slot occupancy.
  - Mounted into a new `#roster-panel` container in the page.

- **Updated** `docs/depth_chart/js/ui/teamSelector.js`
  - Behavior remains the same (team select).
  - No structural changes required; continues to call `setState({ selectedTeam: value })`, which will drive depth plan / roster updates.

### 3.5 Layout & CSS

- **Updated** `docs/depth_chart/css/styles.css`
  - Introduce new layout containers:
    - `.depth-layout` – main flex or grid wrapper for offense, defense, special teams, and roster panel.
    - `.depth-side--offense`, `.depth-side--defense`, `.depth-side--special`.
    - `.field`, `.field--offense`, `.field--defense` – game-style field backgrounds.
  - Use CSS Grid within offense/defense fields to approximate formation:
    - Offense example (columns can be tuned for spacing):

      ```css
      .field--offense {
        display: grid;
        grid-template-columns: repeat(7, minmax(0, 1fr));
        grid-auto-rows: minmax(70px, auto);
      }
      ```

      - Row 1: OL → `LT, LG, C, RG, RT` centered across the middle columns.
      - Row 2: `WR1` on far left, `TE` just outside `RT`, `WR2` on far right.
      - Row 3: `QB` behind `C`, `HB` one column to the right and slightly back.

    - Defense example:
      - Top row: `FS` and `SS` centered.
      - Middle row: `SAM, MIKE, WILL`.
      - Bottom row: `DT1, DT2` interior; `EDGE1, EDGE2` on edges.
      - `CB1`, `CB2` wide left/right on middle or top row.
  - Each position card styled as:
    - `.position-card` with header label and a vertical list of depth rows.
    - Depth rows with clickable affordances (hover/active states).
  - Special teams:
    - Simple horizontal row of three cards (K, P, LS) below or between offense/defense.
  - Maintain existing color palette and typography, extending:
    - Acquisition badges (e.g., `badge--draft`, `badge--trade`, `badge--fa`).
    - Contract/FA markers (e.g., small `FA` tag in yellow/red).

## 4. Data Model & Contract Display

### 4.1 Player model alignment

- Use the cap tool’s normalized `Player` shape via `normalizePlayerRow`.
- For the depth tool we care about:
  - Identity: `id`.
  - Identity/label: `firstName`, `lastName`, `position`.
  - Team membership: `team`, `isFreeAgent`.
  - Overall ratings: `playerBestOvr`, `playerSchemeOvr`.
  - Contracts: `contractSalary`, `contractBonus`, `contractLength`, `contractYearsLeft`.
  - Cap figures: `capHit`, `capReleasePenalty`, `capReleaseNetSavings` (for possible future features).

### 4.2 Contract summary + FA timing

- Helper function in a shared utility (or inside `ui/depthChart.js`):

  ```js
  function getContractSummary(player) {
    const length = player.contractLength ?? player.contractYearsLeft ?? null;
    const yearsLeft = player.contractYearsLeft ?? null;
    const isFaNow = !!player.isFreeAgent;
    const isFaAfterSeason = !isFaNow && Number(yearsLeft) === 1;
    let label = '';
    if (isFaNow) label = 'FA';
    else if (length != null && yearsLeft != null) {
      label = `${length} yrs (${yearsLeft} left)`;
    } else if (yearsLeft != null) {
      label = `${yearsLeft} yr${yearsLeft === 1 ? '' : 's'} left`;
    }
    return { label, isFaAfterSeason };
  }
  ```

- This keeps semantics aligned with the cap tool’s CSV fields without importing full projection logic:
  - Uses `contractLength` and `contractYearsLeft` as defined in `normalizePlayerRow`.
  - Treats `contractYearsLeft === 1` (and non-FA) as “becomes FA after this season” in the current-season (Y+0) view.

### 4.3 Depth plan representation

- Each depth slot is keyed by `slotId` (`QB`, `WR1`, `EDGE2`, etc.).
- Each slot contains up to four `DepthSlotAssignment` entries.
- Acquisition types map directly to PRD concepts:
  - `existing` → player currently under contract with the team when plan started.
  - `faPlayer` → player signed from FA market to this team.
  - `draftR1`, `draftR2` → draft placeholders.
  - `trade` → player expected to arrive via trade (placeholder).
  - `faPlaceholder` → non-specific FA placeholder.

### 4.4 CSV export row shape

The export builder will convert the current team’s plan into rows with columns:

- `team` – team abbreviation.
- `side` – `Offense`, `Defense`, or `Special Teams`.
- `positionSlot` – e.g., `QB`, `WR1`, `CB2`, `EDGE1`.
- `depth` – integer 1–4.
- `playerName` – either `F.LastName` for a real player or placeholder label (`Draft R1`, `Trade`, `FA`).
- `acquisition` – one of:
  - `Existing`, `Draft R1`, `Draft R2`, `Trade`, `FA Placeholder`, `FA Player`.
- `ovr` – numeric OVR used for ordering (empty for placeholders).
- `contractLength` – numeric or empty.
- `contractYearsLeft` – numeric or empty.
- `faAfterSeason` – `true`/`false` for players where the helper flags them as becoming FA after the current season.

## 5. Feature Implementation Details

### 5.1 Roster editing

- **Add player from FA to team**
  - Via slot editor (FA tab) or roster panel:
    - Update `rosterEdits[playerId]` to `{ isFreeAgent: false, team: selectedTeam }`.
    - Optionally, if triggered from a specific slot, also call `updateDepthSlot` to assign `acquisition: 'faPlayer'` and `playerId`.
    - Ensure player is removed from any FA list views due to updated `isFreeAgent`.
- **Remove player from team (cut to FA)**
  - From roster panel:
    - `setRosterEdit(playerId, { isFreeAgent: true, team: '' })`.
    - Clear player from any depth slots (`updateDepthSlot` with `null` assignment wherever `playerId` matches).
- **Trade player to another team**
  - From roster panel or slot editor:
    - `setRosterEdit(playerId, { isFreeAgent: false, team: targetTeamAbbr })`.
    - Clear player from all slots for the old team and (optionally) auto-add to a reasonable depth slot for the new team (or leave unassigned for manual placement).
- **Reset local changes**
  - “Reset to baseline” button:
    - Calls `resetTeamRosterAndPlan(selectedTeam)` as defined in state.
    - Clears any persisted edits for that team from `localStorage`.

### 5.2 Contract visibility & FA flags

- For each player row rendered in:
  - Offense/Defense/Special depth cards.
  - Roster panel lists.
  - FA search results.
- Display:
  - Name: `F.LastName` (reuse existing `formatName` helper).
  - OVR: `playerBestOvr` (fallback to `playerSchemeOvr` or 0).
  - Contract summary label from `getContractSummary`.
  - If `isFaAfterSeason` is true, show a small badge (e.g., `FA after season`) or icon with tooltip.

### 5.3 Slot acquisition type & editing

- Each depth row UI will show:
  - Primary label: player or placeholder.
  - Secondary label: acquisition tag (e.g., `Existing`, `Draft R1`, `Trade`).
- Slot editor interactions:
  - When user chooses a roster player:
    - `updateDepthSlot` with `{ acquisition: 'existing', playerId }`.
  - When user chooses a FA player:
    - `setRosterEdit` to move player onto the team.
    - `updateDepthSlot` with `{ acquisition: 'faPlayer', playerId }`.
  - When user taps a placeholder button:
    - `updateDepthSlot` with the corresponding acquisition type and placeholder label.
  - When user clears the slot:
    - `clearDepthSlot`.

### 5.4 Free-agent market search & assignment

- FA tab in slot editor and FA section of roster panel will share simple, in-memory filtering:
  - **Input**:
    - Text input for name substring (case-insensitive).
    - Position dropdown defaulting to the slot’s primary position(s).
    - Optional OVR min/max slider or inputs.
  - **Filtering**:
    - Operate on `getFreeAgents()` then filter by position and OVR constraints.
  - **Assignment**:
    - “Sign & assign to slot”:
      - Executes both roster edit and depth slot update.
    - “Sign to team only” (from roster panel):
      - Only updates roster edit; leaves depth plan unchanged until user explicitly assigns.

### 5.5 Editable depth ordering

- Depth ordering becomes **owned by the DepthPlan**, not recomputed from OVR each time.
- Default plan generation uses OVR to seed the initial order.
- UI affordances inside each position card:
  - Up/down controls on each occupied depth row:
    - Clicking “up” swaps this `DepthSlotAssignment` with the previous index (if any).
    - Clicking “down” swaps with the next index (if any).
  - Optionally, pointer cursor + drag handle for future enhancement (but not required).
- When order changes:
  - Update the `slots[slotId]` array order.
  - Persist updated plan to `localStorage`.

### 5.6 CSV export

- New helper in `docs/depth_chart/js/csvExport.js` (or added to `js/csv.js`):
  - `buildDepthCsvForTeam(teamAbbr, depthPlan, playersById) => string`
    - Produces a CSV text string with proper escaping and header row.
  - `downloadCsv(filename, csvText)`
    - Creates a Blob and a temporary anchor with `download` attribute to trigger browser download.
- UI integration:
  - Add an “Export CSV” button into the header area of `depth-chart-container`.
  - On click:
    - Lookup `depthPlan` and the relevant players.
    - Build CSV and trigger download with a filename like `depth-plan-{TEAM}.csv`.

### 5.7 Layout & visual design

- Offense/Defense layouts align with PRD:
  - Explicitly group positions into sides:
    - Offense: `LT, LG, C, RG, RT, QB, HB, FB, WR1, WR2, TE`.
    - Defense: `FS, SS, CB1, CB2, SAM, MIKE, WILL, DT1, DT2, EDGE1, EDGE2`.
    - Special: `K, P, LS`.
  - Each card’s absolute/relative placement controlled via CSS grid area assignments or row/column indices.
- Visual consistency:
  - Reuse existing color-coded position classes (e.g. `.pos-QB`, `.pos-WR`) for labels.
  - Ensure depth rows remain legible:
    - Truncate long names with ellipsis.
    - Use smaller secondary text for OVR and contract tags.

## 6. Delivery Phases / Milestones

1. **Data alignment**
   - Update `docs/depth_chart/js/csv.js` and `state.js` to use full player model and maintain `baselinePlayers`.
   - Verify existing read-only depth chart still renders correctly using new data shape.
2. **Depth plan + persistence**
   - Implement `DepthPlan` model, initialization from baseline, `updateDepthSlot`, `clearDepthSlot`, and `localStorage` persistence.
   - Render depth cards from `DepthPlan` but keep existing table layout initially to de-risk.
3. **Game-like layout**
   - Replace table layout in `ui/depthChart.js` and update `styles.css` to new offense/defense/special field views.
   - Adjust tests to assert new structure.
4. **Editing interactions + FA search**
   - Implement `slotEditor` and `rosterPanel` UI.
   - Wire up roster edits (cut, sign, trade) and depth assignments.
   - Add contract summary + FA markers.
5. **Depth ordering + CSV export**
   - Add reordering controls and persistence.
   - Implement CSV export builder and hook up the UI button.
6. **Polish & hardening**
   - Add reset-to-baseline button.
   - Guard against invalid data, empty teams, and malformed localStorage.
   - Finalize accessibility basics (focus management for slot editor, ARIA labels).

Each phase is incremental and testable in isolation.

## 7. Verification Approach

- **Manual checks**
  - Load `/docs/depth_chart/` and verify:
    - Offense/Defense/Special layouts render for a few teams.
    - Initial depth aligns roughly with previous read-only view.
    - Contract summaries and FA markers appear for players with valid data.
  - Perform typical flows:
    - Cut a player to FA and confirm they disappear from team depth and appear in FA search.
    - Sign a FA and place them into a depth slot.
    - Mark placeholders (`Draft R1`, `Trade`, `FA`) in open depth slots.
    - Reorder depth rows and reload the page; confirm order persists.
    - Use “Reset to baseline” and confirm roster and depth revert.
    - Export CSV and open the file to verify columns and values.
- **Automated E2E tests (Playwright)**
  - Extend/adjust `tests/e2e/depth_chart.spec.ts` to cover:
    - New layout structure (offense/defense/special cards rather than 7 tables).
    - Presence and function of the Export CSV button (stub: verify download trigger).
    - Slot editor visibility and basic actions:
      - Opening via click on a depth cell.
      - Assigning a placeholder acquisition type.
    - FA search filters (by name and position) and assignment to team.
    - Roster edits (cut/sign/trade) reflected in the depth chart.
    - Persistence across reload via `localStorage`.
  - Run tests with:
    - `npm install` (once, if not already installed).
    - `npm run test:e2e -- tests/e2e/depth_chart.spec.ts`.

This specification keeps the depth chart tool aligned with the cap tool’s data model while adding the interactive planning features, contract visibility, acquisition tagging, CSV export, and game-like layout described in the PRD.
