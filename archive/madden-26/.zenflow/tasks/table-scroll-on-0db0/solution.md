Proposed fix description

- Introduce a dedicated horizontal scroll wrapper around wide tables and add safe, mobile‑friendly overflow styles:
  - Add a `.table-wrap` container with `overflow-x: auto; -webkit-overflow-scrolling: touch; overscroll-behavior-x: contain;` and `max-width: 100%`.
  - Ensure tables can exceed the viewport when needed while still filling available space: `.table-wrap > table { min-width: 100%; width: max-content; }`.
  - Keep current `.container` styles unchanged to preserve rounded-corner clipping and shadow. The scroll will occur inside the `.table-wrap`, so the outer `overflow:hidden` no longer obstructs horizontal scrolling.
- Wrap each rendered `<table>` in `<div class="table-wrap">...</div>` in the static HTML and in the generator template to make the fix persist across regenerations.
- Optional accessibility enhancement: add `tabindex="0"` to `.table-wrap` in the generator to enable keyboard horizontal scrolling (left/right arrows) when focused.

Why this works

- The problem stems from wide tables and a lack of an inner scroll context. With a `.table-wrap`, overflow is contained and scrollable within the wrapper even if the page container uses `overflow:hidden`. On iOS Safari, `-webkit-overflow-scrolling: touch` ensures smooth, native momentum scrolling.

Files to be modified

- docs/draft_class_2026.html
  - Add the `.table-wrap` CSS rules in the `<style>` block (near other table styles).
  - Wrap each table with `<div class="table-wrap"> ... </div>`.
- scripts/generate_draft_class_analytics.py
  - In the embedded CSS template, add the `.table-wrap` rules and the `.table-wrap > table` min/width rules.
  - Update HTML template to emit `<div class="table-wrap">` wrappers around each `<table>` occurrence:
    - Team draft quality table
    - Most elites table
    - Per-round hits by team (both tables)
    - Position strength table
  - (Optional) Add `tabindex="0"` to the wrapper for keyboard accessibility.

Testing strategy

- Desktop
  - Narrow the browser window below common breakpoints (e.g., 520px and 800px as used in the CSS) and verify tables become horizontally scrollable within the `.table-wrap` with an inner scrollbar.
  - Confirm sorting still works on `.sortable` tables (click headers) and that the scroll position persists during resort.
  - Visual check: rounded corners and card shadows remain intact; no content bleeds past the container edges.
- Mobile (real devices preferred; emulators acceptable)
  - iOS Safari: verify single‑finger horizontal swipe scrolls the tables; check momentum scrolling works due to `-webkit-overflow-scrolling: touch`.
  - Android Chrome: verify horizontal swipe works and vertical page scroll is not hijacked (thanks to `overscroll-behavior-x: contain`).
  - Validate the sticky sub‑nav continues to function as before.
- Accessibility (quick pass)
  - If `tabindex="0"` is added to the wrapper, tab to the wrapper and use arrow keys to scroll horizontally.

Risk assessment

- Scope: Low to moderate. Changes are additive (styling + wrappers) and localized to tables. Generator changes ensure the fix persists across future outputs.
- Side effects considered:
  - Global `table { width:100% }` remains; the wrapper adds `width: max-content; min-width: 100%` only for tables inside `.table-wrap`, avoiding layout changes to any unwrapped tables.
  - Keeping `.container { overflow:hidden }` preserves visual clipping of rounded corners; scroll happens inside the wrapper, so no scrollbar or content bleeds outside the container.
  - Sorting behavior unaffected, as event listeners target the table element; wrapping does not alter table structure.
- Mitigations:
  - If a table is missed and not wrapped, it will continue to be clipped. The generator change minimizes this risk by emitting wrappers for all known tables.
  - If any consumer relies on measuring `table.offsetWidth` expecting it to equal the card width, the `max-content` width may differ; such code is not present in this repo.

