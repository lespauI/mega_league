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

### [ ] Step: Add Link to Root Index

Add navigation link to the new depth chart tool from `index.html`.

---

### [ ] Step: Manual Verification and Report

1. Load tool and verify team selector works
2. Verify players appear in correct position slots
3. Verify OVR-based ordering
4. Write report to `report.md`
