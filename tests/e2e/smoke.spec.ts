import { test, expect } from '@playwright/test';

// Minimal smoke to verify the harness and static server work.
test('loads roster cap tool root', async ({ page, baseURL }) => {
  await page.goto('/docs/roster_cap_tool/');
  await expect(page.locator('h1.app-title')).toHaveText(/Roster Cap Tool/i);
  // Ensure CSV assets are accessible (not strictly required for UI to render)
  const respTeams = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_teams.csv`);
  expect(respTeams.ok()).toBeTruthy();
  const respPlayers = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_players.csv`);
  expect(respPlayers.ok()).toBeTruthy();
});

