# Fix bug

## Configuration
- **Artifacts Path**: `.zenflow/tasks/{task_id}`
the actual path should be substituted for {@artifacts_path}

---

## Workflow Steps

### [x] Step: Investigation
<!-- chat-id: 001f23e2-e6f0-455a-884e-2f25c7a2b450 -->

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
<!-- chat-id: 24ebbd19-6ef2-4ba8-81da-c278decbcc3c -->

Design a solution to fix the bug:

1. Based on the investigation, propose a fix
2. Consider edge cases and potential side effects
3. Document the solution approach in `{@artifacts_path}/solution.md`:
   - Proposed fix description
   - Files to be modified
   - Testing strategy
   - Risk assessment

### [x] Step: Implementation
<!-- chat-id: 06301dd7-8669-414e-87cc-0cf1d0d17324 -->

Implement the bug fix:

1. Apply the solution designed in the previous step
2. Ensure code follows project conventions and style guidelines
3. Add or update tests to cover the bug scenario
4. Verify the fix resolves the issue
5. Update `{@artifacts_path}/implementation.md` with:
   - Changes made
   - Test results
   - Verification steps performed
