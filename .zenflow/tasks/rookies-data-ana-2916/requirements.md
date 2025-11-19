# Clarifications (prioritized)
- Do we keep a way to mask dev traits behind a flag (e.g., `--mask-dev`), or should unhidden be the only mode going forward? [NEEDS CLARIFICATION]
- In round hit/miss visualization, should a “hit” include Star (dev=1) or only Elites (X‑Factor + Superstar; dev=3/2)? This changes counts materially. [NEEDS CLARIFICATION]
- Rename “Hidden Spotlight” to “Elites Spotlight” (X‑Factor + Superstar) or to a full “Dev Spotlight” that includes Stars as well? [NEEDS CLARIFICATION]
- Replace all “Hidden/Normal” KPI and table columns with a four‑tier breakdown (XF/SS/Star/Normal)? Any preference for keeping an “Elites share” KPI (XF+SS) alongside the breakdown? [NEEDS CLARIFICATION]
- Should we update docs/README and any smoke/verify scripts that reference “Hidden” naming in their expected outputs as part of this change? (Recommended to avoid confusion.) [NEEDS CLARIFICATION]

# Feature Specification: Unhide Dev Traits in Draft Class Analytics

## User Stories*

### User Story 1 - See true dev traits
**Acceptance Scenarios**:
1. **Given** I run `scripts/generate_draft_class_analytics.py` for a year, **When** the HTML renders player cards and tables, **Then** X‑Factor, Superstar, Star, and Normal are shown explicitly (no “Hidden” masking).
2. **Given** rookies with dev 3/2/1/0 in the CSV, **When** the report is generated, **Then** badges and counts reflect real labels per player, per team, and per position.

### User Story 2 - Understand dev distribution at a glance
**Acceptance Scenarios**:
1. **Given** the KPIs section, **When** I view the page header, **Then** I see counts for XF, SS, Star, Normal and an “Elites share” (XF+SS) percentage bar.
2. **Given** the team and position tables, **When** I sort by dev columns, **Then** I can rank by counts of XF, SS, Star, and Normal.

### User Story 3 - Spotlight top rookies
**Acceptance Scenarios**:
1. **Given** a spotlight section, **When** I open the report, **Then** I see an “Elites Spotlight” (XF+SS) grid ordered by draft position (round.pick) with OVR tags and dev badges.
2. **Given** Stars exist, **When** I need to find them, **Then** I can locate Star counts in team/position tables even if the spotlight excludes Stars.

### User Story 4 - Preserve round analytics meaningfully
**Acceptance Scenarios**:
1. **Given** the round hit/miss table, **When** I view per‑team in round cells, **Then** the definition of “hit” is consistent across the page and documented in a note.
2. **Given** different interpretations (Elites only vs. non‑Normal), **When** a project default is chosen, **Then** the table labels and footnote reflect that default.

---

## Requirements*

- Default behavior shows real dev traits everywhere (no masking).
- Dev badges
  - Labels: “X‑Factor”, “Superstar”, “Star”, “Normal”.
  - Distinct CSS classes per tier (e.g., `dev-xf`, `dev-ss`, `dev-star`, `dev-norm`) with accessible contrast.
  - Badge colors consistent across player cards and tables.
- KPIs
  - Replace “Hidden/Normal” with four KPIs: XF, SS, Star, Normal.
  - Add “Elites share” = (XF+SS)/Total rookies as percent with a progress bar.
- Spotlight
  - Rename “Hidden Spotlight” to “Elites Spotlight”.
  - Cards show team logo (if available), OVR badge, draft round.pick (if both present), name, position chip, and dev badge.
- Team table
  - Columns: Team | # | Avg OVR | Best OVR | XF | SS | Star | Normal.
  - Sorting enabled for all columns; default sort by Avg OVR desc.
- Team “Most Elites” table
  - Rename from “Most hiddens” to “Most elites (XF+SS) — by team”.
  - Columns: Team | Elites (XF+SS) | # | Avg OVR. Sort by Elites desc.
- Positions table
  - Columns: Position | # | Avg OVR | XF | SS | Star | Normal. Sort by Avg OVR desc then # desc.
- Round hit/miss table
  - Default interpretation: “hit” = dev > Normal (XF/SS/Star). This preserves historic intent while traits are unhidden.
  - Table header and footnote indicate: “Hit = any non‑Normal dev (XF/SS/Star)”.
  - Keep existing visualization (bar with percent and fraction hit/total). Limit columns to first 7–10 rounds for layout.
- Data handling
  - Keep existing CSV schema assumptions: `devTrait` in {3,2,1,0}; tolerate unknowns by coercing to Normal (0).
  - Continue to derive OVR from `playerBestOvr` else `playerSchemeOvr`.
  - No change to filtering rookies by `rookieYear`.
- Accessibility and UX
  - Badge colors meet contrast guidelines; tooltips/labels avoid ambiguity.
  - All tables remain sortable; mobile layout unchanged where possible.
- Backward compatibility
  - Optional: provide `--mask-dev` flag to re‑enable masking (defaults to unhidden). If omitted, proceed with unhidden only.
- Documentation
  - Update README Draft Class Analytics section and any verify/smoke scripts to reflect new labels, KPIs, and table headers.

Assumptions (defaults if not clarified):
- “Elites Spotlight” includes XF+SS only; Stars appear in tables but not in spotlight.
- Round “hit” counts XF/SS/Star (non‑Normal), matching prior “Hidden” semantics.
- Keep “Elites share” KPI (XF+SS) in addition to the full breakdown.

## Success Criteria*

- Running `python3 scripts/generate_draft_class_analytics.py --year <Y>` produces an HTML report where:
  - No “Hidden” labels appear; player badges read XF/SS/Star/Normal.
  - KPIs display counts for XF/SS/Star/Normal and an “Elites share” percent bar.
  - Spotlight title reads “Elites Spotlight” and shows XF/SS only, ordered by round.pick then OVR.
  - Team and position tables show four dev columns (XF/SS/Star/Normal) with sorting.
  - “Most elites — by team” ranks teams by XF+SS count.
  - Round hit/miss table footnote states the chosen “hit” definition and the bars match that definition.
- README is updated to remove “Hidden” terminology and to describe the new output and verifications.
- Any verify/smoke scripts that assert on copy or headers are aligned and pass.
- No regressions in file paths, CLI flags, or default output location.
