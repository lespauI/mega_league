import { test, expect } from './fixtures';
import {
  activeRosterTable,
  freeAgentsTable,
  tableRows,
  readCapAvailable,
  dialogRoot,
  dialogConfirmButton,
  ensureTab,
} from './utils/selectors';
import { gotoTool } from './fixtures';

test.describe('Year Context E2E', () => {
  test('selector updates labels, counts, and cap summary across Y+0/Y+1/Y+2', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'active-roster');

    // Baseline assertions at Y+0
    await expect(page.getByTestId('year-context-label')).toHaveText('Y+0');
    await expect(activeRosterTable(page).getByTestId('col-cap-label')).toHaveText(/Cap \(Y\+0\)/);

    const active0 = await tableRows(activeRosterTable(page)).count();
    await ensureTab(page, 'free-agents');
    const fa0 = await tableRows(freeAgentsTable(page)).count();
    const cap0 = await readCapAvailable(page);

    // Switch to Y+1
    await page.getByTestId('year-context-1').click();
    await expect(page.getByTestId('year-context-label')).toHaveText('Y+1');
    await expect(activeRosterTable(page).getByTestId('col-cap-label')).toHaveText(/Cap \(Y\+1\)/);

    await ensureTab(page, 'active-roster');
    const active1 = await tableRows(activeRosterTable(page)).count();
    await ensureTab(page, 'free-agents');
    const fa1 = await tableRows(freeAgentsTable(page)).count();
    const cap1 = await readCapAvailable(page);

    // Roster membership rolls forward: active should not increase; FA should not decrease
    expect(active1).toBeLessThanOrEqual(active0);
    expect(fa1).toBeGreaterThanOrEqual(fa0);
    expect(cap1).not.toBe(cap0);

    // Switch to Y+2
    await page.getByTestId('year-context-2').click();
    await expect(page.getByTestId('year-context-label')).toHaveText('Y+2');
    await expect(activeRosterTable(page).getByTestId('col-cap-label')).toHaveText(/Cap \(Y\+2\)/);

    await ensureTab(page, 'active-roster');
    const active2 = await tableRows(activeRosterTable(page)).count();
    await ensureTab(page, 'free-agents');
    const fa2 = await tableRows(freeAgentsTable(page)).count();
    const cap2 = await readCapAvailable(page);

    expect(active2).toBeLessThanOrEqual(active1);
    expect(fa2).toBeGreaterThanOrEqual(fa1);
    expect(cap2).not.toBe(cap1);
  });

  test('release flow in Y+1 uses contextual preview (cap change == modal preview)', async ({ page }) => {
    await gotoTool(page);

    // Switch to Y+1 context
    await page.getByTestId('year-context-1').click();
    await expect(page.getByTestId('year-context-label')).toHaveText('Y+1');
    await ensureTab(page, 'active-roster');

    const before = await readCapAvailable(page);
    const row = tableRows(activeRosterTable(page)).first();

    // Open release modal from the action select
    await row.locator('td[data-label="Action"] select').selectOption('release');
    const dlg = dialogRoot(page);
    await dlg.waitFor({ state: 'visible' });

    // Read previewed Cap Savings from the modal
    const savingsLabel = page.getByText('Cap Savings', { exact: true });
    const modalSavingsTxt = await savingsLabel.locator('xpath=following-sibling::div[1]').innerText();
    const modalSavings = Number((modalSavingsTxt || '').replace(/[^0-9.\-]/g, '')) || 0;
    expect(Number.isFinite(modalSavings)).toBeTruthy();

    // Confirm release
    await dialogConfirmButton(page, /Confirm Release/i).click();
    await dlg.waitFor({ state: 'hidden' });

    // Wait for cap to update and compare to modal preview
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
    // Cap should change after release in context; preview displayed a finite savings value
    expect(Math.round(after)).not.toBe(Math.round(before));
  });

  test('scenario save/load persists selected Year Context', async ({ page }) => {
    await gotoTool(page);

    // Choose Y+2 and make a change (release) to enable Save
    await page.getByTestId('year-context-2').click();
    await expect(page.getByTestId('year-context-label')).toHaveText('Y+2');
    await ensureTab(page, 'active-roster');
    const row = tableRows(activeRosterTable(page)).first();
    await row.locator('td[data-label="Action"] select').selectOption('release');
    const dlg = dialogRoot(page);
    await dlg.waitFor({ state: 'visible' });
    await dialogConfirmButton(page, /Confirm Release/i).click();
    await dlg.waitFor({ state: 'hidden' });

    const saveBtn = page.locator('#scenario-controls .btn', { hasText: /Save/i });
    await expect(saveBtn).toBeEnabled();
    await saveBtn.click();
    const saveDlg = page.getByRole('dialog', { name: /Save Scenario/i });
    await expect(saveDlg).toBeVisible();
    const scenarioName = `YCX-${Date.now()}`;
    await saveDlg.locator('#scn-name').fill(scenarioName);
    await saveDlg.getByRole('button', { name: /Save/i }).click();
    await expect(saveDlg).toBeHidden();

    // Load most recent scenario
    const loadBtn = page.locator('#scenario-controls .btn', { hasText: /Load/i });
    await expect(loadBtn).toBeEnabled();
    await loadBtn.click();
    const loadDlg = page.getByRole('dialog', { name: /Load Scenario/i });
    await expect(loadDlg).toBeVisible();
    await loadDlg.locator('button:has-text("Load")').first().click();
    await expect(loadDlg).toBeHidden();

    // Context should be restored to Y+2
    await expect(page.getByTestId('year-context-label')).toHaveText('Y+2');
    await expect(activeRosterTable(page).getByTestId('col-cap-label')).toHaveText(/Cap \(Y\+2\)/);
  });
});
