import React, { useEffect, useState } from 'react';
import { useI18n } from '../i18n.js';
import { getCurrentUser, logoutUser } from '../lib/api.js';

const LINKS = [
  ['/', 'portfolio', 'nav.portfolio'],
  ['/transactions', 'transactions', 'nav.transactions'],
  ['/performance', 'performance', 'nav.performance'],
  ['/guide', 'guide', 'nav.guide'],
];

function preferredTheme() {
  if (typeof window === 'undefined') return 'dark';
  try {
    const stored = window.localStorage.getItem('qport-theme');
    if (stored === 'light' || stored === 'dark') return stored;
  } catch { /* storage may be disabled */ }
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export default function AppNav({ active = 'portfolio', locale = 'en' }) {
  const { t, setLanguage } = useI18n(locale);
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState('dark');
  const [currentUser, setCurrentUser] = useState(null);
  const text = (en, vi) => locale === 'vi' ? vi : en;

  useEffect(() => {
    const current = preferredTheme();
    setTheme(current);
    document.documentElement.dataset.theme = current;
    document.documentElement.style.colorScheme = current;
    getCurrentUser().then(result => setCurrentUser(result.user || null)).catch(() => setCurrentUser(null));
  }, []);

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.dataset.theme = next;
    document.documentElement.style.colorScheme = next;
    try { window.localStorage.setItem('qport-theme', next); } catch { /* storage may be disabled */ }
  }

  async function logout() {
    try { await logoutUser(); } catch { /* cookie is cleared server-side when possible */ }
    window.location.assign('/');
  }

  return (
    <nav className={`app-nav ${open ? 'nav-open' : ''}`} aria-label={t('nav.primary')}>
      <div className="nav-shell">
        <div className="app-nav-head">
          <a className="brand" href="/" aria-label="QPort portfolio home">
            <span className="brand-prompt" aria-hidden="true">$</span>
            <span className="brand-copy">
              <strong>qport</strong>
              <small>/ portfolio</small>
            </span>
            <span className="live-badge"><span className="status-dot" />{text('live', 'live')}</span>
          </a>

          <button
            type="button"
            className="nav-toggle"
            aria-expanded={open}
            aria-label={text('Toggle navigation', 'Mở/đóng điều hướng')}
            onClick={() => setOpen(value => !value)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>

        <div className="app-nav-links">
          {LINKS.map(([href, key, labelKey]) => (
            <a
              key={href}
              href={href}
              className={active === key ? 'active' : ''}
              aria-current={active === key ? 'page' : undefined}
            >
              <span className="nav-prefix" aria-hidden="true">{active === key ? '›' : '·'}</span>
              <span>{t(labelKey)}</span>
            </a>
          ))}
          {currentUser?.role === 'ADMIN' && (
            <a href="/admin" className={active === 'admin' ? 'active' : ''} aria-current={active === 'admin' ? 'page' : undefined}>
              <span className="nav-prefix" aria-hidden="true">{active === 'admin' ? '›' : '·'}</span>
              <span>{text('Admin', 'Admin')}</span>
            </a>
          )}
        </div>

        <div className="app-nav-footer">
          {currentUser && (
            <div className="nav-user">
              <span className="nav-user-name">@{currentUser.username}</span>
              <button type="button" className="nav-logout" onClick={logout}>{text('logout', 'đăng xuất')}</button>
            </div>
          )}

          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? text('Use light theme', 'Dùng giao diện sáng') : text('Use dark theme', 'Dùng giao diện tối')}
            aria-label={theme === 'dark' ? text('Use light theme', 'Dùng giao diện sáng') : text('Use dark theme', 'Dùng giao diện tối')}
          >
            <span aria-hidden="true">{theme === 'dark' ? '☼' : '☾'}</span>
            <span>{theme === 'dark' ? text('light', 'sáng') : text('dark', 'tối')}</span>
          </button>

          <div className="language-switch" aria-label={`${t('lang.english')} / ${t('lang.vietnamese')}`}>
            <button type="button" className={locale === 'en' ? 'active' : ''} onClick={() => setLanguage('en')} title={t('lang.english')}>en</button>
            <span>/</span>
            <button type="button" className={locale === 'vi' ? 'active' : ''} onClick={() => setLanguage('vi')} title={t('lang.vietnamese')}>vi</button>
          </div>
        </div>
      </div>
    </nav>
  );
}
