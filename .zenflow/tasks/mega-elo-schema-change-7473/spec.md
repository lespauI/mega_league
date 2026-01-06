# Technical Specification: mega_elo.csv Schema Change

## Task Classification
**Difficulty**: Medium

This is a data schema migration task requiring updates to multiple Python scripts and HTML files that read the `mega_elo.csv` file. The changes are straightforward but require careful attention to ensure all consumers of the file are updated correctly.

## Technical Context

### Environment
- **Language**: Python 3
- **Key Files**: 
  - `mega_elo.csv` (data file)
  - `scripts/calc_sos_season2_elo.py` (ELO reader)
  - `stats_scripts/aggregate_rankings_stats.py` (ELO reader)
  - `docs/team_elo_correlations.html` (client-side reader)
  - `docs/sos_season2.html` (client-side reader)
  - `README.md` (documentation)

### Dependencies
- Python `csv` module (standard library)
- No external dependencies required

## Schema Change Details

### Old Schema (Expected by Current Code)
- **Delimiter**: Semicolon (`;`)
- **Column Structure**: 
  - Position 0: Index/Rank number
  - Position 1: Team name
  - Position 2: START (ELO rating)
- **Decimal Format**: Comma (e.g., `1310,075527`)
- **Example**: `1;Broncos;1310,075527`

### New Schema (Current File Format)
- **Delimiter**: Comma (`,`)
- **Column Names**: `#`, `Δ`, `Team`, `Coach`, `Week 14+`
  - `#`: Index/Rank number (column 0)
  - `Δ`: Delta/change indicator (column 1)
  - `Team`: Team name (column 2)
  - `Coach`: Coach name (column 3)
  - `Week 14+`: ELO rating (column 4)
- **Decimal Format**: Dot/period (e.g., `1310.075527`)
- **Example**: `1,0,Broncos,Валера Хвост,1310.075527`

### Key Differences
1. Delimiter changed from semicolon to comma
2. Team name moved from position 1 to position 2
3. ELO value moved from position 2 to position 4
4. Decimal separator changed from comma to dot
5. Added columns: `Δ` (delta), `Coach`
6. Column name changed: `START` → `Week 14+`

## Implementation Approach

### Files Requiring Updates

#### 1. Python Scripts (2 files)

**File**: `scripts/calc_sos_season2_elo.py`
- **Function**: `read_elo_map(elo_csv: str)` (lines 195-213)
- **Changes**:
  - Change delimiter from `;` to `,` in `csv.DictReader`
  - Update column reference from `row.get("START")` to `row.get("Week 14+")`
  - Remove decimal comma-to-dot conversion (no longer needed)
  - Update docstring to reflect new format
  - Update column reference from `row.get("Team")` to use position 2 or column name "Team"

**File**: `stats_scripts/aggregate_rankings_stats.py`
- **Function**: ELO loading section (lines 32-52)
- **Changes**:
  - Change delimiter from `;` to `,` in `csv.reader`
  - Update column indices:
    - Team: `row[1]` → `row[2]`
    - ELO: `row[2]` → `row[4]`
    - Index: `row[0]` (unchanged)
  - Remove `start_raw.replace(',', '.')` (no longer needed)
  - Handle new `Δ` column at position 1

#### 2. HTML/JavaScript Files (2 files)

**File**: `docs/sos_season2.html`
- **Location**: Lines 129-167 (ELO parsing section)
- **Changes**:
  - Update CSV parsing to use comma delimiter (may already be default)
  - Update column references in JavaScript parsing logic
  - Handle new column structure

**File**: `docs/team_elo_correlations.html`
- **Location**: Lines 100-102 (file path references)
- **Changes**: 
  - Update CSV parsing logic for new schema
  - Adjust column indices in data extraction

#### 3. Documentation

**File**: `README.md`
- **Location**: Line 275
- **Current Text**: `mega_elo.csv — team ELO snapshot (semicolon ';' delimited; decimal commas)`
- **New Text**: `mega_elo.csv — team ELO snapshot (comma ',' delimited; columns: #, Δ, Team, Coach, Week 14+)`

### Data Model Changes

#### Before
```python
# Reading logic
reader = csv.DictReader(f, delimiter=";")
team = row.get("Team")           # position 1
elo = row.get("START")           # position 2
elo = float(elo.replace(',', '.'))  # convert decimal comma
```

#### After
```python
# Reading logic
reader = csv.DictReader(f, delimiter=",")
team = row.get("Team")              # position 2
elo = row.get("Week 14+")           # position 4
elo = float(elo)                     # direct conversion (already uses dot)
```

## Verification Approach

### Testing Strategy
1. **Unit Testing**: Verify each updated function can correctly parse the new CSV format
2. **Integration Testing**: Run the full pipeline to ensure end-to-end functionality
3. **Data Validation**: Confirm ELO values are correctly extracted and match expected values

### Verification Commands

```bash
# Test ELO-based SoS calculation
python3 scripts/calc_sos_season2_elo.py --season2-start-row 287

# Test team rankings aggregation
python3 stats_scripts/aggregate_rankings_stats.py

# Run full pipeline
python3 scripts/run_all.py
```

### Expected Outputs
- `output/sos/season2_elo.csv` - SoS calculations using correct ELO values
- `output/team_rankings_stats.csv` - Team stats with correct ELO ratings
- No parsing errors or warnings about missing columns
- HTML visualizations display correct ELO data

### Manual Verification
1. Check that team ELO values in output match source `mega_elo.csv`
2. Verify Broncos ELO = 1310.075527 (first team in file)
3. Confirm all 32 teams are loaded
4. Check HTML pages render ELO data correctly

## Risk Assessment

### Low Risk
- Delimiter and column changes are straightforward
- Changes are isolated to CSV parsing logic
- No database or API changes required

### Potential Issues
1. **Column name with special characters**: "Week 14+" contains a plus sign - ensure proper escaping in DictReader
2. **Backwards compatibility**: Old output files may need regeneration
3. **HTML parsing**: JavaScript CSV parsers may need adjustments for comma delimiter

## Source Code Structure Changes

### Files Modified (6 total)
1. `scripts/calc_sos_season2_elo.py` - Update `read_elo_map()` function
2. `stats_scripts/aggregate_rankings_stats.py` - Update ELO loading section
3. `docs/sos_season2.html` - Update JavaScript CSV parsing
4. `docs/team_elo_correlations.html` - Update JavaScript CSV parsing
5. `README.md` - Update documentation
6. (Optional) Add inline code comments where parsing logic was updated

### Files Created
None - all changes are modifications to existing files

## Implementation Plan

1. **Update Python scripts** (2 files)
   - Modify CSV reader configuration (delimiter)
   - Update column references (indices/names)
   - Remove decimal conversion logic
   
2. **Update HTML/JavaScript files** (2 files)
   - Adjust CSV parsing logic
   - Update column references in data extraction
   
3. **Update documentation** (1 file)
   - Correct README.md description of file format
   
4. **Run verification suite**
   - Execute all scripts that read mega_elo.csv
   - Verify output correctness
   - Check HTML visualizations
   
5. **Generate completion report**
   - Document all changes made
   - List verification results
   - Note any issues encountered
