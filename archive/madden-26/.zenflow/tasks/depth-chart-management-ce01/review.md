# Depth Chart Management – Product Owner Review

## Acceptance

- The tool correctly loads MEGA data, groups positions, splits WR/CB/DT/EDGE, shows `F.LastName` + OVR, highlights needs, and is wired into the main index page.
- Playwright tests provide good coverage of page load, grouping, ordering, splits, empty slots, data loading, navigation, and error handling.
- On that basis, this is an acceptable **v1** implementation.

## Fixes / Clean‑ups (Near‑Term)

### 1. CSS Consistency with Actual Layout

- Current layout uses flex groups and tables, but there is legacy grid-based styling that is no longer used:
  - `docs/depth_chart/css/styles.css:60-65` – initial `.depth-chart-grid` grid definition.
  - Related grid media queries at `docs/depth_chart/css/styles.css:182-195`.
- Requested change:
  - Remove or refactor unused `.dc-*` and old grid rules so the stylesheet reflects the actual structure (flex groups + tables).
  - Keep the flex-based `.depth-chart-grid` definition at `docs/depth_chart/css/styles.css:201-205` as the single source of layout truth.

### 2. CSV Loading Consistency with `roster_cap_tool`

- Depth chart currently uses custom parsing in `docs/depth_chart/js/csv.js:1-65` with local `toBool/toNum/toStr` and simple row validation.
- `roster_cap_tool` uses `normalizeTeamRow` and `normalizePlayerRow` from `docs/roster_cap_tool/js/validation.js:37-117` via `docs/roster_cap_tool/js/csv.js:1-30`.
- Requested change (preferred option):
  - Reuse `normalizeTeamRow` and `normalizePlayerRow` for the depth chart as well, so both tools share the same validation and normalization rules when the CSV schema evolves.
- Acceptable alternative:
  - Extract shared helpers (e.g. `validation-lite.js`) and use them from both tools, avoiding divergence in how “valid” players/teams are defined.

### 3. Test Clarity Improvements

- `tests/e2e/depth_chart.spec.ts:18-25`:
  - `await expect(options).toHaveCount(await options.count());` is tautological and obscures intent.
  - Requested change: compute the count once and assert it directly:
    - `const count = await options.count(); expect(count).toBeGreaterThan(0);`
- `tests/e2e/depth_chart.spec.ts:335-361` (“no console errors on team change”):
  - The test subscribes to `pageerror` (runtime errors) rather than console events.
  - Requested change:
    - Either listen to `page.on('console', ...)` and assert no `type() === 'error'`, **or**
    - Rename the test to “no runtime errors on team change” to accurately describe the behavior.

### 4. `.gitignore` Completeness

- Current `.gitignore` (`.gitignore:1-7`) includes:
  - `.DS_Store`, `.idea/`, `node_modules/`, `playwright-report/`, `test-results/`, `__pycache__/`, `*.pyc`.
- Requested change:
  - Add common generated paths to prevent accidental commits of build artifacts and logs:
    - `dist/`
    - `build/`
    - `.cache/`
    - `coverage/`
    - `*.log`

## Product / UX Enhancements (Next Iterations)

### 1. Draft and Free-Agent Planning Inside the Depth Chart

- Current state: excellent read-only visualization of roster depth.
- Product goal: support “prepare for draft and FA” directly in this view.
- Requested direction for next iteration:
  - Introduce a simple per-cell status: `none | draft | FA`, representing how the user plans to address that slot.
  - Use the existing color system defined in `docs/depth_chart/css/styles.css:135-166`:
    - Cyan/need (`.dc-cell--need`) for open or thin positions.
    - Yellow/draft (`.dc-cell--draft` + `.dc-label--draft`) for draft targets.
    - Orange/FA (`.dc-cell--fa` + `.dc-label--fa`) for free-agent targets.
  - Persist these flags per team in `localStorage` (patterned after the scenario and settings persistence in `docs/roster_cap_tool/js/state.js`), so a user’s planning annotations survive page reloads.

### 2. Expose Free Agents Explicitly for Planning

- Current behavior:
  - `getTeamPlayers()` in `docs/depth_chart/js/state.js:27-30` filters out free agents (`!p.isFreeAgent && p.team === selectedTeam`), which is correct for the current roster view.
- Product need:
  - For draft/FA planning, users also need visibility into the FA pool by position.
- Requested direction for next iteration:
  - Add a toggle or secondary tab/view in the depth chart UI that shows free agents in the same slot structure (QB, HB, WR1/WR2, etc.), sorted by OVR.
  - This allows side-by-side mental comparison of “current depth” vs “available upgrades” for each position group.

### 3. Documentation Alignment

- Verification report (`.zenflow/tasks/depth-chart-management-ce01/report.md`) describes specialists as K and P only, while the implementation correctly includes LS:
  - Code: `docs/depth_chart/js/ui/depthChart.js:24-28` and `POSITION_GROUPS` entry for `['K', 'P', 'LS']`.
- Requested change:
  - Update that report (and any user-facing docs) to explicitly list LS as part of the Specialists group so expectations match the actual UI.

---

Overall, the current implementation is accepted as v1.  
The items above are requested for the next refinement cycle, with highest priority on: CSS clean-up, CSV normalization parity with `roster_cap_tool`, and the documented test/gitingore adjustments.+
