# Fix bug

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Workflow Steps

### [x] Step: Investigation
<!-- chat-id: 1534f682-7971-46bd-9cee-3545b487f24f -->

Analyze the bug report and investigate the issue.

1. Review the bug description, error messages, and logs
2. Clarify reproduction steps with the user if unclear
3. Check existing tests for clues about expected behavior
4. Locate relevant code sections and identify root cause

Save findings to `{@artifacts_path}/investigation.md` with:
- Bug summary
- Root cause analysis
- Affected components

### [ ] Step: Solution Planning

Design a solution to fix the bug.

1. Propose a fix based on the investigation
2. Consider edge cases and potential side effects
3. Decide if a regression test is feasible; if so, add a separate step after Implementation
4. Update the Implementation step below with fix details, or replace with multiple steps if the fix is complex

Save the plan to `{@artifacts_path}/plan.md`.

### [ ] Step: Implementation

Implement the bug fix.

1. Add/adjust regression test(s) that fail before the fix and pass after
2. Run relevant tests and note results in `{@artifacts_path}/plan.md` or `{@artifacts_path}/investigation.md`

If blocked or uncertain, ask the user for direction.
