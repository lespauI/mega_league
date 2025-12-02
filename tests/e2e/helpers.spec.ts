import { test, expect } from './fixtures';
import { teamSelect, capAvailableValue, tab, activeRosterTable } from './utils/selectors';

import { gotoTool } from './fixtures';

// Tiny compile-time smoke for helpers; minimal runtime assertions
test('helpers compile and basic selectors resolve', async ({ page }) => {
  await gotoTool(page);
  await expect(teamSelect(page)).toBeVisible();
  await expect(capAvailableValue(page)).toBeVisible();
  await tab(page, 'active-roster').click();
  await expect(activeRosterTable(page)).toBeVisible();
});

