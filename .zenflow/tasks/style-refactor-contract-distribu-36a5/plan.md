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

### [x] Step: Locate Contract Distribution UI
- Found modal at `docs/roster_cap_tool/js/ui/modals/contractEditor.js`
- Confirmed CSS variables and drawer styles in `docs/roster_cap_tool/css/styles.css`

### [x] Step: Define clean, reusable styles
- Added CSS utilities: `.drawer__header`, `.drawer__actions`, `.drawer__titlewrap`, `.drawer__subtitle`, `.field`, `.field__label`, `.muted`
- Existing `.drawer`/`.ce-grid` styles retained; input styles centralized

### [x] Step: Refactor contractEditor markup
- Replaced inline styles with semantic classes in `docs/roster_cap_tool/js/ui/modals/contractEditor.js`
- Preserved all `data-testid` attributes for tests

### [x] Step: Polish spacing and readability
- Removed header margin on title; added subtitle style
- Kept columns consistent via `.ce-col` min-width; unit suffix auto via CSS

### [ ] Step: Verify behavior manually
<!-- chat-id: 826c5d24-fecf-444b-ae46-3b78e3457152 -->
- Check saving, resetting, previews and responsiveness
- Ensure dialog open/close animations and focus behavior

### [ ] Step: Final review and handoff
- Summarize changes and provide quick validation steps
