import assert from 'node:assert/strict';
import { loadCsvRows } from '../../docs/shared/csv.js';

const rows = await loadCsvRows('/teams.csv', {
  parse(url, options) {
    assert.equal(url, '/teams.csv');
    assert.equal(options.header, true);
    options.complete({ data: [{ displayName: 'Chiefs' }], errors: [] });
  },
});
assert.deepEqual(rows, [{ displayName: 'Chiefs' }]);
await assert.rejects(
  loadCsvRows('/bad.csv', { parse(url, options) { options.complete({ data: [], errors: [{ message: 'Malformed row' }] }); } }),
  /Malformed row/,
);
await assert.rejects(loadCsvRows('/missing-parser.csv', null), /parser did not load/);
console.log('Shared browser CSV loader checks passed.');
