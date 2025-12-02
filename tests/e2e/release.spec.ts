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
  dialogRoot,
  dialogConfirmButton,
} from './utils/selectors';
import { gotoTool } from './fixtures';

test.describe('Release Flow E2E', () => {
  test('releasing a player updates cap and dead money', async ({ page }) => {
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

    // Read the preview savings from the table column "Free cap after release"
    const savingsText = await row.locator('td[data-label="Free cap after release"]').innerText();
    const savings = parseMoney(savingsText);

    // Trigger release action -> modal appears
    await rowActionSelect(row).selectOption('release');
    const dlg = dialogRoot(page);
    await dlg.waitFor({ state: 'visible' });

    // Verify modal preview includes Cap Savings that matches the table column
    const capSavingsLabel = dlg.getByText('Cap Savings', { exact: true });
    const modalSavingsText = await capSavingsLabel.locator('xpath=following-sibling::div[1]').innerText();
    expect(parseMoney(modalSavingsText)).toBe(parseMoney(savingsText));

    // Confirm release
    await dialogConfirmButton(page, /Confirm Release/i).click();
    await dlg.waitFor({ state: 'hidden' });

    // Wait for cap to update
    await page.waitForTimeout(50);
    await page.waitForFunction((b) => {
      const el = document.querySelector('#cap-summary .metric:nth-child(4) .value');
      if (!el) return false;
      const txt = el.textContent || '';
      const cleaned = txt.replace(/[^0-9.\-]/g, '');
      const v = Number(cleaned);
      return Number.isFinite(v) && Math.round(v) !== Math.round(b as number);
    }, before, { timeout: 5000 });

    const after = await readCapAvailable(page);

    // Assert final cap equals table-derived math (and thus modal preview)
    expect(Math.round(after)).toBe(Math.round(before + savings));

    // The player should no longer be in Active roster
    await ensureTab(page, 'active-roster');
    await expect(
      activeRosterTable(page).locator('tbody tr td[data-label="Player"] strong', { hasText: name })
    ).toHaveCount(0);

    // Dead Money tab should list an entry for this player
    await ensureTab(page, 'dead-money');
    await expect(deadMoneyTable(page)).toBeVisible();
    await expect(tableRows(deadMoneyTable(page)).filter({ hasText: name })).toHaveCount(1);
  });
});
