# Fix bug

## Configuration
- **Artifacts Path**: `.zenflow/tasks/{task_id}`
the actual path should be substituted for {@artifacts_path}

---

## Workflow Steps

### [x] Step: Investigation
<!-- chat-id: 2a59d042-7efe-44cc-9009-d344b8b81caa -->

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
<!-- chat-id: 4a89ffe0-db8d-40b6-9a21-f64400e98aad -->

Design a solution to fix the bug:

1. Based on the investigation, propose a fix
2. Consider edge cases and potential side effects
3. Document the solution approach in `{@artifacts_path}/solution.md`:
   - Proposed fix description
   - Files to be modified
   - Testing strategy
   - Risk assessment

### [x] Step: Implementation
<!-- chat-id: f228791e-6b51-412e-a8d3-993d7aa7e1a9 -->

Implement the bug fix:

1. Apply the solution designed in the previous step — DONE
2. Ensure code follows project conventions and style guidelines — DONE
3. Add or update tests to cover the bug scenario — DONE (smoke in `docs/roster_cap_tool/test.html`)
4. Verify the fix resolves the issue — DONE
5. Update `{@artifacts_path}/implementation.md` — DONE

### [ ] Step: qqew

test

