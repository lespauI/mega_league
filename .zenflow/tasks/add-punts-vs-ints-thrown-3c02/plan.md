# Vibe code

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

This task has no predefined workflow. You decide the approach.

### Your Approach

1. Assess task size and complexity
2. For complex tasks, create a structured plan that may include:
   - Requirements gathering
   - Technical specification
   - Planning phase
   - Implementation steps
   - Other steps you find useful in order to complete the task
3. For simple tasks, proceed directly with implementation
4. Update this workflow (current plan.md file) with concrete steps as you identify them

### When to Add Structure

Add detailed steps when:
- Task is more complex than initially expected
- Multiple phases need tracking
- Breaking down work improves clarity

If blocked or uncertain, ask the user for direction.

---

## Workflow Steps

### [x] Step: Locate correlations page and data keys
Found `docs/team_stats_correlations.html` and confirmed CSV fields `punts_per_game` and `pass_ints_per_game` in `output/team_aggregated_stats.csv`.

### [x] Step: Add Punts vs INTs chart
Inserted a new chart config in `docs/team_stats_correlations.html` titled "Drive Outcomes — Punts vs INTs Thrown" using `punts_per_game` vs `pass_ints_per_game`, with labels, insight, metric help, and quadrant help.

### [x] Step: Update relationship counts in UI
Updated counts from 34 to 35 in `docs/team_stats_correlations.html`, `docs/stats_dashboard.html`, `index.html`, and `scripts/generate_index.py` description.

### [x] Step: Sanity-check data availability
Verified the referenced keys exist in the CSV and match usage patterns elsewhere in the file.

