import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logoutUser } from '../lib/api.js';
import { navigate } from '../lib/navigation.js';
import {
  clearPersistedQPortState,
  resetClientState,
  selectPortfolio,
  selectRegistry,
  selectUser,
} from '../lib/store.js';
import AppearanceControls from './AppearanceControls.jsx';

const LINKS = [
  ['/', 'portfolio', 'Tổng quan'],
  ['/transactions', 'transactions', 'Giao dịch'],
  ['/performance', 'performance', 'Hiệu quả'],
  ['/risk', 'risk', 'Phân tích'],
];

function NavIcon({ name, size = 18 }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  };

  if (name === 'portfolio') return <svg {...common}><path d="M4 10.5 12 4l8 6.5" /><path d="M6.5 9.5V20h11V9.5" /><path d="M9.5 20v-6h5v6" /></svg>;
  if (name === 'transactions') return <svg {...common}><path d="M7 4v15" /><path d="m3.5 7.5 3.5-3.5 3.5 3.5" /><path d="M17 20V5" /><path d="m13.5 16.5 3.5 3.5 3.5-3.5" /></svg>;
  if (name === 'performance') return <svg {...common}><path d="M4 19V5" /><path d="M4 19h16" /><path d="m7 15 4-4 3 2 5-6" /></svg>;
  if (name === 'risk') return <svg {...common}><path d="M12 3 19 6v5c0 4.5-2.8 8-7 10-4.2-2-7-5.5-7-10V6Z" /><path d="M9 12h6" /></svg>;
  if (name === 'portfolio-stack') return <svg {...common}><rect x="4" y="5" width="16" height="14" rx="3" /><path d="M8 9h8M8 13h5" /></svg>;
  if (name === 'chevron') return <svg {...common}><path d="m8 10 4 4 4-4" /></svg>;
  if (name === 'settings') return <svg {...common}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1 1.55V20h-3v-.09a1.7 1.7 0 0 0-1.1-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 14.7a1.7 1.7 0 0 0-1.55-1H5v-3h.45A1.7 1.7 0 0 0 7 9.65a1.7 1.7 0 0 0-.34-1.88L6.6 7.7l2.12-2.12.06.06A1.7 1.7 0 0 0 10.66 6a1.7 1.7 0 0 0 1-1.55V4h3v.45a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 9.7a1.7 1.7 0 0 0 1.55 1H21v3h-.05A1.7 1.7 0 0 0 19.4 15Z" /></svg>;
  if (name === 'eye-off') return <svg {...common}><path d="m3 3 18 18" /><path d="M10.6 10.7a2 2 0 0 0 2.7 2.7" /><path d="M9.9 4.2A10.7 10.7 0 0 1 12 4c5.5 0 9 8 9 8a17 17 0 0 1-2.1 3.2M6.6 6.6C4.2 8.2 3 12 3 12s3.5 8 9 8a9.7 9.7 0 0 0 4.1-.9" /></svg>;
  if (name === 'eye') return <svg {...common}><path d="M3 12s3.5-8 9-8 9 8 9 8-3.5 8-9 8-9-8-9-8Z" /><circle cx="12" cy="12" r="2.5" /></svg>;
  return <svg {...common}><circle cx="12" cy="8" r="3.25" /><path d="M5.5 20c.6-4 2.75-6 6.5-6s5.9 2 6.5 6" /></svg>;
}

function BrandMark() {
  return <span className="brand-mark" aria-hidden="true"><span>Q</span></span>;
}

export default function AppNav({ active = 'portfolio', locale = 'vi' }) {
  const dispatch = useDispatch();
  const [accountOpen, setAccountOpen] = useState(false);
  const [portfolioOpen, setPortfolioOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(() => (
    typeof window !== 'undefined' && window.localStorage.getItem('qport.privacy-mode.v1') === '1'
  ));
  const currentUser = useSelector(selectUser);
  const registry = useSelector(selectRegistry);
  const portfolios = registry?.portfolios || [];
  const activePortfolioId = String(registry?.active_portfolio_id || '');
  const activePortfolio = portfolios.find(item => String(item.id) === activePortfolioId);
  const adminMode = active === 'admin' || currentUser?.role === 'ADMIN';
  const userInitial = currentUser?.username?.slice(0, 1)?.toUpperCase() || 'U';

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted || typeof document === 'undefined') return undefined;
    document.body.classList.toggle('mobile-sheet-open', accountOpen);
    return () => document.body.classList.remove('mobile-sheet-open');
  }, [accountOpen, mounted]);

  useEffect(() => {
    function closeMenus(event) {
      if (event.key === 'Escape') {
        setAccountOpen(false);
        setPortfolioOpen(false);
      }
    }
    document.addEventListener('keydown', closeMenus);
    return () => document.removeEventListener('keydown', closeMenus);
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.classList.toggle('privacy-mode', privacyMode);
    try { window.localStorage.setItem('qport.privacy-mode.v1', privacyMode ? '1' : '0'); } catch { /* Storage can be unavailable. */ }
  }, [privacyMode]);

  async function logout() {
    setAccountOpen(false);
    try { await logoutUser(); } catch { /* The session may already be expired. */ }
    clearPersistedQPortState();
    dispatch(resetClientState());
    window.location.replace('/login?logged_out=1');
  }

  async function switchPortfolio(value) {
    const id = Number(value);
    if (!id || String(id) === activePortfolioId) return;
    setSwitching(true);
    try {
      await dispatch(selectPortfolio(id)).unwrap();
      setPortfolioOpen(false);
      setAccountOpen(false);
      navigate('/');
    } catch (error) {
      window.alert(`Không thể chuyển danh mục: ${error.message}`);
    } finally {
      setSwitching(false);
    }
  }

  function PortfolioList({ mobile = false }) {
    if (adminMode || portfolios.length === 0) return null;
    return <div className={mobile ? 'portfolio-menu-list mobile-portfolio-list' : 'portfolio-menu-list'}>
      {mobile && <div className="portfolio-list-heading"><span>Không gian tài sản</span><small>Chọn danh mục để chuyển nhanh</small></div>}
      {portfolios.map(item => {
        const selected = String(item.id) === activePortfolioId;
        return <button
          type="button"
          className={`portfolio-menu-option ${selected ? 'active' : ''}`}
          key={item.id}
          onClick={() => switchPortfolio(item.id)}
          disabled={switching}
          aria-current={selected ? 'true' : undefined}
        >
          <span className="portfolio-option-avatar">{item.name.slice(0, 1).toUpperCase()}</span>
          <span className="portfolio-option-copy"><strong>{item.name}</strong><small>{item.is_default ? 'Danh mục mặc định' : 'Danh mục độc lập'}</small></span>
          {selected && <span className="portfolio-option-status">Đang xem</span>}
        </button>;
      })}
      <a className="portfolio-menu-manage" href="/portfolios"><span className="portfolio-menu-plus">+</span><span><strong>Quản lý danh mục</strong><small>Tạo, đổi tên hoặc sắp xếp</small></span><span aria-hidden="true">→</span></a>
    </div>;
  }

  function DesktopPortfolioSwitcher() {
    if (adminMode || portfolios.length === 0) return null;
    return <div className={`header-portfolio-menu ${portfolioOpen ? 'open' : ''}`}>
      <button
        type="button"
        className="header-portfolio-trigger"
        aria-expanded={portfolioOpen}
        aria-haspopup="menu"
        onClick={() => setPortfolioOpen(value => !value)}
      >
        <span className="header-context-icon"><NavIcon name="portfolio-stack" size={17} /></span>
        <span className="header-context-copy"><small>Danh mục đang xem</small><strong>{activePortfolio?.name || 'Danh mục'}</strong></span>
        <span className="header-context-chevron"><NavIcon name="chevron" size={16} /></span>
      </button>
      {portfolioOpen && <div className="portfolio-menu-popover" role="menu"><PortfolioList /></div>}
    </div>;
  }

  const mobileChrome = mounted && typeof document !== 'undefined' ? createPortal(
    <>
      {!adminMode && <nav className="mobile-tab-bar" aria-label="Điều hướng chính">
        {LINKS.map(([href, key, label]) => (
          <a key={href} href={href} className={active === key ? 'active' : ''} aria-current={active === key ? 'page' : undefined}>
            <span className="mobile-tab-icon"><NavIcon name={key} size={21} /></span>
            <span className="mobile-tab-label">{label}</span>
          </a>
        ))}
      </nav>}

      {accountOpen && <button type="button" className="mobile-nav-backdrop" aria-label="Đóng menu tài khoản" onClick={() => setAccountOpen(false)} />}

      {accountOpen && <aside className="mobile-account-sheet header-account-sheet" aria-label="Tài khoản và tùy chọn">
        <div className="mobile-sheet-grabber" aria-hidden="true" />
        <div className="mobile-sheet-title"><span className="header-user-avatar">{userInitial}</span><div><strong>@{currentUser?.username || 'user'}</strong><small>Không gian QPort cá nhân</small></div></div>
        {!adminMode && <PortfolioList mobile />}
        {!adminMode && <div className="header-sheet-links">
          <a href="/dividends">Cổ tức <span>→</span></a>
          <a href="/guide">Hướng dẫn <span>→</span></a>
          <a href="/settings">Cài đặt <span>→</span></a>
        </div>}
        <div className="header-sheet-footer">
          <button type="button" className={`header-privacy-button ${privacyMode ? 'active' : ''}`} onClick={() => setPrivacyMode(value => !value)} aria-pressed={privacyMode}>
            <NavIcon name={privacyMode ? 'eye-off' : 'eye'} /><span>{privacyMode ? 'Hiện số' : 'Ẩn số'}</span>
          </button>
          <AppearanceControls locale={locale} />
          <button type="button" className="mobile-sheet-logout" onClick={logout}>Đăng xuất</button>
        </div>
      </aside>}
    </>,
    document.body,
  ) : null;

  return <>
    <header className={`app-nav wealth-app-nav header-v2 ${accountOpen ? 'nav-open' : ''}`}>
      <nav className="nav-shell" aria-label="Điều hướng chính">
        <div className="app-nav-head">
          <a className="brand" href={adminMode ? '/admin' : '/'} aria-label={adminMode ? 'Trang quản trị QPort' : 'Trang tổng quan QPort'}>
            <BrandMark />
            <span className="brand-copy"><strong>QPort</strong><small>{adminMode ? 'Quản trị' : 'Sổ tài sản'}</small></span>
          </a>
          <button type="button" className="nav-toggle header-user-button" aria-expanded={accountOpen} aria-label="Mở tài khoản và tùy chọn" onClick={() => setAccountOpen(value => !value)}>
            <span className="header-user-avatar">{userInitial}</span><NavIcon name="chevron" size={15} />
          </button>
        </div>

        {!adminMode && <DesktopPortfolioSwitcher />}

        <div className="app-nav-links desktop-nav-links">
          {adminMode ? <a href="/admin" className="active" aria-current="page"><NavIcon name="risk" /><span>Quản trị</span></a> : LINKS.map(([href, key, label]) => (
            <a key={href} href={href} className={active === key ? 'active' : ''} aria-current={active === key ? 'page' : undefined}><NavIcon name={key} /><span>{label}</span></a>
          ))}
        </div>

        <div className="app-nav-footer desktop-nav-footer">
          {!adminMode && <button type="button" className={`header-privacy-button ${privacyMode ? 'active' : ''}`} onClick={() => setPrivacyMode(value => !value)} aria-pressed={privacyMode} title={privacyMode ? 'Hiện số dư' : 'Ẩn số dư'}>
            <NavIcon name={privacyMode ? 'eye-off' : 'eye'} /><span>{privacyMode ? 'Hiện số' : 'Ẩn số'}</span>
          </button>}
          {!adminMode && <a className="header-icon-link" href="/settings" aria-label="Cài đặt"><NavIcon name="settings" /></a>}
          <AppearanceControls locale={locale} />
          {currentUser && <div className="header-user-menu">
            <span className="header-user-avatar">{userInitial}</span>
            <span className="header-user-copy"><strong>@{currentUser.username}</strong><small>{adminMode ? 'Quản trị viên' : 'Nhà đầu tư'}</small></span>
            <button type="button" className="header-logout-button" onClick={logout}>Đăng xuất</button>
          </div>}
        </div>
      </nav>
    </header>
    {portfolioOpen && <button type="button" className="portfolio-menu-backdrop" aria-label="Đóng danh sách danh mục" onClick={() => setPortfolioOpen(false)} />}
    {mobileChrome}
  </>;
}
