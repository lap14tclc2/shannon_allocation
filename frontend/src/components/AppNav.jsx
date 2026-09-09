import React, { useEffect, useRef, useState } from 'react';
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
  ['/terminal', 'portfolio', 'Terminal'],
  ['/business', 'valuation', 'Doanh nghiệp'],
  ['/capital', 'allocation', 'Vốn cá nhân'],
  ['/history', 'performance', 'Lịch sử tích sản'],
];

const NAVIGATION_LINKS = [
  ['/terminal', 'portfolio', 'Terminal', 'Pháo đài cá nhân và ma trận quyết định'],
  ['/business', 'valuation', 'Doanh nghiệp', 'Phân tích 7 chiều, Moat và Bẫy giá trị'],
  ['/capital', 'allocation', 'Vốn cá nhân', 'Dự phòng sinh tồn và Vốn khả dụng dài hạn'],
  ['/history', 'performance', 'Lịch sử tích sản', 'Lợi nhuận TWR/XIRR và nhật ký giao dịch'],
  ['/risk', 'risk', 'Phân tích rủi ro', 'Chẩn đoán biến động nâng cao'],
  ['/guide', 'guide', 'Hướng dẫn', 'Triết lý và cách dùng QPort'],
];


function anchoredPopoverStyle(trigger, preferredWidth) {
  if (!trigger || typeof window === 'undefined') return undefined;
  const gutter = 12;
  const rect = trigger.getBoundingClientRect();
  const width = Math.min(preferredWidth, window.innerWidth - gutter * 2);
  const centeredLeft = rect.left + rect.width / 2 - width / 2;
  const left = Math.min(Math.max(gutter, centeredLeft), window.innerWidth - width - gutter);
  return { top: `${rect.bottom + 10}px`, left: `${left}px`, width: `${width}px` };
}

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
  if (name === 'valuation') return <svg {...common}><path d="M5 3h14v18H5z" /><path d="M8 8h8M8 12h5M8 16h8" /></svg>;
  if (name === 'screener') return <svg {...common}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></svg>;
  if (name === 'allocation') return <svg {...common}><path d="M4 7h16" /><path d="M4 12h10" /><path d="M4 17h6" /><circle cx="18" cy="12" r="3" /><circle cx="16" cy="17" r="2.5" /></svg>;
  if (name === 'risk') return <svg {...common}><path d="M12 3 19 6v5c0 4.5-2.8 8-7 10-4.2-2-7-5.5-7-10V6Z" /><path d="M9 12h6" /></svg>;
  if (name === 'portfolio-stack') return <svg {...common}><rect x="4" y="5" width="16" height="14" rx="3" /><path d="M8 9h8M8 13h5" /></svg>;
  if (name === 'chevron') return <svg {...common}><path d="m8 10 4 4 4-4" /></svg>;
  if (name === 'settings') return <svg {...common}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1 1.55V20h-3v-.09a1.7 1.7 0 0 0-1.1-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 14.7a1.7 1.7 0 0 0-1.55-1H5v-3h.45A1.7 1.7 0 0 0 7 9.65a1.7 1.7 0 0 0-.34-1.88L6.6 7.7l2.12-2.12.06.06A1.7 1.7 0 0 0 10.66 6a1.7 1.7 0 0 0 1-1.55V4h3v.45a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 9.7a1.7 1.7 0 0 0 1.55 1H21v3h-.05A1.7 1.7 0 0 0 19.4 15Z" /></svg>;
  if (name === 'menu') return <svg {...common}><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></svg>;
  if (name === 'dividends') return <svg {...common}><path d="M12 3s6 5.4 6 10a6 6 0 0 1-12 0c0-4.6 6-10 6-10Z" /><path d="M9 14.5c.7 1.4 1.7 2 3 2" /></svg>;
  if (name === 'snapshots') return <svg {...common}><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M8 3v4M16 3v4M4 10h16M8 14h3" /></svg>;
  if (name === 'operations') return <svg {...common}><path d="M20 7h-6V1" /><path d="M20 7a8 8 0 1 0 1 7" /><path d="M8 12h8M12 8v8" /></svg>;
  if (name === 'guide') return <svg {...common}><path d="M4 5.5A3.5 3.5 0 0 1 7.5 2H12v18H7.5A3.5 3.5 0 0 0 4 23Z" /><path d="M20 5.5A3.5 3.5 0 0 0 16.5 2H12v18h4.5A3.5 3.5 0 0 1 20 23Z" /></svg>;
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
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [portfolioPosition, setPortfolioPosition] = useState(undefined);
  const [navigationPosition, setNavigationPosition] = useState(undefined);
  const [mounted, setMounted] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(() => (
    typeof window !== 'undefined' && window.localStorage.getItem('qport.privacy-mode.v1') === '1'
  ));
  const portfolioTriggerRef = useRef(null);
  const navigationTriggerRef = useRef(null);
  const currentUser = useSelector(selectUser);
  const registry = useSelector(selectRegistry);
  const portfolios = registry?.portfolios || [];
  const activePortfolioId = String(registry?.active_portfolio_id || '');
  const activePortfolio = portfolios.find(item => String(item.id) === activePortfolioId);
  const adminMode = active === 'admin' || currentUser?.role === 'ADMIN';
  const userInitial = currentUser?.username?.slice(0, 1)?.toUpperCase() || 'U';
  const activeNavigation = NAVIGATION_LINKS.find(([, key]) => key === active);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    setPortfolioOpen(false);
    setNavigationOpen(false);
    setAccountOpen(false);
  }, [active]);

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
        setNavigationOpen(false);
      }
    }
    document.addEventListener('keydown', closeMenus);
    return () => document.removeEventListener('keydown', closeMenus);
  }, []);

  useEffect(() => {
    if (!portfolioOpen && !navigationOpen) return undefined;
    function updatePopoverPositions() {
      if (portfolioOpen) setPortfolioPosition(anchoredPopoverStyle(portfolioTriggerRef.current, 360));
      if (navigationOpen) setNavigationPosition(anchoredPopoverStyle(navigationTriggerRef.current, 430));
    }
    updatePopoverPositions();
    window.addEventListener('resize', updatePopoverPositions);
    window.addEventListener('scroll', updatePopoverPositions, { passive: true });
    return () => {
      window.removeEventListener('resize', updatePopoverPositions);
      window.removeEventListener('scroll', updatePopoverPositions);
    };
  }, [navigationOpen, portfolioOpen]);

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

  function togglePortfolioMenu() {
    setAccountOpen(false);
    setNavigationOpen(false);
    if (!portfolioOpen) setPortfolioPosition(anchoredPopoverStyle(portfolioTriggerRef.current, 360));
    setPortfolioOpen(value => !value);
  }

  function toggleNavigationMenu() {
    setAccountOpen(false);
    setPortfolioOpen(false);
    if (!navigationOpen) setNavigationPosition(anchoredPopoverStyle(navigationTriggerRef.current, 430));
    setNavigationOpen(value => !value);
  }

  async function switchPortfolio(value) {
    const id = Number(value);
    if (!id) return;
    if (String(id) === activePortfolioId) {
      setPortfolioOpen(false);
      setAccountOpen(false);
      return;
    }
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
      <a className="portfolio-menu-manage" href="/portfolios" onClick={() => { setPortfolioOpen(false); setAccountOpen(false); }}><span className="portfolio-menu-plus">+</span><span><strong>Quản lý danh mục</strong><small>Tạo, đổi tên hoặc sắp xếp</small></span><span aria-hidden="true">→</span></a>
    </div>;
  }

  function DesktopPortfolioSwitcher() {
    if (adminMode || portfolios.length === 0) return null;
    return <div className={`header-portfolio-menu ${portfolioOpen ? 'open' : ''}`}>
      <button
        type="button"
        className="header-portfolio-trigger"
        ref={portfolioTriggerRef}
        aria-expanded={portfolioOpen}
        aria-haspopup="dialog"
        aria-controls="desktop-portfolio-menu"
        onClick={togglePortfolioMenu}
      >
        <span className="header-context-icon"><NavIcon name="portfolio-stack" size={17} /></span>
        <span className="header-context-copy"><small>Danh mục đang xem</small><strong>{activePortfolio?.name || 'Danh mục'}</strong></span>
        <span className="header-context-chevron"><NavIcon name="chevron" size={16} /></span>
      </button>
    </div>;
  }

  function DesktopNavigationTrigger() {
    return <div className={`header-navigation-menu ${navigationOpen ? 'open' : ''}`}>
      <button
        type="button"
        className="header-navigation-trigger"
        ref={navigationTriggerRef}
        aria-expanded={navigationOpen}
        aria-haspopup="dialog"
        aria-controls="desktop-navigation-menu"
        onClick={toggleNavigationMenu}
      >
        <span className="header-navigation-icon"><NavIcon name="menu" size={17} /></span>
        <span className="header-navigation-copy"><small>Điều hướng</small><strong>{adminMode ? 'Quản trị' : activeNavigation?.[2] || 'Các trang'}</strong></span>
        <span className="header-navigation-chevron"><NavIcon name="chevron" size={15} /></span>
      </button>
    </div>;
  }

  const desktopPortfolioMenu = mounted && portfolioOpen && typeof document !== 'undefined' ? createPortal(
    <>
      <button type="button" className="portfolio-menu-backdrop" aria-label="Đóng danh sách danh mục" onClick={() => setPortfolioOpen(false)} />
      <aside id="desktop-portfolio-menu" className="portfolio-menu-popover" style={portfolioPosition} role="dialog" aria-modal="true" aria-labelledby="desktop-portfolio-title">
        <div className="portfolio-popover-head">
          <div><span className="eyebrow">Không gian tài sản</span><strong id="desktop-portfolio-title">Chọn danh mục</strong></div>
          <button type="button" className="portfolio-popover-close" aria-label="Đóng danh sách danh mục" onClick={() => setPortfolioOpen(false)}>×</button>
        </div>
        <PortfolioList />
      </aside>
    </>,
    document.body,
  ) : null;

  const desktopNavigationMenu = mounted && navigationOpen && typeof document !== 'undefined' ? createPortal(
    <>
      <button type="button" className="portfolio-menu-backdrop navigation-menu-backdrop" aria-label="Đóng menu điều hướng" onClick={() => setNavigationOpen(false)} />
      <aside id="desktop-navigation-menu" className="navigation-menu-popover" style={navigationPosition} role="dialog" aria-modal="true" aria-labelledby="desktop-navigation-title">
        <div className="portfolio-popover-head navigation-popover-head">
          <div><span className="eyebrow">QPort</span><strong id="desktop-navigation-title">Đi đến trang</strong></div>
          <button type="button" className="portfolio-popover-close" aria-label="Đóng menu điều hướng" onClick={() => setNavigationOpen(false)}>×</button>
        </div>
        <nav className="navigation-menu-grid" aria-label="Danh sách trang">
          {(adminMode ? [
            ['/admin', 'admin', 'Người dùng', 'Quản lý tài khoản và portfolio'],
            ['/logs', 'logs', 'System Logs', 'Theo dõi request, lỗi và audit log'],
            ['/admin/auth', 'admin-auth', 'Xác thực admin', 'Đổi password quản trị'],
            ['/admin/finance-data', 'admin-finance-data', 'Finance Data', 'Crawl và quản lý BCTC'],
          ] : NAVIGATION_LINKS).map(([href, key, label, description]) => (
            <a key={href} href={href} className={active === key ? 'active' : ''} aria-current={active === key ? 'page' : undefined} onClick={() => setNavigationOpen(false)}>
              <span className="navigation-option-icon"><NavIcon name={key === 'admin' ? 'risk' : key === 'admin-auth' ? 'settings' : key === 'logs' ? 'guide' : key === 'admin-finance-data' ? 'valuation' : key} size={18} /></span>
              <span><strong>{label}</strong><small>{description}</small></span>
              <span className="navigation-option-arrow" aria-hidden="true">→</span>
            </a>
          ))}
        </nav>
      </aside>
    </>,
    document.body,
  ) : null;

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
          <a href="/screener">Bộ lọc cổ phiếu <span>→</span></a>
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
    <header className={`app-nav wealth-app-nav header-v2 ${accountOpen ? 'nav-open' : ''} ${adminMode ? 'admin-header' : ''}`}>
      <nav className="nav-shell" aria-label="Điều hướng chính">
        <div className="app-nav-head">
          <a className="brand" href={adminMode ? '/admin' : '/'} aria-label={adminMode ? 'Trang quản trị QPort' : 'Trang tổng quan QPort'}>
            <BrandMark />
            <span className="brand-copy"><strong>QPort</strong><small>{adminMode ? 'Quản trị' : 'Sổ tài sản'}</small></span>
          </a>
          <button type="button" className="nav-toggle header-user-button" aria-expanded={accountOpen} aria-label="Mở tài khoản và tùy chọn" onClick={() => { setPortfolioOpen(false); setNavigationOpen(false); setAccountOpen(value => !value); }}>
            <span className="header-user-avatar">{userInitial}</span><NavIcon name="chevron" size={15} />
          </button>
        </div>

        {!adminMode && portfolios.length > 0 && <DesktopPortfolioSwitcher />}
        <DesktopNavigationTrigger />

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
    {desktopPortfolioMenu}
    {desktopNavigationMenu}
    {mobileChrome}
  </>;
}
