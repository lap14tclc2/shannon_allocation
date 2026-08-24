import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useI18n } from '../i18n.js';
import { getCurrentUser, logoutUser } from '../lib/api.js';
import AppearanceControls from './AppearanceControls.jsx';

const LINKS = [
  ['/', 'portfolio', 'nav.portfolio'],
  ['/transactions', 'transactions', 'nav.transactions'],
  ['/performance', 'performance', 'nav.performance'],
  ['/guide', 'guide', 'nav.guide'],
];

function MobileTabIcon({ name }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  };

  if (name === 'portfolio') {
    return <svg {...common}><path d="M4 10.5 12 4l8 6.5" /><path d="M6.5 9.5V20h11V9.5" /><path d="M9.5 20v-6h5v6" /></svg>;
  }
  if (name === 'transactions') {
    return <svg {...common}><path d="M7 4v15" /><path d="m3.5 7.5 3.5-3.5 3.5 3.5" /><path d="M17 20V5" /><path d="m13.5 16.5 3.5 3.5 3.5-3.5" /></svg>;
  }
  if (name === 'performance') {
    return <svg {...common}><path d="M4 19V5" /><path d="M4 19h16" /><path d="m7 15 4-4 3 2 5-6" /></svg>;
  }
  return <svg {...common}><path d="M5 5.5A3.5 3.5 0 0 1 8.5 2H12v18H8.5A3.5 3.5 0 0 0 5 23Z" /><path d="M19 5.5A3.5 3.5 0 0 0 15.5 2H12v18h3.5A3.5 3.5 0 0 1 19 23Z" /></svg>;
}

export default function AppNav({ active = 'portfolio', locale = 'vi' }) {
  const { t } = useI18n(locale);
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const adminMode = active === 'admin' || currentUser?.role === 'ADMIN';

  useEffect(() => {
    setMounted(true);
    getCurrentUser().then(result => setCurrentUser(result.user || null)).catch(() => setCurrentUser(null));
  }, []);

  useEffect(() => {
    if (!mounted || typeof document === 'undefined') return undefined;
    document.body.classList.toggle('mobile-sheet-open', open);
    return () => document.body.classList.remove('mobile-sheet-open');
  }, [mounted, open]);

  async function logout() {
    setOpen(false);
    try {
      await logoutUser();
    } catch {
      // Vẫn điều hướng về trang đăng nhập để phiên hết hạn hoặc lỗi có thể tự phục hồi.
    }
    window.location.replace('/login?logged_out=1');
  }

  const mobileChrome = mounted && typeof document !== 'undefined' ? createPortal(
    <>
      {!adminMode && <nav className="mobile-tab-bar" aria-label={text('Main app tabs', 'Tab chính của ứng dụng')}>
        {LINKS.map(([href, key, labelKey]) => (
          <a
            key={href}
            href={href}
            className={active === key ? 'active' : ''}
            aria-current={active === key ? 'page' : undefined}
          >
            <span className="mobile-tab-icon"><MobileTabIcon name={key} /></span>
            <span className="mobile-tab-label">{t(labelKey)}</span>
          </a>
        ))}
      </nav>}

      {open && <button
        type="button"
        className="mobile-nav-backdrop"
        aria-label={text('Close account and appearance menu', 'Đóng menu tài khoản và giao diện')}
        onClick={() => setOpen(false)}
      />}

      {open && <aside className="mobile-account-sheet" aria-label={text('Account and appearance', 'Tài khoản và giao diện')}>
        <div className="mobile-sheet-grabber" aria-hidden="true" />
        {currentUser && (
          <div className="mobile-sheet-user">
            <div>
              <span className="mobile-sheet-caption">{text('Signed in as', 'Đang đăng nhập')}</span>
              <strong>@{currentUser.username}</strong>
            </div>
            <button type="button" className="mobile-sheet-logout" onClick={logout}>{text('Log out', 'Đăng xuất')}</button>
          </div>
        )}
        <div className="mobile-sheet-setting">
          <span>{text('Appearance', 'Giao diện')}</span>
          <AppearanceControls locale={locale} />
        </div>
      </aside>}
    </>,
    document.body,
  ) : null;

  return (
    <>
      <nav className={`app-nav ${open ? 'nav-open' : ''}`} aria-label={t('nav.primary')}>
        <div className="nav-shell">
          <div className="app-nav-head">
            <a className="brand" href={adminMode ? '/admin' : '/'} aria-label={adminMode ? 'Trang quản trị QPort' : 'Trang danh mục QPort'}>
              <span className="brand-prompt" aria-hidden="true">$</span>
              <span className="brand-copy">
                <strong>qport</strong>
                <small>{adminMode ? '/ quản trị' : '/ danh mục'}</small>
              </span>
              <span className="live-badge"><span className="status-dot" />hoạt động</span>
            </a>

            <button
              type="button"
              className="nav-toggle"
              aria-expanded={open}
              aria-label={text('Open account and appearance menu', 'Mở menu tài khoản và giao diện')}
              onClick={() => setOpen(value => !value)}
            >
              <span />
              <span />
              <span />
            </button>
          </div>

          <div className="app-nav-links desktop-nav-links">
            {adminMode ? (
              <a href="/admin" className="active" aria-current="page">
                <span className="nav-prefix" aria-hidden="true">›</span>
                <span>Quản trị</span>
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

          <div className="app-nav-footer desktop-nav-footer">
            {currentUser && (
              <div className="nav-user">
                <span className="nav-user-name">@{currentUser.username}</span>
                <button type="button" className="nav-logout" onClick={logout}>{text('logout', 'đăng xuất')}</button>
              </div>
            )}

            <AppearanceControls locale={locale} />
          </div>
        </div>
      </nav>
      {mobileChrome}
    </>
  );
}
