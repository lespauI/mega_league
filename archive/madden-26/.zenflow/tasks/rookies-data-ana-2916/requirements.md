# Decisions from Clarifications
- Unhidden only: remove masking entirely; no `--mask-dev` mode.
- Round “hit” includes Stars: default hits = dev in {3,2,1}. Add a second rounds table for Elites‑only hits (dev in {3,2}).
- Spotlight = “Elites Spotlight”: includes X‑Factor + Superstar only (excludes Stars).
- KPIs: replace Hidden/Normal with XF/SS/Star/Normal; add distribution grading based on targets XF ≥ 10%, SS ≥ 15%.
- Documentation/scripts: update README and any verify/smoke scripts to remove “Hidden” terminology and reflect new outputs.

# Feature Specification: Unhide Dev Traits in Draft Class Analytics

## User Stories*

### User Story 1 - See true dev traits
**Acceptance Scenarios**:
1. **Given** I run `scripts/generate_draft_class_analytics.py` for a year, **When** the HTML renders player cards and tables, **Then** X‑Factor, Superstar, Star, and Normal are shown explicitly (no “Hidden” masking).
2. **Given** rookies with dev 3/2/1/0 in the CSV, **When** the report is generated, **Then** badges and counts reflect real labels per player, per team, and per position.

### User Story 2 - Understand dev distribution at a glance
**Acceptance Scenarios**:
1. **Given** the KPIs section, **When** I view the page header, **Then** I see counts and percentages for XF, SS, Star, Normal and a distribution grading that evaluates XF vs a 10% target and SS vs a 15% target, along with an “Elites share” (XF+SS) percentage bar.
2. **Given** the team and position tables, **When** I sort by dev columns, **Then** I can rank by counts of XF, SS, Star, and Normal.

### User Story 3 - Spotlight top rookies
**Acceptance Scenarios**:
1. **Given** a spotlight section, **When** I open the report, **Then** I see an “Elites Spotlight” (XF+SS) grid ordered by draft position (round.pick) with OVR tags and dev badges.
2. **Given** Stars exist, **When** I need to find them, **Then** I can locate Star counts in team/position tables even if the spotlight excludes Stars.

### User Story 4 - Preserve round analytics meaningfully
**Acceptance Scenarios**:
1. **Given** the round hit/miss tables, **When** I view per‑team in round cells, **Then** one table shows hits = non‑Normal (XF/SS/Star) and a second table shows Elites‑only hits (XF/SS), with both definitions documented in notes.
2. **Given** different interpretations (Elites only vs. non‑Normal), **When** a project default is chosen, **Then** the table labels and footnote reflect that default.

---

## Requirements*

- Default behavior shows real dev traits everywhere (no masking). No CLI flag to mask.
- Dev badges
  - Labels: “X‑Factor”, “Superstar”, “Star”, “Normal”.
  - Distinct CSS classes per tier (e.g., `dev-xf`, `dev-ss`, `dev-star`, `dev-norm`) with accessible contrast.
  - Badge colors consistent across player cards and tables.
- KPIs
  - Replace “Hidden/Normal” with four KPIs: XF, SS, Star, Normal (counts and percentages).
  - Add “Elites share” = (XF+SS)/Total rookies as percent with a progress bar.
  - Distribution grading: compute simple badges for XF and SS vs targets:
    - Targets: XF ≥ 10%, SS ≥ 15%.
    - Badge logic per tier: On‑target (≥ target), Near‑target (≥ 75% of target), Below‑target (< 75% of target).
    - Display as small badges next to XF% and SS% (e.g., XF 11.2% — On‑target).
- Spotlight
  - Rename “Hidden Spotlight” to “Elites Spotlight” (XF+SS only; Stars excluded).
  - Cards show team logo (if available), OVR badge, draft round.pick (if both present), name, position chip, and dev badge.
- Team table
  - Columns: Team | # | Avg OVR | Best OVR | XF | SS | Star | Normal.
  - Sorting enabled for all columns; default sort by Avg OVR desc.
- Team “Most Elites” table
  - Rename from “Most hiddens” to “Most elites (XF+SS) — by team”.
  - Columns: Team | Elites (XF+SS) | # | Avg OVR. Sort by Elites desc.
- Positions table
  - Columns: Position | # | Avg OVR | XF | SS | Star | Normal. Sort by Avg OVR desc then # desc.
- Round hit/miss tables
  - Table A (Default): hits = any non‑Normal dev (XF/SS/Star). Header and footnote indicate: “Hit = XF/SS/Star”.
  - Table B (Elites only): hits = Elites (XF/SS). Header and footnote indicate: “Hit = Elites (XF/SS)”.
  - Keep existing visualization (bar with percent and fraction hit/total). Limit columns to first 7–10 rounds per table.
- Data handling
  - Keep existing CSV schema assumptions: `devTrait` in {3,2,1,0}; tolerate unknowns by coercing to Normal (0).
  - Continue to derive OVR from `playerBestOvr` else `playerSchemeOvr`.
  - No change to filtering rookies by `rookieYear`.
- Accessibility and UX
  - Badge colors meet contrast guidelines; tooltips/labels avoid ambiguity.
  - All tables remain sortable; mobile layout unchanged where possible.
- Backward compatibility
  - No masking fallback. Remove or update any references to “Hidden” in UI and docs.
- Documentation
  - Update README Draft Class Analytics section and any verify/smoke scripts to reflect new labels, KPIs, and table headers.

Assumptions
- Spotlight excludes Stars; Stars are fully represented in tables.
- Round Table A uses non‑Normal (XF/SS/Star); Round Table B uses XF/SS only.
- Keep “Elites share” KPI (XF+SS) in addition to the full breakdown and grading badges.

## Success Criteria*

- Running `python3 scripts/generate_draft_class_analytics.py --year <Y>` produces an HTML report where:
  - No “Hidden” labels appear; player badges read XF/SS/Star/Normal.
  - KPIs display counts and percentages for XF/SS/Star/Normal, an “Elites share” percent bar, and grading badges for XF and SS vs targets (10% and 15%).
  - Spotlight title reads “Elites Spotlight” and shows XF/SS only, ordered by round.pick then OVR.
  - Team and position tables show four dev columns (XF/SS/Star/Normal) with sorting.
  - “Most elites — by team” ranks teams by XF+SS count.
  - Two rounds tables are present: Table A uses hits = XF/SS/Star; Table B uses hits = XF/SS only. Each has clear footnotes and matching bar logic.
- README and any verify/smoke scripts are updated to remove “Hidden” terminology and to describe new labels, KPIs, grading, and tables; checks pass.
- No regressions in file paths, CLI flags, or default output location.
