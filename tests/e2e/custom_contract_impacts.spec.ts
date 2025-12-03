import { test, expect } from './fixtures';
import { gotoTool } from './fixtures';
import {
  ensureTab,
  activeRosterTable,
  tableRows,
  rowPlayerName,
  rowActionSelect,
  parseMoney,
} from './utils/selectors';

/** Extract the numeric value from a Confirm dialog message line like "Savings: $12,345,678" */
function parseLabeledMoney(msg: string, label: string): number {
  const re = new RegExp(`${label}:(.*?)$`, 'mi');
  const m = msg.match(re);
  if (!m) return 0;
  return parseMoney(m[1]);
}

test.describe('Custom contract distribution impacts projections, release, and trade', () => {
  test('editing a future year updates projections and context previews', async ({ page }) => {
    // Navigate to tool and wait for basic UI to mount
    await page.goto('/docs/roster_cap_tool/');
    await expect(page.locator('h1.app-title')).toHaveText(/Roster Cap Tool/i);
    // Wait for tabs to initialize and Active Roster to be visible
    await expect(page.locator('#tabs')).toBeVisible();
    await ensureTab(page, 'active-roster');

    // Ensure selected team has a calendar year so editor + projections use absolute years
    const baseYear: number = await page.evaluate(async () => {
      const mod = await import('/docs/roster_cap_tool/js/state.js');
      const st = mod.getState();
      const sel = st.selectedTeam;
      const byId = Object.fromEntries((st.teams || []).map((t: any) => [t.abbrName, t]));
      const team = byId[sel];
      const yr = 2026;
      if (!team || Number(team.calendarYear) === yr) return yr;
      const nextTeams = (st.teams || []).map((t: any) => t.abbrName === sel ? { ...t, calendarYear: yr } : t);
      mod.setState({ teams: nextTeams });
      return yr;
    });

    // Find a player that has at least one future year (baseYear+1 or later) to edit
    const table = activeRosterTable(page);
    await expect(table).toBeVisible();
    const rows = tableRows(table);
    const count = await rows.count();

    let chosenIndex = -1;
    let chosenName = '';
    let targetYear = 0;
    for (let i = 0; i < Math.min(count, 30); i++) {
      const row = rows.nth(i);
      const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
      if (!name) continue;
      await row.locator('td[data-label="Player"]').click();
      const dlg = page.locator('dialog[data-testid="contract-editor"]');
      await expect(dlg).toBeVisible();
      const yearEls = dlg.locator('[data-testid="ce-year"]');
      const yCount = await yearEls.count();
      if (yCount === 0) {
        await dlg.locator('[data-testid="ce-close"]').click();
        await expect(dlg).toBeHidden();
        continue;
      }
      // Collect absolute years shown by the editor
      const years: number[] = [];
      for (let k = 0; k < yCount; k++) {
        const txt = (await yearEls.nth(k).innerText()).trim();
        const y = Number(txt);
        if (Number.isFinite(y)) years.push(y);
      }
      // Prefer first future year > baseYear
      const fut = years.find((y) => y > baseYear);
      if (fut) {
        chosenIndex = i;
        chosenName = name;
        targetYear = fut;
        await dlg.locator('[data-testid="ce-close"]').click();
        await expect(dlg).toBeHidden();
        break;
      }
      await dlg.locator('[data-testid="ce-close"]').click();
      await expect(dlg).toBeHidden();
    }

    expect(chosenIndex).toBeGreaterThanOrEqual(0);
    expect(targetYear).toBeGreaterThan(baseYear);

    // Baseline: capture Projections row for targetYear (Roster Cap or Cap Space)
    await ensureTab(page, 'projections');
    const projPanel = page.locator('#panel-projections');
    await expect(projPanel).toBeVisible();
    // Ensure horizon includes our target year
    const needOffset = targetYear - baseYear; // >= 1
    const slider = projPanel.locator('input[data-horizon]');
    await expect(slider).toBeVisible();
    await slider.evaluate((el: HTMLInputElement, off: number) => {
      const val = Math.max(3, Math.min(5, off + 1));
      el.value = String(val);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, needOffset);
    // Find projections row by first column text (exact year)
    const projRows = projPanel.locator('table tbody tr');
    await expect(projRows.first()).toBeVisible();
    const rowCount = await projRows.count();
    let projRowIndex = -1;
    for (let i = 0; i < rowCount; i++) {
      const yrText = (await projRows.nth(i).locator('td').first().innerText()).trim();
      if (yrText === String(targetYear)) { projRowIndex = i; break; }
    }
    expect(projRowIndex).toBeGreaterThanOrEqual(0);
    const baselineRosterCapTxt = await projRows.nth(projRowIndex).locator('td').nth(2).innerText();
    const baselineCapSpaceTxt = await projRows.nth(projRowIndex).locator('td').nth(5).innerText();
    const baselineRosterCap = parseMoney(baselineRosterCapTxt);
    const baselineCapSpace = parseMoney(baselineCapSpaceTxt);

    // Baseline: capture Release + Trade (Quick) savings in target Year Context
    await ensureTab(page, 'active-roster');
    await page.getByTestId(`year-context-${needOffset}`).click();
    await expect(page.getByTestId('year-context-label')).toHaveText(String(targetYear));
    // Re-find row by name
    const aTable = activeRosterTable(page);
    const aRows = tableRows(aTable);
    const targetRow = aRows.filter({ hasText: chosenName }).first();
    await expect(targetRow).toBeVisible();
    // Release modal: read Cap Savings, then cancel
    await rowActionSelect(targetRow).selectOption('release');
    const relDlg = page.locator('dialog[data-testid="modal-release"]');
    await expect(relDlg).toBeVisible();
    const relSavingsLabel = relDlg.getByText('Cap Savings', { exact: true });
    const relSavingsTxt0 = await relSavingsLabel.locator('xpath=following-sibling::div[1]').innerText();
    const relSavings0 = parseMoney(relSavingsTxt0);
    await relDlg.getByTestId('cancel-release').click();
    await expect(relDlg).toBeHidden();
    // Trade (Quick): open confirm dialog, read message, cancel
    await rowActionSelect(targetRow).selectOption('tradeQuick');
    const confDlg = page.getByRole('dialog');
    await expect(confDlg).toBeVisible();
    const confMsg = (await confDlg.locator('#confirm-msg').innerText()).trim();
    const tradeSavings0 = parseLabeledMoney(confMsg, 'Savings');
    await confDlg.getByRole('button', { name: /Cancel/i }).click();
    await expect(confDlg).toBeHidden();

    // Edit the target year's salary and bonus to large values and Save
    await targetRow.locator('td[data-label="Player"]').click();
    const ce = page.locator('dialog[data-testid="contract-editor"]');
    await expect(ce).toBeVisible();
    const sInp = ce.locator(`[data-testid="ce-input-salary"][data-year="${targetYear}"]`);
    const bInp = ce.locator(`[data-testid="ce-input-bonus"][data-year="${targetYear}"]`);
    await expect(sInp).toBeVisible();
    await expect(bInp).toBeVisible();
    await sInp.fill('20.0');
    await bInp.fill('20.0');
    await ce.locator('[data-testid="ce-save"]').click();
    await expect(ce).toBeHidden();

    // Projections should change for targetYear
    await ensureTab(page, 'projections');
    const projRows2 = projPanel.locator('table tbody tr');
    await expect(projRows2.first()).toBeVisible();
    // Find the same year row again
    let projRowIndex2 = -1;
    const rowCount2 = await projRows2.count();
    for (let i = 0; i < rowCount2; i++) {
      const yrText = (await projRows2.nth(i).locator('td').first().innerText()).trim();
      if (yrText === String(targetYear)) { projRowIndex2 = i; break; }
    }
    expect(projRowIndex2).toBeGreaterThanOrEqual(0);
    const newRosterCap = parseMoney(await projRows2.nth(projRowIndex2).locator('td').nth(2).innerText());
    const newCapSpace = parseMoney(await projRows2.nth(projRowIndex2).locator('td').nth(5).innerText());
    expect(Math.round(newRosterCap)).not.toBe(Math.round(baselineRosterCap));
    expect(Math.round(newCapSpace)).not.toBe(Math.round(baselineCapSpace));

    // Release preview in context should change
    await ensureTab(page, 'active-roster');
    await page.getByTestId(`year-context-${needOffset}`).click();
    await expect(page.getByTestId('year-context-label')).toHaveText(String(targetYear));
    const row2 = tableRows(activeRosterTable(page)).filter({ hasText: chosenName }).first();
    await expect(row2).toBeVisible();
    await rowActionSelect(row2).selectOption('release');
    const relDlg2 = page.locator('dialog[data-testid="modal-release"]');
    await expect(relDlg2).toBeVisible();
    const relSavingsTxt1 = await relDlg2.getByText('Cap Savings', { exact: true }).locator('xpath=following-sibling::div[1]').innerText();
    const relSavings1 = parseMoney(relSavingsTxt1);
    await relDlg2.getByTestId('cancel-release').click();
    await expect(relDlg2).toBeHidden();
    expect(Math.round(relSavings1)).not.toBe(Math.round(relSavings0));

    // Trade (Quick) preview should change
    await rowActionSelect(row2).selectOption('tradeQuick');
    const confDlg2 = page.getByRole('dialog');
    await expect(confDlg2).toBeVisible();
    const confMsg2 = (await confDlg2.locator('#confirm-msg').innerText()).trim();
    const tradeSavings1 = parseLabeledMoney(confMsg2, 'Savings');
    await confDlg2.getByRole('button', { name: /Cancel/i }).click();
    await expect(confDlg2).toBeHidden();
    expect(Math.round(tradeSavings1)).not.toBe(Math.round(tradeSavings0));
  });
});
