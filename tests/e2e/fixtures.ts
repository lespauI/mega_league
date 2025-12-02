import { test as base, expect } from '@playwright/test';

// Re-export test and expect for convenience
export const test = base;
export { expect } from '@playwright/test';

// Clear localStorage before app scripts run on every navigation
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    try {
      localStorage.clear();
      sessionStorage.clear?.();
    } catch {}
  });
});

/**
 * Navigate to the roster cap tool and wait for key UI to be ready.
 */
export async function gotoTool(page: import('@playwright/test').Page) {
  await page.goto('/docs/roster_cap_tool/');
  // Header title renders immediately
  await expect(page.locator('h1.app-title')).toHaveText(/Roster Cap Tool/i);
  // Wait until cap summary shows Cap Space metric
  const capSpace = page.locator('#cap-summary .metric', { hasText: 'Cap Space' }).locator('.value');
  await expect(capSpace).toBeVisible();
}

