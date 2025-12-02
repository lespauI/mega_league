import type { Locator, Page } from '@playwright/test';

// Generic money parser: "$1,234,567" -> 1234567; "- $2,000" -> -2000
export function parseMoney(text: string): number {
  const cleaned = (text || '').replace(/[^0-9.\-]/g, '');
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : 0;
}

export function teamSelect(page: Page): Locator {
  // Mounted with aria-label "Select Team"
  return page.getByLabel('Select Team');
}

export function tabsRoot(page: Page): Locator {
  return page.locator('#tabs');
}

export function tab(page: Page, nameOrSlug: string): Locator {
  // Prefer data-tab slug if provided; fallback to text match
  const bySlug = page.locator(`nav#tabs .tab[data-tab="${nameOrSlug}"]`);
  return bySlug.first().or(page.getByRole('tab', { name: new RegExp(nameOrSlug, 'i') }));
}

export async function ensureTab(page: Page, slug: string): Promise<void> {
  const button = tab(page, slug);
  await button.click();
  // Wait for corresponding panel to be active
  const panel = page.locator(`#panel-${slug}`);
  await panel.waitFor({ state: 'visible' });
}

export function capSummaryRoot(page: Page): Locator {
  return page.locator('#cap-summary');
}

function capMetricValueLocator(page: Page, label: string): Locator {
  return page.locator('#cap-summary .metric', { hasText: label }).locator('.value');
}

export function capRoomValue(page: Page): Locator {
  return capMetricValueLocator(page, 'Original Cap');
}

export function capSpentValue(page: Page): Locator {
  return capMetricValueLocator(page, 'Cap Spent');
}

export function capAvailableValue(page: Page): Locator {
  return capMetricValueLocator(page, 'Cap Space');
}

export async function readCapAvailable(page: Page): Promise<number> {
  const txt = await capAvailableValue(page).innerText();
  return parseMoney(txt);
}

// Tables
export function activeRosterTable(page: Page): Locator {
  return page.locator('#active-roster-table table');
}

export function injuredReserveTable(page: Page): Locator {
  return page.locator('#injured-reserve-table table');
}

export function deadMoneyTable(page: Page): Locator {
  return page.locator('#dead-money-table table');
}

export function freeAgentsTable(page: Page): Locator {
  return page.locator('#free-agents-table table');
}

export function tableRows(table: Locator): Locator {
  return table.locator('tbody tr');
}

export function rowPlayerCell(row: Locator): Locator {
  return row.locator('td[data-label="Player"]');
}

export function rowPlayerName(row: Locator): Locator {
  return row.locator('td[data-label="Player"] strong');
}

export function rowActionSelect(row: Locator): Locator {
  return row.locator('td[data-label="Action"] select');
}

export function rowMakeOfferButton(row: Locator): Locator {
  return row.locator('td[data-label="Action"] button:has-text("Make Offer")');
}

// Modals
export function dialogRoot(page: Page): Locator {
  return page.locator('dialog');
}

export function dialogConfirmButton(page: Page, namePattern: RegExp | string): Locator {
  return dialogRoot(page).getByRole('button', { name: typeof namePattern === 'string' ? new RegExp(namePattern, 'i') : namePattern });
}

