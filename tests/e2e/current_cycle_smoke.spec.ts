import { test, expect } from './fixtures';

// These checks derive their cycle and team expectations from the current import,
// rather than relying on a player, team assignment, or franchise calendar year.
test.describe('Current-cycle publication', () => {
  test('playoff table labels the active snapshot week', async ({ page, request }) => {
    const response = await request.get('/docs/data/import_metadata.json');
    const metadata = await response.json();
    await page.goto('/docs/playoff_race_table.html');
    await expect(page.locator('.subtitle')).toHaveText(
      `Week ${metadata.completedThroughWeek} Standings & Playoff Probabilities`
    );
    await expect(page).toHaveTitle(`MEGA League Playoff Race - Week ${metadata.completedThroughWeek}`);
  });

  for (const dashboard of [
    'team_stats_explorer', 'team_stats_correlations', 'team_player_usage',
    'rankings_explorer', 'power_rankings_roster_charts', 'team_elo_correlations',
    'sos_graphs', 'sos_graphs_season1',
  ]) {
    test(`${dashboard} renders current-data charts`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`/docs/${dashboard}.html`);
      await expect(page.locator('svg').first()).toBeVisible({ timeout: 15_000 });
      expect(errors).toEqual([]);
    });
  }

  test('active ELO table renders current teams', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/docs/sos_season1.html');
    await expect(page.locator('#tbody tr').first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('#error')).toHaveText('');
    await expect(page.locator('#elo-source-label')).toContainText('Week');
    expect(errors).toEqual([]);
  });

  test('matchup helper populates its team selectors', async ({ page }) => {
    await page.goto('/docs/matchup_gameplan.html');
    await expect(page.locator('#my-team-select option')).not.toHaveCount(0);
    await expect(page.locator('#opp-team-select option')).not.toHaveCount(0);
    await expect(page.locator('#matchup-overview')).not.toContainText('Error loading');
  });

  test('every declared browser dataset is available', async ({ request, baseURL }) => {
    const response = await request.get('/docs/data/data_manifest.json');
    expect(response.ok()).toBeTruthy();
    const manifest = await response.json();
    expect(manifest.schemaVersion).toBe(1);
    expect(manifest.snapshotId).toBeTruthy();
    const metadata = await (await request.get('/docs/data/import_metadata.json')).json();
    expect(manifest.cycle.csvSeasonIndex).toBe(metadata.seasonIndex);
    expect(manifest.cycle.eloSourceWeek).toBe(metadata.eloSourceWeek);
    const manifestURL = new URL('/docs/data/data_manifest.json', baseURL);
    for (const [key, relative] of Object.entries(manifest.data)) {
      const data = await request.get(new URL(relative as string, manifestURL).href);
      expect(data.ok(), key).toBeTruthy();
      expect((await data.body()).length, key).toBeGreaterThan(0);
    }
  });

  test('browser modules resolve data independently of the current page', async ({ page }) => {
    await page.goto('/index.html');
    await page.addScriptTag({ url: '/docs/shared/data.js' });
    const result = await page.evaluate(async () => {
      const data = (globalThis as any).MegaData;
      const response = await fetch(await data.getDataUrl('teams'));
      return { ok: response.ok, text: await response.text() };
    });
    expect(result.ok).toBeTruthy();
    expect(result.text).toContain('displayName');
  });

  test('cap manager and depth chart load the same active teams', async ({ page }) => {
    await page.goto('/docs/roster_cap_tool/');
    const capTeams = page.getByTestId('team-select');
    await expect(capTeams).toBeVisible();
    await expect(page.locator('#cap-summary')).toContainText('Cap Space');
    const teams = await capTeams.locator('option').allTextContents();
    expect(teams.length).toBeGreaterThan(1);
    await expect(page.locator('#cycle-storage-controls')).toContainText('Season');

    await page.goto('/docs/depth_chart/');
    await expect(page.locator('#depth-chart-grid .depth-layout')).toBeVisible();
    expect(await page.getByTestId('team-select').locator('option').allTextContents()).toHaveLength(teams.length);
    await expect(page.locator('#cycle-storage-controls')).toContainText('Season');
  });

  test('missing browser manifest produces a visible startup error', async ({ page }) => {
    await page.route('**/docs/data/data_manifest.json', route => route.fulfill({ status: 404, body: 'missing manifest' }));
    await page.goto('/docs/depth_chart/');
    await expect(page.locator('#cycle-storage-controls')).toContainText(/could not load|manifest/i);
    await expect(page.locator('#depth-chart-grid .depth-layout')).toHaveCount(0);
  });

  test('usage dashboard shows a visible error when its manifest cannot load', async ({ page }) => {
    await page.route('https://cdn.jsdelivr.net/npm/d3@7', route => route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: `window.d3 = { select: selector => ({ text: value => { document.querySelector(selector).textContent = value; } }) };`,
    }));
    await page.route('**/docs/data/data_manifest.json', route => route.fulfill({ status: 404, body: 'missing manifest' }));
    await page.goto('/docs/team_player_usage.html');
    await expect(page.locator('#error')).toContainText(/Error loading usage data: Data manifest request failed/);
  });

  test('shared Season 1 and 2 shell resolves ELO module under a project subpath', async ({ page, baseURL }) => {
    const requestedModules: string[] = [];
    page.on('request', request => {
      const url = new URL(request.url());
      if (url.pathname.endsWith('/elo_sos.js')) requestedModules.push(url.pathname);
    });
    await page.route('https://cdn.jsdelivr.net/npm/d3@7', route => route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: `window.d3 = { select: selector => ({ text: value => { document.querySelector(selector).textContent = value; } }) };`,
    }));
    await page.route('**/league/**', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/league/docs/data/data_manifest.json') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            schemaVersion: 1,
            snapshotId: 'subpath-fixture',
            cycle: {
              edition: 'Madden 27',
              csvSeasonIndex: 4,
              displaySeason: 5,
              calendarYear: 2030,
              completedThroughWeek: 12,
              exportWeekIndex: 12,
              eloSourceWeek: 8,
            },
            data: {},
          }),
        });
      }
      url.pathname = url.pathname.replace(/^\/league/, '') || '/';
      const response = await route.fetch({ url: url.href });
      return route.fulfill({ response });
    });

    for (const season of [1, 2]) {
      await page.goto(new URL(`/league/docs/sos_season${season}.html`, baseURL).href);
      await expect(page.locator('#error')).toContainText(`This page is for Season ${season}`);
      await expect(page.locator('#error')).toContainText('active data is Madden 27 Season 5');
    }
    expect(requestedModules).toContain('/league/docs/shared/elo_sos.js');
    expect(requestedModules).not.toContain('/league/docs/elo_sos.js');
  });
});
