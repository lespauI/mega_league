# Technical Specification: Depth Chart Management Tool

## Task Difficulty: **Medium**

Multi-position roster visualization with grouped layout, similar to existing roster_cap_tool architecture. 

## Technical Context

- **Language**: JavaScript (ES Modules, vanilla JS)
- **Dependencies**: PapaParse (CSV parsing via CDN)
- **Existing Pattern**: `docs/roster_cap_tool/` - team selector, state management, table rendering
- **Data Source**: `../roster_cap_tool/data/MEGA_players.csv`, `../roster_cap_tool/data/MEGA_teams.csv` (relative paths from depth_chart directory)

## Implementation Approach

Create a new standalone HTML tool at `docs/depth_chart/` that reuses the architecture patterns from `roster_cap_tool`:

1. **Team Selector**: Reuse same pattern - dropdown with all teams from MEGA_teams.csv
2. **State Management**: Simplified version of state.js with team selection and player data
3. **Depth Chart View**: Grid layout showing positions with ranked players per position

### Depth Chart Structure (from screenshot)

The depth chart groups players by position slots:

| Position Group | Slots |
|----------------|-------|
| Offense Skill | QB, HB, FB, WR1, WR2, TE |
| Offensive Line | LT, LG, C, RG, RT |
| Edge Rushers | EDGE (x2) |
| Interior DL | DT (x2) |
| Linebackers | SAM, MIKE, WILL |
| Secondary | CB1, CB2, FS, SS |
| Specialists | K, P, LS |

Each slot shows up to 4 players (1st string through 4th string).

### Position Mapping Logic

Map CSV positions to depth chart slots:
- `QB` → QB
- `HB`, `RB` → HB
- `FB` → FB
- `WR` → WR1/WR2 (top half by OVR are WR1, bottom half are WR2)
- `TE` → TE
- `LT`, `LG`, `C`, `RG`, `RT` → Respective OL positions
- `LEDGE`, `REDGE`, `LE`, `RE` → EDGE (combined, split into EDGE1/EDGE2)
- `DT` → DT (split into DT1/DT2)
- `SAM`, `ROLB` → SAM
- `MIKE`, `MLB` → MIKE
- `WILL`, `LOLB` → WILL
- `CB` → CB1/CB2 (top by OVR split between slots)
- `FS`, `SS` → Respective safety positions
- `K`, `P`, `LS` → Specialists

### Depth Ordering

Players ranked within each slot by `playerBestOvr` (or `playerSchemeOvr` as fallback), descending.

### Empty Slots & Needs Highlighting

- If a slot has fewer than expected starters, highlight cell (cyan in mockup = "needs attention")
- "draft" label = position need for draft planning
- "FA" label = free agent target

## Source Code Structure

```
docs/depth_chart/
├── index.html          # Main HTML with layout structure
├── css/
│   └── styles.css      # Reuse patterns from roster_cap_tool with depth chart specific additions
└── js/
    ├── main.js         # Boot, load data, initialize
    ├── csv.js          # CSV loading (copy from roster_cap_tool)
    ├── state.js        # Simplified state (team selection, players)
    └── ui/
        ├── teamSelector.js    # Copy from roster_cap_tool
        └── depthChart.js      # Core depth chart grid rendering
```

Also link from root `index.html` for discoverability.

## Data Model

```javascript
// Depth chart slot configuration
// `split: 0` = first half of sorted players, `split: 1` = second half
const DEPTH_CHART_SLOTS = [
  { id: 'QB', label: 'QB', positions: ['QB'], max: 3 },
  { id: 'HB', label: 'HB', positions: ['HB', 'RB'], max: 3 },
  { id: 'FB', label: 'FB', positions: ['FB'], max: 1 },
  { id: 'WR1', label: 'WR1', positions: ['WR'], max: 4, split: 0 },
  { id: 'WR2', label: 'WR2', positions: ['WR'], max: 4, split: 1 },
  { id: 'TE', label: 'TE', positions: ['TE'], max: 4 },
  { id: 'LT', label: 'LT', positions: ['LT'], max: 2 },
  { id: 'LG', label: 'LG', positions: ['LG'], max: 2 },
  { id: 'C', label: 'C', positions: ['C'], max: 2 },
  { id: 'RG', label: 'RG', positions: ['RG'], max: 2 },
  { id: 'RT', label: 'RT', positions: ['RT'], max: 2 },
  { id: 'EDGE1', label: 'EDGE', positions: ['LEDGE', 'REDGE', 'LE', 'RE'], max: 3, split: 0 },
  { id: 'EDGE2', label: 'EDGE', positions: ['LEDGE', 'REDGE', 'LE', 'RE'], max: 3, split: 1 },
  { id: 'DT1', label: 'DT', positions: ['DT'], max: 3, split: 0 },
  { id: 'DT2', label: 'DT', positions: ['DT'], max: 3, split: 1 },
  { id: 'SAM', label: 'SAM', positions: ['ROLB', 'SAM'], max: 2 },
  { id: 'MIKE', label: 'MIKE', positions: ['MLB', 'MIKE'], max: 2 },
  { id: 'WILL', label: 'WILL', positions: ['LOLB', 'WILL'], max: 2 },
  { id: 'CB1', label: 'CB1', positions: ['CB'], max: 4, split: 0 },
  { id: 'CB2', label: 'CB2', positions: ['CB'], max: 4, split: 1 },
  { id: 'FS', label: 'FS', positions: ['FS'], max: 2 },
  { id: 'SS', label: 'SS', positions: ['SS'], max: 2 },
  { id: 'K', label: 'K', positions: ['K'], max: 1 },
  { id: 'P', label: 'P', positions: ['P'], max: 1 },
  { id: 'LS', label: 'LS', positions: ['LS'], max: 1 },
];

// Player display in cell
{
  name: "J.Herbert",       // Formatted as "FirstInitial.LastName"
  ovr: 88,
  status: 'normal' | 'need' | 'draft' | 'fa'
}
```

## UI Layout

Grid-based layout with:
- Header row: Position slot names
- Column headers: "1", "2", "3", "4" for string depth
- Row per position slot
- Cells showing player name (abbreviated), can be styled by status

### Color Coding (matching mockup)
- Normal cell: default panel background
- Cyan (`#06b6d4`): Position needs attention (uncertainty/target)
- Yellow (`#eab308`): Specific need highlight
- Orange (`#f97316`): Free agent

## Verification Approach

1. **Manual Testing**: 
   - Load tool, select team
   - Verify players appear in correct positions
   - Verify sorting by OVR works correctly
   - Verify position splitting (WR1/WR2, EDGE1/EDGE2, etc.) works

2. **E2E Test** (optional):
   - Add smoke test to verify page loads and team selector works
   - Test in `tests/e2e/depth_chart.spec.ts`

## Implementation Steps

1. Create directory structure `docs/depth_chart/`
2. Create index.html with grid layout
3. Copy and adapt css/styles.css from roster_cap_tool
4. Copy csv.js and adapt state.js (simplified)
5. Copy teamSelector.js
6. Implement depthChart.js with position grouping logic
7. Wire up main.js to boot the application
8. Add link to root index.html
9. Manual verification
