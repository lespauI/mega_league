import assert from 'node:assert/strict';
import { loadCurrentElo } from '../../docs/shared/elo.js';

const csvParse = (text) => {
  const [header, ...lines] = text.trim().split('\n');
  const fields = header.split(',');
  return lines.map((line) => Object.fromEntries(
    line.split(',').map((value, index) => [fields[index], value]),
  ));
};

const validRows = 'Team,GM,ELO,sourceWeek\nAlpha,GM A,1000,8\nBeta,GM B,1001,8\n';
let csv = validRows;
const requests = [];
const previousLoader = globalThis.MegaData;
globalThis.MegaData = {
  async getManifest() {
    requests.push('manifest');
    return { cycle: { eloSourceWeek: 8 } };
  },
  async loadCsv(key, parseCsv) {
    requests.push(key);
    return parseCsv(csv);
  },
};

try {
  const current = await loadCurrentElo(csvParse);
  assert.equal(current.sourceWeek, 8);
  assert.equal(current.byTeam.get('Alpha'), 1000);
  assert.deepEqual(requests, ['manifest', 'elo']);

  csv = 'Team,GM,ELO,sourceWeek\nAlpha,GM A,1200,12\n';
  await assert.rejects(() => loadCurrentElo(csvParse), /does not match manifest Week 8/);

  csv = 'Team,GM,ELO,sourceWeek\nAlpha,GM A,1000,8\nAlpha,GM B,1001,8\n';
  await assert.rejects(() => loadCurrentElo(csvParse), /duplicate team Alpha/);

  csv = 'Team,GM,ELO,sourceWeek\n,GM A,not-an-elo,8\n';
  await assert.rejects(() => loadCurrentElo(csvParse), /invalid team rating/);
} finally {
  if (previousLoader === undefined) delete globalThis.MegaData;
  else globalThis.MegaData = previousLoader;
}

console.log('Current ELO browser source checks passed.');
