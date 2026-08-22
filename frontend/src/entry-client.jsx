// Client entry: hydrate the server-rendered page from window.__PAGE__.
import React from 'react';
import { hydrateRoot } from 'react-dom/client';
import HomePage from './pages/HomePage.jsx';
import RunPage from './pages/RunPage.jsx';
import ComboPage from './pages/ComboPage.jsx';
import OptimizerListPage from './pages/OptimizerListPage.jsx';
import OptimizerDetailPage from './pages/OptimizerDetailPage.jsx';
import './styles.css';

const PAGES = {
  home: HomePage,
  run: RunPage,
  combo: ComboPage,
  optimizer_list: OptimizerListPage,
  optimizer_detail: OptimizerDetailPage,
};

// Optimizer is the product landing experience. The explicit `home` key remains
// supported because the Python SSR server uses it for `/` as a compatibility
// adapter, but a missing page payload now fails toward the optimizer rather than
// the retired legacy backtest landing page.
const page = window.__PAGE__ || { page: 'optimizer_list', props: { experiments: [] } };
const C = PAGES[page.page] || OptimizerListPage;
hydrateRoot(document.getElementById('root'), React.createElement(C, page.props || {}));
