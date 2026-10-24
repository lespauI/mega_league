# Implementation

## Changes made

- Updated the roster power rankings HTML generator in `scripts/power_rankings_roster.py` to inject the same "Simple table sorter" script used on the draft analytics pages.
  - The generated `<head>` script block now includes a small IIFE that:
    - Locates all `table.sortable` instances.
    - Attaches `click` handlers to their header cells (`<th>`).
    - Sorts the corresponding `<tbody>` rows by the clicked column, preferring numeric comparison via a helper that parses numbers (stripping commas/whitespace) and falling back to locale-aware string comparison when needed.
    - Uses a `data-sort-dir` attribute on the active header to track and toggle sort direction between ascending and descending, re-appending sorted rows to the table body.
  - The existing search (`initSearch`) and team-detail overlay logic are left unchanged and still run inside their own IIFE.
- Regenerated `docs/power_rankings_roster.html` via `scripts/power_rankings_roster.py` so the published report now includes the sorter script in its inline `<script>` block.
- Added a new unit test in `tests/test_power_rankings_roster.py` (`HtmlReportIncludesSorterTests.test_render_html_report_includes_sortable_table_script`) that calls `render_html_report` with a small, synthetic `teams_metrics` payload and then asserts that the resulting HTML file contains:
  - The "Simple table sorter" comment line.
  - The `initSortableTables` function definition.
  - References to `table.sortable`, confirming that the sortable table markup and script are emitted together.

## Test results

- Attempted to run the test suite with `pytest tests/test_power_rankings_roster.py`, but `pytest` is not installed in the current environment (`pytest: command not found`).
- Despite the missing test runner, the new test is self-contained and should pass once `pytest` (or an equivalent test runner) is available, as it only relies on:
  - `scripts.power_rankings_roster.render_html_report`.
  - Standard file-system writes/reads under the `output/` directory.

## Verification steps performed

- Regenerated the roster power rankings HTML via:
  - `python3 scripts/power_rankings_roster.py --players MEGA_players.csv --teams MEGA_teams.csv --out-html docs/power_rankings_roster.html --out-csv output/power_rankings_roster.csv --no-export-rosters`.
- Manually inspected `docs/power_rankings_roster.html` to confirm:
  - The inline `<script>` in the `<head>` now includes the full "Simple table sorter" IIFE with `getCellValue`, `asNumber`, `makeComparer`, and `initSortableTables` implementations identical in behavior to those on `docs/draft_class_2026.html`.
  - `initSortableTables` is wired to `DOMContentLoaded` (or runs immediately if the document is already loaded), ensuring the sorter is initialized whenever the page is opened.
  - The main roster table retains `class="sortable"` and uses `data-sort` attributes on numeric cells, so clicking headers will sort by those numeric values while leaving existing search and team-detail interactions intact.

Recommended manual UI verification (for a browser session outside this environment):

1. Open `docs/power_rankings_roster.html` in a browser.
2. In the "Teams – Roster Power Table":
   - Click `Overall` and confirm the rows reorder by the `data-sort` overall score.
   - Click `Overall` again and confirm the sort order reverses.
   - Repeat for other numeric columns (Off Pass, Off Run, Def Coverage, Pass Rush, Run Def).
3. After sorting, confirm that:
   - The search box still filters rows by team name/abbrev.
   - Clicking a team row still opens the correct team-detail overlay, and the overlay can be closed as before (button, backdrop, Escape key).

