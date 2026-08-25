import React from 'react';
import { createRoot } from 'react-dom/client';
import AuthPage from './pages/AuthPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import AdminUserPortfolioPage from './pages/AdminUserPortfolioPage.jsx';
import PortfolioPage from './pages/PortfolioPage.jsx';
import PortfoliosPage from './pages/PortfoliosPage.jsx';
import TransactionsPage from './pages/TransactionsPage.jsx';
import PerformancePage from './pages/PerformancePageV2.jsx';
import RiskPage from './pages/RiskPage.jsx';
import DividendHistoryPage from './pages/DividendHistoryPage.jsx';
import SnapshotsPage from './pages/SnapshotsPage.jsx';
import OperationsPage from './pages/OperationsPage.jsx';
import LogsPage from './pages/LogsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import GuidePage from './pages/GuidePage.jsx';
import {
  getActivityLog,
  getAdminUserPortfolio,
  getCurrentUser,
  getPortfolioDashboard,
  getPortfolioHoldingSymbols,
  getPortfolioOperations,
  getPortfolioPerformance,
  getPortfolioRisk,
  listPortfolioSnapshots,
  listPortfolios,
  listPortfolioTransactionAudit,
  listPortfolioTransactions,
} from './lib/api.js';
import { applyStoredAppearance } from './lib/appearance.js';
import './styles.css';
import './buyhold.css';
import './responsive.css';
import './portfolio-insights.css';
import './received-dividends.css';
import './table-alignment.css';
import './auth.css';
import './ui-polish.css';
import './insight-depth.css';
import './holding-info-row.css';
import './accessibility-polish.css';
import './appearance-controls.css';
import './risk-readable.css';
import './guide-friendly.css';
import './dividend-history.css';
import './settings-friendly.css';
import './portfolio-manager.css';
import './mobile-iphone.css';
import './mobile-scroll-fix.css';

const APP_LOCALE = 'vi';

applyStoredAppearance();
document.body.classList.remove('mobile-sheet-open');
document.documentElement.lang = APP_LOCALE;

const root = createRoot(document.getElementById('root'));

function todayVn() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function LoadingScreen() {
  return <main className="auth-shell vercel-boot-shell" aria-busy="true">
    <section className="auth-card vercel-boot-card">
      <div className="eyebrow">QPort</div>
      <h1>Đang tải dữ liệu…</h1>
      <p className="muted">Các giá trị thực sẽ hiển thị sau khi dữ liệu tải xong.</p>
    </section>
  </main>;
}

function ErrorScreen({ error }) {
  return <main className="auth-shell vercel-boot-shell">
    <section className="auth-card vercel-boot-card">
      <div className="eyebrow">QPort</div>
      <h1>Không thể tải dữ liệu</h1>
      <p className="error">{error?.message || 'Ứng dụng hiện không thể tải dữ liệu. Vui lòng thử lại.'}</p>
      <button type="button" className="btn-primary" onClick={() => window.location.reload()}>Thử lại</button>
    </section>
  </main>;
}

async function loadPage(pathname, locale) {
  if (pathname === '/login') {
    try {
      const me = await getCurrentUser();
      if (me?.user) {
        window.location.replace(me.user.role === 'ADMIN' ? '/admin' : '/');
        return null;
      }
    } catch {
      // Chưa đăng nhập là trạng thái bình thường của trang đăng nhập.
    }
    return { Page: AuthPage, props: { locale } };
  }

  const me = await getCurrentUser();
  const user = me?.user || null;
  if (!user) {
    window.location.replace('/login');
    return null;
  }

  const isAdminPath = pathname === '/admin' || /^\/admin\/users\/\d+$/.test(pathname);
  if (user.role === 'ADMIN' && !isAdminPath) {
    window.location.replace('/admin');
    return null;
  }
  if (user.role !== 'ADMIN' && isAdminPath) {
    window.location.replace('/');
    return null;
  }

  const common = { locale, currentUser: user };

  const adminUserMatch = pathname.match(/^\/admin\/users\/(\d+)$/);
  if (adminUserMatch) {
    const payload = await getAdminUserPortfolio(Number(adminUserMatch[1]));
    return { Page: AdminUserPortfolioPage, props: { ...common, payload } };
  }

  switch (pathname) {
    case '/': {
      const dashboard = await getPortfolioDashboard();
      return { Page: PortfolioPage, props: { ...common, dashboard } };
    }
    case '/portfolios':
      return { Page: PortfoliosPage, props: { ...common, registry: await listPortfolios() } };
    case '/transactions': {
      const [transactions, corrections] = await Promise.all([
        listPortfolioTransactions(),
        listPortfolioTransactionAudit(),
      ]);
      return {
        Page: TransactionsPage,
        props: { ...common, transactions, corrections, today: todayVn() },
      };
    }
    case '/performance':
      return { Page: PerformancePage, props: { ...common, performance: await getPortfolioPerformance() } };
    case '/risk':
      return { Page: RiskPage, props: { ...common, risk: await getPortfolioRisk() } };
    case '/dividends':
      return { Page: DividendHistoryPage, props: { ...common, symbols: await getPortfolioHoldingSymbols() } };
    case '/snapshots':
      return { Page: SnapshotsPage, props: { ...common, snapshots: await listPortfolioSnapshots() } };
    case '/operations':
      return {
        Page: OperationsPage,
        props: { ...common, operations: await getPortfolioOperations(), today: todayVn() },
      };
    case '/logs':
      return { Page: LogsPage, props: { ...common, activity: await getActivityLog() } };
    case '/settings':
      return { Page: SettingsPage, props: { ...common, dashboard: await getPortfolioDashboard() } };
    case '/guide':
      return { Page: GuidePage, props: common };
    case '/admin':
      return { Page: AdminPage, props: common };
    default:
      window.history.replaceState({}, '', user.role === 'ADMIN' ? '/admin' : '/');
      return loadPage(user.role === 'ADMIN' ? '/admin' : '/', locale);
  }
}

async function boot() {
  root.render(<LoadingScreen />);
  const pathname = window.location.pathname.replace(/\/+$/, '') || '/';
  const locale = APP_LOCALE;
  try {
    const loaded = await loadPage(pathname, locale);
    if (!loaded) return;
    const { Page, props } = loaded;
    root.render(<Page {...props} />);
  } catch (error) {
    root.render(<ErrorScreen error={error} />);
  }
}

boot();
