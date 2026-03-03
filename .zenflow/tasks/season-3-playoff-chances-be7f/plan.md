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
<!-- chat-id: c3589f0a-7853-4278-bc9d-9903905ac5ff -->

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

### [ ] Step: Implementation

Implement the Season 3 playoff changes per `.zenflow/tasks/season-3-playoff-chances-be7f/spec.md`.

1. In `scripts/calc_playoff_probabilities.py`: change `seasonIndex != 1` → `seasonIndex != 2` (lines 45 and 106, in `load_rankings_data()` and `load_data()`)
2. In `scripts/playoff_race_table.py`: change `seasonIndex != 1` → `seasonIndex != 2` (line 38, in `load_power_rankings()`)
3. In `scripts/run_all_playoff_analysis.py`: update the `calc_sos_by_rankings.py` entry in the `scripts` list to pass `extra_args=['--season-index', '2', '--out-csv', 'output/ranked_sos_by_conference.csv']`
4. Run `python3 scripts/run_all_playoff_analysis.py` from the project root and confirm all steps succeed
5. Spot-check `output/ranked_sos_by_conference.csv`, `output/playoff_probabilities.json`, `docs/playoff_race.html`, `docs/playoff_race_table.html` contain Season 3 data
6. Write a report to `.zenflow/tasks/season-3-playoff-chances-be7f/report.md`
