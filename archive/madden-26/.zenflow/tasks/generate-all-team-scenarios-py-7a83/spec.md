# Technical Specification: Team Playoff Scenarios Rework

## Difficulty Assessment: **Medium**

The task involves reworking the data flow, eliminating redundant simulations, and improving the HTML rendering. While architecturally significant, it builds on existing patterns.

---

## Problem Analysis

### Current Issues

1. **Data Inconsistency / Caching Problems**
   - Two separate simulation runs: `calc_playoff_probabilities.py` outputs to `output/playoff_probabilities.json`, while `team_scenario_report.py` runs independent simulations per team
   - Team scenario reports may show different probabilities than the main playoff data
   - Each of 32 teams runs 10,000 simulations independently = 320,000 simulation runs total

2. **Missing Data in HTML**
   - HTML (`docs/team_scenarios.html`) parses markdown files via regex to extract stats
   - This parsing is fragile and can fail to extract data properly
   - Conference/Division parsing uses regex that may not match markdown format correctly

3. **CSS Performance Issues**
   - Heavy use of gradients, box-shadows, transitions on multiple elements
   - External font loading adds latency
   - Large CSS block embedded in HTML

4. **Architecture Problems**
   - Markdown-based data storage is inefficient for programmatic access
   - No single source of truth for playoff probabilities
   - `generate_team_scenario_html.py` only generates the HTML shell, doesn't include data

---

## Technical Context

- **Language**: Python 3.x
- **Dependencies**: 
  - csv (stdlib)
  - json (stdlib)
  - random (stdlib)
  - collections (stdlib)
- **Key Files**:
  - `scripts/generate_all_team_scenarios.py` - Orchestrates team report generation
  - `scripts/team_scenario_report.py` - Runs simulations, generates markdown
  - `scripts/generate_team_scenario_html.py` - Creates HTML viewer
  - `scripts/calc_playoff_probabilities.py` - Core simulation logic (reusable)
  - `output/playoff_probabilities.json` - Existing playoff data output

---

## Implementation Approach

### Solution Overview

Rework the pipeline to:
1. **Generate consolidated JSON data** containing all team scenarios in a single simulation run
2. **Embed JSON in HTML** for direct access (no markdown parsing)
3. **Simplify CSS** for better performance
4. **Remove markdown dependency** for the HTML viewer (markdown files can still be generated optionally)

### Data Flow (New)

```
calc_playoff_probabilities.py
           ↓
generate_all_team_scenarios.py (reworked)
           ↓
output/team_scenarios.json (new consolidated data)
           ↓
generate_team_scenario_html.py (reworked)
           ↓
docs/team_scenarios.html (with embedded JSON)
```

---

## Source Code Changes

### 1. `scripts/generate_all_team_scenarios.py` (Major Rework)

**Current**: Loops through teams, runs independent simulations for each, outputs markdown files.

**New**: 
- Run simulations once, tracking results for all teams simultaneously
- Output consolidated JSON to `output/team_scenarios.json`
- Optionally generate markdown files (for backward compatibility)
- Include: remaining games, game probabilities, record distributions, playoff/division/bye probabilities per record

### 2. `scripts/generate_team_scenario_html.py` (Major Rework)

**Current**: Generates HTML that fetches and parses markdown files at runtime.

**New**:
- Read `output/team_scenarios.json` 
- Embed the JSON data directly in the HTML
- Simplified JavaScript that reads from embedded data
- No fetch calls, no markdown parsing

### 3. `scripts/team_scenario_report.py` (Minor Update)

- Keep existing markdown generation for backward compatibility
- Refactor `run_team_scenarios` to be reusable for consolidated runs

### 4. New Output: `output/team_scenarios.json`

**Structure**:
```json
{
  "generated_at": "ISO timestamp",
  "num_simulations": 10000,
  "teams": {
    "Chiefs": {
      "conference": "AFC",
      "division": "AFC West", 
      "current_record": "5-7-0",
      "win_pct": 0.417,
      "remaining_games": [...],
      "game_probabilities": [...],
      "overall_probabilities": {
        "playoff": 8.7,
        "division": 0.0,
        "bye": 0.0
      },
      "record_outcomes": [
        {
          "record": "7-10-0",
          "frequency": 3178,
          "percentage": 31.8,
          "playoff_pct": 0.0,
          "division_pct": 0.0,
          "bye_pct": 0.0
        },
        ...
      ],
      "most_likely": {
        "record": "7-10-0",
        "frequency": 3178,
        "percentage": 31.8,
        "example_outcomes": [...]
      }
    },
    ...
  }
}
```

---

## CSS Improvements

1. Remove heavy gradients in favor of solid colors with subtle accents
2. Reduce box-shadow usage
3. Use `will-change` sparingly and only where needed
4. Keep transitions minimal (hover states only)
5. Remove external font dependency (use system fonts)

---

## Verification Approach

1. **Run the pipeline**: `python scripts/run_all_playoff_analysis.py`
2. **Verify JSON output**: Check `output/team_scenarios.json` contains all 32 teams with complete data
3. **Test HTML**: Open `docs/team_scenarios.html` in browser
   - Select each team and verify data displays correctly
   - Verify probabilities match `output/playoff_probabilities.json`
   - Test on mobile viewport
4. **Performance check**: Verify page loads quickly without lag
5. **Compare with old reports**: Ensure playoff probabilities are consistent

---

## Files Modified

| File | Change Type |
|------|-------------|
| `scripts/generate_all_team_scenarios.py` | Major rework |
| `scripts/generate_team_scenario_html.py` | Major rework |
| `scripts/team_scenario_report.py` | Minor update (refactor for reuse) |
| `output/team_scenarios.json` | New file |
| `docs/team_scenarios.html` | Generated (output) |

---

## Risk Assessment

- **Low risk**: Changes are isolated to the scenario generation pipeline
- **Backward compatibility**: Markdown files can still be generated
- **Rollback**: Original files can be restored from git

---

## Out of Scope

- Changes to `calc_playoff_probabilities.py` core logic
- Changes to other playoff analysis scripts
- E2E test updates (if any exist for this feature)
