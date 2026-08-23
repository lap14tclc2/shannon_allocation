// SSR + hydration smoke test for the bilingual portfolio-only QPort product.
import { JSDOM } from 'jsdom';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

const position = {
  symbol: 'FPT', shares: 200, average_cost: 65000, price: 70000,
  price_date: '2026-08-21', price_source: 'vnstock', cost_value: 13000000,
  market_value: 14000000, weight: 14000000 / 24000000, equity_weight: 1,
  unrealized_pnl: 1000000, unrealized_return: 1000000 / 13000000,
  risk_contribution: 1, erc_reference_weight: 1, status: 'HOLD',
};
const performance = {
  returns: { daily: 0.01, mtd: 0.03, ytd: 0.1, since_inception: 0.12 },
  annualized_twr: 0.14, xirr: 0.11, xirr_status: 'AVAILABLE', cashflow_history_quality: 'COMPLETE',
  history_status: 'SUFFICIENT', total_pnl: 1000000, accounting_return: 1000000 / 23000000,
  unrealized_pnl: 1000000, realized_pnl: 0, dividend_income: 200000, fees_and_taxes: 10000,
  net_external_contributions: 23000000, cash: 10000000, equity_value: 14000000, nav: 24000000,
  current_drawdown: -0.02, max_drawdown: -0.08, snapshot_count: 120, official_snapshot_count: 118,
  first_date: '2026-01-02', latest_date: '2026-08-21', best_day: 0.035, worst_day: -0.028,
  positive_day_ratio: 0.54,
  latest: { nav: 24000000 },
  series: [{ date: '2026-08-20', nav: 23700000 }, { date: '2026-08-21', nav: 24000000 }],
};
const risk = {
  status: 'VALID', volatility_63: 0.21, volatility_252: 0.24, volatility_ratio: 0.875,
  max_position_weight: 0.5833, max_equity_weight: 1, equity_hhi: 1,
  effective_positions: 1, effective_position_ratio: 1,
  average_correlation: null, max_correlation: null, diversification_ratio: 1,
  daily_var_95: -0.021, daily_cvar_95: -0.031, max_daily_loss: -0.049,
  downside_volatility: 0.19, positive_day_ratio: 0.54, return_observations: 240,
  largest_risk_symbol: 'FPT', largest_risk_contribution: 1, equal_risk_contribution: 1,
  risk_concentration_ratio: 1, risk_contribution_hhi: 1,
  risk_contributions: { FPT: 1 }, erc_reference_weights: { FPT: 1 },
  quality: { coverage_weight: 1, requested_symbols: 1, eligible_symbols: 1, missing_covariance_cells: 0 },
  methodology: { concentration_basis: 'equity_normalized' },
};
const health = {
  status: 'HEALTHY', flags: [], accounting_return: performance.accounting_return,
  performance_history_status: 'SUFFICIENT', current_drawdown: -0.02, max_drawdown: -0.08,
  effective_positions: 1, effective_position_ratio: 1, equity_hhi: 1, max_equity_weight: 1,
  average_correlation: null, max_correlation: null, diversification_ratio: 1,
  largest_risk_symbol: 'FPT', largest_risk_contribution: 1,
  daily_var_95: -0.021, daily_cvar_95: -0.031, risk_coverage: 1,
  official_snapshot_count: 118, cash_weight: 10 / 24,
};
const dashboard = {
  philosophy: 'BUY_AND_HOLD_INFORMATION_SYSTEM', today: '2026-08-23',
  portfolio: {
    cash: 10000000, equity_value: 14000000, nav: 24000000, cost_value: 13000000,
    total_pnl: 1000000, accounting_return: 1000000 / 23000000, unrealized_pnl: 1000000,
    realized_pnl: 0, reference_weights: { FPT: 1 }, positions: [position],
  },
  preferences: { cash_reserve_configured: true, cash_reserve: 5000000, reference_weights: { FPT: 1 } },
  performance_summary: performance,
  risk, health,
  market_data: { status: 'VALID', market_date: '2026-08-21', aligned: true, calendar_age_days: 2, provider: { provider: 'auto' } },
  data_lineage: { analytics: { status: 'UNVERIFIED', corporate_action_adjusted: null } },
  contribution_suggestions: { available_cash: 10000000, strategic_cash_reserve: 5000000, deployable_cash: 0, policy: 'EXPLICIT_REFERENCE_WEIGHT_DEFICITS', suggestions: [] },
};
const snapshots = [{ snapshot_date: '2026-08-21', official: true, data_quality: 'VALID', nav: 24000000, cash: 10000000, equity_value: 14000000, daily_pnl: 200000, daily_return: 0.0084, current_drawdown: -0.02, volatility_252: 0.24, positions: [position] }];
const transactions = [{ id: 1, event_date: '2026-01-02', event_type: 'POSITION_IMPORT', symbol: 'FPT', quantity: 200, price: 65000, fee: 0, tax: 0, amount: 0, created_by: 'local' }];

let pass = true;
function check(name, ok) { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`); if (!ok) pass = false; }

const ssrEntry = join(root, 'dist-ssr', 'ssr-entry.mjs');
check('SSR bundle exists', existsSync(ssrEntry));
let renderPage = null;
if (existsSync(ssrEntry)) {
  ({ renderPage } = await import(`file://${ssrEntry.replace(/\\/g, '/')}`));

  const portfolioHtml = renderPage('portfolio', { dashboard, locale: 'en' });
  check('portfolio renders live P/L', portfolioHtml.includes('Total P/L') && portfolioHtml.includes('1,000,000 VND'));
  check('portfolio renders cash management', portfolioHtml.includes('Cash management') && portfolioHtml.includes('Add cash'));
  check('portfolio renders corrected health', portfolioHtml.includes('Effective positions / ratio') && portfolioHtml.includes('Equity HHI') && portfolioHtml.includes('Largest risk contributor'));
  check('portfolio renders canonical valuation columns', portfolioHtml.includes('Cost value') && portfolioHtml.includes('Market value') && portfolioHtml.includes('Unrealized P/L'));
  check('portfolio renders AI export control', portfolioHtml.includes('Export for AI'));
  check('portfolio has no research navigation', !portfolioHtml.includes('Research Lab') && !portfolioHtml.includes('Optimizer'));

  const viPortfolio = renderPage('portfolio', { dashboard, locale: 'vi' });
  check('Vietnamese portfolio renders cash and health', viPortfolio.includes('Quản lý tiền mặt') && viPortfolio.includes('Vị thế hiệu dụng / tỷ lệ'));

  const perfHtml = renderPage('performance', { performance, locale: 'en' });
  check('performance renders P/L drawdown and history quality', perfHtml.includes('Total P/L') && perfHtml.includes('Current drawdown') && perfHtml.includes('History quality'));
  const viPerf = renderPage('performance', { performance, locale: 'vi' });
  check('Vietnamese performance renders', viPerf.includes('Hiệu suất') && viPerf.includes('Lãi/lỗ tổng'));

  const riskHtml = renderPage('risk', { risk, locale: 'en' });
  check('risk renders equity concentration and tail risk', riskHtml.includes('Equity HHI') && riskHtml.includes('Daily CVaR 95%') && riskHtml.includes('Largest risk contribution'));
  const viRisk = renderPage('risk', { risk, locale: 'vi' });
  check('Vietnamese risk renders expanded diagnostics', viRisk.includes('HHI phần cổ phiếu') && viRisk.includes('Chẩn đoán rủi ro đuôi'));

  const snapshotHtml = renderPage('snapshots', { snapshots, locale: 'en' });
  check('snapshots explain automatic usage', snapshotHtml.includes('automatic daily checkpoints') && snapshotHtml.includes('OFFICIAL'));
  const viSnapshot = renderPage('snapshots', { snapshots, locale: 'vi' });
  check('Vietnamese snapshots explain usage', viSnapshot.includes('Bạn không cần nhập thủ công') && viSnapshot.includes('CHÍNH THỨC'));

  const settingsHtml = renderPage('settings', { dashboard, locale: 'en' });
  check('settings explain cash and target policy', settingsHtml.includes('Cash policy') && settingsHtml.includes('Strategic cash reserve') && settingsHtml.includes('Optional target-weight guidance'));
  const viSettings = renderPage('settings', { dashboard, locale: 'vi' });
  check('Vietnamese settings explain policy', viSettings.includes('Chính sách tiền mặt') && viSettings.includes('Tham chiếu tỷ trọng không bắt buộc'));

  const txHtml = renderPage('transactions', { transactions, today: '2026-08-23', locale: 'en' });
  check('transactions render validation guidance', txHtml.includes('validated twice') && txHtml.includes('Full VND/share'));
  check('transactions still render immutable ledger', txHtml.includes('Immutable event history') && txHtml.includes('Opening position import'));
  const guideHtml = renderPage('guide', { locale: 'en' });
  check('guide explains data integrity', guideHtml.includes('Data integrity rules') && guideHtml.includes('MONITOR means no explicit strategic target'));
  check('removed research page cannot render', renderPage('research', { locale: 'en' }) === '');
  check('removed optimizer page cannot render', renderPage('optimizer_list', { locale: 'en' }) === '');
}

const clientJs = join(root, 'dist', 'assets', 'client.js');
check('client bundle exists', existsSync(clientJs));
if (existsSync(clientJs) && renderPage) {
  const dom = new JSDOM('<html><body><div id="root"></div></body></html>', { url: 'http://localhost:8080/', pretendToBeVisual: true });
  const { window } = dom;
  globalThis.window = window; globalThis.document = window.document;
  Object.defineProperty(globalThis, 'navigator', { value: window.navigator, configurable: true });
  globalThis.HTMLElement = window.HTMLElement; globalThis.MutationObserver = window.MutationObserver;
  globalThis.requestAnimationFrame = window.requestAnimationFrame?.bind(window) || ((cb) => setTimeout(cb, 16));
  globalThis.fetch = async () => ({ ok: true, json: async () => ({}) });
  const errors = []; window.addEventListener('error', (e) => errors.push(e.message));
  window.document.getElementById('root').innerHTML = renderPage('portfolio', { dashboard, locale: 'vi' });
  window.__PAGE__ = { page: 'portfolio', props: { dashboard, locale: 'vi' } };
  eval(readFileSync(clientJs, 'utf8')); // eslint-disable-line no-eval
  await new Promise((r) => setTimeout(r, 300));
  const pageText = window.document.getElementById('root').textContent;
  check('Vietnamese hydration rendered', pageText.includes('FPT') && pageText.includes('Danh mục'));
  check('no hydration errors', errors.length === 0);
}

console.log(pass ? '\nSMOKE TEST PASSED' : '\nSMOKE TEST FAILED');
process.exit(pass ? 0 : 1);
