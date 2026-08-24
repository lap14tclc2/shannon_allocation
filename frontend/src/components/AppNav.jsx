import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { getCurrentUser, logoutUser } from '../lib/api.js';
import AppearanceControls from './AppearanceControls.jsx';

const LINKS = [
  ['/', 'portfolio', 'Danh mục'],
  ['/transactions', 'transactions', 'Giao dịch'],
  ['/performance', 'performance', 'Hiệu quả'],
  ['/risk', 'risk', 'Phân tích'],
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
  return <svg {...common}><path d="M12 3 19 6v5c0 4.5-2.8 8-7 10-4.2-2-7-5.5-7-10V6Z" /><path d="M9 12h6" /></svg>;
}

export default function AppNav({ active = 'portfolio', locale = 'vi' }) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
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
      // Vẫn quay về trang đăng nhập nếu phiên đã hết hạn hoặc API đăng xuất gặp lỗi.
    }
    window.location.replace('/login?logged_out=1');
  }

  const mobileChrome = mounted && typeof document !== 'undefined' ? createPortal(
    <>
      {!adminMode && <nav className="mobile-tab-bar" aria-label="Điều hướng chính">
        {LINKS.map(([href, key, label]) => (
          <a key={href} href={href} className={active === key ? 'active' : ''} aria-current={active === key ? 'page' : undefined}>
            <span className="mobile-tab-icon"><MobileTabIcon name={key} /></span>
            <span className="mobile-tab-label">{label}</span>
          </a>
        ))}
      </nav>}

      {open && <button type="button" className="mobile-nav-backdrop" aria-label="Đóng menu tài khoản" onClick={() => setOpen(false)} />}

      {open && <aside className="mobile-account-sheet" aria-label="Tài khoản và giao diện">
        <div className="mobile-sheet-grabber" aria-hidden="true" />
        {currentUser && (
          <div className="mobile-sheet-user">
            <div><span className="mobile-sheet-caption">Đang đăng nhập</span><strong>@{currentUser.username}</strong></div>
            <button type="button" className="mobile-sheet-logout" onClick={logout}>Đăng xuất</button>
          </div>
        )}
        {!adminMode && <>
          <div className="mobile-sheet-setting"><span>Cổ tức</span><a className="text-link" href="/dividends">Lịch sử cổ tức →</a></div>
          <div className="mobile-sheet-setting"><span>Hỗ trợ</span><a className="text-link" href="/guide">Hướng dẫn sử dụng →</a></div>
          <div className="mobile-sheet-setting"><span>Tùy chọn</span><a className="text-link" href="/settings">Cài đặt →</a></div>
        </>}
        <div className="mobile-sheet-setting"><span>Giao diện</span><AppearanceControls locale={locale} /></div>
      </aside>}
    </>,
    document.body,
  ) : null;

  return (
    <>
      <nav className={`app-nav ${open ? 'nav-open' : ''}`} aria-label="Điều hướng chính">
        <div className="nav-shell">
          <div className="app-nav-head">
            <a className="brand" href={adminMode ? '/admin' : '/'} aria-label={adminMode ? 'Trang quản trị QPort' : 'Trang danh mục QPort'}>
              <span className="brand-copy"><strong>qport</strong><small>{adminMode ? 'Quản trị' : 'Danh mục đầu tư'}</small></span>
            </a>

            <button type="button" className="nav-toggle" aria-expanded={open} aria-label="Mở menu tài khoản" onClick={() => setOpen(value => !value)}>
              <span /><span /><span />
            </button>
          </div>

          <div className="app-nav-links desktop-nav-links">
            {adminMode ? (
              <a href="/admin" className="active" aria-current="page"><span>Quản trị</span></a>
            ) : LINKS.map(([href, key, label]) => (
              <a key={href} href={href} className={active === key ? 'active' : ''} aria-current={active === key ? 'page' : undefined}>
                <span>{label}</span>
              </a>
            ))}
          </div>

          <div className="app-nav-footer desktop-nav-footer">
            {!adminMode && <div className="nav-user"><a className="text-link" href="/dividends">Cổ tức</a><a className="text-link" href="/guide">Hướng dẫn</a><a className="text-link" href="/settings">Cài đặt</a></div>}
            {currentUser && <div className="nav-user"><span className="nav-user-name">@{currentUser.username}</span><button type="button" className="nav-logout" onClick={logout}>Đăng xuất</button></div>}
            <AppearanceControls locale={locale} />
          </div>
        </div>
      </nav>
      {mobileChrome}
    </>
  );
}
