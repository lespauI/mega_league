import { test, expect } from './fixtures';
import {
  ensureTab,
  activeRosterTable,
  freeAgentsTable,
  tableRows,
  readCapAvailable,
} from './utils/selectors';
import { gotoTool } from './fixtures';
import { releaseFirstRosterPlayer, signFirstFreeAgent } from './utils/flows';

test.describe('Scenario Save/Load/Reset E2E', () => {
  test('edits -> save -> more edits -> load -> reset restores baseline', async ({ page }) => {
    await gotoTool(page);

    // Baseline snapshot
    await ensureTab(page, 'active-roster');
    const baselineActiveCount = await tableRows(activeRosterTable(page)).count();
    const baselineCap = await readCapAvailable(page);

    // Make a change (release a player)
    const rel = await releaseFirstRosterPlayer(page);
    const afterReleaseActive = await tableRows(activeRosterTable(page)).count();
    expect(afterReleaseActive).toBeLessThan(baselineActiveCount);
    const afterReleaseCap = await readCapAvailable(page);
    expect(afterReleaseCap).not.toBe(baselineCap);

    // Save scenario with a unique name
    const saveBtn = page.locator('#scenario-controls .btn', { hasText: /Save/i });
    await expect(saveBtn).toBeEnabled();
    await saveBtn.click();
    const saveDlg = page.getByRole('dialog', { name: /Save Scenario/i });
    await expect(saveDlg).toBeVisible();
    const scenarioName = `E2E Scenario ${Date.now()}`;
    await saveDlg.locator('#scn-name').fill(scenarioName);
    await saveDlg.getByRole('button', { name: /Save/i }).click();
    await expect(saveDlg).toBeHidden();

    // Load button should reflect at least one saved scenario for this team
    const loadBtn = page.locator('#scenario-controls .btn', { hasText: /Load/i });
    await expect(loadBtn).toBeEnabled();
    const loadBtnText = await loadBtn.innerText();
    expect(loadBtnText).toMatch(/Load\s*\(\d+\)/);

    // Record saved-state snapshot for later comparison
    const savedActiveCount = afterReleaseActive;
    const savedCap = afterReleaseCap;

    // Make more changes (sign a free agent)
    await ensureTab(page, 'free-agents');
    const faBefore = await tableRows(freeAgentsTable(page)).count();
    expect(faBefore).toBeGreaterThan(0);
    const sign = await signFirstFreeAgent(page);
    expect(sign.after).not.toBe(savedCap);

    // Load the saved scenario (should revert to post-release state)
    await loadBtn.click();
    const loadDlg = page.getByRole('dialog', { name: /Load Scenario/i });
    await expect(loadDlg).toBeVisible();
    // Click the first Load action in the list (newest first)
    await loadDlg.locator('button:has-text("Load")').first().click();
    await expect(loadDlg).toBeHidden();

    // Validate we returned to the saved state
    await ensureTab(page, 'active-roster');
    await expect(tableRows(activeRosterTable(page))).toHaveCount(savedActiveCount);
    await expect
      .poll(async () => readCapAvailable(page), { timeout: 3000 })
      .toBe(savedCap);

    // Reset to baseline and confirm
    const resetBtn = page.locator('#scenario-controls .btn', { hasText: /Reset/i });
    await expect(resetBtn).toBeEnabled();
    const once = page.once('dialog', (d) => d.accept());
    await resetBtn.click();
    await once;

    // Baseline should be restored (counts and cap)
    await expect
      .poll(async () => tableRows(activeRosterTable(page)).count(), { timeout: 4000 })
      .toBe(baselineActiveCount);
    await expect
      .poll(async () => readCapAvailable(page), { timeout: 4000 })
      .toBe(baselineCap);

    // Save should now be disabled (no changes), and Reset disabled
    await expect(page.locator('#scenario-controls .btn', { hasText: /Save/i })).toBeDisabled();
    await expect(page.locator('#scenario-controls .btn', { hasText: /Reset/i })).toBeDisabled();
  });
});
