import type { Page } from '@playwright/test';
import {
  activeRosterTable,
  freeAgentsTable,
  tableRows,
  rowActionSelect,
  rowMakeOfferButton,
  rowPlayerName,
  ensureTab,
  readCapAvailable,
  parseMoney,
  dialogRoot,
  dialogConfirmButton,
} from './selectors';

export async function releaseFirstRosterPlayer(page: Page) {
  await ensureTab(page, 'active-roster');
  const before = await readCapAvailable(page);

  const row = tableRows(activeRosterTable(page)).first();
  const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();

  await rowActionSelect(row).selectOption('release');
  const dlg = dialogRoot(page);
  await dlg.waitFor({ state: 'visible' });
  await dialogConfirmButton(page, /Confirm Release/i).click();
  await dlg.waitFor({ state: 'hidden' });

  // Wait for cap to change
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
  return { name, before, after, delta: after - before };
}

export async function signFirstFreeAgent(page: Page) {
  await ensureTab(page, 'free-agents');
  const before = await readCapAvailable(page);

  const row = tableRows(freeAgentsTable(page)).first();
  const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();
  await rowMakeOfferButton(row).click();

  const dlg = dialogRoot(page);
  await dlg.waitFor({ state: 'visible' });

  // If confirm disabled due to cap, lower terms then retry
  const confirm = dialogConfirmButton(page, /Confirm Signing/i);
  if (await confirm.isDisabled()) {
    const salary = dlg.locator('#offer-salary');
    const bonus = dlg.locator('#offer-bonus');
    await salary.fill('0');
    await bonus.fill('0');
  }
  // Capture preview for reference
  const previewRemainingTxt = await dlg.locator('#offer-remaining').innerText().catch(() => '');
  const previewRemaining = parseMoney(previewRemainingTxt);

  await confirm.click();
  await dlg.waitFor({ state: 'hidden' });

  await page.waitForTimeout(50);
  const after = await readCapAvailable(page);
  return { name, before, after, delta: after - before, previewRemaining };
}

export async function tradeQuick(page: Page) {
  await ensureTab(page, 'active-roster');
  const before = await readCapAvailable(page);
  const row = tableRows(activeRosterTable(page)).first();
  const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();

  // Accept native confirm
  const once = page.once('dialog', (d) => d.accept());
  await rowActionSelect(row).selectOption('tradeQuick');
  await once; // ensure handled

  // Wait for cap change
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
  return { name, before, after, delta: after - before };
}

export async function extendFirst(page: Page) {
  await ensureTab(page, 'active-roster');
  const before = await readCapAvailable(page);
  const row = tableRows(activeRosterTable(page)).first();
  const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();

  await rowActionSelect(row).selectOption('extend');
  const dlg = dialogRoot(page);
  await dlg.waitFor({ state: 'visible' });

  const remainingTxt = await dlg.locator('#ext-remaining').innerText().catch(() => '');
  const deltaTxt = await dlg.locator('#ext-delta').innerText().catch(() => '');
  const previewRemaining = parseMoney(remainingTxt);
  const previewDelta = parseMoney(deltaTxt);

  await dialogConfirmButton(page, /Apply Extension/i).click();
  await dlg.waitFor({ state: 'hidden' });
  await page.waitForTimeout(50);
  const after = await readCapAvailable(page);
  return { name, before, after, delta: after - before, previewRemaining, previewDelta };
}

export async function convertFirst(page: Page) {
  await ensureTab(page, 'active-roster');
  const before = await readCapAvailable(page);
  const row = tableRows(activeRosterTable(page)).first();
  const name = (await rowPlayerName(row).innerText().catch(() => '')).trim();

  await rowActionSelect(row).selectOption('convert');
  const dlg = dialogRoot(page);
  await dlg.waitFor({ state: 'visible' });

  const remainingTxt = await dlg.locator('#conv-remaining').innerText().catch(() => '');
  const deltaTxt = await dlg.locator('#conv-delta').innerText().catch(() => '');
  const previewRemaining = parseMoney(remainingTxt);
  const previewDelta = parseMoney(deltaTxt);

  await dialogConfirmButton(page, /Apply Conversion/i).click();
  await dlg.waitFor({ state: 'hidden' });
  await page.waitForTimeout(50);
  const after = await readCapAvailable(page);
  return { name, before, after, delta: after - before, previewRemaining, previewDelta };
}

