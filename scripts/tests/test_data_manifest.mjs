import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../../docs/shared/data.js', import.meta.url), 'utf8');
const context = { URL };
context.globalThis = context;
vm.runInNewContext(source, context, { filename: 'docs/shared/data.js' });

const manifestUrl = 'https://example.test/league/docs/data/data_manifest.json';
const validManifest = {
  schemaVersion: 1,
  snapshotId: 'snapshot-123',
  cycle: {
    edition: 'Madden 27',
    csvSeasonIndex: 0,
    displaySeason: 1,
    calendarYear: 2026,
    completedThroughWeek: 12,
    exportWeekIndex: 12,
    eloSourceWeek: 8,
  },
  data: {
    teams: '../../MEGA_teams.csv',
    elo: 'current_elo.csv',
    playoffs: 'playoff_probabilities.json',
  },
};

const sourceAnchoredRequests = [];
const sourceAnchoredContext = { URL };
sourceAnchoredContext.globalThis = sourceAnchoredContext;
sourceAnchoredContext.document = {
  currentScript: { src: 'https://example.test/league/docs/shared/data.js' },
  baseURI: 'https://example.test/league/docs/team_stats.html',
};
sourceAnchoredContext.fetch = async (url) => {
  sourceAnchoredRequests.push(String(url));
  return { ok: true, status: 200, json: async () => validManifest };
};
vm.runInNewContext(source, sourceAnchoredContext, { filename: 'docs/shared/data.js (source anchor fixture)' });
assert.equal(
  await sourceAnchoredContext.MegaData.getDataUrl('teams'),
  'https://example.test/league/MEGA_teams.csv',
  'browser loader uses the shared script URL as its manifest base under a project subpath',
);
assert.deepEqual(sourceAnchoredRequests, ['https://example.test/league/docs/data/data_manifest.json']);

function createMockLoader(manifest, resources = {}) {
  const requests = [];
  const loader = context.MegaData.createDataLoader({
    manifestUrl,
    fetchImpl: async (url) => {
      requests.push(String(url));
      if (String(url) === manifestUrl) {
        return { ok: true, status: 200, json: async () => manifest };
      }
      const value = resources[String(url)];
      if (value === undefined) return { ok: false, status: 404 };
      return {
        ok: true,
        status: 200,
        text: async () => value,
      };
    },
  });
  return { loader, requests };
}

const teamUrl = 'https://example.test/league/MEGA_teams.csv';
const currentEloUrl = 'https://example.test/league/docs/data/current_elo.csv';
const { loader, requests } = createMockLoader(validManifest, {
  [teamUrl]: 'abbrName,displayName\nSEA,Seattle Seahawks\n',
  [currentEloUrl]: 'Team,ELO,sourceWeek\nSeattle Seahawks,1200,8\n',
});

assert.equal(await loader.getDataUrl('teams'), teamUrl, 'manifest-relative URLs preserve a hosting subpath');
assert.deepEqual(requests, [manifestUrl], 'resolving a data URL loads only the manifest');
await loader.assertCycle({ displaySeason: 1, csvSeasonIndex: 0 });
assert.deepEqual(
  await loader.loadCsv('teams', (text) => text.trim().split('\n')),
  ['abbrName,displayName', 'SEA,Seattle Seahawks'],
);
await loader.loadCsv('teams', (text) => text);
assert.equal(requests.filter((url) => url === teamUrl).length, 1, 'resource text is cached per data key');
assert.equal(await loader.getDataUrl('elo'), currentEloUrl);
await assert.rejects(loader.loadJson('playoffs'), /Data request for "playoffs" failed \(404\)/);

await assert.rejects(loader.getDataUrl('unknown'), /Unknown browser data key/);
await assert.rejects(loader.getDataUrl('players'), /no URL for "players"/);
await assert.rejects(loader.assertCycle({ displaySeason: 2 }), /active data is Madden 27 Season 1/);

const malformed = createMockLoader({ ...validManifest, schemaVersion: 2 }).loader;
await assert.rejects(malformed.getManifest(), /Unsupported data manifest schemaVersion/);

const invalidManifestJson = context.MegaData.createDataLoader({
  manifestUrl,
  fetchImpl: async () => ({
    ok: true,
    status: 200,
    json: async () => { throw new SyntaxError('Unexpected token'); },
  }),
});
await assert.rejects(invalidManifestJson.getManifest(), /Data manifest is not valid JSON/);

const unknownData = createMockLoader({
  ...validManifest,
  data: { ...validManifest.data, old_season: 'season4.csv' },
}).loader;
await assert.rejects(unknownData.getManifest(), /unknown data key "old_season"/);

const absolutePath = createMockLoader({
  ...validManifest,
  data: { ...validManifest.data, teams: '/MEGA_teams.csv' },
}).loader;
await assert.rejects(absolutePath.getManifest(), /must be relative to the manifest/);

const malformedJson = createMockLoader(validManifest, {
  [teamUrl]: 'abbrName,displayName\n',
  [currentEloUrl]: '[]',
  'https://example.test/league/docs/data/playoff_probabilities.json': '{broken',
}).loader;
await assert.rejects(malformedJson.loadJson('playoffs'), /JSON data "playoffs" is malformed/);

const primitiveJson = createMockLoader(validManifest, {
  [teamUrl]: 'abbrName,displayName\n',
  [currentEloUrl]: 'Team,ELO,sourceWeek\n',
  'https://example.test/league/docs/data/playoff_probabilities.json': '[]',
}).loader;
await assert.rejects(primitiveJson.loadJson('playoffs'), /expected a JSON object/);

console.log('Browser data manifest checks passed.');
