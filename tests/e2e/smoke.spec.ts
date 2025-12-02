import { test, expect } from './fixtures';
import {
  capRoomValue,
  capSpentValue,
  capAvailableValue,
  tabsRoot,
  tab,
  parseMoney,
} from './utils/selectors';
import { gotoTool } from './fixtures';

test.describe('Smoke: Load + Cap Summary', () => {
  test('app loads, tabs render, cap summary shows numbers', async ({ page, baseURL }) => {
    await gotoTool(page);

    // Tabs render with expected labels
    await expect(tabsRoot(page)).toBeVisible();
    await expect(tab(page, 'active-roster')).toBeVisible();
    await expect(tab(page, 'injured-reserve')).toBeVisible();
    await expect(tab(page, 'dead-money')).toBeVisible();
    await expect(tab(page, 'projections')).toBeVisible();
    await expect(tab(page, 'draft-picks')).toBeVisible();
    await expect(tab(page, 'free-agents')).toBeVisible();

    // Cap Summary values are visible and numeric
    const roomTxt = await capRoomValue(page).innerText();
    const spentTxt = await capSpentValue(page).innerText();
    const availTxt = await capAvailableValue(page).innerText();
    const room = parseMoney(roomTxt);
    const spent = parseMoney(spentTxt);
    const avail = parseMoney(availTxt);
    expect(Number.isFinite(room)).toBeTruthy();
    expect(Number.isFinite(spent)).toBeTruthy();
    expect(Number.isFinite(avail)).toBeTruthy();

    // Basic sanity: room should be >= 0; spent not negative
    expect(room).toBeGreaterThanOrEqual(0);
    expect(spent).toBeGreaterThanOrEqual(0);

    // Ensure CSV assets are accessible (parsing relies on them)
    const respTeams = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_teams.csv`);
    expect(respTeams.ok()).toBeTruthy();
    const respPlayers = await page.request.get(`${baseURL}/docs/roster_cap_tool/data/MEGA_players.csv`);
    expect(respPlayers.ok()).toBeTruthy();
  });
});
