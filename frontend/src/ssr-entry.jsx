// Server-side render entry for the operational Buy & Hold product.
import React from 'react';
import { renderToString } from 'react-dom/server';
import PortfolioDashboardPage from './pages/PortfolioDashboardPage.jsx';
import TransactionsPage from './pages/TransactionsPage.jsx';
import PerformancePage from './pages/PerformancePage.jsx';
import RiskPage from './pages/RiskPage.jsx';
import SnapshotsPage from './pages/SnapshotsPage.jsx';
import OperationsPage from './pages/OperationsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
import GuidePage from './pages/GuidePage.jsx';

const PAGES = {
  portfolio: PortfolioDashboardPage,
  transactions: TransactionsPage,
  performance: PerformancePage,
  risk: RiskPage,
  snapshots: SnapshotsPage,
  operations: OperationsPage,
  settings: SettingsPage,
  guide: GuidePage,
};

export function renderPage(page, props) {
  const C = PAGES[page];
  if (!C) return '';
  return renderToString(React.createElement(C, props || {}));
}

export default { renderPage };
