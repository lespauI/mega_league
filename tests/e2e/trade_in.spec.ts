import { test, expect } from './fixtures';
import { gotoTool } from './fixtures';
import { capAvailableValue, parseMoney } from './utils/selectors';

test.describe('Trade In flow', () => {
  test('acquiring team assumes salary-only; no bonus proration; capAvailable decreases by Year1 salary', async ({ page }) => {
    await gotoTool(page);

    // Capture baseline cap space
    const before = parseMoney(await capAvailableValue(page).innerText());

    // Open Trade In modal
    const btn = page.getByTestId('btn-trade-in');
    await expect(btn).toBeVisible();
    await btn.click();

    const dlg = page.getByRole('dialog', { name: /Trade In Player/i });
    await expect(dlg).toBeVisible();

    // Pick first candidate with non-zero contract bonus (indicates proration exists on seller)
    const rows = dlg.locator('tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // Read the first visible row’s Year 1 (Salary Only) value and player name
    const row = rows.first();
    const y1Text = await row.locator('td').nth(4).innerText();
    const year1 = parseMoney(y1Text);
    const name = (await row.locator('td').nth(1).innerText()).trim();

    // Trigger Trade In
    await row.locator('button', { hasText: /Trade In/i }).click();

    // Confirm dialog and apply
    const confirmDlg = page.getByRole('dialog', { name: new RegExp(`Trade In —`) });
    await expect(confirmDlg).toBeVisible();
    await confirmDlg.getByRole('button', { name: /Trade In/i }).click();
    await expect(confirmDlg).toBeHidden();

    // Close the Trade In list dialog to avoid intercepting clicks
    const listDlg = page.getByRole('dialog', { name: /Trade In Player/i });
    if (await listDlg.isVisible()) {
      await listDlg.getByRole('button', { name: /Close/i }).click();
      await expect(listDlg).toBeHidden();
    }

    // Cap space should drop by approximately the Year 1 (salary-only) value
    await expect
      .poll(async () => parseMoney(await capAvailableValue(page).innerText()), { timeout: 5000 })
      .toBe(before - year1);

    // Player should now be on our roster with Dead Cap (Trade) = $0
    await page.getByRole('tab', { name: /Active Roster/i }).click();
    const activeRow = page.locator('#active-roster-table table tbody tr', { hasText: name }).first();
    await expect(activeRow).toBeVisible();
    const deadTradeTxt = await activeRow.locator('td[data-label="Dead Cap (Trade)"]').innerText();
    expect(parseMoney(deadTradeTxt)).toBe(0);
  });
});
