import { test, expect } from './fixtures';
import {
  ensureTab,
  activeRosterTable,
  deadMoneyTable,
  tableRows,
  rowActionSelect,
  rowPlayerName,
  parseMoney,
  readCapAvailable,
} from './utils/selectors';
import { gotoTool } from './fixtures';

test.describe('Trade (Quick) E2E', () => {
  test('trading a player updates cap and dead money', async ({ page }) => {
    await gotoTool(page);

    // Ensure Active Roster is visible
    await ensureTab(page, 'active-roster');
    const table = activeRosterTable(page);
    await expect(table).toBeVisible();

    // Pick the first player row and capture details
    const row = tableRows(table).first();
    const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
    expect(name.length).toBeGreaterThan(0);

    const before = await readCapAvailable(page);

    // Read the table's "Free cap after release" which equals in-game Savings
    const savingsText = await row.locator('td[data-label="Free cap after release"]').innerText();
    const savings = parseMoney(savingsText);
    const expectedAfter = Math.round(before + savings);

    // Trigger Trade (Quick) which uses a native confirm dialog
    const confirmOnce = page.once('dialog', (d) => d.accept());
    await rowActionSelect(row).selectOption('tradeQuick');
    await confirmOnce; // ensure confirm handled

    // Wait for cap to update and match expected preview math
    await page.waitForFunction((exp) => {
      const el = document.querySelector('#cap-summary [data-testid="cap-available"]');
      if (!el) return false;
      const txt = el.textContent || '';
      const cleaned = txt.replace(/[^0-9.\-]/g, '');
      const v = Number(cleaned);
      return Number.isFinite(v) && Math.round(v) === Math.round(exp as number);
    }, expectedAfter, { timeout: 5000 });

    const after = await readCapAvailable(page);
    expect(Math.round(after)).toBe(expectedAfter);

    // The player should no longer be in Active roster
    await ensureTab(page, 'active-roster');
    await expect(
      activeRosterTable(page).locator('tbody tr td[data-label="Player"] strong', { hasText: name })
    ).toHaveCount(0);

    // Dead Money tab should list an entry for this player with move type Trade (Quick)
    await ensureTab(page, 'dead-money');
    await expect(deadMoneyTable(page)).toBeVisible();
    await expect(
      tableRows(deadMoneyTable(page)).filter({ hasText: name }).filter({ hasText: 'Trade (Quick)' })
    ).toHaveCount(1);
  });
});
