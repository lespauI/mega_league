import assert from 'node:assert/strict';
import { loadCurrentElo } from '../../docs/shared/elo.js';

const csvParse = (text) => {
  const [header, ...lines] = text.trim().split('\n');
  const fields = header.split(',');
  return lines.map((line) => Object.fromEntries(
    line.split(',').map((value, index) => [fields[index], value]),
  ));
};

const requests = [];
const fetchWeekEight = async (url) => {
  requests.push(new URL(url).pathname);
  const text = new URL(url).pathname.endsWith('import_metadata.json')
    ? '{"eloSourceWeek":8}'
    : 'Team,GM,ELO,sourceWeek\nAlpha,GM A,1000,8\nBeta,GM B,1001,8\n';
  return { ok: true, text: async () => text };
};

const current = await loadCurrentElo(csvParse, fetchWeekEight);
assert.equal(current.sourceWeek, 8);
assert.equal(current.byTeam.get('Alpha'), 1000);
assert.deepEqual(requests.map((path) => path.split('/').at(-1)), [
  'import_metadata.json', 'current_elo.csv',
]);

await assert.rejects(() => loadCurrentElo(csvParse, async (url) => ({
  ok: true,
  text: async () => new URL(url).pathname.endsWith('import_metadata.json')
    ? '{"eloSourceWeek":8}'
    : 'Team,GM,ELO,sourceWeek\nAlpha,GM A,1200,12\n',
})), /does not match metadata Week 8/);

console.log('Current ELO browser source checks passed.');
