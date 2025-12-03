# Vibe code
**Mode:** No predefined workflow

## Agent Instructions
This task does not have a predefined workflow or subtasks.

### Your Approach
- Analyze the task requirements
- Determine the best sequence of actions
- Execute steps as needed
- Document significant decisions or discoveries

### When to Add Structured Steps
**Consider updating this plan with detailed subtasks if:**
- The task becomes more complex than initially expected
- Multiple phases need to be tracked
- Breaking down work into checkboxes would improve clarity

**To add structured workflow:**
Replace the sections below with phase headers that include checkboxes.

Example format (wrapped in code block to prevent parsing):
```
### [ ] Step: 1. Analysis
- Review requirements
- Identify dependencies

### [ ] Step: 2. Implementation
- Build core functionality
- Add error handling
```

---

## Workflow Steps
### [x] Step: 1. Analysis
- Review spec and cap math code
- Identify projection/add-back bug for zero-dead-money releases

### [x] Step: 2. Algorithm Fix
- Update add-back overlay to include all remaining out-years
- Add salary-only fallback for zero-dead-money players

### [x] Step: 3. Documentation
- Update usage doc to clarify zero-dead-money releases add back salary in projections

### [x] Step: 4. Tests
<!-- chat-id: daade0b4-2dd1-44b2-946d-f7b0e82a8f0d -->
- Add E2E test for Kenny Clark (SF) case
- Verify Y+1 and Y+2 increase by ≥ $10M after release

### [x] Step: 5. Validation
<!-- chat-id: 543b7c1a-bae8-4465-ae93-d685f9c72dd0 -->
- Run Playwright tests locally
- Run cap math verification script and review output
- Result: Playwright release.spec.ts passed; zero_dead_money_release.spec.ts failed (Y+1/Y+2 projections did not increase by ≥ $10M).
- Result: scripts/verify_cap_math.py completed with 15/15 assertions passing; report at output/cap_tool_verification.json.
