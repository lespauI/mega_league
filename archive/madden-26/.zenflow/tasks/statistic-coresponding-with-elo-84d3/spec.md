# Technical Specification: ELO-Based Statistics Visualization

## Task Complexity Assessment

**Complexity Level**: **Medium**

**Reasoning**:
- Straightforward data integration (merging ELO with existing team stats)
- Following established visualization patterns in the codebase
- Multiple graphs to implement (15 charts) but repeating same pattern
- No complex algorithms or architectural changes needed
- Well-defined existing patterns to follow

---

## Technical Context

### Language & Dependencies
- **Frontend**: Vanilla JavaScript with D3.js v7 (CDN: `https://cdn.jsdelivr.net/npm/d3@7`)
- **Data Format**: CSV files (comma-separated with decimal commas e.g., `1297,1`)
- **No Build Process**: Static HTML files served directly

### Existing Architecture
- **Data Sources**:
  - `mega_elo.csv`: Team ELO ratings (32 teams)
  - `output/team_aggregated_stats.csv`: Team statistics with 70+ metrics
- **Visualization Pattern**: Self-contained HTML files in `/docs` directory
- **Chart Type**: D3.js scatter plots with:
  - Team logos as data points
  - Linear regression trend lines
  - Average lines for X and Y axes
  - Interactive tooltips with team details
  - Quadrant analysis
  - R² correlation badges

---

## Implementation Approach

### 1. Data Integration Strategy

**ELO Data Processing**:
- Parse `mega_elo.csv` (European format: decimal comma `,` → needs conversion to `.`)
- Extract columns: `#`, `Team`, `START` (ELO rating)
- Normalize team names to match `team_aggregated_stats.csv` naming convention

**Data Merge**:
- Load both CSVs asynchronously using D3.csv
- Join on team name after normalization
- Handle any mismatches (Cardinals shows as 1101,0 in ELO)

### 2. Visualization File Structure

**New File**: `docs/team_elo_correlations.html`

**Structure**:
```
- HTML boilerplate with D3.js CDN
- Inline CSS (matching existing style guide)
- JavaScript module with:
  - CSV loading utilities (tryCsv function)
  - Number formatting functions
  - Linear regression calculator
  - Scatter plot renderer
  - 15 chart configurations
```

### 3. Chart Configurations (15 Graphs)

#### High-Value Correlations (Strong Expected Relationships)

1. **ELO vs Win Percentage**
   - X: ELO Rating, Y: win_pct
   - Most fundamental correlation - validates ELO system

2. **ELO vs Offensive Efficiency** 
   - X: ELO Rating, Y: yds_per_play
   - Tests if better teams have more efficient offenses

3. **ELO vs Turnover Differential**
   - X: ELO Rating, Y: turnover_diff
   - Measures ball security/takeaway correlation with rating

4. **ELO vs QB Rating**
   - X: ELO Rating, Y: qb_rating
   - Tests quarterback performance impact on team strength

5. **ELO vs Defensive Sacks**
   - X: ELO Rating, Y: def_sacks_per_game
   - Measures pass rush effectiveness correlation

#### Offensive Metrics vs ELO

6. **ELO vs Pass Yards per Attempt**
   - X: ELO Rating, Y: pass_yds_per_att
   - Passing efficiency indicator

7. **ELO vs Rush Yards per Attempt**
   - X: ELO Rating, Y: rush_yds_per_att
   - Running game effectiveness

8. **ELO vs TD per Play**
   - X: ELO Rating, Y: td_per_play
   - Red zone/scoring efficiency

9. **ELO vs Total Offensive Yards**
   - X: ELO Rating, Y: off_yds_per_game
   - Overall offensive production

#### Defensive Metrics vs ELO

10. **ELO vs Defensive Interceptions**
    - X: ELO Rating, Y: def_ints_per_game
    - Takeaway generation

11. **ELO vs Opponent Pass Completion %**
    - X: ELO Rating, Y: pass_comp_pct (inverted interpretation)
    - Coverage effectiveness proxy

12. **ELO vs Points Allowed** (if available, else substitute)
    - Alternative: X: ELO Rating, Y: def_tds
    - Defensive scoring prevention

#### Specialized Metrics vs ELO

13. **ELO vs Sack Rate Differential**
    - X: ELO Rating, Y: (def_sacks_per_game - sacks_allowed_per_game)
    - Net pressure advantage

14. **ELO vs Explosive Play Rate**
    - X: ELO Rating, Y: explosive_plays_per_game
    - Big play capability

15. **ELO vs Interception Differential**
    - X: ELO Rating, Y: (def_ints_per_game - pass_ints_per_game)
    - Passing game net efficiency

### 4. Chart Features (Following Existing Pattern)

**Visual Elements**:
- Team logos (30x30px from logoUrl)
- Background rectangles colored by trend position (red=above, blue=below)
- Gray trend line with R² calculation
- Dashed average lines for X and Y
- Grid lines and axes

**Interactive Features**:
- Hover tooltips showing:
  - Team name
  - X-axis value (ELO)
  - Y-axis value (metric)
  - Win percentage
  - Deviation from trend
  - Quadrant interpretation
- Help icon (?) with metric explanations

**Statistical Display**:
- R² correlation badge with color coding:
  - Strong (≥0.5): Green
  - Moderate (0.25-0.5): Yellow
  - Weak (<0.25): Red

---

## Source Code Changes

### Files to Create

**1. `/docs/team_elo_correlations.html`**
- Complete visualization page
- ~1200-1500 lines (following pattern from team_stats_correlations.html)

### Files to Modify

**2. `/index.html`** (if exists, for navigation)
- Add link to new ELO correlations page

**3. `/.gitignore`** (verify existence)
- Ensure no generated artifacts are tracked (already exists)

---

## Data Model Changes

### ELO Data Structure (from mega_elo.csv)
```javascript
{
  rank: Number,          // #
  team: String,         // Team name
  elo: Number           // START (ELO rating, e.g., 1297.1)
}
```

### Merged Data Structure
```javascript
{
  ...teamStats,         // All fields from team_aggregated_stats.csv
  elo: Number,          // Merged from mega_elo.csv
  logoUrl: String       // Computed from logoId
}
```

---

## Verification Approach

### Manual Testing
1. Open `docs/team_elo_correlations.html` in browser
2. Verify all 15 charts render correctly
3. Test interactions:
   - Hover tooltips display accurate data
   - Help icons show metric explanations
   - All team logos load
4. Check data integrity:
   - All 32 teams present (or filtered appropriately)
   - ELO values match source CSV
   - Statistics values match source CSV

### Cross-Browser Testing
- Chrome/Edge (primary)
- Firefox
- Safari

### Data Validation
```bash
# Verify CSV loading paths
python3 -c "
import csv
with open('mega_elo.csv') as f:
    print(f'ELO teams: {len(list(csv.DictReader(f)))}')
with open('output/team_aggregated_stats.csv') as f:
    print(f'Stats teams: {len(list(csv.DictReader(f)))}')
"
```

### No Automated Tests Required
- Static visualization page
- No backend logic
- Manual verification sufficient for this scope

---

## Implementation Notes

### ELO Data Parsing Considerations
- European decimal format: `1297,1` → needs to be parsed as `1297.1`
- CSV has headers starting with `#;Team;START;;`
- Delimiter is semicolon `;` not comma `,`

### Team Name Normalization
- Must match naming convention from existing stats
- Example: "49ers" vs "San Francisco 49ers"
- Use existing `normalize_team_display` pattern if available in JavaScript

### Performance Considerations
- All 15 charts on single page
- ~32 data points per chart
- D3.js handles this easily
- No lazy loading needed

### Accessibility
- Follow existing pattern with help icons
- Ensure tooltips are keyboard accessible
- Proper ARIA labels on SVG elements

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| ELO team names don't match stats CSV | Implement fuzzy matching or manual mapping |
| European number format causes parsing errors | Use custom parser for comma decimals |
| Too many charts cause page slowdown | Monitor performance; can split into tabs if needed |
| R² correlations are all weak | Document findings; weak correlations are still valuable insights |

---

## Success Criteria

✅ All 15 charts render correctly with data points  
✅ ELO data successfully merged with team statistics  
✅ Interactive features work (tooltips, hover effects)  
✅ R² correlation values calculated accurately  
✅ Page follows existing design patterns and styling  
✅ All 32 teams represented in visualizations  
✅ Page accessible via docs/ directory  

---

## Estimated Effort

- **Data Integration**: 30 minutes
- **Chart Configuration**: 1.5 hours (15 charts × 6 min each)
- **Styling & Polish**: 30 minutes
- **Testing & Verification**: 30 minutes
- **Total**: ~3 hours

---

## Future Enhancements (Out of Scope)

- Dynamic Y-axis metric selector
- Conference filtering
- Time-series ELO tracking
- ELO prediction vs actual performance
- Integration with playoff probability models
