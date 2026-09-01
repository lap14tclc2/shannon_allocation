function intlLocale(locale) {
  return String(locale || '').toLowerCase().startsWith('vi') ? 'vi-VN' : 'en-US';
}

export function formatMoney(value, compact = false, locale = 'en') {
  if (value == null || Number.isNaN(Number(value))) return '-';
  const n = Number(value);
  if (compact) {
    if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
    if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
    if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
    return n.toFixed(0);
  }
  return n.toLocaleString(intlLocale(locale), { maximumFractionDigits: 0 });
}

export function formatPercent(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  return `${Number(value).toFixed(digits)}%`;
}

export function formatWeight(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function formatNumber(value, digits = 2) {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  return Number(value).toFixed(digits);
}

export function formatShares(value, locale = 'en') {
  if (value == null || Number.isNaN(Number(value))) return '-';
  return Number(value).toLocaleString(intlLocale(locale), { maximumFractionDigits: 4 });
}

/** Format a VND monetary value. suffix defaults to '₫'; pass 'VND' for text-label style. */
export function money(value, locale = 'vi', suffix = '₫') {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  return `${formatMoney(value, false, locale)} ${suffix}`;
}

/** Format a signed VND monetary value with +/- prefix. */
export function signedMoney(value, locale = 'vi', suffix = '₫') {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  const prefix = Number(value) >= 0 ? '+' : '';
  return `${prefix}${money(value, locale, suffix)}`;
}

/** Format a ratio (0–1) as a percentage string, e.g. 0.25 → '25.00%'. */
export function pct(value, digits = 2) {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

/** Format a plain number with an optional suffix and digit precision. */
export function displayNumber(value, suffix = '', digits = 1) {
  if (value == null || !Number.isFinite(Number(value))) return '—';
  return `${Number(value).toFixed(digits)}${suffix}`;
}
