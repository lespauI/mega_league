# Solution Design: Enable Sorting on Roster Power Table

## Proposed fix description

The investigation showed that `docs/power_rankings_roster.html` is missing the JavaScript that wires up sorting for tables with the `sortable` class, even though the table markup and tooltip expect sortable behavior. Other pages (e.g. `docs/draft_class_2026.html`) already ship a small, self-contained “Simple table sorter” script that:

- Finds all `table.sortable` elements.
- Attaches `click` handlers to their header cells (`<th>`).
- Sorts the corresponding `<tbody>` rows by the clicked column, preferring numeric comparison when possible and falling back to locale-aware string comparison.
- Uses `data-sort` attributes when present on cells to control the sort key.
- Toggles sort direction via a `data-sort-dir` attribute on the active header.

The fix is to add the same table sorter logic to the roster power rankings page via its generator script:

1. In `scripts/power_rankings_roster.py`, extend the inline `<script>` block that is currently responsible for search and the team-detail overlay to also include the "Simple table sorter" IIFE used in `docs/draft_class_2026.html`.
2. Keep the sorter logic self-contained and page-local, following the existing pattern:
   - Implement a `getCellValue` helper that prefers `td.getAttribute('data-sort')` when available, otherwise uses trimmed text content.
   - Implement an `asNumber` helper that strips commas and whitespace, attempts `parseFloat`, and returns `NaN` on failure.
   - Implement a `makeComparer` factory that returns a comparison function based on column index and ascending/descending direction, choosing numeric comparison when both values are numeric.
   - Implement `initSortableTables()` that:
     - Locates all `table.sortable` instances on the page.
     - For each table, iterates over the first header row’s cells and attaches `click` handlers that:
       - Determine the next sort direction by toggling a `data-sort-dir` attribute on the clicked header.
       - Build a new ordered list of `<tr>` elements from the existing `tbody` rows using the comparer.
       - Re-append the rows to the `tbody` in sorted order.
   - Wrap the whole module in an IIFE that runs `initSortableTables` on `DOMContentLoaded` (or immediately if the document is already loaded), matching the pattern already used on the draft class page.
3. Ensure the new sorter script is emitted before the closing `</head>` tag in the generated HTML, just like in `docs/draft_class_2026.html`, so the behavior is available as soon as the DOM is ready.
4. Leave the existing search (`initSearch`) and team-detail overlay logic unchanged; they will continue to run as they do now.

With this change, clicking any header in the "Teams – Roster Power Table" will correctly re-order the rows based on that column’s values, honoring `data-sort` attributes and toggling between ascending and descending order on repeated clicks.

## Files to be modified

- `scripts/power_rankings_roster.py`
  - Extend the generated `<script>` contents to include the "Simple table sorter" IIFE used by `docs/draft_class_2026.html` (adapted to this page if needed, but keeping behavior identical).
  - Ensure the sorter initialization runs on page load, either via its own `DOMContentLoaded` listener (as in `draft_class_2026.html`) or by being invoked from the existing `attachTeamDetailHandlers` initialization function.
- `docs/power_rankings_roster.html` (generated artifact)
  - Will be regenerated from `scripts/power_rankings_roster.py` so that the final HTML includes the sorter script in its head `<script>` block.

## Testing strategy

Manual browser verification (primary):

1. Regenerate the roster rankings HTML from the generator script (using the existing project command or script, e.g. running the appropriate `python scripts/power_rankings_roster.py ...` or higher-level build step).
2. Open `docs/power_rankings_roster.html` in a browser.
3. Verify baseline behavior still works:
   - The "Search team" input filters rows as before.
   - Clicking a table row still opens the team-detail overlay.
   - The overlay can be closed via the close button, backdrop click, and the Escape key.
4. Test sorting behavior on the "Teams – Roster Power Table":
   - Click the `Overall` header; confirm rows reorder and that the best/worst overall values move as expected.
   - Click `Overall` again and confirm the order reverses (ascending vs descending), and that only this header has the `data-sort-dir` attribute set.
   - Repeat for other numeric columns (`Off Pass`, `Off Run`, `Def Coverage`, `Pass Rush`, `Run Def`) and confirm they sort numerically based on their `data-sort` values.
   - Optionally click textual columns (`Team`, `Dev traits`, `Top contributors`) and verify they sort alphabetically using text content.
5. After sorting by one or more columns, confirm that clicking a team row still opens the correct team-detail overlay, and that search filtering continues to work on the sorted table.
6. Open the browser developer console to ensure there are no JavaScript errors related to the new sorter script.

Automated / consistency checks (if available in this repo):

- Run any existing unit tests or integration tests that cover HTML generation or front-end behavior (e.g. `pytest`, project-specific test runners, or snapshot tests) to verify that adding the sorter script does not break expectations.
- If the project has HTML diff or snapshot tests for `power_rankings_roster.html`, update expectations to include the new sorter script once behavior is validated.

## Risk assessment

Overall risk: **Low**, localized to the roster rankings page’s front-end behavior.

Potential risks and mitigations:

- **Behavior differences vs reference sorter**:
  - Risk: If the sorter implementation differs from the one in `docs/draft_class_2026.html`, users might see inconsistent sorting rules between pages.
  - Mitigation: Copy the existing "Simple table sorter" logic as-is (modulo quoting/formatting for Python string literals) so the behavior is consistent across pages.

- **Interaction with row click handlers (team-detail overlay)**:
  - Risk: Sorting reorders `<tr>` elements while each row also has a `click` handler to open the overlay.
  - Mitigation: The sorter reuses existing DOM nodes and only re-appends them, so event listeners remain attached. Manual tests will specifically verify that clicking a row after one or more sorts still opens the correct team-detail overlay.

- **Numeric vs string sorting edge cases**:
  - Risk: Some cells may be blank or contain formatted numbers (e.g. with commas or spaces), leading to incorrect comparisons.
  - Mitigation: The sorter uses `data-sort` attributes and a numeric parsing helper (as in the reference implementation) that strips commas/whitespace and falls back to locale-aware string comparison when values are not numeric. This matches the known-good behavior on `draft_class_2026.html`.

- **Impact on other tables**:
  - Risk: If additional tables on the page are later given the `sortable` class unintentionally, they will also gain click-to-sort behavior.
  - Mitigation: This is usually desirable, but the behavior is opt-in via the `sortable` class. The current markup intentionally tags the roster power table with `class="sortable"`, so the new behavior aligns with the existing tip text.

- **Performance considerations**:
  - Risk: On very large tables, repeated client-side sorting could introduce minor UI lag.
  - Mitigation: The roster table is limited to league teams (small N), so the simple DOM-based sort is sufficient and has already been validated on other pages.

Given these factors, adding the sorter script via the generator is a targeted, low-risk fix that restores the advertised functionality without altering existing data structures or back-end logic.

