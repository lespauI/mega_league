import { test, expect } from './fixtures';

const DEPTH_CHART_URL = '/docs/depth_chart/';

async function gotoDepthChart(page: import('@playwright/test').Page) {
  await page.goto(DEPTH_CHART_URL);
  await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
  await expect(page.locator('#depth-chart-grid')).toBeVisible();
}

test.describe('Depth Chart: Page Load', () => {
  test('page loads with correct title and header', async ({ page }) => {
    await page.goto(DEPTH_CHART_URL);
    await expect(page).toHaveTitle(/Depth Chart/i);
    await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
  });

  test('team selector is visible and populated', async ({ page }) => {
    await gotoDepthChart(page);
    const selector = page.locator('[data-testid="team-select"]');
    await expect(selector).toBeVisible();
    const options = selector.locator('option');
    await expect(options).toHaveCount(await options.count());
    expect(await options.count()).toBeGreaterThan(0);
  });

  test('depth chart grid renders', async ({ page }) => {
    await gotoDepthChart(page);
    const grid = page.locator('#depth-chart-grid');
    await expect(grid).toBeVisible();
    await expect(grid.locator('.depth-group')).toHaveCount(7);
  });
});

test.describe('Depth Chart: Position Groups', () => {
  const POSITION_GROUPS = [
    'Offense Skill',
    'Offensive Line',
    'Edge Rushers',
    'Interior DL',
    'Linebackers',
    'Secondary',
    'Specialists',
  ];

  test('all position groups render with headers', async ({ page }) => {
    await gotoDepthChart(page);
    for (const groupName of POSITION_GROUPS) {
      await expect(page.locator('.depth-group__header', { hasText: groupName })).toBeVisible();
    }
  });

  test('Offense Skill group has correct positions', async ({ page }) => {
    await gotoDepthChart(page);
    const group = page.locator('.depth-group').filter({ hasText: 'Offense Skill' });
    const posLabels = group.locator('.depth-cell--pos');
    await expect(posLabels).toContainText(['QB', 'HB', 'FB', 'WR1', 'WR2', 'TE']);
  });

  test('Offensive Line group has correct positions', async ({ page }) => {
    await gotoDepthChart(page);
    const group = page.locator('.depth-group').filter({ hasText: 'Offensive Line' });
    const posLabels = group.locator('.depth-cell--pos');
    await expect(posLabels).toContainText(['LT', 'LG', 'C', 'RG', 'RT']);
  });

  test('Secondary group has correct positions', async ({ page }) => {
    await gotoDepthChart(page);
    const group = page.locator('.depth-group').filter({ hasText: 'Secondary' });
    const posLabels = group.locator('.depth-cell--pos');
    await expect(posLabels).toContainText(['CB1', 'CB2', 'FS', 'SS']);
  });

  test('Specialists group has K, P, LS', async ({ page }) => {
    await gotoDepthChart(page);
    const group = page.locator('.depth-group').filter({ hasText: 'Specialists' });
    const posLabels = group.locator('.depth-cell--pos');
    await expect(posLabels).toContainText(['K', 'P', 'LS']);
  });
});

test.describe('Depth Chart: Team Selection', () => {
  test('changing team updates depth chart players', async ({ page }) => {
    await gotoDepthChart(page);

    const selector = page.locator('[data-testid="team-select"]');
    const options = selector.locator('option');
    const optCount = await options.count();
    if (optCount < 2) {
      test.skip();
      return;
    }

    const initialHtml = await page.locator('#depth-chart-grid').innerHTML();

    const secondTeam = await options.nth(1).getAttribute('value');
    await selector.selectOption(secondTeam!);

    await page.waitForFunction(
      (initial) => document.getElementById('depth-chart-grid')?.innerHTML !== initial,
      initialHtml
    );

    const updatedHtml = await page.locator('#depth-chart-grid').innerHTML();
    expect(updatedHtml).not.toBe(initialHtml);
  });

  test('selected team persists visually in dropdown', async ({ page }) => {
    await gotoDepthChart(page);

    const selector = page.locator('[data-testid="team-select"]');
    const options = selector.locator('option');
    const optCount = await options.count();
    if (optCount < 2) {
      test.skip();
      return;
    }

    const secondTeamValue = await options.nth(1).getAttribute('value');
    await selector.selectOption(secondTeamValue!);

    await expect(selector).toHaveValue(secondTeamValue!);
  });
});

test.describe('Depth Chart: Player Display', () => {
  test('players display with name and OVR', async ({ page }) => {
    await gotoDepthChart(page);

    const playerCells = page.locator('.depth-cell .player-name');
    const count = await playerCells.count();
    expect(count).toBeGreaterThan(0);

    const firstPlayerName = await playerCells.first().textContent();
    expect(firstPlayerName).toBeTruthy();
    expect(firstPlayerName!.length).toBeGreaterThan(0);

    const ovrCells = page.locator('.depth-cell .player-ovr');
    const firstOvr = await ovrCells.first().textContent();
    expect(firstOvr).toBeTruthy();
    const ovrNum = parseInt(firstOvr!, 10);
    expect(Number.isFinite(ovrNum)).toBeTruthy();
    expect(ovrNum).toBeGreaterThanOrEqual(0);
    expect(ovrNum).toBeLessThanOrEqual(99);
  });

  test('player names follow F.LastName format', async ({ page }) => {
    await gotoDepthChart(page);

    const playerNames = page.locator('.depth-cell .player-name');
    const count = await playerNames.count();
    expect(count).toBeGreaterThan(0);

    const name = await playerNames.first().textContent();
    expect(name).toMatch(/^[A-Z]\..+$/);
  });

  test('players are ordered by OVR (descending) within position', async ({ page }) => {
    await gotoDepthChart(page);

    const qbRow = page.locator('.depth-group').filter({ hasText: 'Offense Skill' }).locator('tr').filter({ hasText: 'QB' }).first();
    const ovrCells = qbRow.locator('.player-ovr');
    const count = await ovrCells.count();

    if (count >= 2) {
      const ovrs: number[] = [];
      for (let i = 0; i < count; i++) {
        const txt = await ovrCells.nth(i).textContent();
        ovrs.push(parseInt(txt!, 10));
      }
      for (let i = 1; i < ovrs.length; i++) {
        expect(ovrs[i]).toBeLessThanOrEqual(ovrs[i - 1]);
      }
    }
  });
});

test.describe('Depth Chart: Empty Slots', () => {
  test('empty needed slots show dash with need styling', async ({ page }) => {
    await gotoDepthChart(page);

    const needCells = page.locator('.depth-cell--need');
    const count = await needCells.count();
    if (count > 0) {
      const firstNeed = needCells.first();
      await expect(firstNeed).toHaveText('—');
    }
  });

  test('empty slots beyond max do not show dash', async ({ page }) => {
    await gotoDepthChart(page);

    const fbRow = page.locator('.depth-group').filter({ hasText: 'Offense Skill' }).locator('tr').filter({ hasText: 'FB' }).first();
    const cells = fbRow.locator('.depth-cell').filter({ hasNotText: 'FB' });
    const count = await cells.count();
    expect(count).toBe(4);

    for (let i = 1; i < 4; i++) {
      const cell = cells.nth(i);
      const text = await cell.textContent();
      if (text === '' || text === null) {
        await expect(cell).not.toHaveClass(/depth-cell--need/);
      }
    }
  });
});

test.describe('Depth Chart: Position Splits', () => {
  test('WR1 and WR2 show different players from WR pool', async ({ page }) => {
    await gotoDepthChart(page);

    const offenseGroup = page.locator('.depth-group').filter({ hasText: 'Offense Skill' });
    const wr1Row = offenseGroup.locator('tr').filter({ hasText: 'WR1' }).first();
    const wr2Row = offenseGroup.locator('tr').filter({ hasText: 'WR2' }).first();

    const wr1Players = wr1Row.locator('.player-name');
    const wr2Players = wr2Row.locator('.player-name');

    const wr1Count = await wr1Players.count();
    const wr2Count = await wr2Players.count();

    if (wr1Count > 0 && wr2Count > 0) {
      const wr1Names: string[] = [];
      const wr2Names: string[] = [];
      for (let i = 0; i < wr1Count; i++) {
        wr1Names.push((await wr1Players.nth(i).textContent()) || '');
      }
      for (let i = 0; i < wr2Count; i++) {
        wr2Names.push((await wr2Players.nth(i).textContent()) || '');
      }
      const overlap = wr1Names.filter((n) => wr2Names.includes(n));
      expect(overlap.length).toBe(0);
    }
  });

  test('CB1 and CB2 show different players from CB pool', async ({ page }) => {
    await gotoDepthChart(page);

    const secondaryGroup = page.locator('.depth-group').filter({ hasText: 'Secondary' });
    const cb1Row = secondaryGroup.locator('tr').filter({ hasText: 'CB1' }).first();
    const cb2Row = secondaryGroup.locator('tr').filter({ hasText: 'CB2' }).first();

    const cb1Players = cb1Row.locator('.player-name');
    const cb2Players = cb2Row.locator('.player-name');

    const cb1Count = await cb1Players.count();
    const cb2Count = await cb2Players.count();

    if (cb1Count > 0 && cb2Count > 0) {
      const cb1Names: string[] = [];
      const cb2Names: string[] = [];
      for (let i = 0; i < cb1Count; i++) {
        cb1Names.push((await cb1Players.nth(i).textContent()) || '');
      }
      for (let i = 0; i < cb2Count; i++) {
        cb2Names.push((await cb2Players.nth(i).textContent()) || '');
      }
      const overlap = cb1Names.filter((n) => cb2Names.includes(n));
      expect(overlap.length).toBe(0);
    }
  });
});

test.describe('Depth Chart: Data Loading', () => {
  test('CSV assets are accessible', async ({ page, baseURL }) => {
    const respTeams = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_teams.csv`);
    expect(respTeams.ok()).toBeTruthy();

    const respPlayers = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_players.csv`);
    expect(respPlayers.ok()).toBeTruthy();
  });

  test('handles page refresh gracefully', async ({ page }) => {
    await gotoDepthChart(page);

    const initialSelector = page.locator('[data-testid="team-select"]');
    await expect(initialSelector).toBeVisible();

    await page.reload();

    await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
    await expect(page.locator('[data-testid="team-select"]')).toBeVisible();
    await expect(page.locator('#depth-chart-grid .depth-group')).toHaveCount(7);
  });
});

test.describe('Depth Chart: Edge Cases', () => {
  test('depth table has correct column structure', async ({ page }) => {
    await gotoDepthChart(page);

    const firstTable = page.locator('.depth-table').first();
    const headerCells = firstTable.locator('thead th');
    await expect(headerCells).toHaveCount(5);
    await expect(headerCells).toContainText(['Pos', '1', '2', '3', '4']);
  });

  test('all teams from selector are valid', async ({ page }) => {
    await gotoDepthChart(page);

    const selector = page.locator('[data-testid="team-select"]');
    const options = selector.locator('option');
    const count = await options.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const value = await options.nth(i).getAttribute('value');
      expect(value).toBeTruthy();
      expect(value!.length).toBeGreaterThan(0);
    }
  });

  test('rapid team switching does not break UI', async ({ page }) => {
    await gotoDepthChart(page);

    const selector = page.locator('[data-testid="team-select"]');
    const options = selector.locator('option');
    const count = await options.count();

    if (count >= 3) {
      for (let i = 0; i < 3; i++) {
        const value = await options.nth(i % count).getAttribute('value');
        await selector.selectOption(value!);
      }
      await expect(page.locator('#depth-chart-grid .depth-group')).toHaveCount(7);
    }
  });
});

test.describe('Depth Chart: Negative Cases', () => {
  test('gracefully handles direct navigation', async ({ page }) => {
    await page.goto(DEPTH_CHART_URL);
    await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
    await expect(page.locator('#depth-chart-grid')).toBeVisible();
  });

  test('no JavaScript errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await gotoDepthChart(page);

    expect(errors).toHaveLength(0);
  });

  test('no console errors on team change', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await gotoDepthChart(page);

    const selector = page.locator('[data-testid="team-select"]');
    const options = selector.locator('option');
    const count = await options.count();

    if (count >= 2) {
      const secondTeam = await options.nth(1).getAttribute('value');
      await selector.selectOption(secondTeam!);
      await page.waitForTimeout(500);
    }

    expect(errors).toHaveLength(0);
  });
});
