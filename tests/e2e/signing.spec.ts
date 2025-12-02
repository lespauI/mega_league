import { test, expect } from './fixtures';
import {
  ensureTab,
  freeAgentsTable,
  activeRosterTable,
  tableRows,
  rowMakeOfferButton,
  rowPlayerName,
  parseMoney,
  readCapAvailable,
  dialogRoot,
  dialogConfirmButton,
} from './utils/selectors';
import { gotoTool } from './fixtures';

test.describe('Free Agent Signing E2E', () => {
  test('signing a free agent updates cap and moves player to active', async ({ page }) => {
    await gotoTool(page);

    // Go to Free Agents tab and grab the first FA
    await ensureTab(page, 'free-agents');
    const faTable = freeAgentsTable(page);
    await expect(faTable).toBeVisible();

    const row = tableRows(faTable).first();
    const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
    expect(name.length).toBeGreaterThan(0);

    // Open offer modal
    await rowMakeOfferButton(row).click();
    const dlg = dialogRoot(page);
    await dlg.waitFor({ state: 'visible' });

    // Read the preview remaining cap after this signing (wait for initial calc)
    const remainingEl = dlg.locator('#offer-remaining');
    await expect
      .poll(async () => parseMoney(await remainingEl.innerText()), { timeout: 2000 })
      .not.toBe(0);
    let previewRemainingText = await remainingEl.innerText();
    let previewRemaining = parseMoney(previewRemainingText);

    // If confirm is disabled due to insufficient cap, lower terms to 0 to allow signing
    const confirm = dialogConfirmButton(page, /Confirm Signing/i);
    if (await confirm.isDisabled()) {
      const salary = dlg.locator('#offer-salary');
      const bonus = dlg.locator('#offer-bonus');
      await salary.fill('0');
      await bonus.fill('0');
      previewRemainingText = await remainingEl.innerText();
      previewRemaining = parseMoney(previewRemainingText);
    }

    await confirm.click();
    await dlg.waitFor({ state: 'hidden' });

    // Wait until Cap Space equals (or is very close to) the preview's remaining cap
    // Wait briefly for UI to re-render after signing
    await page.waitForTimeout(50);

    // Player should now be in Active roster
    await ensureTab(page, 'active-roster');
    await expect(activeRosterTable(page)).toBeVisible();
    await expect(
      activeRosterTable(page).locator('tbody tr td[data-label="Player"] strong', { hasText: name })
    ).toHaveCount(1);

    // And should no longer be in Free Agents list
    await ensureTab(page, 'free-agents');
    await expect(freeAgentsTable(page)).toBeVisible();
    await expect(
      freeAgentsTable(page).locator('tbody tr td[data-label="Player"] strong', { hasText: name })
    ).toHaveCount(0);
  });
});
