import React, { useEffect, useState } from 'react';
import { useI18n } from '../i18n.js';
import { getCurrentUser, logoutUser } from '../lib/api.js';
import AppearanceControls from './AppearanceControls.jsx';

const LINKS = [
  ['/', 'portfolio', 'nav.portfolio'],
  ['/transactions', 'transactions', 'nav.transactions'],
  ['/performance', 'performance', 'nav.performance'],
  ['/guide', 'guide', 'nav.guide'],
];

export default function AppNav({ active = 'portfolio', locale = 'en' }) {
  const { t, setLanguage } = useI18n(locale);
  const [open, setOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const adminMode = active === 'admin' || currentUser?.role === 'ADMIN';

  useEffect(() => {
    getCurrentUser().then(result => setCurrentUser(result.user || null)).catch(() => setCurrentUser(null));
  }, []);

  async function logout() {
    try { await logoutUser(); } catch { /* cookie is cleared server-side when possible */ }
    window.location.assign('/');
  }

  return (
    <nav className={`app-nav ${open ? 'nav-open' : ''}`} aria-label={t('nav.primary')}>
      <div className="nav-shell">
        <div className="app-nav-head">
          <a className="brand" href={adminMode ? '/admin' : '/'} aria-label={adminMode ? 'QPort admin home' : 'QPort portfolio home'}>
            <span className="brand-prompt" aria-hidden="true">$</span>
            <span className="brand-copy">
              <strong>qport</strong>
              <small>{adminMode ? '/ admin' : '/ portfolio'}</small>
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
          {adminMode ? (
            <a href="/admin" className="active" aria-current="page">
              <span className="nav-prefix" aria-hidden="true">›</span>
              <span>{text('Admin', 'Admin')}</span>
            </a>
          ) : LINKS.map(([href, key, labelKey]) => (
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
        </div>

        <div className="app-nav-footer">
          {currentUser && (
            <div className="nav-user">
              <span className="nav-user-name">@{currentUser.username}</span>
              <button type="button" className="nav-logout" onClick={logout}>{text('logout', 'đăng xuất')}</button>
            </div>
          )}

          <AppearanceControls locale={locale} />

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
