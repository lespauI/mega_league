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

### [x] Step: 5. Validation
<!-- chat-id: f2a73b43-4d46-4614-8118-8bb95b83dcc0 -->
- Run Playwright tests locally (15/15 tests passed)
- Run cap math verification script and review output (15/15 assertions passed; see output/cap_tool_verification.json)

### [x] Step: Replayse Y0 Y1, year 1 with real years
<!-- chat-id: b9760f65-84a1-42d1-9883-59f31ed0ef1a -->

Actually, lets get rid of random Year 1 and etc and replce them with real
year labels wired to calendar years, using 2026 as the current franchise
season (so Y+0 = 2026, Y+1 = 2027, etc). Active roster FA Year now shows
the actual calendar year (e.g. 2027) based on team.calendarYear and
contractYearsLeft.
