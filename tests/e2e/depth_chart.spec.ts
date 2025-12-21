import { test, expect } from './fixtures';
import * as fs from 'fs/promises';

const DEPTH_CHART_URL = '/docs/depth_chart/';

async function gotoDepthChart(page: import('@playwright/test').Page) {
  await page.goto(DEPTH_CHART_URL);
  await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
  await expect(page.locator('#depth-chart-grid .depth-layout')).toBeVisible();
}

async function openRosterPanel(page: import('@playwright/test').Page) {
  const rosterPanel = page.locator('#roster-panel');
  const isVisible = await rosterPanel.isVisible();
  if (isVisible) return;

  const toggleBtn = page.locator('button.depth-chart-toolbar__btn--roster-toggle');
  await expect(toggleBtn).toBeVisible();
  await toggleBtn.click();
  await expect(rosterPanel).toBeVisible();
}

test.describe('Depth Chart: Page Load & Layout', () => {
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
    const count = await options.count();
    expect(count).toBeGreaterThan(0);
  });

  test('offense, defense and special sections render expected slots', async ({ page }) => {
    await gotoDepthChart(page);

    const offense = page.locator('.depth-side.depth-side--offense');
    await expect(offense).toBeVisible();
    await expect(offense.locator('.position-card.slot-LT')).toBeVisible();
    await expect(offense.locator('.position-card.slot-C')).toBeVisible();
    await expect(offense.locator('.position-card.slot-QB')).toBeVisible();
    await expect(offense.locator('.position-card.slot-HB')).toBeVisible();
    await expect(offense.locator('.position-card.slot-WR1')).toBeVisible();
    await expect(offense.locator('.position-card.slot-WR2')).toBeVisible();
    await expect(offense.locator('.position-card.slot-TE')).toBeVisible();

    const defense = page.locator('.depth-side.depth-side--defense');
    await expect(defense).toBeVisible();
    await expect(defense.locator('.position-card.slot-FS')).toBeVisible();
    await expect(defense.locator('.position-card.slot-SS')).toBeVisible();
    await expect(defense.locator('.position-card.slot-SAM')).toBeVisible();
    await expect(defense.locator('.position-card.slot-MIKE')).toBeVisible();
    await expect(defense.locator('.position-card.slot-WILL')).toBeVisible();
    await expect(defense.locator('.position-card.slot-DT1')).toBeVisible();
    await expect(defense.locator('.position-card.slot-DT2')).toBeVisible();
    await expect(defense.locator('.position-card.slot-EDGE1')).toBeVisible();
    await expect(defense.locator('.position-card.slot-EDGE2')).toBeVisible();
    await expect(defense.locator('.position-card.slot-CB1')).toBeVisible();
    await expect(defense.locator('.position-card.slot-CB2')).toBeVisible();

    const special = page.locator('.depth-side.depth-side--special');
    await expect(special).toBeVisible();
    await expect(special.locator('.position-card.slot-K')).toBeVisible();
    await expect(special.locator('.position-card.slot-P')).toBeVisible();
    await expect(special.locator('.position-card.slot-LS')).toBeVisible();
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

    const grid = page.locator('#depth-chart-grid');
    const initialHtml = await grid.innerHTML();

    const secondTeam = await options.nth(1).getAttribute('value');
    await selector.selectOption(secondTeam!);

    await page.waitForFunction(
      (initial) => document.getElementById('depth-chart-grid')?.innerHTML !== initial,
      initialHtml
    );

    const updatedHtml = await grid.innerHTML();
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

    const playerNames = page.locator('.depth-row--player .player-name');
    const count = await playerNames.count();
    expect(count).toBeGreaterThan(0);

    const firstPlayerName = await playerNames.first().textContent();
    expect(firstPlayerName).toBeTruthy();
    expect(firstPlayerName!.length).toBeGreaterThan(0);

    const ovrCells = page.locator('.depth-row--player .player-ovr');
    const firstOvr = await ovrCells.first().textContent();
    expect(firstOvr).toBeTruthy();
    const ovrNum = parseInt(firstOvr!, 10);
    expect(Number.isFinite(ovrNum)).toBeTruthy();
    expect(ovrNum).toBeGreaterThanOrEqual(0);
    expect(ovrNum).toBeLessThanOrEqual(99);
  });

  test('player names follow F.LastName format', async ({ page }) => {
    await gotoDepthChart(page);

    const playerNames = page.locator('.depth-row--player .player-name');
    const count = await playerNames.count();
    expect(count).toBeGreaterThan(0);

    const name = await playerNames.first().textContent();
    expect(name).toMatch(/^[A-Z]\..+$/);
  });

  test('players are ordered by OVR (descending) within QB card', async ({ page }) => {
    await gotoDepthChart(page);

    const qbCard = page.locator('.position-card.slot-QB');
    await expect(qbCard).toBeVisible();

    const ovrCells = qbCard.locator('.depth-row--player .player-ovr');
    const count = await ovrCells.count();

    if (count >= 2) {
      const ovrs: number[] = [];
      for (let i = 0; i < count; i++) {
        const txt = await ovrCells.nth(i).textContent();
        ovrs.push(parseInt(txt || '0', 10));
      }
      for (let i = 1; i < ovrs.length; i++) {
        expect(ovrs[i]).toBeLessThanOrEqual(ovrs[i - 1]);
      }
    }
  });
});

test.describe('Depth Chart: Empty & Optional Slots', () => {
  test('empty needed slots show dash with need styling', async ({ page }) => {
    await gotoDepthChart(page);

    const needRows = page.locator('.depth-row.depth-row--need');
    const count = await needRows.count();
    if (count > 0) {
      const firstNeed = needRows.first().locator('.depth-row__empty');
      await expect(firstNeed).toHaveText('—');
    }
  });

  test('optional rows beyond max depth do not show dash', async ({ page }) => {
    await gotoDepthChart(page);

    const optionalRows = page.locator('.depth-row.depth-row--optional');
    const count = await optionalRows.count();
    if (count > 0) {
      const first = optionalRows.first().locator('.depth-row__empty');
      const text = (await first.textContent()) || '';
      expect(text.trim()).toBe('');
    }
  });
});

test.describe('Depth Chart: Position Splits', () => {
  test('WR1 and WR2 show different players from WR pool', async ({ page }) => {
    await gotoDepthChart(page);

    const wr1Card = page.locator('.position-card.slot-WR1');
    const wr2Card = page.locator('.position-card.slot-WR2');

    const wr1Players = wr1Card.locator('.player-name');
    const wr2Players = wr2Card.locator('.player-name');

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

    const cb1Card = page.locator('.position-card.slot-CB1');
    const cb2Card = page.locator('.position-card.slot-CB2');

    const cb1Players = cb1Card.locator('.player-name');
    const cb2Players = cb2Card.locator('.player-name');

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

test.describe('Depth Chart: Data Loading & Refresh', () => {
  test('CSV assets are accessible', async ({ page, baseURL }) => {
    const respTeams = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_teams.csv`);
    expect(respTeams.ok()).toBeTruthy();

    const respPlayers = await page.request.get(
      `${baseURL}/docs/roster_cap_tool/data/MEGA_players.csv`
    );
    expect(respPlayers.ok()).toBeTruthy();
  });

  test('handles page refresh gracefully', async ({ page }) => {
    await gotoDepthChart(page);

    const initialSelector = page.locator('[data-testid="team-select"]');
    await expect(initialSelector).toBeVisible();

    await page.reload();

    await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
    await expect(page.locator('[data-testid="team-select"]')).toBeVisible();
    const cardCount = await page.locator('#depth-chart-grid .position-card').count();
    expect(cardCount).toBeGreaterThan(0);
  });
});

test.describe('Depth Chart: Roster, editing & export flows', () => {
  test('slot editor can set draft placeholder and persist across team switches', async ({ page }) => {
    await gotoDepthChart(page);

    const selector = page.locator('[data-testid="team-select"]');
    const initialTeam = await selector.inputValue();

    const targetRow = page.locator(
      '.depth-row[data-slot-id="WR1"][data-depth-index="3"]'
    );
    await expect(targetRow).toBeVisible();

    await targetRow.click();

    const editor = page.locator('.slot-editor-backdrop.is-open');
    await expect(editor).toBeVisible();

    await editor.locator('.slot-editor__pill', { hasText: 'Draft R1' }).click();

    await expect(targetRow).toHaveText(/Draft R1/);

    const options = selector.locator('option');
    const optCount = await options.count();
    if (optCount >= 2) {
      const secondTeam = await options.nth(1).getAttribute('value');
      if (secondTeam && secondTeam !== initialTeam) {
        await selector.selectOption(secondTeam);
        await expect(page.locator('#depth-chart-grid .position-card.slot-WR1')).toBeVisible();

        await selector.selectOption(initialTeam);
        await expect(
          page.locator('.depth-row[data-slot-id="WR1"][data-depth-index="3"]')
        ).toHaveText(/Draft R1/);
      }
    }
  });

  test('slot editor free-agent search filters list', async ({ page }) => {
    await gotoDepthChart(page);

    const targetRow = page.locator(
      '.depth-row[data-slot-id="WR1"][data-depth-index="2"]'
    );
    await expect(targetRow).toBeVisible();
    await targetRow.click();

    const editor = page.locator('.slot-editor-backdrop.is-open');
    await expect(editor).toBeVisible();

    const faSection = editor.locator('.slot-editor__section', { hasText: 'Free agents' });
    const search = faSection.locator('.slot-editor__search');
    await expect(search).toBeVisible();

    await search.fill('zzzzzzzz');

    const empty = faSection.locator('.slot-editor__empty');
    await expect(empty).toHaveText(/No free agents match the filters/i);
  });

  test('roster panel cut to FA updates roster, FA list and depth chart', async ({ page }) => {
    await gotoDepthChart(page);
    await openRosterPanel(page);

    const rosterSection = page
      .locator('.roster-panel__section')
      .filter({ hasText: 'Team roster' });
    const firstRow = rosterSection.locator('.roster-panel__row').first();
    await expect(firstRow).toBeVisible();

    const playerName = (await firstRow.locator('.roster-panel__row-name').textContent())?.trim();
    expect(playerName).toBeTruthy();

    await firstRow.locator('button', { hasText: 'Cut to FA' }).click();

    await expect(
      rosterSection.locator('.roster-panel__row-name', { hasText: playerName! })
    ).toHaveCount(0);

    const faSection = page.locator('.roster-panel__section').filter({ hasText: 'Free agents' });
    const faSearch = faSection.locator('.roster-panel__search');
    await expect(faSearch).toBeVisible();
    await faSearch.fill(playerName!);

    await expect(
      faSection.locator('.roster-panel__row-name', { hasText: playerName! })
    ).toHaveCount(1);

    await expect(
      page.locator('.depth-row--player .player-name', { hasText: playerName! })
    ).toHaveCount(0);
  });

  test('Reset to baseline button clears depth changes for team', async ({ page }) => {
    await gotoDepthChart(page);

    const targetRow = page.locator(
      '.depth-row[data-slot-id="WR1"][data-depth-index="3"]'
    );
    await expect(targetRow).toBeVisible();

    const beforeText = (await targetRow.textContent()) || '';

    await targetRow.click();
    const editor = page.locator('.slot-editor-backdrop.is-open');
    await expect(editor).toBeVisible();
    await editor.locator('.slot-editor__pill', { hasText: 'Draft R2' }).click();

    await expect(targetRow).toHaveText(/Draft R2/);

    const resetBtn = page.locator('button.depth-chart-toolbar__btn--reset');
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    const afterText = (await targetRow.textContent()) || '';
    expect(afterText).not.toMatch(/Draft R2/);
    if (beforeText.trim().length > 0) {
      expect(afterText.trim()).toBe(beforeText.trim());
    }
  });

  test('Export CSV button downloads depth plan with expected header', async ({ page }) => {
    await gotoDepthChart(page);

    const exportBtn = page.locator('button', { hasText: /Export CSV/i });
    await expect(exportBtn).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      exportBtn.click(),
    ]);

    const path = await download.path();
    expect(path).toBeTruthy();

    const content = await fs.readFile(path!, 'utf8');
    expect(content).toContain(
      'team,side,positionSlot,depth,playerName,acquisition,ovr,contractLength,contractYearsLeft,faAfterSeason'
    );
    const lines = content.trim().split('\n');
    expect(lines.length).toBeGreaterThan(1);
  });
});

test.describe('Depth Chart: Negative & error cases', () => {
  test('gracefully handles direct navigation', async ({ page }) => {
    await page.goto(DEPTH_CHART_URL);
    await expect(page.locator('h1.app-title')).toHaveText(/Depth Chart/i);
    await expect(page.locator('#depth-chart-grid')).toBeVisible();
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
      const cardCount = await page.locator('#depth-chart-grid .position-card').count();
      expect(cardCount).toBeGreaterThan(0);
    }
  });

  test('no JavaScript errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await gotoDepthChart(page);

    expect(errors).toHaveLength(0);
  });

  test('no runtime errors on team change', async ({ page }) => {
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

test.describe('Depth Chart: Visual Snapshot', () => {
  test('capture main layout screenshot', async ({ page }) => {
    await gotoDepthChart(page);
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.screenshot({
      path: 'test-results/depth-chart-main.png',
      fullPage: true,
    });
  });
});
