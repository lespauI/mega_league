import { test, expect } from './fixtures';

test.describe('Docs: graphs and tables scroll on mobile', () => {
  test('team_stats_explorer chart is horizontally scrollable on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 430, height: 900 });
    await page.goto('/docs/team_stats_explorer.html');

    const chartWrap = page.locator('.chart-wrap').first();
    await expect(chartWrap).toBeVisible();

    const { scrollWidth, clientWidth } = await chartWrap.evaluate((el) => ({
      // Use offsetWidth as a fallback for clientWidth if needed
      scrollWidth: (el as HTMLElement).scrollWidth,
      clientWidth: (el as HTMLElement).clientWidth || (el as HTMLElement).offsetWidth,
    }));

    expect(scrollWidth).toBeGreaterThan(clientWidth);

    const bodyOverflowX = await page.evaluate(
      () => getComputedStyle(document.body).overflowX,
    );
    expect(bodyOverflowX).not.toBe('hidden');
  });

  test('playoff_race_table standings table is horizontally scrollable on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 430, height: 900 });
    await page.goto('/docs/playoff_race_table.html');

    const tableWrap = page
      .locator('.conference-section')
      .first()
      .locator('.table-wrap')
      .first();
    await expect(tableWrap).toBeVisible();

    const { scrollWidth, clientWidth } = await tableWrap.evaluate((el) => ({
      scrollWidth: (el as HTMLElement).scrollWidth,
      clientWidth: (el as HTMLElement).clientWidth || (el as HTMLElement).offsetWidth,
    }));

    expect(scrollWidth).toBeGreaterThan(clientWidth);

    const bodyOverflowX = await page.evaluate(
      () => getComputedStyle(document.body).overflowX,
    );
    expect(bodyOverflowX).not.toBe('hidden');
  });
});

