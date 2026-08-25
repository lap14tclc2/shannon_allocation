export const NAVIGATION_EVENT = 'qport:navigate';

export function navigate(path, { replace = false } = {}) {
  if (typeof window === 'undefined') return;
  const target = new URL(path, window.location.origin);
  if (target.origin !== window.location.origin) {
    window.location.assign(target.href);
    return;
  }
  if (replace) window.history.replaceState({}, '', target.href);
  else window.history.pushState({}, '', target.href);
  window.dispatchEvent(new Event(NAVIGATION_EVENT));
  window.scrollTo({ top: 0, behavior: 'auto' });
}
