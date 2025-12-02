# Fix bug

## Configuration
- **Artifacts Path**: `.zenflow/tasks/{task_id}`
the actual path should be substituted for {@artifacts_path}

---

## Workflow Steps

### [x] Step: Investigation
<!-- chat-id: 514355d9-b8ac-4b79-90b1-7a92ca60f420 -->

Analyze the bug report and investigate the issue:

1. Review the bug description and any provided error messages or logs
2. Locate the relevant code sections that might be causing the issue
3. Identify the root cause of the bug
4. Document your findings in `{@artifacts_path}/investigation.md`:
   - Summary of the bug
   - Root cause analysis
   - Affected components
   - Impact assessment

### [ ] Step: Solution Design

Design a solution to fix the bug:

1. Based on the investigation, propose a fix
2. Consider edge cases and potential side effects
3. Document the solution approach in `{@artifacts_path}/solution.md`:
   - Proposed fix description
   - Files to be modified
   - Testing strategy
   - Risk assessment

### [ ] Step: Implementation

Implement the bug fix:

1. Apply the solution designed in the previous step
2. Ensure code follows project conventions and style guidelines
3. Add or update tests to cover the bug scenario
4. Verify the fix resolves the issue
5. Update `{@artifacts_path}/implementation.md` with:
   - Changes made
   - Test results
   - Verification steps performed
