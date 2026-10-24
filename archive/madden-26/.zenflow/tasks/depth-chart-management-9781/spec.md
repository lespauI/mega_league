# Technical Specification: Depth Chart Layout Fixes

## Difficulty: Easy

## Technical Context
- **Language**: HTML, CSS, JavaScript (ES modules)
- **Location**: `docs/depth_chart/`
- **Framework**: Vanilla JS with modular architecture
- **No external dependencies** for layout (pure CSS grid)

## Issues to Fix

### 1. Position Overlap Bug
**Current state** (`styles.css` lines 419-424):
```css
.field--offense .slot-TE { grid-column: 2; grid-row: 2; }
.field--offense .slot-FB { grid-column: 2; grid-row: 2; }
```
Both TE and FB are assigned to the same grid cell, causing overlap.

**Required changes per user**:
- TE should be with O-line (row 1)
- HB should be left of QB (column 2, row 2)
- FB should be right of QB (column 4, row 2)

**New layout**:
- Row 1 (O-line + TE): LT, LG, C, RG, RT, TE (expand to 6 columns)
- Row 2 (Skill): WR1, HB, QB, FB, WR2

### 2. Text Overflow with Badges
**Current state**: Player names in `.depth-row__name` can overflow and overlap with badges/salary info in `.depth-row__meta`.

**Fix**: Ensure proper flex behavior so name truncates with ellipsis before overlapping meta content.

## Files to Modify

1. **`docs/depth_chart/css/styles.css`**:
   - Change grid to 6 columns for offense
   - Update grid positions for all offensive positions
   - Fix `.depth-row` flex layout for proper text truncation

## Implementation Approach

### Grid Layout Changes
```css
.field--offense {
  grid-template-columns: repeat(6, minmax(120px, 1fr));
}

/* Row 1: O-line + TE */
.field--offense .slot-LT { grid-column: 1; grid-row: 1; }
.field--offense .slot-LG { grid-column: 2; grid-row: 1; }
.field--offense .slot-C { grid-column: 3; grid-row: 1; }
.field--offense .slot-RG { grid-column: 4; grid-row: 1; }
.field--offense .slot-RT { grid-column: 5; grid-row: 1; }
.field--offense .slot-TE { grid-column: 6; grid-row: 1; }

/* Row 2: Skill positions (centered in 6-col grid) */
.field--offense .slot-WR1 { grid-column: 1; grid-row: 2; }
.field--offense .slot-HB { grid-column: 2; grid-row: 2; }
.field--offense .slot-QB { grid-column: 3; grid-row: 2; }
.field--offense .slot-FB { grid-column: 4; grid-row: 2; }
.field--offense .slot-WR2 { grid-column: 5; grid-row: 2; }
```

### Text Overflow Fix
Ensure `.depth-row__name` has `overflow: hidden` and proper `min-width: 0` to allow truncation in flex context.

## Verification

1. Run Playwright screenshot test
2. Verify:
   - No overlapping positions
   - TE appears in row 1 with O-line
   - HB is left of QB, FB is right of QB
   - Long names truncate properly with ellipsis
   - All badges visible without overlap
