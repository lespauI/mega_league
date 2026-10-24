Summary of the bug

- On `docs/power_rankings_roster.html`, clicking column headers in the “Teams – Roster Power Table” does nothing. The UI tip says “click column headers to sort,” but there is no response when clicked.

Root cause analysis

- The page is missing the JavaScript that initializes sorting for tables with class `sortable`.
- The table markup includes `class="sortable"` and `data-sort` attributes on numeric cells (e.g., Overall, Off Pass, etc.), indicating intent to support sorting by headers.
- However, `docs/power_rankings_roster.html` only includes a script that handles search filtering and the team-detail overlay; it does not attach click handlers to `<th>` elements for sorting.
- Other pages (e.g., `docs/draft_class_2026.html`) include a “Simple table sorter” script that:
  - Adds `click` listeners to header cells (`<th>`) for tables with `table.sortable`.
  - Sorts rows by the clicked column, preferring `data-sort` values when present.
  - Toggles sort direction via a `data-sort-dir` attribute.
- The generator for this page, `scripts/power_rankings_roster.py`, mentions keeping style and table sorter aligned with `draft_class_2026.html`, but currently only injects search and overlay logic. There is no `initSortableTables` logic added to this page’s `<script>` block.

Evidence

- Missing sorter in roster page: `docs/power_rankings_roster.html:111-178, 245-278` contains only search and team detail overlay logic; no sorter initialization.
- Sorter present in reference page: `docs/draft_class_2026.html:156-210` includes the “Simple table sorter” (`initSortableTables`) and binds `click` handlers on `table.sortable th`.
- Generator file does not add sorter: `scripts/power_rankings_roster.py:1690-1760` and `1760-1880` show injected script for search and overlay only.

Affected components

- `docs/power_rankings_roster.html` (generated output that lacks sorter script).
- `scripts/power_rankings_roster.py` (HTML generator that omits sorter initialization code).

Impact assessment

- Users cannot sort the roster power table, reducing interactivity and making it harder to explore rankings by different metrics.
- The UI tip suggests sorting should work, which can confuse users when nothing happens.
- No functional errors or crashes; this is a missing behavior due to absent event handlers. Fix is low risk and localized to the roster page’s script block and/or shared sorter utility inclusion.

