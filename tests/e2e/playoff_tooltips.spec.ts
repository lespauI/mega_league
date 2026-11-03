import { test, expect } from '@playwright/test';

for (const viewport of [{ width: 1280, height: 900 }, { width: 800, height: 600 }]) {
  test(`embedded playoff tooltip stays visible ${viewport.width}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/docs/playoff_race.html');
    const frame = page.frameLocator('#tableFrame');
    const trigger = frame.locator('tbody tr').filter({ has: frame.locator('img[alt="Giants"]') })
      .locator('td:last-child .prob-wrapper');
    await trigger.scrollIntoViewIfNeeded();
    await trigger.hover();
    const tip = frame.locator('.floating-report-tooltip');
    await expect(tip).toBeVisible();
    await expect(tip).toContainText('Выход в Супербоул');
    await expect(tip).toContainText('1,54');
    // Playwright bounding boxes use the outer viewport, even for frames.
    const box = await tip.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height);
    await tip.hover();
    await tip.evaluate(el => { el.scrollTop = el.scrollHeight; });
    await expect(tip).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(frame.locator('.floating-report-tooltip')).toHaveCount(0);
    await trigger.focus();
    await expect(frame.locator('.floating-report-tooltip')).toBeVisible();
  });
}
