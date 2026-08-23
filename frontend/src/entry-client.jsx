// Client entry: hydrate the server-rendered page from window.__PAGE__.
import React from 'react';
import { hydrateRoot } from 'react-dom/client';
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
import './styles.css';

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

const page = window.__PAGE__ || { page: 'portfolio', props: { dashboard: {} } };
const C = PAGES[page.page] || PortfolioDashboardPage;
hydrateRoot(document.getElementById('root'), React.createElement(C, page.props || {}));
