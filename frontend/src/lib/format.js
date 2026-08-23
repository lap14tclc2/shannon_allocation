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
  if (value == null || Number.isNaN(Number(value))) return '-';
  return Number(value).toFixed(digits);
}

export function formatShares(value, locale = 'en') {
  if (value == null || Number.isNaN(Number(value))) return '-';
  return Number(value).toLocaleString(intlLocale(locale), { maximumFractionDigits: 4 });
}
