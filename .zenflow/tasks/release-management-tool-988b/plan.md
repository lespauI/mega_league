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
- Remove erroneous out-year add-back overlay (released contracts are fully voided)
- Ensure dead money handled via 60/40 split only (Y0/Y1)
- Zero-dead-money players: free full salary in current and remaining years

### [x] Step: 3. Documentation
- Update usage doc to clarify zero-dead-money releases free salary; projections remove out-year caps (no add-backs)

### [x] Step: 4. Tests
- Add E2E test for Kenny Clark (SF) zero-dead-money release
- Assert Y+1 projection increases by ≥ $10M; Y+2 does not decrease

### [ ] Step: 5. Validation
- Run Playwright tests locally
- Run cap math verification script and review output
