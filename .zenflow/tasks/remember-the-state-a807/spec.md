# Technical Specification: Persist Team Selection

## Overview
Add localStorage persistence for the selected team in the depth chart tool so that when users reload the page, their last selected team is remembered instead of defaulting to the first team (49ers).

## Complexity Assessment
**Easy** - Straightforward implementation following existing localStorage patterns in the codebase.

## Technical Context
- **Language**: JavaScript (ES6 modules)
- **File**: `docs/depth_chart/js/state.js`
- **Dependencies**: None (uses existing localStorage infrastructure)
- **State Management**: Centralized state object with pub-sub pattern
- **Testing**: Playwright e2e tests (`tests/e2e/depth_chart.spec.ts`)

## Current Behavior
1. On page load, `initState()` is called with teams and players data
2. The default team is determined by: `state.selectedTeam || teams[0].abbrName`
3. Since `state.selectedTeam` is null initially, it always defaults to the first team
4. When user changes team via selector, `setState({ selectedTeam: sel.value })` is called
5. The selection is lost on page reload

## Implementation Approach

The codebase already has a localStorage persistence pattern established for:
- `rosterEdits` - player roster modifications
- `depthPlans` - per-team depth chart assignments

We'll follow the same pattern to persist `selectedTeam`:

### Changes Required

#### 1. Add Storage Key (`state.js:18-22`)
Add `selectedTeam` to the `STORAGE_KEYS` object:
```javascript
const STORAGE_KEYS = {
  rosterEdits: `${STORAGE_PREFIX}.rosterEdits`,
  depthPlans: `${STORAGE_PREFIX}.depthPlans`,
  selectedTeam: `${STORAGE_PREFIX}.selectedTeam`,
};
```

#### 2. Load Persisted Team (`state.js:82-112`)
Modify `initState()` to load the persisted team:
- Call `loadPersistedSelectedTeam()` before setting default team
- Use persisted value if it exists and is valid
- Fall back to first team if no persisted value or team doesn't exist

#### 3. Save Team on Change (`state.js:56-80`)
Modify `setState()` to persist when `selectedTeam` changes:
- Check if `selectedTeam` property is being updated
- Call `saveSelectedTeam()` with the new value

#### 4. Helper Functions (`state.js:523-621`)
Add two new helper functions following existing patterns:
- `loadPersistedSelectedTeam()` - reads from localStorage, validates against available teams
- `saveSelectedTeam(teamAbbr)` - writes to localStorage

## Data Model Changes
None - uses existing localStorage string storage.

## API/Interface Changes
None - all changes are internal to `state.js`.

## Edge Cases to Handle
1. **Invalid persisted team** - If stored team no longer exists in MEGA_teams.csv, fall back to first team
2. **localStorage unavailable** - Already handled by existing `getStorage()` function
3. **Malformed data** - Validate that loaded value is a non-empty string
4. **Empty teams list** - Existing code handles this (sets null)

## Verification Approach

### Manual Testing
1. Open depth chart in browser
2. Select a different team (e.g., "KC")
3. Verify selection is visible in dropdown
4. Reload page
5. Verify selected team is still "KC" (not "SF")

### E2E Testing
Add test to `tests/e2e/depth_chart.spec.ts`:
```typescript
test('selected team persists after page reload', async ({ page }) => {
  await gotoDepthChart(page);
  
  const selector = page.locator('[data-testid="team-select"]');
  const options = selector.locator('option');
  const secondTeam = await options.nth(1).getAttribute('value');
  
  await selector.selectOption(secondTeam!);
  await expect(selector).toHaveValue(secondTeam!);
  
  await page.reload();
  await expect(page.locator('[data-testid="team-select"]')).toHaveValue(secondTeam!);
});
```

### localStorage Inspection
Check browser DevTools > Application > Local Storage for key:
- `depthChartPlanner.v1.selectedTeam` should contain the team abbreviation

## Risk Assessment
**Low Risk**
- Isolated change to one file
- Follows established patterns
- No breaking changes to existing functionality
- localStorage failures are already gracefully handled

## Success Criteria
- [x] Team selection is saved to localStorage when changed
- [x] Team selection is restored from localStorage on page load
- [x] Invalid/missing teams fall back to first team gracefully
- [x] Existing e2e tests continue to pass
- [x] New e2e test for persistence passes
