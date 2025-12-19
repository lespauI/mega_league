# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification

**Difficulty**: Medium

Created `spec.md` with:
- Architecture following `roster_cap_tool` patterns (vanilla JS, ES modules, PapaParse)
- Depth chart grid layout with position slots and 1-4 string depth
- Position mapping logic for CSV positions to depth chart slots
- Color coding for status (normal, needs, draft, FA)

---

### [x] Step: Create Directory Structure and HTML
<!-- chat-id: 3bf73d4a-2e4d-45c4-b195-97a47da810b7 -->

Create `docs/depth_chart/` with:
- `index.html` - Main page with team selector and depth chart container
- `css/styles.css` - Adapted from roster_cap_tool
- `js/` directory for modules

---

### [x] Step: Implement Core JavaScript Modules
<!-- chat-id: d200b30f-e247-402e-b4a8-534b891f86d1 -->

Create JS modules:
- `js/csv.js` - Copy from roster_cap_tool
- `js/state.js` - Simplified state management (team selection, players)
- `js/ui/teamSelector.js` - Copy from roster_cap_tool
- `js/ui/depthChart.js` - Core depth chart rendering logic
- `js/main.js` - Boot and initialization

---

### [x] Step: Add Link to Root Index
<!-- chat-id: 15d29ea7-babe-405d-9569-7fa4c6fbfdf5 -->

Add navigation link to the new depth chart tool from `index.html`.

---

### [x] Step: Manual Verification and Report
<!-- chat-id: 197a7795-c952-4897-9bb4-78e1237f5927 -->

1. Load tool and verify team selector works
2. Verify players appear in correct position slots
3. Verify OVR-based ordering
4. Write report to `report.md`

### [x] Step: Review
<!-- chat-id: a7cae3ad-638c-4520-8037-390cb66f22bc -->

Review feedback resolved:

1. **Data Path Specification** - Added explicit CSV paths to spec: `../roster_cap_tool/data/MEGA_*.csv`
2. **Position Mapping** - Updated spec to document all fallback positions (`ROLB`, `MLB`, `LOLB`, `LE`, `RE`)
3. **LS Position** - Added LS to implementation (`DEPTH_CHART_SLOTS` and `POSITION_GROUPS`)
4. **Filter vs Split** - Updated spec data model to use `split` property matching implementation
5. **Status Tracking** - Clarified in spec: current impl only highlights empty slots; draft/FA labels are future enhancement
6. **Player Data Model** - Removed unused `status` field from player object in spec
7. **E2E Tests** - Clarified in spec that E2E tests are out of scope for this phase

### [x] Step: Add e2e tests with playwright
<!-- chat-id: d27712cc-361f-48d6-8e98-3bd2c75182db -->

Created `tests/e2e/depth_chart.spec.ts` with 25 tests covering:

**Happy paths:**
- Page load with correct title and header
- Team selector visible and populated
- Depth chart grid renders with 7 position groups
- All position groups (Offense Skill, O-Line, Edge, DT, LB, Secondary, Specialists)
- Players display with name (F.LastName format) and OVR
- Players ordered by OVR descending within position
- Team selection changes update depth chart

**Edge cases:**
- Position splits (WR1/WR2, CB1/CB2, DT1/DT2, EDGE1/EDGE2) show different players
- Empty needed slots show dash with need styling
- Empty slots beyond max position depth don't show dash
- Correct table column structure (Pos, 1, 2, 3, 4)
- Rapid team switching stability
- Page refresh handling

**Negative cases:**
- Direct navigation works
- No JavaScript errors on load
- No console errors on team change
- CSV assets accessibility

### [x] Step: Did a review
<!-- chat-id: d042a4a5-16f8-40ee-a95c-16aa43956740 -->
<!-- agent: CODEX:5_1_HIGH -->

I need you to complete a review

### [x] Step: Fixes after review
<!-- chat-id: 675d5ff4-3b78-4276-9221-c6b019481e58 -->
<!-- agent: ZEN_CLI:MAX -->

Fixed all items from review.md:

1. **CSS Cleanup** - Removed unused `.dc-*` grid rules and old grid media queries; kept flex-based layout
2. **CSV Loading** - Updated `docs/depth_chart/js/csv.js` to import and use `normalizeTeamRow`/`normalizePlayerRow` from `roster_cap_tool/js/validation.js`
3. **Test Fixes** - Fixed tautological assertion in team selector test; renamed "no console errors" to "no runtime errors" for accuracy
4. **Gitignore** - Added `dist/`, `build/`, `.cache/`, `coverage/`, `*.log`
5. **Documentation** - Updated report.md to include LS in Specialists group

All 25 depth chart tests pass.
