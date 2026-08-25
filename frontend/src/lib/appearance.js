const STORAGE_KEY = 'qport-appearance-v2';

export const DEFAULT_APPEARANCE = Object.freeze({
  background: '#14171a',
  text: '#ede8df',
  secondary: '#b8b1a7',
  muted: '#8e9cae',
  accent: '#ff4d36',
  success: '#3fb68b',
  warning: '#e5b54f',
  danger: '#ff5a36',
  info: '#86a9c7',
});

export const TOKYO_SUMI_APPEARANCE = DEFAULT_APPEARANCE;

export const SHOWA_PAPER_APPEARANCE = Object.freeze({
  background: '#f5f0e6',
  text: '#1a1d20',
  secondary: '#4e5660',
  muted: '#646d76',
  accent: '#c8382b',
  success: '#236e47',
  warning: '#966115',
  danger: '#b92e24',
  info: '#3d6380',
});

const VARIABLE_BY_FIELD = {
  background: '--bg',
  text: '--text',
  secondary: '--text-secondary',
  muted: '--muted',
  accent: '--accent',
  success: '--success',
  warning: '--warning',
  danger: '--danger',
  info: '--info',
};

const DERIVED_VARIABLES = [
  '--bg-elevated', '--panel', '--panel-2', '--panel-hover', '--input',
  '--border', '--border-strong', '--accent-soft', '--accent-border',
  '--selection', '--row-hover', '--overlay', '--chart-grid', '--card',
  '--surface', '--surface-soft',
];

const CUSTOM_VARIABLES = [...Object.values(VARIABLE_BY_FIELD), ...DERIVED_VARIABLES];

function validHex(value) {
  return typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value.trim());
}

export function normalizeAppearance(value = {}) {
  const next = {};
  for (const [key, fallback] of Object.entries(DEFAULT_APPEARANCE)) {
    const candidate = value?.[key];
    next[key] = validHex(candidate) ? candidate.toLowerCase() : fallback;
  }
  return next;
}

function backgroundIsLight(hex) {
  const value = hex.replace('#', '');
  const r = parseInt(value.slice(0, 2), 16) / 255;
  const g = parseInt(value.slice(2, 4), 16) / 255;
  const b = parseInt(value.slice(4, 6), 16) / 255;
  const linear = channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  const luminance = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
  return luminance > 0.42;
}

function setDerivedVariables(root, palette) {
  const { background: bg, text, accent } = palette;
  const style = root.style;
  style.setProperty('--bg-elevated', `color-mix(in srgb, ${bg} 97%, ${text} 3%)`);
  style.setProperty('--panel', `color-mix(in srgb, ${bg} 95%, ${text} 5%)`);
  style.setProperty('--panel-2', `color-mix(in srgb, ${bg} 92%, ${text} 8%)`);
  style.setProperty('--panel-hover', `color-mix(in srgb, ${bg} 88%, ${text} 12%)`);
  style.setProperty('--input', `color-mix(in srgb, ${bg} 98%, ${text} 2%)`);
  style.setProperty('--border', `color-mix(in srgb, ${bg} 82%, ${text} 18%)`);
  style.setProperty('--border-strong', `color-mix(in srgb, ${bg} 70%, ${text} 30%)`);
  style.setProperty('--accent-soft', `color-mix(in srgb, ${accent} 10%, transparent)`);
  style.setProperty('--accent-border', `color-mix(in srgb, ${accent} 38%, transparent)`);
  style.setProperty('--selection', `color-mix(in srgb, ${accent} 24%, transparent)`);
  style.setProperty('--row-hover', `color-mix(in srgb, ${text} 5%, transparent)`);
  style.setProperty('--overlay', `color-mix(in srgb, ${bg} 94%, transparent)`);
  style.setProperty('--chart-grid', `color-mix(in srgb, ${bg} 78%, ${text} 22%)`);
  style.setProperty('--card', 'var(--panel)');
  style.setProperty('--surface', 'var(--panel-2)');
  style.setProperty('--surface-soft', 'var(--bg-elevated)');
}

export function applyAppearance(value) {
  if (typeof document === 'undefined') return normalizeAppearance(value);
  const palette = normalizeAppearance(value);
  const root = document.documentElement;

  root.dataset.theme = backgroundIsLight(palette.background) ? 'light' : 'dark';
  root.dataset.visualSystem = 'japanese-ledger';
  for (const [field, variable] of Object.entries(VARIABLE_BY_FIELD)) {
    root.style.setProperty(variable, palette[field]);
  }
  setDerivedVariables(root, palette);
  root.style.colorScheme = backgroundIsLight(palette.background) ? 'light' : 'dark';
  return palette;
}

export function clearCustomAppearance() {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  for (const variable of CUSTOM_VARIABLES) root.style.removeProperty(variable);
  root.dataset.theme = 'dark';
  root.dataset.visualSystem = 'japanese-ledger';
  root.style.colorScheme = 'dark';
}

export function getStoredAppearance() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return normalizeAppearance(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function applyStoredAppearance() {
  const stored = getStoredAppearance();
  if (stored) return applyAppearance(stored);
  clearCustomAppearance();
  return { ...DEFAULT_APPEARANCE };
}

export function saveAppearance(value) {
  const palette = applyAppearance(value);
  if (typeof window !== 'undefined') {
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(palette)); } catch { /* storage may be unavailable */ }
  }
  return palette;
}

export function resetAppearance() {
  if (typeof window !== 'undefined') {
    try { window.localStorage.removeItem(STORAGE_KEY); } catch { /* storage may be unavailable */ }
  }
  clearCustomAppearance();
  return { ...DEFAULT_APPEARANCE };
}

export function useAppearancePreset(preset) {
  if (preset === 'showa-paper') return saveAppearance(SHOWA_PAPER_APPEARANCE);
  return saveAppearance(TOKYO_SUMI_APPEARANCE);
}
