Implementation Summary

Changes made
- Added horizontal scroll wrapper styles to docs and generator:
  - docs/draft_class_2026.html: added `.table-wrap` CSS with `overflow-x:auto`, `-webkit-overflow-scrolling:touch`, and `.table-wrap > table { width:max-content; min-width:100%; }`.
  - scripts/generate_draft_class_analytics.py: same CSS injected into the embedded `<style>`.
- Wrapped all wide tables in a `.table-wrap` div for scrollability:
  - docs/draft_class_2026.html: wrapped 5 tables (2 team tables, 2 rounds tables, 1 positions table).
  - scripts/generate_draft_class_analytics.py: template updated to emit wrappers around all generated tables.
- Added an auxiliary verification script for this bug scenario:
  - scripts/verify_table_scroll_wrap.py — checks for `.table-wrap` CSS and that all `<table>` elements are wrapped.

Tests and results
- Ran `python3 scripts/verify_table_scroll_wrap.py --html docs/draft_class_2026.html`:
  - Output: `wrap-verify: OK — 5/5 tables wrapped; CSS present`.
- Note: Did not modify the existing `scripts/verify_draft_class_analytics.py` verification beyond earlier experimentation (reverted), to avoid impacting unrelated KPI checks.

Verification steps performed
- Manual code review of docs/draft_class_2026.html to ensure:
  - `.container { overflow:hidden; }` remains unchanged to preserve visual clipping.
  - Each `<table>` is wrapped in `<div class="table-wrap" tabindex="0"> ... </div>`.
  - Added `.table-wrap` CSS directly after the global `table { ... }` rule.
- Generator changes implemented to persist the fix across future regenerations and cover all emitted tables.
- Confirmed wrapper count equals table count and CSS present via the new verifier.

Notes
- The existing analytics verifier may fail on older KPI variants (e.g., missing "Elites share") but this is orthogonal to the scroll bug; no changes were kept to that script.

