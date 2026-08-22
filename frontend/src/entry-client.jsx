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

const page = window.__PAGE__ || { page: 'home', props: { runs: [] } };
const C = PAGES[page.page] || HomePage;
hydrateRoot(document.getElementById('root'), React.createElement(C, page.props || {}));