import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Provider, useDispatch, useSelector } from 'react-redux';
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
import { applyStoredAppearance } from './lib/appearance.js';
import { NAVIGATION_EVENT, navigate } from './lib/navigation.js';
import {
  bootstrapApp,
  loadRoute,
  selectBootError,
  selectBootStatus,
  selectRegistry,
  selectRouteState,
  selectUser,
  store,
} from './lib/store.js';
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
import './spa-state.css';
import './mobile-iphone.css';
import './mobile-scroll-fix.css';

const APP_LOCALE = 'vi';

const ROUTES = {
  '/': PortfolioPage,
  '/portfolios': PortfoliosPage,
  '/transactions': TransactionsPage,
  '/performance': PerformancePage,
  '/risk': RiskPage,
  '/dividends': DividendHistoryPage,
  '/snapshots': SnapshotsPage,
  '/operations': OperationsPage,
  '/logs': LogsPage,
  '/settings': SettingsPage,
  '/guide': GuidePage,
  '/admin': AdminPage,
};

applyStoredAppearance();
document.body.classList.remove('mobile-sheet-open');
document.documentElement.lang = APP_LOCALE;

function currentPathname() {
  return window.location.pathname.replace(/\/+$/, '') || '/';
}

function LoadingScreen({ compact = false }) {
  return <main className={compact ? 'spa-route-loading' : 'auth-shell vercel-boot-shell'} aria-busy="true">
    <section className={compact ? 'spa-route-loading-card' : 'auth-card vercel-boot-card'}>
      <div className="spa-loading-spinner" aria-hidden="true" />
      <div>
        <div className="eyebrow">QPort</div>
        <h1>Äang táº£i dá»¯ liá»uâ¦</h1>
        <p className="muted">Trang váº«n an toÃ n; cÃ¡c giÃ¡ trá» thá»±c chá» hiá»n thá» sau khi dá»¯ liá»u sáºµn sÃ ng.</p>
      </div>
    </section>
  </main>;
}

function ErrorScreen({ error, onRetry }) {
  return <main className="auth-shell vercel-boot-shell">
    <section className="auth-card vercel-boot-card">
      <div className="eyebrow">QPort</div>
      <h1>KhÃ´ng thá» táº£i dá»¯ liá»u</h1>
      <p className="error">{error || 'á»¨ng dá»¥ng hiá»n khÃ´ng thá» táº£i dá»¯ liá»u. Vui lÃ²ng thá»­ láº¡i.'}</p>
      <button type="button" className="btn-primary" onClick={onRetry}>Thá»­ láº¡i</button>
    </section>
  </main>;
}

function resolveRoute(pathname) {
  const adminUserMatch = pathname.match(/^\/admin\/users\/\d+$/);
  if (adminUserMatch) return AdminUserPortfolioPage;
  return ROUTES[pathname] || null;
}

function App() {
  const dispatch = useDispatch();
  const [pathname, setPathname] = useState(currentPathname);
  const bootStatus = useSelector(selectBootStatus);
  const bootError = useSelector(selectBootError);
  const user = useSelector(selectUser);
  const registry = useSelector(selectRegistry);
  const route = useSelector(state => selectRouteState(state, pathname));
  const activePortfolioId = registry?.active_portfolio_id || 0;
  const Page = useMemo(() => resolveRoute(pathname), [pathname]);

  useEffect(() => {
    dispatch(bootstrapApp());
  }, [dispatch]);

  useEffect(() => {
    const updatePath = () => setPathname(currentPathname());
    const handleDocumentClick = event => {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = event.target.closest?.('a[href]');
      if (!anchor || anchor.target || anchor.hasAttribute('download')) return;
      const target = new URL(anchor.href, window.location.origin);
      if (target.origin !== window.location.origin) return;
      event.preventDefault();
      navigate(`${target.pathname}${target.search}${target.hash}`);
    };
    window.addEventListener('popstate', updatePath);
    window.addEventListener(NAVIGATION_EVENT, updatePath);
    document.addEventListener('click', handleDocumentClick);
    return () => {
      window.removeEventListener('popstate', updatePath);
      window.removeEventListener(NAVIGATION_EVENT, updatePath);
      document.removeEventListener('click', handleDocumentClick);
    };
  }, []);

  useEffect(() => {
    if (bootStatus !== 'ready') return;
    if (pathname === '/login') {
      if (user) navigate(user.role === 'ADMIN' ? '/admin' : '/', { replace: true });
      return;
    }
    if (!user) {
      navigate('/login', { replace: true });
      return;
    }
    const adminPath = pathname === '/admin' || /^\/admin\/users\/\d+$/.test(pathname);
    if (user.role === 'ADMIN' && !adminPath) {
      navigate('/admin', { replace: true });
      return;
    }
    if (user.role !== 'ADMIN' && adminPath) {
      navigate('/', { replace: true });
      return;
    }
    if (!resolveRoute(pathname)) {
      navigate(user.role === 'ADMIN' ? '/admin' : '/', { replace: true });
      return;
    }
    dispatch(loadRoute({ pathname }));
  }, [activePortfolioId, bootStatus, dispatch, pathname, user]);

  if (bootStatus === 'idle' || bootStatus === 'loading') return <LoadingScreen />;

  if (pathname === '/login') {
    if (user) return <LoadingScreen />;
    return <AuthPage locale={APP_LOCALE} />;
  }

  if (bootStatus === 'failed') {
    return <ErrorScreen error={bootError} onRetry={() => dispatch(bootstrapApp())} />;
  }

  if (!user || !Page) return <LoadingScreen />;

  const common = { locale: APP_LOCALE, currentUser: user };
  const data = route.data || {};
  const isLoading = route.status === 'idle' || route.status === 'loading';
  const hasCachedData = Boolean(route.data);

  if (pathname === '/') {
    return <>
      {isLoading && hasCachedData && <div className="spa-data-banner" role="status">Äang cáº­p nháº­t dá»¯ liá»u má»i nháº¥tâ¦</div>}
      {route.status === 'failed' && hasCachedData && <div className="spa-data-banner spa-data-error" role="alert">{route.error} Dá»¯ liá»u lÆ°u gáº§n nháº¥t váº«n ÄÆ°á»£c giá»¯ láº¡i.</div>}
      <Page
        {...common}
        {...data}
        dashboard={data.dashboard || {}}
        dataLoading={isLoading}
        dataUpdatedAt={route.updatedAt}
      />
    </>;
  }

  if (isLoading && !hasCachedData) return <LoadingScreen compact />;
  if (route.status === 'failed' && !hasCachedData) {
    return <ErrorScreen error={route.error} onRetry={() => dispatch(loadRoute({ pathname }))} />;
  }

  return <>
    {isLoading && <div className="spa-data-banner" role="status">Äang cáº­p nháº­t dá»¯ liá»u má»i nháº¥tâ¦</div>}
    {route.status === 'failed' && <div className="spa-data-banner spa-data-error" role="alert">{route.error} Dá»¯ liá»u lÆ°u gáº§n nháº¥t váº«n ÄÆ°á»£c giá»¯ láº¡i.</div>}
    <Page {...common} {...data} />
  </>;
}

const root = createRoot(document.getElementById('root'));
root.render(<Provider store={store}><App /></Provider>);
