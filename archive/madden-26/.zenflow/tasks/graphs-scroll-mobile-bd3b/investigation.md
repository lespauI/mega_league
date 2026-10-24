# Investigation: Graphs scroll mobile

## Bug summary

On mobile devices (narrow viewports, e.g. ~375–430px wide), several HTML docs under `docs/` that render D3-based graphs are not usable:

- Graphs appear wider than the screen; only the middle portion is visible.
- Users cannot horizontally scroll to see the full X axis or all points.
- Tooltips and labels at the extremes of the chart are effectively inaccessible.

Reproduction (any of these pages):

1. Serve the repo from the root, for example: `python3 -m http.server 8000`.
2. Open a page such as `docs/team_stats_explorer.html`, `docs/team_stats_correlations.html`, `docs/sos_graphs.html`, or `docs/power_rankings_roster_charts.html`.
3. View it on a mobile device or via browser devtools with a narrow viewport (e.g. iPhone-sized).
4. Observe that charts are clipped horizontally and you cannot scroll to see the full graph content.

## Root cause analysis

### 1. Fixed, desktop-centric SVG chart sizes

Most of the D3 scatterplot pages hard-code large desktop dimensions for the charts:

- `docs/team_stats_explorer.html` — `const width = 1080, height = 480;`
- `docs/team_stats_correlations.html` — `const width = 1080, height = 480;`
- `docs/team_player_usage.html` — `const width = 1080, height = 480;`
- `docs/power_rankings_roster_charts.html` — `const width = 1080, height = 480;`
- `docs/rankings_explorer.html` — `const width = 1080, height = 480;`
- `docs/sos_graphs.html` — `const width = 1080, height = 480;`
- `docs/sos_season2.html` — multiple `const width = 1080;` definitions.

On a typical mobile viewport (≈375–420px wide), these 1080px-wide SVGs cannot shrink to fit, so each chart is much wider than the available space.

### 2. Parent containers hide overflow instead of allowing scroll

The graph containers use `overflow: hidden`, which clips the oversized SVGs instead of letting the user scroll horizontally:

- In the above graph-heavy pages (e.g. `team_stats_explorer.html`, `team_stats_correlations.html`, `team_player_usage.html`, `power_rankings_roster_charts.html`, `rankings_explorer.html`, `sos_graphs.html`), the CSS includes:

  ```css
  .panel {
    margin: 12px 0 14px;
    border: 1px solid #e5e5e5;
    border-radius: 10px;
    overflow: hidden;       /* clips wide charts, no scrollbar */
    background: #fff;
  }
  ```

- The charts are rendered as `<svg width="1080" height="480">` inside `.panel` (often nested via `.chart-wrap`).
- When the viewport is narrower than 1080px, the panel’s width shrinks, but the SVG remains 1080px wide, so the right side is cut off and cannot be reached.

Combined effect:

- The large fixed-width SVG wants to overflow horizontally.
- The `.panel` container explicitly forbids overflow; it does not provide scrollbars.
- So the user is locked into seeing only a central slice of each chart on small screens.

### 3. Global `overflow-x: hidden` on some docs pages

Separate from the D3 scatterplots, some docs pages also disable horizontal scroll at the page level:

- `docs/playoff_race.html`:

  ```css
  body {
    ...
    overflow-x: hidden;
  }
  ```

- `docs/playoff_race_table.html`:

  ```css
  body {
    ...
    overflow-x: hidden;
  }
  ```

Any table or container that ends up wider than the viewport on these pages cannot be scrolled horizontally at all on mobile, because scrolling is disabled at the body level.

### 4. Layout choices that assume desktop widths

Some layout structures in the docs also assume relatively large minimum widths (e.g. cards or grids with `minmax(500px, 1fr)` bases in `docs/stats_dashboard.html`). These are mostly navigational/summary pages, but they reinforce that the overall design was tuned for desktop and not tested on small screens.

While these layouts do not directly cause the D3 charts to be clipped, they contribute to awkward experiences on smaller devices.

## Affected components

Graph-heavy docs where charts are clipped and non-scrollable on mobile:

- `docs/sos_graphs.html`
- `docs/sos_season2.html`
- `docs/team_stats_explorer.html`
- `docs/team_stats_correlations.html`
- `docs/team_player_usage.html`
- `docs/power_rankings_roster_charts.html`
- `docs/rankings_explorer.html`

Docs with global horizontal scrolling disabled (problematic for any wide content, including graphs or tables):

- `docs/playoff_race.html` — `body { overflow-x: hidden; }`
- `docs/playoff_race_table.html` — `body { overflow-x: hidden; }`

Other layout pages that assume desktop widths and may feel cramped on mobile (but are not the primary graph-clipping issue):

- `docs/stats_dashboard.html` (cards grid with large `minmax` base widths).

## Summary of root cause

The mobile issues with the graphs primarily stem from a combination of:

1. **Fixed, desktop-sized SVG dimensions** (`width = 1080`) for all major charts, so charts do not shrink on narrow screens.
2. **Containers with `overflow: hidden`**, especially `.panel` wrappers around charts, which clip the oversized SVGs and prevent horizontal scrolling inside the chart area.
3. **Global `overflow-x: hidden` on some pages**, disabling horizontal scrolling entirely for the whole document.

Together, these decisions make the graph views effectively desktop-only. On mobile, users cannot scroll to see the full chart, even though the data and rendering logic are otherwise correct.

Potential fixes (to be detailed in the Solution Planning step) will likely involve making chart wrappers responsive or horizontally scrollable on small viewports and relaxing `overflow-x` restrictions where appropriate.

