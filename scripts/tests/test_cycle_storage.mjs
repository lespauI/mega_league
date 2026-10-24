import assert from 'node:assert/strict';
import {
  configureCycleStorage,
  copyLegacyEntries,
  exportStorageBackup,
  getCycleStorage,
  importStorageBackup,
  legacyEntries,
  normalizeCycleIdentity,
  scopedStorageKey,
} from '../../docs/shared/cycleStorage.js';

class MemoryStorage {
  values = new Map();
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null; }
  setItem(key, value) { this.values.set(key, String(value)); }
  removeItem(key) { this.values.delete(key); }
}

const localStorage = new MemoryStorage();
globalThis.window = { localStorage };
const keys = ['rosterCap.scenarios', 'rosterCap.draftPicks'];
localStorage.setItem(keys[0], '[{"id":"legacy"}]');
localStorage.setItem(keys[1], '{"SEA":{"1":2}}');

const seasonOne = configureCycleStorage({ game: 'Madden 27', seasonIndex: 0, calendarYear: 2026 });
assert.equal(seasonOne.key, 'madden-27-s0-y2026');
assert.equal(legacyEntries('rosterCap', keys).length, 2);
assert.equal(getCycleStorage('rosterCap').getItem(keys[0]), null, 'legacy values do not auto-apply to a cycle');

let copied = copyLegacyEntries('rosterCap', keys);
assert.deepEqual(copied, { copied: 2, skipped: 0 });
assert.equal(localStorage.getItem(keys[0]), '[{"id":"legacy"}]', 'copy keeps legacy bytes');
assert.equal(getCycleStorage('rosterCap').getItem(keys[0]), '[{"id":"legacy"}]');
copied = copyLegacyEntries('rosterCap', keys);
assert.deepEqual(copied, { copied: 0, skipped: 2 }, 'copy does not overwrite current cycle data');

const backup = exportStorageBackup('rosterCap', keys);
configureCycleStorage({ game: 'Madden 27', seasonIndex: 1, calendarYear: 2027 });
assert.equal(getCycleStorage('rosterCap').getItem(keys[0]), null, 'seasons use separate storage keys');
const imported = importStorageBackup(backup, 'rosterCap', keys);
assert.deepEqual(imported, { imported: 2, skipped: 0, sourceCycle: seasonOne });
assert.equal(getCycleStorage('rosterCap').getItem(keys[0]), '[{"id":"legacy"}]');

getCycleStorage('rosterCap').setItem(keys[0], 'current-season');
assert.deepEqual(importStorageBackup(backup, 'rosterCap', keys).skipped, 2, 'existing target values are preserved');
assert.equal(getCycleStorage('rosterCap').getItem(keys[0]), 'current-season');
assert.equal(localStorage.getItem(keys[0]), '[{"id":"legacy"}]');
assert.notEqual(scopedStorageKey('rosterCap', keys[0]), keys[0]);
assert.throws(() => normalizeCycleIdentity({ game: 'Madden 27', seasonIndex: -1, calendarYear: 2026 }));
assert.throws(() => importStorageBackup(backup, 'depthChart', keys), /does not match/);

const capState = await import('../../docs/roster_cap_tool/js/state.js');
const seasonThree = { game: 'Madden 27', seasonIndex: 2, calendarYear: 2028 };
capState.initState({ teams: [], players: [], cycle: seasonThree });
const savedId = capState.saveScenario('cycle scoped');
assert.equal(capState.listScenarios()[0].id, savedId);
assert.equal(localStorage.getItem(keys[0]), '[{"id":"legacy"}]', 'cap state did not overwrite the legacy scenario list');
assert.ok(localStorage.getItem(scopedStorageKey('rosterCap', keys[0])).includes('cycle scoped'));

const depthState = await import('../../docs/depth_chart/js/state.js');
const draftPicks = await import('../../docs/depth_chart/js/draftPicks.js');
const {
  DEPTH_CHART_STORAGE_CONTROLS,
  SHARED_DRAFT_PICKS_STORAGE_CONTROLS,
} = await import('../../docs/depth_chart/js/storageConfig.js');
const depthKeys = Object.values(depthState.STORAGE_KEYS);
assert.deepEqual(DEPTH_CHART_STORAGE_CONTROLS.keys, depthKeys, 'depth controls use the state module keys');
assert.equal(DEPTH_CHART_STORAGE_CONTROLS.namespace, depthState.STORAGE_NAMESPACE);
assert.deepEqual(SHARED_DRAFT_PICKS_STORAGE_CONTROLS.keys, [draftPicks.DRAFT_PICKS_STORAGE_KEY]);
assert.equal(SHARED_DRAFT_PICKS_STORAGE_CONTROLS.namespace, draftPicks.DRAFT_PICKS_STORAGE_NAMESPACE);
localStorage.setItem(depthKeys[0], '{"legacy-player":{"isFreeAgent":true}}');
configureCycleStorage({ game: 'Madden 27', seasonIndex: 4, calendarYear: 2030 });
assert.deepEqual(copyLegacyEntries(
  DEPTH_CHART_STORAGE_CONTROLS.namespace, DEPTH_CHART_STORAGE_CONTROLS.keys,
), { copied: 1, skipped: 0 });
depthState.initState({
  teams: [{ abbrName: 'SEA', displayName: 'Seattle Seahawks' }],
  players: [{ id: 'player-1', team: 'SEA', position: 'QB' }],
  cycle: { game: 'Madden 27', seasonIndex: 4, calendarYear: 2030 },
});
depthState.setRosterEdit('player-1', { isFreeAgent: true });
assert.ok(localStorage.getItem(scopedStorageKey(depthState.STORAGE_NAMESPACE, depthKeys[0])).includes('player-1'));
assert.equal(localStorage.getItem(depthKeys[0]), '{"legacy-player":{"isFreeAgent":true}}', 'depth edits preserve the legacy value');
assert.equal(localStorage.getItem(scopedStorageKey(depthState.STORAGE_NAMESPACE, depthKeys[2])), 'SEA');
const legacyPickBytes = '{"SEA":{"1":2}}';
localStorage.setItem(draftPicks.DRAFT_PICKS_STORAGE_KEY, legacyPickBytes);
assert.deepEqual(copyLegacyEntries(
  DEPTH_CHART_STORAGE_CONTROLS.namespace, DEPTH_CHART_STORAGE_CONTROLS.keys,
), { copied: 0, skipped: 1 });
assert.equal(getCycleStorage(draftPicks.DRAFT_PICKS_STORAGE_NAMESPACE)
  .getItem(draftPicks.DRAFT_PICKS_STORAGE_KEY), null, 'depth controls do not copy shared picks into the wrong namespace');
assert.deepEqual(copyLegacyEntries(
  SHARED_DRAFT_PICKS_STORAGE_CONTROLS.namespace, SHARED_DRAFT_PICKS_STORAGE_CONTROLS.keys,
), { copied: 1, skipped: 0 });
assert.equal(getCycleStorage(draftPicks.DRAFT_PICKS_STORAGE_NAMESPACE)
  .getItem(draftPicks.DRAFT_PICKS_STORAGE_KEY), legacyPickBytes);
draftPicks.setDraftPicksForTeam('SEA', { 1: 4, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1 });
assert.equal(draftPicks.getDraftPicksForTeam('SEA')[1], 4);
const sharedBackup = JSON.parse(exportStorageBackup(
  SHARED_DRAFT_PICKS_STORAGE_CONTROLS.namespace, SHARED_DRAFT_PICKS_STORAGE_CONTROLS.keys,
));
assert.equal(sharedBackup.entries[draftPicks.DRAFT_PICKS_STORAGE_KEY].legacy, legacyPickBytes);
assert.equal(JSON.parse(sharedBackup.entries[draftPicks.DRAFT_PICKS_STORAGE_KEY].cycle).SEA[1], 4,
  'backup captures the edited shared pick value');

const nextCycle = configureCycleStorage({ game: 'Madden 27', seasonIndex: 5, calendarYear: 2031 });
assert.deepEqual(importStorageBackup(
  JSON.stringify(sharedBackup), SHARED_DRAFT_PICKS_STORAGE_CONTROLS.namespace,
  SHARED_DRAFT_PICKS_STORAGE_CONTROLS.keys,
).imported, 1);
assert.equal(draftPicks.getDraftPicksForTeam('SEA')[1], 4, 'depth chart consumer restores the backup');
capState.initState({ teams: [{ abbrName: 'SEA' }], players: [], cycle: nextCycle });
assert.equal(capState.getDraftPicksForSelectedTeam()[1], 4, 'cap consumer sees the same restored shared picks');
assert.equal(localStorage.getItem(draftPicks.DRAFT_PICKS_STORAGE_KEY), legacyPickBytes,
  'migration and restore preserve original legacy bytes');

class FakeElement {
  children = [];
  listeners = {};
  style = {};
  files = [];
  value = '';
  textContent = '';
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  setAttribute() {}
  click() { this.listeners.click?.(); }
}
const panels = new Map([
  ['cycle-storage-controls', new FakeElement()],
  ['shared-draft-storage-controls', new FakeElement()],
]);
const allElements = [];
globalThis.document = {
  getElementById(id) { return panels.get(id) || null; },
  createElement() { const element = new FakeElement(); allElements.push(element); return element; },
};
let reloads = 0;
window.confirm = () => true;
window.location = { reload() { reloads++; } };
const { mountCycleStorageControls } = await import('../../docs/shared/cycleStorageControls.js');
const uiCycle = configureCycleStorage({ game: 'Madden 27', seasonIndex: 6, calendarYear: 2032 });
localStorage.setItem(keys[0], '[{"id":"preserve-ui"}]');
mountCycleStorageControls('cycle-storage-controls', { namespace: 'rosterCap', legacyKeys: keys, title: 'Test' });
mountCycleStorageControls('shared-draft-storage-controls', {
  namespace: SHARED_DRAFT_PICKS_STORAGE_CONTROLS.namespace,
  legacyKeys: SHARED_DRAFT_PICKS_STORAGE_CONTROLS.keys,
  title: SHARED_DRAFT_PICKS_STORAGE_CONTROLS.title,
});
const copyButton = allElements.find((element) => element.textContent.startsWith('Copy '));
assert.ok(copyButton, 'legacy migration action is visible');
copyButton.click();
assert.equal(getCycleStorage('rosterCap').getItem(keys[0]), '[{"id":"preserve-ui"}]');
assert.equal(localStorage.getItem(keys[0]), '[{"id":"preserve-ui"}]', 'UI copy preserves the original entry');
const sharedCopyButton = panels.get('shared-draft-storage-controls').children
  .find((element) => element.textContent.startsWith('Copy '));
assert.ok(sharedCopyButton, 'depth chart exposes a separate migration control for shared draft picks');
sharedCopyButton.click();
assert.equal(getCycleStorage(draftPicks.DRAFT_PICKS_STORAGE_NAMESPACE)
  .getItem(draftPicks.DRAFT_PICKS_STORAGE_KEY), legacyPickBytes);
assert.equal(reloads, 2, 'copy actions reload so imported data is re-read by the apps');
assert.match(uiCycle.label, /Madden 27/);

console.log('Cycle-scoped storage copy/export/import checks passed.');
