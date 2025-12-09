# Fix bug

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Investigation
<!-- chat-id: 1534f682-7971-46bd-9cee-3545b487f24f -->

Analyze the bug report and investigate the issue.

1. Review the bug description, error messages, and logs
2. Clarify reproduction steps with the user if unclear
3. Check existing tests for clues about expected behavior
4. Locate relevant code sections and identify root cause

Save findings to `{@artifacts_path}/investigation.md` with:
- Bug summary
- Root cause analysis
- Affected components

### [x] Step: Solution Planning
<!-- chat-id: 80b274f5-5f5b-43a5-911f-16f0fea29bb0 -->

Design a solution to fix the bug.

1. Make graph containers horizontally scrollable on narrow viewports by reusing the existing `.chart-wrap` wrapper:
   - Update each affected D3 graph page (`team_stats_explorer.html`, `team_stats_correlations.html`, `team_player_usage.html`, `power_rankings_roster_charts.html`, `rankings_explorer.html`, `sos_graphs.html`, `sos_season2.html`) so that `.chart-wrap` has `width: 100%`, `overflow-x: auto`, `-webkit-overflow-scrolling: touch`, and `overscroll-behavior-x: contain`.
   - Keep the existing `.panel { overflow: hidden; }` styling so the card borders still clip background and vertical overflow, relying on `.chart-wrap` to provide the horizontal scrollbar when the SVG (`width = 1080`) exceeds the viewport.
2. Relax global horizontal overflow locks that prevent scrolling the whole page when content is wider than the viewport:
   - In `docs/playoff_race.html` and `docs/playoff_race_table.html`, remove or override `body { overflow-x: hidden; }` so users can scroll horizontally on mobile if necessary.
   - Where wide tables exist, prefer wrapping them in a horizontally scrollable container (similar to `.table-wrap` patterns in other docs) instead of hiding overflow.
3. Keep the solution scoped to graph/table areas so other layouts remain stable:
   - Avoid changing global layout or card/grid sizing beyond what is needed for scrollability.
   - Use existing utility patterns (e.g. `.table-wrap` in `power_rankings_roster.html` / draft-class docs) to stay consistent with the current design.
4. Plan regression coverage:
   - Add a small targeted regression check (likely Playwright-based) that loads at least one graph page (e.g. `team_stats_explorer.html`) and one wide-table page (e.g. `playoff_race_table.html`) at a mobile-width viewport and asserts that the primary chart/table container has `scrollWidth > clientWidth` (i.e., horizontal scroll is available while the page itself is not globally locked).

Save the plan to `{@artifacts_path}/plan.md`.

### [x] Step: Implementation
<!-- chat-id: f46ec1b3-38ba-44e3-a1a8-d6347470edc1 -->

Implement the bug fix.

1. Added a targeted Playwright regression test (`tests/e2e/docs_scroll_mobile.spec.ts`) that exercises `docs/team_stats_explorer.html` and `docs/playoff_race_table.html` at a mobile viewport and asserts that their primary chart/table containers have `scrollWidth > clientWidth` while `body { overflow-x }` is not locked to `hidden`.
2. Updated the affected docs pages so D3 charts live in horizontally scrollable `.chart-wrap` containers and the playoff race table lives inside a horizontally scrollable `.table-wrap` wrapper, with `body { overflow-x: hidden; }` removed from `docs/playoff_race.html` and `docs/playoff_race_table.html`.
3. Attempted to run the new Playwright test (`npx playwright test tests/e2e/docs_scroll_mobile.spec.ts --project=chromium`), but it failed locally because `@playwright/test` is not installed in this environment. Once dependencies are installed, this test should validate the new mobile scroll behavior.

If blocked or uncertain, ask the user for direction.
