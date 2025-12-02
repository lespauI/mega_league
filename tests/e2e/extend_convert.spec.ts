import { test, expect } from './fixtures';
import {
  ensureTab,
  activeRosterTable,
  tableRows,
  rowActionSelect,
  rowPlayerName,
  parseMoney,
  readCapAvailable,
  dialogRoot,
  dialogConfirmButton,
} from './utils/selectors';
import { gotoTool } from './fixtures';

async function findRowWithEnabledExtend(page) {
  const table = activeRosterTable(page);
  await expect(table).toBeVisible();
  const rows = tableRows(table);
  const total = await rows.count();
  for (let i = 0; i < total; i++) {
    const row = rows.nth(i);
    const hasEnabled = await row.locator("td[data-label='Action'] option[data-testid='action-extend']:not([disabled])").count();
    if (hasEnabled > 0) return row;
  }
  return null;
}

test.describe('Extension + Conversion E2E', () => {
  test('Extension updates preview, cap, and contract fields', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'active-roster');

    // Find a row with an enabled Extension action
    const row = await findRowWithEnabledExtend(page);
    expect(row).not.toBeNull();
    if (!row) return; // type guard for TS

    const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
    expect(name.length).toBeGreaterThan(0);

    // Capture baseline cap space
    const before = await readCapAvailable(page);

    // Open extension modal
    await rowActionSelect(row).selectOption('extend');
    const dlg = dialogRoot(page);
    await dlg.waitFor({ state: 'visible' });

    // Tweak inputs minimally to force a change and predictable assertion: set salary to 0
    const salary = dlg.locator('#ext-salary');
    await salary.fill('0');

    // Wait for preview to compute and read delta and remaining
    await expect
      .poll(async () => parseMoney(await dlg.locator('#ext-remaining').innerText()), { timeout: 2000 })
      .not.toBe(0);
    const deltaText = await dlg.locator('#ext-delta').innerText();
    const remainingText = await dlg.locator('#ext-remaining').innerText();
    const previewDelta = parseMoney(deltaText);
    const previewRemaining = parseMoney(remainingText);

    // Confirm
    await dialogConfirmButton(page, /Apply Extension/i).click();
    await dlg.waitFor({ state: 'hidden' });

    // Wait briefly and read new cap space
    await page.waitForTimeout(50);
    const after = await readCapAvailable(page);

    // Assert delta semantics: previewDelta is Cap Impact (positive = less space).
    // Cap Space after = before - previewDelta, so change in space = -(previewDelta).
    expect(Math.round(after - before)).toBe(Math.round(-previewDelta));
    expect(Math.round(after)).toBe(Math.round(before - previewDelta));

    // Verify contract column updated (salary should reflect $0 now)
    await ensureTab(page, 'active-roster');
    const table = activeRosterTable(page);
    const rowByName = table
      .locator('tbody tr')
      .filter({ has: page.locator('td[data-label="Player"] strong', { hasText: name }) })
      .first();
    await expect(rowByName).toHaveCount(1);
    const contractCell = rowByName.locator('td[data-label="Contract"]');
    const contractText = (await contractCell.innerText().catch(() => '')).trim();
    expect(contractText).toMatch(/\$0/);
  });

  test('Conversion updates preview and current-year cap hit', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'active-roster');

    const table = activeRosterTable(page);
    await expect(table).toBeVisible();

    // Pick the first player
    const row = tableRows(table).first();
    const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
    expect(name.length).toBeGreaterThan(0);

    // Capture baseline cap space and the player's current-year cap cell
    const before = await readCapAvailable(page);
    const oldCapText = await row.locator('td[data-label="2025 Cap"]').innerText();
    const oldCap = parseMoney(oldCapText);

    // Open conversion modal
    await rowActionSelect(row).selectOption('convert');
    const dlg = dialogRoot(page);
    await dlg.waitFor({ state: 'visible' });

    // Wait for preview to compute and read delta and remaining (defaults provide a valid conversion)
    await expect
      .poll(async () => parseMoney(await dlg.locator('#conv-remaining').innerText()), { timeout: 2000 })
      .not.toBe(0);
    const deltaText = await dlg.locator('#conv-delta').innerText();
    const remainingText = await dlg.locator('#conv-remaining').innerText();
    const previewDelta = parseMoney(deltaText);
    const previewRemaining = parseMoney(remainingText);

    // Confirm
    await dialogConfirmButton(page, /Apply Conversion/i).click();
    await dlg.waitFor({ state: 'hidden' });

    // Wait and read new cap space
    await page.waitForTimeout(50);
    const after = await readCapAvailable(page);

    // Assert delta semantics: change in Cap Space is the negative of Cap Impact.
    expect(Math.round(after - before)).toBe(Math.round(-previewDelta));
    expect(Math.round(after)).toBe(Math.round(before - previewDelta));

    // Verify player's current-year cap cell updated by approx the preview delta
    await ensureTab(page, 'active-roster');
    const rowByName = table
      .locator('tbody tr')
      .filter({ has: page.locator('td[data-label="Player"] strong', { hasText: name }) })
      .first();
    await expect(rowByName).toHaveCount(1);
    const newCapText = await rowByName.locator('td[data-label="2025 Cap"]').innerText();
    const newCap = parseMoney(newCapText);
    expect(Math.round(newCap)).toBe(Math.round(oldCap + previewDelta));
  });
});
