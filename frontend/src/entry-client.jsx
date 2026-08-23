// Client entry: hydrate the server-rendered operational QPort page.
import React from 'react';
import { hydrateRoot } from 'react-dom/client';
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

const PAGES = {
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

const page = window.__PAGE__ || { page: 'portfolio', props: { dashboard: {}, locale: 'en' } };
const C = PAGES[page.page] || PortfolioDashboardPage;
hydrateRoot(document.getElementById('root'), React.createElement(C, page.props || {}));
