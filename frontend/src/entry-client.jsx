// Client entry: hydrate the server-rendered operational QPort page.
import React from 'react';
import { hydrateRoot } from 'react-dom/client';
import AuthPage from './pages/AuthPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import PortfolioDashboardPage from './pages/PortfolioDashboardPage.jsx';
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
import './auth.css';

const PAGES = {
  auth: AuthPage,
  admin: AdminPage,
  portfolio: PortfolioDashboardPage,
  transactions: TransactionsPage,
  performance: PerformancePage,
  risk: RiskPage,
  snapshots: SnapshotsPage,
  operations: OperationsPage,
  logs: LogsPage,
  settings: SettingsPage,
  guide: GuidePage,
};

function readPageBootstrap() {
  const node = document.getElementById('qport-page-data');
  if (!node) return { page: 'auth', props: { locale: 'en' } };
  try {
    return JSON.parse(node.textContent || '{}');
  } catch {
    return { page: 'auth', props: { locale: 'en' } };
  }
}

const page = readPageBootstrap();
const C = PAGES[page.page] || AuthPage;
hydrateRoot(document.getElementById('root'), React.createElement(C, page.props || {}));
