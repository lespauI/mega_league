import { test, expect } from './fixtures';
import { gotoTool } from './fixtures';
import { ensureTab, activeRosterTable, tableRows, rowPlayerName } from './utils/selectors';

test.describe('Contract Distribution Editor E2E', () => {
  test('open, defaults, edit + persist, formatting, reset', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'active-roster');

    // Ensure the selected team has a calendarYear so the editor can compute default years
    await page.evaluate(async () => {
      const mod = await import('/docs/roster_cap_tool/js/state.js');
      const st = mod.getState();
      const sel = st.selectedTeam;
      const nextTeams = (st.teams || []).map((t: any) => t.abbrName === sel ? { ...t, calendarYear: 2026 } : t);
      mod.setState({ teams: nextTeams });
    });

    // Find a player whose editor shows at least one editable year
    const table = activeRosterTable(page);
    await expect(table).toBeVisible();
    const rows = tableRows(table);
    const count = await rows.count();

    let rowIndex = -1;
    let playerName = '';
    for (let i = 0; i < Math.min(count, 20); i++) {
      const row = rows.nth(i);
      const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
      await row.locator('td[data-label="Player"]').click();

      const dlg = page.locator('dialog[data-testid="contract-editor"]');
      await expect(dlg).toBeVisible();

      if (await dlg.locator('[data-testid="ce-input-salary"]').count() > 0) {
        rowIndex = i;
        playerName = name;
        break;
      } else {
        // No remaining years for this player; close and continue
        await dlg.locator('[data-testid="ce-close"]').click();
        await expect(dlg).toBeHidden();
      }
    }

    expect(rowIndex).toBeGreaterThanOrEqual(0);

    const dlg = page.locator('dialog[data-testid="contract-editor"]');
    await expect(dlg).toBeVisible();

    // Verify there is at least one year column and headers look like calendar years
    const yearHeaders = dlg.locator('[data-testid="ce-year"]');
    await expect(yearHeaders.first()).toBeVisible();
    const firstYearText = (await yearHeaders.first().innerText()).trim();
    expect(firstYearText).toMatch(/^\d{4}$/);

    // Grab the first year's inputs and previews
    const year = firstYearText;
    const salaryInput = dlg.locator(`[data-testid="ce-input-salary"][data-year="${year}"]`);
    const bonusInput = dlg.locator(`[data-testid="ce-input-bonus"][data-year="${year}"]`);
    await expect(salaryInput).toBeVisible();
    await expect(bonusInput).toBeVisible();

    const salaryPrev = dlg.locator(`[data-testid=ce-prev-salary][data-year="${year}"]`);
    const bonusPrev = dlg.locator(`[data-testid=ce-prev-bonus][data-year="${year}"]`);
    await expect(salaryPrev).toBeVisible();
    await expect(bonusPrev).toBeVisible();

    // Defaults should be formatted as $XM
    const defSalaryPrev = (await salaryPrev.innerText()).trim();
    const defBonusPrev = (await bonusPrev.innerText()).trim();
    expect(defSalaryPrev).toMatch(/^\$\d+\.?\d*M$/);
    expect(defBonusPrev).toMatch(/^\$\d+\.?\d*M$/);

    // Record default input values (millions) for later Reset assertion
    const defSalaryInput = await salaryInput.inputValue();
    const defBonusInput = await bonusInput.inputValue();

    // Edit values and verify previews update with currency formatting
    await salaryInput.fill('22.7');
    await expect(salaryPrev).toHaveText('$22.7M');
    await bonusInput.fill('49.5');
    await expect(bonusPrev).toHaveText('$49.5M');

    // Close and reopen for the same player; ensure persistence within session
    await dlg.locator('[data-testid="ce-close"]').click();
    await expect(dlg).toBeHidden();

    const row = rows.nth(rowIndex);
    await row.locator('td[data-label="Player"]').click();
    await expect(dlg).toBeVisible();

    // Values should persist as 22.7 and 49.5
    await expect(dlg.locator(`[data-testid="ce-input-salary"][data-year="${year}"]`)).toHaveValue('22.7');
    await expect(dlg.locator(`[data-testid="ce-input-bonus"][data-year="${year}"]`)).toHaveValue('49.5');
    await expect(dlg.locator(`[data-testid=ce-prev-salary][data-year="${year}"]`)).toHaveText('$22.7M');
    await expect(dlg.locator(`[data-testid=ce-prev-bonus][data-year="${year}"]`)).toHaveText('$49.5M');

    // Reset should restore default 50/50 values and clear custom state
    await dlg.locator('[data-testid="ce-reset"]').click();
    // Inputs should revert to defaults we captured earlier
    await expect(dlg.locator(`[data-testid="ce-input-salary"][data-year="${year}"]`)).toHaveValue(defSalaryInput);
    await expect(dlg.locator(`[data-testid="ce-input-bonus"][data-year="${year}"]`)).toHaveValue(defBonusInput);

    // Close and reopen again; still defaults (custom cleared)
    await dlg.locator('[data-testid="ce-close"]').click();
    await expect(dlg).toBeHidden();
    await rows.nth(rowIndex).locator('td[data-label="Player"]').click();
    await expect(dlg).toBeVisible();
    await expect(dlg.locator(`[data-testid="ce-input-salary"][data-year="${year}"]`)).toHaveValue(defSalaryInput);
    await expect(dlg.locator(`[data-testid="ce-input-bonus"][data-year="${year}"]`)).toHaveValue(defBonusInput);

    // Final close
    await dlg.locator('[data-testid="ce-close"]').click();
    await expect(dlg).toBeHidden();
  });
});
