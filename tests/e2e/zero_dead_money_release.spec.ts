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

    // Expect Y+1 to increase materially (≥ $10M). Y+2 depends on years remaining.
    await expect
      .poll(async () => parseMoney(await projY1.innerText()), { timeout: 5000 })
      .toBeGreaterThanOrEqual(y1Before + 10_000_000);

    await expect
      .poll(async () => parseMoney(await projY2.innerText()), { timeout: 5000 })
      .toBeGreaterThanOrEqual(y2Before);
  });
});
