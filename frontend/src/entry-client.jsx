// Client entry: hydrate the server-rendered operational QPort page.
import React from 'react';
import { hydrateRoot } from 'react-dom/client';
import AuthPage from './pages/AuthPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import PortfolioPage from './pages/PortfolioPage.jsx';
import TransactionsPage from './pages/TransactionsPage.jsx';
import PerformancePage from './pages/PerformancePageV2.jsx';
import RiskPage from './pages/RiskPage.jsx';
import SnapshotsPage from './pages/SnapshotsPage.jsx';
import OperationsPage from './pages/OperationsPage.jsx';
import LogsPage from './pages/LogsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import GuidePage from './pages/GuidePage.jsx';
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
import './mobile-iphone.css';
import './mobile-scroll-fix.css';

// Apply a persisted custom palette before hydration. With no saved palette the
// app explicitly stays on QPort's default dark appearance.
applyStoredAppearance();

// Browser device simulators, bfcache and hot reload can preserve a body class
// from an open mobile sheet. Never carry that scroll lock into a fresh page.
if (typeof document !== 'undefined') document.body.classList.remove('mobile-sheet-open');

const PAGES = {
  auth: AuthPage,
  admin: AdminPage,
  portfolio: PortfolioPage,
  transactions: TransactionsPage,
  performance: PerformancePage,
  risk: RiskPage,
  snapshots: SnapshotsPage,
  operations: OperationsPage,
  logs: LogsPage,
  settings: SettingsPage,
  guide: GuidePage,
};

const root = document.getElementById('root');

// buyhold_server.py serializes the SSR bootstrap as window.__PAGE__ =
// { page, props }. Keep the older object name as a temporary compatibility
// fallback, but never default a known login/auth document to PortfolioPage.
const bootstrap = window.__PAGE__ || window.__QPORT_PROPS__ || {};
const pageName = bootstrap.page || 'portfolio';
const props = bootstrap.props || (bootstrap.page ? {} : bootstrap);
const Page = PAGES[pageName] || PortfolioPage;

hydrateRoot(root, <Page {...props} />);
