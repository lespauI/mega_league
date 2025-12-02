import { test, expect } from './fixtures';
import { gotoTool } from './fixtures';
import { ensureTab, parseMoney } from './utils/selectors';

test.describe('Projections E2E', () => {
  test('re-sign budget + horizon slider update and persist', async ({ page }) => {
    await gotoTool(page);

    // Header projections should be visible and have numeric values
    const y1Header = page.locator('[data-testid="proj-y1"]');
    await expect(y1Header).toBeVisible();
    const y1BeforeTxt = await y1Header.innerText();
    const y1Before = parseMoney(y1BeforeTxt);
    expect(Number.isFinite(y1Before)).toBeTruthy();

    // Go to Projections tab
    await ensureTab(page, 'projections');

    const panel = page.locator('#panel-projections');
    await expect(panel).toBeVisible();

    // Ensure projections table rendered
    const tableRows = panel.locator('table tbody tr');
    await expect(tableRows.first()).toBeVisible();

    // Check horizon slider exists and row count matches its value
    const slider = panel.locator('input[data-horizon]');
    await expect(slider).toBeVisible();
    let sliderVal = Number(await slider.inputValue());
    const initialCount = await tableRows.count();
    expect(initialCount).toBe(sliderVal);

    // Set horizon to 3 and verify label + row count update
    const yearsLabel = panel.locator('#proj-years-label');
    await slider.evaluate((el: HTMLInputElement) => {
      el.value = '3';
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await expect(yearsLabel).toHaveText(/3 year\(s\)/);
    await expect
      .poll(async () => panel.locator('table tbody tr').count(), { timeout: 4000 })
      .toBe(3);

    // Change the re-sign budget in the Projections view and assert header projections update
    const projResignInput = panel.locator('#proj-resign-ingame-value');
    await expect(projResignInput).toBeVisible();
    const newBudget = 15000000; // $15M
    await projResignInput.fill(String(newBudget));
    await projResignInput.evaluate((el: HTMLInputElement) => el.dispatchEvent(new Event('change', { bubbles: true })));

    // Header's re-sign input should reflect the new value
    const headerResignInput = page.locator('[data-testid="resign-budget-input"]');
    await expect(headerResignInput).toHaveValue(String(newBudget));

    // Header Y+1 projection should decrease (more spending applied to Y+1)
    await expect
      .poll(async () => parseMoney(await y1Header.innerText()), { timeout: 5000 })
      .not.toBe(y1Before);
    const y1After = parseMoney(await y1Header.innerText());
    expect(y1After).toBeLessThan(y1Before);

    // Switch tabs away and back; settings should persist
    await ensureTab(page, 'active-roster');
    await ensureTab(page, 'projections');
    await expect(panel).toBeVisible();
    await expect(slider).toHaveValue('3');
    await expect(panel.locator('table tbody tr')).toHaveCount(3);
    // Header value should persist
    const y1AfterAgain = parseMoney(await y1Header.innerText());
    expect(y1AfterAgain).toBe(y1After);
  });
});

