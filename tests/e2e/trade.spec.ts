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

    // Choose a row with a non-zero savings if available, else the first
    const rows = tableRows(table);
    const count = await rows.count();
    let row = rows.first();
    let name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
    let savings = parseMoney(await row.locator('td[data-label="Free cap after release"]').innerText().catch(() => ''));
    for (let i = 0; i < Math.min(count, 10); i++) {
      const candidate = rows.nth(i);
      const candSavings = parseMoney(await candidate.locator('td[data-label="Free cap after release"]').innerText().catch(() => ''));
      const candName = (await rowPlayerName(candidate).innerText().catch(() => '')).trim();
      if (Math.round(candSavings) !== 0 && candName) {
        row = candidate;
        name = candName;
        savings = candSavings;
        break;
      }
    }
    expect(name.length).toBeGreaterThan(0);

    const before = await readCapAvailable(page);
    const expectedAfter = Math.round(before + savings);

    // Trigger Trade (Quick) which uses a native confirm dialog
    page.once('dialog', (d) => d.accept());
    await rowActionSelect(row).selectOption('tradeQuick');

    if (Math.round(before) !== expectedAfter) {
      // Wait for cap to change from the baseline "before"
      await page.waitForFunction((b) => {
        const el = document.querySelector('#cap-summary [data-testid="cap-available"]');
        if (!el) return false;
        const txt = el.textContent || '';
        const cleaned = txt.replace(/[^0-9.\-]/g, '');
        const v = Number(cleaned);
        return Number.isFinite(v) && Math.round(v) !== Math.round(b as number);
      }, before, { timeout: 5000 });
    } else {
      // If expectedAfter equals before, just give the UI a moment
      await page.waitForTimeout(100);
    }

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

