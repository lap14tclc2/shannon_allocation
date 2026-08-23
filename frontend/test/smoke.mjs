// SSR + hydration smoke test for the buy-and-hold operational product.
import { JSDOM } from 'jsdom';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

const dashboard = {
  philosophy: 'BUY_AND_HOLD_INFORMATION_SYSTEM',
  portfolio: {
    cash: 10000000,
    equity_value: 14000000,
    nav: 24000000,
    realized_pnl: 0,
    reference_weights: { FPT: 1 },
    positions: [{
      symbol: 'FPT', shares: 200, average_cost: 65000, price: 70000,
      price_date: '2026-08-21', price_source: 'vnstock', market_value: 14000000,
      weight: 14000000 / 24000000, unrealized_pnl: 1000000,
      unrealized_return: 1000000 / 13000000, risk_contribution: 1,
      status: 'HOLD',
    }],
  },
  latest_snapshot: {
    snapshot_date: '2026-08-21', nav: 24000000, total_pnl: 1000000,
    current_drawdown: -0.02, max_drawdown: -0.05,
  },
  risk: { status: 'VALID', volatility_63: 0.21, volatility_252: 0.24, max_position_weight: 0.5833, hhi: 0.34 },
  market_data: { status: 'VALID', provider: { provider: 'auto' } },
  contribution_suggestions: { available_cash: 10000000, policy: 'REFERENCE_WEIGHT_DEFICITS', suggestions: [] },
  invariants: ['price movement never changes shares', 'only explicit ledger events change holdings or cash'],
};

const fixtures = {
  transactions: [{ id: 1, event_date: '2026-01-02', event_type: 'POSITION_IMPORT', symbol: 'FPT', quantity: 200, price: 65000, fee: 0, tax: 0, amount: 0, created_by: 'local' }],
  performance: {
    returns: { daily: 0.01, mtd: 0.03, ytd: 0.1, since_inception: 0.12 },
    xirr: 0.11, realized_pnl: 0, dividend_income: 200000, fees_and_taxes: 10000,
    net_external_contributions: 23000000, latest: { nav: 24000000 },
    series: [{ date: '2026-08-20', nav: 23700000 }, { date: '2026-08-21', nav: 24000000 }],
  },
  risk: {
    status: 'VALID', volatility_63: 0.21, volatility_252: 0.24, max_position_weight: 0.58,
    hhi: 0.34, risk_contributions: { FPT: 1 }, erc_reference_weights: { FPT: 1 },
    quality: { coverage_weight: 1, requested_symbols: 1, eligible_symbols: 1, missing_covariance_cells: 0 },
  },
  snapshots: [{ snapshot_date: '2026-08-21', official: true, data_quality: 'VALID', nav: 24000000, cash: 10000000, equity_value: 14000000, daily_pnl: 200000, daily_return: 0.0084, current_drawdown: -0.02, volatility_252: 0.24, positions: [{ symbol: 'FPT' }] }],
};

let pass = true;
function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) pass = false;
}

const ssrEntry = join(root, 'dist-ssr', 'ssr-entry.mjs');
check('SSR bundle exists', existsSync(ssrEntry));
let renderPage = null;
if (existsSync(ssrEntry)) {
  ({ renderPage } = await import(`file://${ssrEntry.replace(/\\/g, '/')}`));

  const portfolioHtml = renderPage('portfolio', { dashboard });
  check('portfolio SSR is product landing', portfolioHtml.includes('Portfolio') && portfolioHtml.includes('BUY &amp; HOLD'));
  check('portfolio SSR renders holdings', portfolioHtml.includes('FPT') && portfolioHtml.includes('Holdings'));

  const txHtml = renderPage('transactions', { transactions: fixtures.transactions, today: '2026-08-23' });
  check('transactions SSR renders immutable ledger', txHtml.includes('Immutable event history') && txHtml.includes('POSITION_IMPORT'));

  const perfHtml = renderPage('performance', { performance: fixtures.performance });
  check('performance SSR renders TWR/XIRR', perfHtml.includes('TWR since inception') && perfHtml.includes('XIRR'));

  const riskHtml = renderPage('risk', { risk: fixtures.risk });
  check('risk SSR is informational', riskHtml.includes('Information only') && riskHtml.includes('ERC reference'));

  const snapshotsHtml = renderPage('snapshots', { snapshots: fixtures.snapshots });
  check('snapshot SSR renders official state', snapshotsHtml.includes('OFFICIAL') && snapshotsHtml.includes('2026-08-21'));

  const settingsHtml = renderPage('settings', { dashboard });
  check('settings SSR is strategic-only', settingsHtml.includes('Strategic reference weights') && settingsHtml.includes('no annual allocation'));

  const researchHtml = renderPage('research', { experiments: [], runs: [] });
  check('research SSR shows hard boundary', researchHtml.includes('Research Lab') && researchHtml.includes('Proposal only'));
}

const clientJs = join(root, 'dist', 'assets', 'client.js');
check('client bundle exists', existsSync(clientJs));
if (existsSync(clientJs) && renderPage) {
  const dom = new JSDOM('<html><head></head><body><div id="root"></div></body></html>', {
    url: 'http://localhost:8080/',
    pretendToBeVisual: true,
  });
  const { window } = dom;
  globalThis.window = window;
  globalThis.document = window.document;
  Object.defineProperty(globalThis, 'navigator', { value: window.navigator, configurable: true });
  globalThis.HTMLElement = window.HTMLElement;
  globalThis.MutationObserver = window.MutationObserver;
  globalThis.requestAnimationFrame = window.requestAnimationFrame?.bind(window) || ((cb) => setTimeout(cb, 16));
  globalThis.fetch = async () => ({ ok: true, json: async () => ({}) });

  const errors = [];
  window.addEventListener('error', (e) => errors.push(e.message));
  const html = renderPage('portfolio', { dashboard });
  window.document.getElementById('root').innerHTML = html;
  window.__PAGE__ = { page: 'portfolio', props: { dashboard } };

  eval(readFileSync(clientJs, 'utf8')); // eslint-disable-line no-eval
  await new Promise((r) => setTimeout(r, 300));
  const text = window.document.getElementById('root').textContent;
  check('portfolio hydration rendered', text.includes('FPT') && text.includes('Portfolio'));
  check('no hydration errors', errors.length === 0);
  if (errors.length) console.log('errors:', errors);
}

console.log(pass ? '\nSMOKE TEST PASSED' : '\nSMOKE TEST FAILED');
process.exit(pass ? 0 : 1);
