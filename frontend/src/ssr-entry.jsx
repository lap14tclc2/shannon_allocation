// Server-side render entry (bundled by Vite for Node via `npm run build:ssr`).
import React from 'react';
import { renderToString } from 'react-dom/server';
import HomePage from './pages/HomePage.jsx';
import RunPage from './pages/RunPage.jsx';
import ComboPage from './pages/ComboPage.jsx';
import OptimizerListPage from './pages/OptimizerListPage.jsx';
import OptimizerDetailPage from './pages/OptimizerDetailPage.jsx';

const PAGES = {
  home: HomePage,
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