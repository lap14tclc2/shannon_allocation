// SSR + hydration smoke test.
// 1. Imports the built SSR bundle and asserts renderPage() produces HTML.
// 2. Loads the client bundle in jsdom and asserts hydration runs without errors.
import { JSDOM } from 'jsdom';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

const fixtures = {
  runs: [
    { run_id: 'r1', generated_at: '2026-08-21T19:06:01' },
    { run_id: 'r0', generated_at: '2026-08-20T10:00:00' },
  ],
  meta: {
    run_id: 'r1',
    params: {
      initial_balance: 200000000,
      annual_deposit: 20000000,
      allocation_frequency: 'quarterly',
      lookback_days: 252,
    },
  },
  index: {
    combinations: [
      {
        rank: 1,
        slug: 'HAG_LPB_PGB_TCB_VPB_VTP',
        symbols: 'HAG LPB PGB TCB VPB VTP',
        n_symbols: 6,
        n_allocations: 19,
        score: 45.42,
        final_nav: 518824250,
        twr_annualized_pct: 12.53,
        xirr_pct: 12.73,
        sortino: 1.23,
        sharpe: 0.872,
        max_drawdown_pct: -36.6,
      },
    ],
  },
  combo: {
    symbols: ['HAG', 'LPB', 'PGB', 'TCB', 'VPB', 'VTP'],
    score: 45.42,
    final_nav: 518824250,
    absolute_profit: 218824250,
    twr_annualized_pct: 12.53,
    xirr_pct: 12.73,
    sortino: 1.233,
    calmar: 0.34,
    annual_returns: { 2022: -13.4, 2023: 34.55 },
    total_return_pct: 72.94,
    cagr_pct: 11.85,
    annualized_volatility_pct: 27.2,
    sharpe: 0.717,
    max_drawdown_pct: -56.66,
    nav_history: [
      ['2022-01-04', 220000000],
      ['2022-04-01', 220218607],
      ['2026-07-01', 518824250],
    ],
    allocations: [
      {
        year: 2022,
        quarter: 1,
        allocation_date: '2022-01-04',
        initial_allocation: true,
        deposit_amount: 20000000,
        rebalances_since_last_allocation: 0,
        nav_before: 200000000,
        cash_before: 200000000,
        nav_after: 220000000,
        cash_after: 0,
        erc: {
          observations: 98,
          window_start: '2021-08-16',
          window_end: '2021-12-31',
          portfolio_risk: 0.31,
          portfolio_variance: 0.096,
          erc_error: 1e-8,
          weights: { HAG: 0.2, LPB: 0.17, PGB: 0.16, TCB: 0.15, VPB: 0.15, VTP: 0.17 },
        },
        targets: { HAG: 0.2, LPB: 0.17, PGB: 0.16, TCB: 0.15, VPB: 0.15, VTP: 0.17 },
        holdings_before: [],
        recommendations: [
          {
            symbol: 'HAG',
            current_weight: 0,
            target_weight: 0.2,
            band: 'HARD',
            drift: -0.2,
            recommendation: 'BUY',
            target_trade_amount: 44000000,
            funded_trade_amount: 44000000,
            shares_to_trade: 10000,
          },
        ],
        holdings_after: [{ symbol: 'HAG', shares: 10000, price: 4400, value: 44000000, weight: 0.2 }],
      },
    ],
  },
};

let pass = true;
function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) pass = false;
}

// ---- 1. SSR rendering (react-dom/server) ----
const ssrEntry = join(root, 'dist-ssr', 'ssr-entry.mjs');
check('SSR bundle exists', existsSync(ssrEntry));
let renderPage = null;
if (existsSync(ssrEntry)) {
  ({ renderPage } = await import(`file://${ssrEntry.replace(/\\/g, '/')}`));

  const homeHtml = renderPage('home', { runs: fixtures.runs });
  check('home SSR renders Dynamic Alpha optimizer landing page', homeHtml.includes('Growth Optimizer') && homeHtml.includes('Dynamic Alpha + allocation'));

  const optimizerHtml = renderPage('optimizer_list', { experiments: [] });
  check('optimizer SSR renders the same primary workflow', optimizerHtml.includes('Growth Optimizer') && optimizerHtml.includes('Dynamic Alpha + allocation'));

  const runHtml = renderPage('run', { meta: fixtures.meta, index: fixtures.index });
  check('run SSR renders ranking row', runHtml.includes('HAG') && runHtml.includes('45.4'));
  check('run SSR shows score', runHtml.includes('Score') || runHtml.includes('45.4'));

  const comboHtml = renderPage('combo', { combo: fixtures.combo, runId: 'r1' });
  check('combo SSR renders symbols', comboHtml.includes('HAG') && comboHtml.includes('VPB'));
  check('combo SSR renders score metric', comboHtml.includes('45.42'));
  check('combo SSR renders allocation date', comboHtml.includes('2022-01-04'));
  check('combo SSR renders equity chart svg', comboHtml.includes('<svg') || comboHtml.includes('viewBox'));
}

// ---- 2. Hydration (client bundle in jsdom) ----
const clientJs = join(root, 'dist', 'assets', 'client.js');
check('client bundle exists', existsSync(clientJs));
if (existsSync(clientJs)) {
  const dom = new JSDOM('<html><head></head><body><div id="root"></div></body></html>', {
    url: 'http://localhost:8090/runs/r1/combinations/HAG_LPB_PGB_TCB_VPB_VTP',
    pretendToBeVisual: true,
  });
  const { window } = dom;
  globalThis.window = window;
  globalThis.document = window.document;
  Object.defineProperty(globalThis, 'navigator', { value: window.navigator, configurable: true });
  globalThis.HTMLElement = window.HTMLElement;
  globalThis.MutationObserver = window.MutationObserver;
  globalThis.requestAnimationFrame = window.requestAnimationFrame?.bind(window) || ((cb) => setTimeout(cb, 16));

  const errors = [];
  window.addEventListener('error', (e) => errors.push(e.message));
  const comboHtml = renderPage('combo', { combo: fixtures.combo, runId: 'r1' });
  window.document.getElementById('root').innerHTML = comboHtml;
  window.__PAGE__ = { page: 'combo', props: { combo: fixtures.combo, runId: 'r1' } };

  eval(readFileSync(clientJs, 'utf8')); // eslint-disable-line no-eval
  await new Promise((r) => setTimeout(r, 500));

  const text = window.document.getElementById('root').textContent;
  check('hydration rendered content', text.length > 0);
  check('hydration shows symbols', text.includes('HAG') && text.includes('VPB'));
  check('hydration shows allocation', text.includes('2022-01-04'));
  check('no hydration errors', errors.length === 0);
  if (errors.length) console.log('errors:', errors);
}

console.log(pass ? '\nSMOKE TEST PASSED' : '\nSMOKE TEST FAILED');
process.exit(pass ? 0 : 1);
