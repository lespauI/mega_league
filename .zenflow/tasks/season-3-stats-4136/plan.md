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

If you are blocked and need user clarification, mark the current step with `[!]` in plan.md before stopping.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: 1db25747-db4e-47ca-90cf-1629a4ed0d5c -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Important: unit tests must be part of each implementation task, not separate tasks. Each task should implement the code and its tests together, if relevant.

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [ ] Step: Fix hardcoded seasonIndex filters

Update the two scripts that hardcode `seasonIndex != 1` so they target Season 3 (`!= 2`):
- `scripts/calc_playoff_probabilities.py` lines 45 and 106: change `!= 1` to `!= 2`
- `scripts/playoff_race_table.py` lines 38 and 106: change `!= 1` to `!= 2`

### [ ] Step: Run the full stats pipeline

Execute `python3 scripts/run_all.py` from the project root to regenerate all Season 3 outputs:
- `output/player_team_stints.csv` (seasonIndex should be 2)
- `output/team_aggregated_stats.csv`
- `output/team_player_usage.csv`
- `output/team_rankings_stats.csv`
- `output/playoff_probabilities.json`
- `docs/playoff_race_table.html` and other HTML dashboards
- Verify `scripts/verify_trade_stats.py` passes

Write a report to `.zenflow/tasks/season-3-stats-4136/report.md` describing what was done and any issues encountered.
