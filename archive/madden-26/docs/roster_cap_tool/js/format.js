// Formatting helpers for contract editor

/**
 * Format an absolute dollar amount as millions with one decimal place.
 * Example: 22700000 -> "$22.7M"; -15340000 -> "-$15.3M"
 * @param {number} n Absolute dollars
 * @returns {string}
 */
export function formatMillions(n) {
  const v = Number(n) || 0;
  const sign = v < 0 ? '-' : '';
  const m = Math.abs(v) / 1_000_000;
  const s = m.toFixed(1);
  return `${sign}$${s}M`;
}

/**
 * Convert a millions value to absolute dollars, rounding to nearest dollar.
 * Accepts numbers (e.g. 22.7) or strings like "$22.7M" / "22.7" / "22.7m".
 * @param {number|string} m
 * @returns {number}
 */
export function toAbsoluteDollarsFromMillions(m) {
  if (typeof m === 'number') {
    if (!Number.isFinite(m)) return 0;
    return Math.round(m * 1_000_000);
  }
  const raw = String(m || '')
    .trim()
    .replace(/[$,\s]/g, '')
    .replace(/[mM]$/, '');
  const num = Number.parseFloat(raw);
  if (!Number.isFinite(num)) return 0;
  return Math.round(num * 1_000_000);
}

export default {
  formatMillions,
  toAbsoluteDollarsFromMillions,
};

