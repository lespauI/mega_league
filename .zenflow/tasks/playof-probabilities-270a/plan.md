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
<!-- chat-id: 553238b0-dd0d-4dab-9621-fd90740a22f7 -->

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

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [x] Step: Implementation
<!-- chat-id: 022f9aff-5194-4a16-a2fe-73d51526b183 -->

Implement the task according to the technical specification and general engineering best practices.

1. Break the task into steps where possible.
2. Implement the required changes in the codebase.
3. Add and run relevant tests and linters.
4. Perform basic manual verification if applicable.
5. After completion, write a report to `{@artifacts_path}/report.md` describing:
   - What was implemented
   - How the solution was tested
   - The biggest issues or challenges encountered

### [x] Step: Review Monte Carlo & Implement Probability Capping
<!-- chat-id: 25a750a6-d691-4f1a-afbd-cf26c54ffe7e -->


Implement probability capping with mathematical certainty detection in `scripts/calc_playoff_probabilities.py`:

1. Add `check_mathematical_certainty()` function
   - Worst-case scenario: team loses all, check if still in playoffs → clinched
   - Best-case scenario: team wins all, check if still misses playoffs → eliminated

2. Add `cap_probability()` function
   - Clinched → 100.0%
   - Eliminated → 0.0%
   - Simulation 100% but not clinched → 99.9%
   - Simulation 0% but not eliminated → 0.1%

3. Update `main()` to use certainty detection and capping

4. Run script and verify output:
   - No false 100%/0% for non-certain teams
   - Mathematically certain teams show true 100%/0%

### [x] Step: Review the montecarlo suggest improvements
<!-- chat-id: 362bb8a3-81d3-47ec-bc7f-a36ff9d6460e -->

I need you to do a review of whole playoff probability and sugest improvements

### [x] Step: Fix certainty check logic for other teams' games
<!-- chat-id: 4fff8b74-4e95-4211-ab4e-68c8c4298d31 -->
<!-- Priority: High -->

Fix `check_mathematical_certainty()` - currently uses arbitrary home team as winner for games not involving target team. Should use conference-aware logic:
- **Worst-case**: Same-conference rivals should win their games
- **Best-case**: Same-conference rivals should lose their games

### [x] Step: Fix division/bye probability capping
<!-- chat-id: 671a1cdf-cada-4f30-83e8-36bb2d58dd96 -->
<!-- Priority: Medium -->

Division and bye probabilities shouldn't use same `certainty` status as playoff probability. A team can be clinched for playoffs but not for division winner. Add separate certainty checks for division/bye or only apply capping to playoff probability.

**Completed**: Added `cap_simulation_probability()` function that caps division/bye probabilities at 99.9%/0.1% without using playoff certainty status. Division and bye probabilities now only get simulation-based capping (preventing false 100%/0%) while playoff probability continues to use mathematical certainty detection.

### [ ] Step: Add configurable simulation count
<!-- Priority: Medium -->

Replace hardcoded `num_simulations=1000` with configurable parameter. Consider increasing default to 10,000 for better statistical precision.

### [ ] Step: Add random seed for reproducibility
<!-- Priority: Low -->

Add optional `random.seed()` parameter for debugging and reproducible results.

### [ ] Step: Track conference points in simulation
<!-- Priority: Low -->

Lines 360-366 update conference wins but don't update `conference_points_for/against`. Add point tracking if needed for tiebreakers.

### [ ] Step: Consider tie games in simulation
<!-- Priority: Low -->

Real NFL has rare ties (~0.3% of games). Currently simulation only produces wins/losses. Add small probability for ties if desired for realism.
