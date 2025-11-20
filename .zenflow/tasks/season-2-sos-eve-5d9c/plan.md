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

### [x] Step: Locate SoS page
- Identify `docs/sos_season2.html` as the page to extend

### [x] Step: Add Scatter tab UI
- Add a new "Scatter" tab and view container to the page

### [x] Step: Load own ELO data
- Implement semicolon-delimited loader for `mega_elo.csv` and map team -> ELO

### [x] Step: Join data to SoS rows
- Attach `self_elo` to SoS rows from the ELO map

### [x] Step: Implement D3 scatter chart
- X: own ELO • Y: SoS (avg opponent ELO), y=x line, colors above/below

### [ ] Step: Quick sanity check
- Verify rendering locally (paths, tooltips, legend) and adjust if needed
