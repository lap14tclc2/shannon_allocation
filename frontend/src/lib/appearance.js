const STORAGE_KEY = 'qport-theme-v1';
const LEGACY_APPEARANCE_KEYS = ['qport-appearance-v1', 'qport-appearance-v2', 'qport-appearance-v3'];

export const DEFAULT_THEME = 'retro';
export const VISUAL_THEMES = Object.freeze(['retro', 'cyber']);

export function normalizeTheme(value) {
  return VISUAL_THEMES.includes(value) ? value : DEFAULT_THEME;
}

function updateBrowserChrome(theme) {
  if (typeof document === 'undefined') return;
  const themeColor = theme === 'cyber' ? '#080b14' : '#efe4cf';
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', themeColor);
}

export function applyTheme(value) {
  const theme = normalizeTheme(value);
  if (typeof document === 'undefined') return theme;

  const root = document.documentElement;
  const colorScheme = theme === 'retro' ? 'light' : 'dark';
  root.dataset.theme = colorScheme;
  root.dataset.visualTheme = theme;
  root.style.colorScheme = colorScheme;
  updateBrowserChrome(theme);
  return theme;
}

export function getStoredTheme() {
  if (typeof window === 'undefined') return DEFAULT_THEME;
  try {
    return normalizeTheme(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_THEME;
  }
}

export function applyStoredTheme() {
  return applyTheme(getStoredTheme());
}

export function saveTheme(value) {
  const theme = applyTheme(value);
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
      for (const key of LEGACY_APPEARANCE_KEYS) window.localStorage.removeItem(key);
    } catch { /* Storage can be unavailable. */ }
  }
  return theme;
}
