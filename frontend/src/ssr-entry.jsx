// Server-side render entry (bundled by Vite for Node via `npm run build:ssr`).
import React from 'react';
import { renderToString } from 'react-dom/server';
import HomePage from './pages/HomePage.jsx';
import PortfolioDashboardPage from './pages/PortfolioDashboardPage.jsx';
import TransactionsPage from './pages/TransactionsPage.jsx';
import PerformancePage from './pages/PerformancePage.jsx';
import RiskPage from './pages/RiskPage.jsx';
import SnapshotsPage from './pages/SnapshotsPage.jsx';
import ResearchPage from './pages/ResearchPage.jsx';
import RunPage from './pages/RunPage.jsx';
import ComboPage from './pages/ComboPage.jsx';
import OptimizerListPage from './pages/OptimizerListPage.jsx';
import OptimizerDetailPage from './pages/OptimizerDetailPage.jsx';

const PAGES = {
  home: HomePage,
  portfolio: PortfolioDashboardPage,
  transactions: TransactionsPage,
  performance: PerformancePage,
  risk: RiskPage,
  snapshots: SnapshotsPage,
  research: ResearchPage,
  run: RunPage,
  combo: ComboPage,
  optimizer_list: OptimizerListPage,
  optimizer_detail: OptimizerDetailPage,
};

export function renderPage(page, props) {
  const C = PAGES[page];
  if (!C) return '';
  return renderToString(React.createElement(C, props || {}));
}

export default { renderPage };
