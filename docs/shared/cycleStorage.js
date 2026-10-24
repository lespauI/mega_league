const STORAGE_PREFIX = 'megaCycleStorage.v1';
let activeCycle = null;

function rawStorage() {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null;
  } catch {
    return null;
  }
}

function cleanPart(value) {
  return String(value ?? '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'unknown';
}

export function normalizeCycleIdentity(metadata) {
  if (!metadata || typeof metadata !== 'object') throw new Error('Cycle metadata is required for saved browser state.');
  const edition = String(metadata.game || '').trim();
  const seasonIndex = Number(metadata.seasonIndex);
  const calendarYear = Number(metadata.calendarYear);
  if (!edition || !Number.isInteger(seasonIndex) || seasonIndex < 0 || !Number.isInteger(calendarYear) || calendarYear < 1900) {
    throw new Error('Cycle metadata must include game, a nonnegative seasonIndex, and calendarYear.');
  }
  return Object.freeze({
    edition,
    seasonIndex,
    calendarYear,
    key: `${cleanPart(edition)}-s${seasonIndex}-y${calendarYear}`,
    label: `${edition} · Season ${seasonIndex + 1} · ${calendarYear}`,
  });
}

export async function loadCycleIdentity(url = '../../docs/data/import_metadata.json') {
  if (typeof fetch !== 'function') throw new Error('Fetch is unavailable; cycle metadata cannot be read.');
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`Cycle metadata request failed (${response.status}).`);
  return normalizeCycleIdentity(await response.json());
}

export function configureCycleStorage(metadataOrIdentity) {
  activeCycle = metadataOrIdentity && metadataOrIdentity.key && metadataOrIdentity.label
    ? Object.freeze({ ...metadataOrIdentity })
    : normalizeCycleIdentity(metadataOrIdentity);
  return activeCycle;
}

export function currentCycleIdentity() {
  return activeCycle ? { ...activeCycle } : null;
}

export function scopedStorageKey(namespace, legacyKey, cycle = activeCycle) {
  if (!cycle) return legacyKey;
  return `${STORAGE_PREFIX}:${cleanPart(namespace)}:${cycle.key}:${legacyKey}`;
}

export function getCycleStorage(namespace) {
  return {
    getItem(key) {
      const storage = rawStorage();
      if (!storage) return null;
      try { return storage.getItem(scopedStorageKey(namespace, key)); } catch { return null; }
    },
    setItem(key, value) {
      const storage = rawStorage();
      if (!storage) return false;
      try { storage.setItem(scopedStorageKey(namespace, key), String(value)); return true; } catch { return false; }
    },
    removeItem(key) {
      const storage = rawStorage();
      if (!storage) return false;
      try { storage.removeItem(scopedStorageKey(namespace, key)); return true; } catch { return false; }
    },
  };
}

export function legacyEntries(namespace, keys) {
  const storage = rawStorage();
  if (!storage) return [];
  return (keys || []).filter((key) => {
    try { return storage.getItem(key) !== null; } catch { return false; }
  });
}

export function copyLegacyEntries(namespace, keys) {
  const storage = rawStorage();
  if (!storage) throw new Error('Browser storage is unavailable.');
  if (!activeCycle) throw new Error('Select a cycle before copying legacy data.');
  let copied = 0;
  let skipped = 0;
  for (const key of keys || []) {
    let value;
    try { value = storage.getItem(key); } catch (error) { throw new Error(`Cannot read legacy key ${key}: ${error}`); }
    if (value === null) continue;
    const targetKey = scopedStorageKey(namespace, key);
    if (storage.getItem(targetKey) !== null) { skipped++; continue; }
    storage.setItem(targetKey, value);
    copied++;
  }
  return { copied, skipped };
}

export function exportStorageBackup(namespace, keys) {
  const storage = rawStorage();
  if (!storage) throw new Error('Browser storage is unavailable.');
  const entries = {};
  for (const key of keys || []) {
    entries[key] = {
      cycle: storage.getItem(scopedStorageKey(namespace, key)),
      legacy: storage.getItem(key),
    };
  }
  return JSON.stringify({
    schemaVersion: 1,
    namespace,
    cycle: currentCycleIdentity(),
    exportedAt: new Date().toISOString(),
    entries,
  }, null, 2) + '\n';
}

export function importStorageBackup(text, namespace, allowedKeys) {
  const storage = rawStorage();
  if (!storage) throw new Error('Browser storage is unavailable.');
  if (!activeCycle) throw new Error('Cycle metadata is required before importing saved data.');
  let backup;
  try { backup = JSON.parse(text); } catch { throw new Error('Backup file is not valid JSON.'); }
  if (!backup || backup.schemaVersion !== 1 || backup.namespace !== namespace || !backup.entries || typeof backup.entries !== 'object') {
    throw new Error('Backup version or tool name does not match this page.');
  }
  const allowed = new Set(allowedKeys || []);
  let imported = 0;
  let skipped = 0;
  for (const [key, saved] of Object.entries(backup.entries)) {
    if (!allowed.has(key) || !saved || typeof saved !== 'object') throw new Error(`Backup contains an unsupported storage key: ${key}`);
    const value = typeof saved.cycle === 'string' ? saved.cycle : saved.legacy;
    if (value === null || value === undefined) continue;
    if (typeof value !== 'string') throw new Error(`Backup value for ${key} must be a string.`);
    const targetKey = scopedStorageKey(namespace, key);
    if (storage.getItem(targetKey) !== null) { skipped++; continue; }
    storage.setItem(targetKey, value);
    imported++;
  }
  return { imported, skipped, sourceCycle: backup.cycle || null };
}
