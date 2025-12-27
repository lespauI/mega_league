import { test, expect } from '@playwright/test';

const ALL_TEAMS = [
  '49ers', 'Bears', 'Bengals', 'Bills', 'Broncos', 'Browns', 'Buccaneers', 'Cardinals',
  'Chargers', 'Chiefs', 'Colts', 'Commanders', 'Cowboys', 'Dolphins', 'Eagles', 'Falcons',
  'Giants', 'Jaguars', 'Jets', 'Lions', 'Packers', 'Panthers', 'Patriots', 'Raiders',
  'Rams', 'Ravens', 'Saints', 'Seahawks', 'Steelers', 'Texans', 'Titans', 'Vikings'
];

function getRandomTeams(count: number): string[] {
  const shuffled = [...ALL_TEAMS].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

test.describe('Team Scenarios Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/docs/team_scenarios.html');
  });

  test('page loads with header and team selector', async ({ page }) => {
    await expect(page.locator('.header h1')).toContainText('NFL Playoff Scenarios');
    await expect(page.locator('#team-select')).toBeVisible();
    
    const options = await page.locator('#team-select option').allTextContents();
    expect(options.length).toBe(33);
  });

  test('selecting a team displays all sections correctly', async ({ page }) => {
    const randomTeams = getRandomTeams(3);

    for (const teamName of randomTeams) {
      await test.step(`Verify ${teamName}`, async () => {
        await page.locator('#team-select').selectOption(teamName);

        await expect(page.locator('#team-header')).not.toHaveClass(/hidden/);
        await expect(page.locator('#team-header .team-info h2')).toHaveText(teamName);
        await expect(page.locator('#team-header .subtitle')).toBeVisible();

        await expect(page.locator('#stats-grid')).not.toHaveClass(/hidden/);
        const statCards = page.locator('#stats-grid .stat-card');
        await expect(statCards).toHaveCount(4);

        const labels = await page.locator('#stats-grid .stat-label').allTextContents();
        expect(labels).toContain('Current Record');
        expect(labels).toContain('Playoff Chances');
        expect(labels).toContain('Win Division');
        expect(labels).toContain('First Round Bye');

        const statValues = page.locator('#stats-grid .stat-value');
        await expect(statValues).toHaveCount(4);
        for (let i = 0; i < 4; i++) {
          const text = await statValues.nth(i).textContent();
          expect(text?.trim().length).toBeGreaterThan(0);
        }

        await expect(page.locator('#charts-section')).not.toHaveClass(/hidden/);
        await expect(page.locator('#recordChart')).toBeVisible();
        await expect(page.locator('#probChart')).toBeVisible();

        await expect(page.locator('#team-content')).not.toHaveClass(/hidden/);
        await expect(page.locator('#content-placeholder')).toHaveClass(/hidden/);

        await expect(page.locator('.games-table')).toBeVisible();
        const gameRows = page.locator('.games-table tbody tr');
        const gameCount = await gameRows.count();
        expect(gameCount).toBeGreaterThan(0);

        await expect(page.locator('.outcomes-table')).toBeVisible();
        const outcomeRows = page.locator('.outcomes-table tbody tr');
        const outcomeCount = await outcomeRows.count();
        expect(outcomeCount).toBeGreaterThan(0);

        await expect(page.locator('#team-content')).toContainText('Most Likely Outcome');
      });
    }
  });

  test('stats show valid probability values', async ({ page }) => {
    const randomTeams = getRandomTeams(3);

    for (const teamName of randomTeams) {
      await test.step(`Validate probabilities for ${teamName}`, async () => {
        await page.locator('#team-select').selectOption(teamName);

        const playoffValue = await page.locator('#stats-grid .stat-card:nth-child(2) .stat-value').textContent();
        const divisionValue = await page.locator('#stats-grid .stat-card:nth-child(3) .stat-value').textContent();
        const byeValue = await page.locator('#stats-grid .stat-card:nth-child(4) .stat-value').textContent();

        const parsePercent = (s: string | null) => parseFloat(s?.replace('%', '') || 'NaN');

        const playoff = parsePercent(playoffValue);
        const division = parsePercent(divisionValue);
        const bye = parsePercent(byeValue);

        expect(playoff).toBeGreaterThanOrEqual(0);
        expect(playoff).toBeLessThanOrEqual(100);
        expect(division).toBeGreaterThanOrEqual(0);
        expect(division).toBeLessThanOrEqual(100);
        expect(bye).toBeGreaterThanOrEqual(0);
        expect(bye).toBeLessThanOrEqual(100);

        expect(division).toBeLessThanOrEqual(playoff + 0.1);
        expect(bye).toBeLessThanOrEqual(division + 0.1);
      });
    }
  });

  test('games table shows valid win/loss probabilities', async ({ page }) => {
    const randomTeams = getRandomTeams(3);

    for (const teamName of randomTeams) {
      await test.step(`Check game probs for ${teamName}`, async () => {
        await page.locator('#team-select').selectOption(teamName);

        const rows = page.locator('.games-table tbody tr');
        const count = await rows.count();
        expect(count).toBeGreaterThan(0);

        for (let i = 0; i < Math.min(count, 3); i++) {
          const row = rows.nth(i);
          const cells = row.locator('td');
          
          const weekText = await cells.nth(0).textContent();
          expect(weekText).toMatch(/Week \d+/);

          const winText = await cells.nth(2).textContent();
          const lossText = await cells.nth(3).textContent();

          const winProb = parseFloat(winText?.replace('%', '') || '0');
          const lossProb = parseFloat(lossText?.replace('%', '') || '0');

          expect(winProb).toBeGreaterThanOrEqual(0);
          expect(winProb).toBeLessThanOrEqual(100);
          expect(lossProb).toBeGreaterThanOrEqual(0);
          expect(lossProb).toBeLessThanOrEqual(100);
        }
      });
    }
  });

  test('resetting selection hides content', async ({ page }) => {
    await page.locator('#team-select').selectOption('Chiefs');
    await expect(page.locator('#team-header')).not.toHaveClass(/hidden/);

    await page.locator('#team-select').selectOption('');
    await expect(page.locator('#team-header')).toHaveClass(/hidden/);
    await expect(page.locator('#stats-grid')).toHaveClass(/hidden/);
    await expect(page.locator('#charts-section')).toHaveClass(/hidden/);
    await expect(page.locator('#team-content')).toHaveClass(/hidden/);
    await expect(page.locator('#content-placeholder')).not.toHaveClass(/hidden/);
  });
});
