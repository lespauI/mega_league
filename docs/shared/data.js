/* Shared, manifest-backed browser data access for maintained dashboard pages. */
(function attachMegaData(global) {
  'use strict';

  const KNOWN_DATA_KEYS = new Set([
    'teams', 'players', 'games', 'team_stats', 'player_usage', 'rankings_stats',
    'stints', 'trades', 'roster_rankings', 'rankings_sos', 'elo', 'elo_sos',
    'schedules', 'playoffs',
  ]);
  const REQUIRED_CYCLE_FIELDS = [
    'edition', 'csvSeasonIndex', 'displaySeason', 'calendarYear',
    'completedThroughWeek', 'exportWeekIndex', 'eloSourceWeek',
  ];

  function validateManifest(manifest) {
    if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
      throw new Error('Data manifest must be a JSON object.');
    }
    if (manifest.schemaVersion !== 1) {
      throw new Error(`Unsupported data manifest schemaVersion: ${String(manifest.schemaVersion)}.`);
    }
    if (typeof manifest.snapshotId !== 'string' || !manifest.snapshotId.trim()) {
      throw new Error('Data manifest is missing a snapshotId.');
    }
    if (!manifest.cycle || typeof manifest.cycle !== 'object' || Array.isArray(manifest.cycle)) {
      throw new Error('Data manifest is missing cycle metadata.');
    }
    for (const field of REQUIRED_CYCLE_FIELDS) {
      const value = manifest.cycle[field];
      if (field === 'edition') {
        if (typeof value !== 'string' || !value.trim()) {
          throw new Error(`Data manifest cycle.${field} must be a non-empty string.`);
        }
      } else if (!Number.isInteger(value) || value < 0 || (field === 'displaySeason' && value < 1)) {
        throw new Error(`Data manifest cycle.${field} must be a valid nonnegative integer.`);
      }
    }
    if (!manifest.data || typeof manifest.data !== 'object' || Array.isArray(manifest.data)) {
      throw new Error('Data manifest is missing its data map.');
    }
    for (const key of Object.keys(manifest.data)) {
      if (!KNOWN_DATA_KEYS.has(key)) throw new Error(`Data manifest contains unknown data key "${key}".`);
      const path = manifest.data[key];
      if (typeof path !== 'string' || !path.trim()) {
        throw new Error(`Data manifest entry "${key}" must be a non-empty relative URL.`);
      }
      if (path.startsWith('/') || /^[a-z][a-z\d+.-]*:/i.test(path)) {
        throw new Error(`Data manifest entry "${key}" must be relative to the manifest.`);
      }
    }
    return manifest;
  }

  function createDataLoader(options = {}) {
    const manifestUrl = new URL(options.manifestUrl || '../data/data_manifest.json', options.baseUrl || global.document?.baseURI || global.location?.href || 'http://localhost/');
    const fetchImpl = options.fetchImpl || global.fetch;
    let manifestPromise;
    const resourcePromises = new Map();

    async function getManifest() {
      if (!manifestPromise) {
        manifestPromise = (async () => {
          if (typeof fetchImpl !== 'function') throw new Error('Fetch is unavailable; browser data cannot be loaded.');
          let response;
          try {
            response = await fetchImpl(manifestUrl.href, { cache: 'no-store' });
          } catch (error) {
            throw new Error(`Unable to load data manifest at ${manifestUrl.href}: ${error.message || error}`);
          }
          if (!response?.ok) throw new Error(`Data manifest request failed (${response?.status ?? 'no response'}): ${manifestUrl.href}`);
          let value;
          try {
            value = await response.json();
          } catch (error) {
            throw new Error(`Data manifest is not valid JSON: ${error.message || error}`);
          }
          return validateManifest(value);
        })().catch((error) => {
          manifestPromise = null;
          throw error;
        });
      }
      return manifestPromise;
    }

    async function getDataUrl(key) {
      if (!KNOWN_DATA_KEYS.has(key)) throw new Error(`Unknown browser data key "${String(key)}".`);
      const manifest = await getManifest();
      const path = manifest.data[key];
      if (typeof path !== 'string' || !path.trim()) {
        throw new Error(`Data manifest has no URL for "${key}".`);
      }
      return new URL(path, manifestUrl).href;
    }

    async function loadText(key) {
      if (!resourcePromises.has(`text:${key}`)) {
        resourcePromises.set(`text:${key}`, (async () => {
          const url = await getDataUrl(key);
          let response;
          try {
            response = await fetchImpl(url, { cache: 'no-store' });
          } catch (error) {
            throw new Error(`Unable to load "${key}" data from ${url}: ${error.message || error}`);
          }
          if (!response?.ok) throw new Error(`Data request for "${key}" failed (${response?.status ?? 'no response'}): ${url}`);
          return response.text();
        })().catch((error) => {
          resourcePromises.delete(`text:${key}`);
          throw error;
        }));
      }
      return resourcePromises.get(`text:${key}`);
    }

    async function loadCsv(key, parseCsv) {
      const text = await loadText(key);
      if (typeof parseCsv === 'function') return parseCsv(text);
      const parser = parseCsv || global.Papa;
      if (!parser || typeof parser.parse !== 'function') {
        throw new Error(`A CSV parser is required to load "${key}" data.`);
      }
      const result = parser.parse(text, { header: true, skipEmptyLines: true });
      if (result.errors?.length) {
        throw new Error(`CSV parse failed for "${key}": ${result.errors.map((entry) => entry.message || entry.code || 'invalid row').join('; ')}`);
      }
      return Array.isArray(result.data) ? result.data : [];
    }

    async function loadJson(key) {
      const text = await loadText(key);
      try {
        const value = JSON.parse(text);
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
          throw new Error('expected a JSON object.');
        }
        return value;
      } catch (error) {
        throw new Error(`JSON data "${key}" is malformed: ${error.message || error}`);
      }
    }

    async function assertCycle(expected = {}) {
      const manifest = await getManifest();
      for (const [field, value] of Object.entries(expected)) {
        if (!Object.hasOwn(manifest.cycle, field)) throw new Error(`Unknown cycle field "${field}" requested by this page.`);
        if (manifest.cycle[field] !== value) {
          const actual = manifest.cycle[field];
          const isSeason = field === 'displaySeason';
          throw new Error(isSeason
            ? `This page is for Season ${value}, but the active data is ${manifest.cycle.edition} Season ${actual}.`
            : `This page expects cycle.${field}=${value}, but the active data manifest has ${actual}.`);
        }
      }
      return manifest.cycle;
    }

    return { getManifest, getDataUrl, loadText, loadCsv, loadJson, assertCycle };
  }

  const scriptUrl = global.document?.currentScript?.src;
  const manifestUrl = scriptUrl ? new URL('../data/data_manifest.json', scriptUrl).href : undefined;
  global.MegaData = Object.assign(createDataLoader({ manifestUrl }), { createDataLoader, validateManifest });
})(globalThis);
