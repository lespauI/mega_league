import { test, expect } from './fixtures';
import { gotoTool } from './fixtures';
import {
  ensureTab,
  activeRosterTable,
  tableRows,
  rowPlayerName,
  rowActionSelect,
  parseMoney,
  dialogRoot,
  dialogConfirmButton,
} from './utils/selectors';

test.describe('Zero-dead-money release projections', () => {
  test('releasing Kenny Clark (SF) increases Y+1 and Y+2 projections', async ({ page }) => {
    await gotoTool(page);
    await ensureTab(page, 'active-roster');

    // Capture header projections before
    const projY1 = page.getByTestId('proj-y1');
    const projY2 = page.getByTestId('proj-y2');
    await expect(projY1).toBeVisible();
    await expect(projY2).toBeVisible();
    const y1Before = parseMoney(await projY1.innerText());
    const y2Before = parseMoney(await projY2.innerText());

    // Find Kenny Clark on 49ers with Dead Cap (Trade) = $0
    const table = activeRosterTable(page);
    const rows = tableRows(table);
    const count = await rows.count();
    let targetIndex = -1;
    for (let i = 0; i < Math.min(count, 50); i++) {
      const row = rows.nth(i);
      const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
      if (!/\bKenny\s+Clark\b/i.test(name)) continue;
      const deadTradeText = await row.locator('td[data-label="Dead Cap (Trade)"]').innerText().catch(() => '');
      const deadTrade = parseMoney(deadTradeText);
      if (deadTrade === 0) { targetIndex = i; break; }
    }
    expect(targetIndex).toBeGreaterThanOrEqual(0);

    const targetRow = rows.nth(targetIndex);

    // Trigger release and confirm
    await rowActionSelect(targetRow).selectOption('release');
    const dlg = dialogRoot(page);
    await expect(dlg).toBeVisible();
    await dialogConfirmButton(page, /Confirm Release/i).click();
    await expect(dlg).toBeHidden();

    // Read projections after
    const y1After = await page.waitForFunction(() => {
      const el = document.querySelector('[data-testid="proj-y1"]');
      const txt = (el?.textContent || '').replace(/[^0-9.\-]/g, '');
      return Number(txt) || 0;
    });
    const y2After = await page.waitForFunction(() => {
      const el = document.querySelector('[data-testid="proj-y2"]');
      const txt = (el?.textContent || '').replace(/[^0-9.\-]/g, '');
      return Number(txt) || 0;
    });

    // Expect both Y+1 and Y+2 to increase materially (≥ $10M)
    expect(Math.round((y1After as number) - y1Before)).toBeGreaterThanOrEqual(10_000_000);
    expect(Math.round((y2After as number) - y2Before)).toBeGreaterThanOrEqual(10_000_000);
  });
});

