import { test, expect } from './fixtures';

test.describe('Playoff Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/docs/playoff_dashboard.html');
    await page.waitForSelector('.matchup-card', { timeout: 15000 });
  });

  test('page loads with header and bracket', async ({ page }) => {
    await expect(page.locator('.header h1')).toContainText('MEGA PLAYOFFS');
    await expect(page.locator('.conf-label.afc')).toContainText('AFC');
    await expect(page.locator('.conf-label.nfc')).toContainText('NFC');
  });

  test('bracket renders 6 wild card matchups', async ({ page }) => {
    const wcCards = page.locator('.matchup-card').filter({ has: page.locator('.team-row') });
    const count = await wcCards.count();
    expect(count).toBeGreaterThanOrEqual(6);
  });

  test('bracket renders 2 BYE badges', async ({ page }) => {
    const byeCards = page.locator('#bracket .bye-card');
    await expect(byeCards).toHaveCount(2);
    const byeLabels = page.locator('#bracket .bye-card .bye-label');
    await expect(byeLabels.first()).toContainText('Bye');
    await expect(byeLabels.last()).toContainText('Bye');
  });

  test('TBD placeholders shown for unresolved rounds', async ({ page }) => {
    const tbdCards = page.locator('.tbd-card');
    const count = await tbdCards.count();
    expect(count).toBeGreaterThanOrEqual(1);
    await expect(tbdCards.first().locator('.tbd-text')).toContainText('TBD');
  });

  test('clicking matchup opens modal with win probability', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();

    const overlay = page.locator('#modal-overlay');
    await expect(overlay).toBeVisible();

    const modalBody = page.locator('#modal-body');
    await expect(modalBody).toContainText('Win Probability');
  });

  test('modal shows team stats comparison', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();

    const modalBody = page.locator('#modal-body');
    await expect(modalBody).toContainText('Team Stats Comparison');
    await expect(modalBody).toContainText('OVR');
    await expect(modalBody).toContainText('ELO');
    await expect(modalBody).toContainText('Pts/G');
  });

  test('modal shows best players section', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();

    const modalBody = page.locator('#modal-body');
    await expect(modalBody).toContainText('Best Players');
    await expect(modalBody).toContainText('OVR');
  });

  test('modal shows head-to-head history', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();

    const modalBody = page.locator('#modal-body');
    await expect(modalBody).toContainText('Head-to-Head');
  });

  test('modal shows community prediction vote UI', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();

    const modalBody = page.locator('#modal-body');
    await expect(modalBody).toContainText('Community Prediction');

    const voteButtons = page.locator('.vote-btn');
    await expect(voteButtons).toHaveCount(2);

    const voteBar = page.locator('.vote-bar');
    await expect(voteBar).toBeVisible();
  });

  test('modal closes on X button click', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();
    await expect(page.locator('#modal-overlay')).toBeVisible();

    await page.locator('#modal-close').click();
    await expect(page.locator('#modal-overlay')).toBeHidden();
  });

  test('modal closes on Escape key', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();
    await expect(page.locator('#modal-overlay')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.locator('#modal-overlay')).toBeHidden();
  });

  test('prediction vote persists after page reload', async ({ page }) => {
    const firstCard = page.locator('.matchup-card:not(.pending)').first();
    await firstCard.click();
    await expect(page.locator('#modal-overlay')).toBeVisible();

    const homeBtn = page.locator('#vote-btn-home');
    await homeBtn.click();
    await expect(homeBtn).toHaveClass(/voted/);
    await expect(homeBtn.locator('.vote-label')).toContainText('YOUR PICK');

    const teamName = await homeBtn.locator('.vote-team-name').innerText();

    await page.reload();
    await page.waitForSelector('.matchup-card', { timeout: 15000 });

    await page.locator('.matchup-card:not(.pending)').first().click();
    await expect(page.locator('#modal-overlay')).toBeVisible();

    const reloadedBtn = page.locator('#vote-btn-home');
    await expect(reloadedBtn.locator('.vote-label')).toContainText('YOUR PICK');
  });
});
