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

**Problem Summary**:
- Two separate simulation runs causing data inconsistency
- HTML parses markdown via fragile regex (missing data)
- Heavy CSS causing lag
- No single source of truth for scenario data

**Solution**: Consolidate simulations into JSON output, embed in HTML directly, simplify CSS.

See `spec.md` for full details.

---

### [ ] Step 1: Rework generate_all_team_scenarios.py

Modify to run simulations once for all teams and output consolidated JSON:
- Reuse simulation logic from `calc_playoff_probabilities.py`
- Track per-team scenario outcomes in a single simulation run
- Output to `output/team_scenarios.json`
- Include: remaining games, probabilities, record distributions

**Verification**: Run script, check JSON output contains all 32 teams with correct structure.

---

### [ ] Step 2: Rework generate_team_scenario_html.py

Update HTML generation to:
- Read from `output/team_scenarios.json`
- Embed JSON data directly in HTML
- Simplify JavaScript (no fetch/markdown parsing)
- Streamline CSS (remove heavy gradients, reduce shadows)

**Verification**: Open HTML in browser, verify all teams display correctly with matching data.

---

### [ ] Step 3: Integration & Verification

1. Run full pipeline: `python scripts/run_all_playoff_analysis.py`
2. Verify data consistency between `playoff_probabilities.json` and `team_scenarios.json`
3. Test HTML in browser (multiple teams, mobile viewport)
4. Write completion report to `report.md`
