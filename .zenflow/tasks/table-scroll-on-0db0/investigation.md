Summary of the bug
- On mobile devices, wide tables in `docs/draft_class_2026.html` cannot be horizontally scrolled. Content to the right gets clipped instead of being scrollable.

Root cause analysis
- The page-level container applies `overflow:hidden` which clips any overflowing content and prevents a horizontal scrollbar from appearing.
  - In `docs/draft_class_2026.html:13`, the CSS sets: `.container { ... overflow:hidden; }`.
- Tables with many columns (e.g., “Rounds” and other analytics tables) can exceed the viewport width due to fixed/min widths (e.g., `.round-cell { width: 60px; }`), making horizontal overflow necessary on small screens.
- There is no dedicated scroll wrapper (e.g., a `.table-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }`) around tables, so the overflow occurs at the `.container` level where it is hidden.
- Generator source also bakes in this style, meaning regenerated pages will reproduce the issue:
  - `scripts/generate_draft_class_analytics.py:506` includes `.container { ... overflow:hidden; }`.

Affected components
- `docs/draft_class_2026.html` (rendered page users visit)
- `scripts/generate_draft_class_analytics.py` (HTML/CSS generator that defines the `.container` CSS)
- Potentially any other generated pages using the same container CSS pattern

Impact assessment
- Usability: Mobile users cannot access rightmost table columns; key data is inaccessible.
- Accessibility: Lack of horizontal scroll impairs navigation for touch users.
- Scope: All wide tables in the report are affected on small screens; regression recurs on regeneration until the generator CSS or structure is corrected.
