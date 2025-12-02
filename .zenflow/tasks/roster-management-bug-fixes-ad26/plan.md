# Fix bug

## Configuration
- **Artifacts Path**: `.zenflow/tasks/{task_id}`
the actual path should be substituted for {@artifacts_path}

---

## Workflow Steps

### [x] Step: Investigation
<!-- chat-id: 384e8a24-8841-453c-a2d1-547b159d0a8c -->

Analyze the bug report and investigate the issue:

1. Review the bug description and any provided error messages or logs
2. Locate the relevant code sections that might be causing the issue
3. Identify the root cause of the bug
4. Document your findings in `{@artifacts_path}/investigation.md`:
   - Summary of the bug
   - Root cause analysis
   - Affected components
   - Impact assessment

### [x] Step: Solution Design
<!-- chat-id: 7f95c961-1b77-4ba0-9457-08b3b04bb048 -->

Design a solution to fix the bug:

1. Based on the investigation, propose a fix
2. Consider edge cases and potential side effects
3. Document the solution approach in `{@artifacts_path}/solution.md`:
   - Proposed fix description
   - Files to be modified
   - Testing strategy
   - Risk assessment

Notes:
- Proposed fixes documented in `{@artifacts_path}/solution.md`.
- Cap Space = Current Cap − Cap Spent; gate in‑game re‑sign override; decouple Y+1 re‑sign reserve from ΔSpace; ensure Y+1 fully recalculates after releases.

### [x] Step: Implementation
<!-- chat-id: 76f59d15-98c3-4e78-bd35-da766a0d5a0a -->

Implement the bug fix:

1. Apply the solution designed in the previous step
2. Ensure code follows project conventions and style guidelines
3. Add or update tests to cover the bug scenario
4. Verify the fix resolves the issue
5. Update `{@artifacts_path}/implementation.md` with:
   - Changes made
   - Test results
   - Verification steps performed
