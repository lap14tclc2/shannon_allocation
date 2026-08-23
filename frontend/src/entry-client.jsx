// Client entry: hydrate the server-rendered operational QPort page.
import React from 'react';
import { hydrateRoot } from 'react-dom/client';
import AuthPage from './pages/AuthPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import PortfolioPage from './pages/PortfolioPage.jsx';
import TransactionsPage from './pages/TransactionsPage.jsx';
import PerformancePage from './pages/PerformancePage.jsx';
import RiskPage from './pages/RiskPage.jsx';
import SnapshotsPage from './pages/SnapshotsPage.jsx';
import OperationsPage from './pages/OperationsPage.jsx';
import LogsPage from './pages/LogsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import GuidePage from './pages/GuidePage.jsx';
import './styles.css';
import './buyhold.css';
import './responsive.css';
import './portfolio-insights.css';
import './received-dividends.css';
import './table-alignment.css';
import './auth.css';
import './ui-polish.css';

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

const page = window.__PAGE__ || { page: 'auth', props: { locale: 'en' } };

if (page.props?.currentUser?.role === 'ADMIN' && page.page !== 'admin') {
  window.location.replace('/admin');
} else {
  const C = PAGES[page.page] || AuthPage;
  hydrateRoot(document.getElementById('root'), React.createElement(C, page.props || {}));
}
