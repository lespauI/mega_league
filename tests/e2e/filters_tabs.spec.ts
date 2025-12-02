import { test, expect } from './fixtures';
import {
  ensureTab,
  activeRosterTable,
  freeAgentsTable,
  tableRows,
} from './utils/selectors';
import { gotoTool } from './fixtures';

async function getFirstPositionChip(page: import('@playwright/test').Page, containerSelector: string) {
  const container = page.locator(containerSelector);
  // Position chips have a nested span.badge with the POS text; skip "All" and "Clear"
  const chip = container.locator('button.chip', { has: page.locator('span.badge') }).first();
  const pos = (await chip.locator('span.badge').innerText()).trim();
  return { chip, pos };
}

async function getFirstTwoPositionChips(page: import('@playwright/test').Page, containerSelector: string) {
  const container = page.locator(containerSelector);
  const chips = container.locator('button.chip', { has: page.locator('span.badge') });
  const first = chips.nth(0);
  const second = chips.nth(1);
  const pos1 = (await first.locator('span.badge').innerText()).trim();
  const pos2 = (await second.locator('span.badge').innerText()).trim();
  return [
    { chip: first, pos: pos1 },
    { chip: second, pos: pos2 },
  ];
}

test.describe('Filters and Tabs E2E', () => {
  test('Active roster: position filter reduces rows and persists across tab switches', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'active-roster');

    const table = activeRosterTable(page);
    await expect(table).toBeVisible();
    const rows = tableRows(table);
    const beforeCount = await rows.count();
    expect(beforeCount).toBeGreaterThan(0);

    // Pick the first available position chip and apply filter
    const { pos } = await getFirstPositionChip(page, '#active-roster-filters');
    await page.locator('#active-roster-filters button.chip', { has: page.locator('span.badge', { hasText: pos }) }).click();

    // Wait for the table to re-render with fewer rows
    await expect
      .poll(async () => tableRows(activeRosterTable(page)).count(), { timeout: 4000 })
      .not.toBe(beforeCount);

    const afterCount = await tableRows(activeRosterTable(page)).count();
    expect(afterCount).toBeGreaterThan(0);
    expect(afterCount).toBeLessThan(beforeCount);

    // Assert all visible rows have the selected position badge
    const filteredRows = tableRows(activeRosterTable(page));
    const totalFiltered = await filteredRows.count();
    for (let i = 0; i < totalFiltered; i++) {
      const row = filteredRows.nth(i);
      await expect(row.locator(`td[data-label="Player"] .badge.pos-${pos}`)).toHaveCount(1);
    }

    // Switch to another tab and back; the filter should persist
    await ensureTab(page, 'free-agents');
    await ensureTab(page, 'active-roster');
    await expect(activeRosterTable(page)).toBeVisible();
    await expect(tableRows(activeRosterTable(page))).toHaveCount(afterCount);
  });

  test('Free agents: multi-position filter narrows rows and persists across tab switches', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'free-agents');

    const table = freeAgentsTable(page);
    await expect(table).toBeVisible();
    const rows = tableRows(table);
    const beforeCount = await rows.count();
    expect(beforeCount).toBeGreaterThan(0);

    // Select first two position chips
    const [c1, c2] = await getFirstTwoPositionChips(page, '#free-agents-filters');
    await page.locator('#free-agents-filters button.chip', { has: page.locator('span.badge', { hasText: c1.pos }) }).click();
    await page.locator('#free-agents-filters button.chip', { has: page.locator('span.badge', { hasText: c2.pos }) }).click();

    // Wait for count to change
    await expect
      .poll(async () => tableRows(freeAgentsTable(page)).count(), { timeout: 4000 })
      .not.toBe(beforeCount);

    const afterCount = await tableRows(freeAgentsTable(page)).count();
    expect(afterCount).toBeGreaterThan(0);
    expect(afterCount).toBeLessThan(beforeCount);

    // Assert all rows have one of the selected position badges
    const filteredRows = tableRows(freeAgentsTable(page));
    const totalFiltered = await filteredRows.count();
    for (let i = 0; i < totalFiltered; i++) {
      const row = filteredRows.nth(i);
      const hasPos1 = await row.locator(`td[data-label="Player"] .badge.pos-${c1.pos}`).count();
      const hasPos2 = await row.locator(`td[data-label="Player"] .badge.pos-${c2.pos}`).count();
      expect(hasPos1 + hasPos2).toBeGreaterThan(0);
    }

    // Switch tabs and back; counts should persist
    await ensureTab(page, 'dead-money');
    await ensureTab(page, 'free-agents');
    await expect(freeAgentsTable(page)).toBeVisible();
    await expect(tableRows(freeAgentsTable(page))).toHaveCount(afterCount);
  });
});

