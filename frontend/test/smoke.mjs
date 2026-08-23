// SSR + hydration smoke test for the bilingual buy-and-hold operational product.
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
      price_date: '2026-08-21', price_source: 'vnstock', cost_value: 13000000,
      market_value: 14000000, weight: 14000000 / 24000000,
      unrealized_pnl: 1000000, unrealized_return: 1000000 / 13000000,
      risk_contribution: 1, status: 'HOLD',
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

  const portfolioHtml = renderPage('portfolio', { dashboard, locale: 'en' });
  check('English portfolio SSR is product landing', portfolioHtml.includes('Portfolio') && portfolioHtml.includes('BUY &amp; HOLD'));
  check('English portfolio SSR renders holdings', portfolioHtml.includes('FPT') && portfolioHtml.includes('Holdings'));
  check('portfolio SSR renders explicit valuation columns', portfolioHtml.includes('Cost value') && portfolioHtml.includes('Market value') && portfolioHtml.includes('Unrealized P/L'));
  check('portfolio SSR renders canonical VND values', portfolioHtml.includes('65,000 VND') && portfolioHtml.includes('70,000 VND') && portfolioHtml.includes('14,000,000 VND'));
  check('language switch renders EN and VI', portfolioHtml.includes('>EN<') && portfolioHtml.includes('>VI<'));

  const viPortfolioHtml = renderPage('portfolio', { dashboard, locale: 'vi' });
  check('Vietnamese portfolio SSR renders translated labels', viPortfolioHtml.includes('Danh mục') && viPortfolioHtml.includes('Giá trị vốn') && viPortfolioHtml.includes('Lãi/lỗ chưa thực hiện'));
  check('Vietnamese portfolio SSR translates status', viPortfolioHtml.includes('GIỮ') && viPortfolioHtml.includes('HỢP LỆ'));

  const txHtml = renderPage('transactions', { transactions: fixtures.transactions, today: '2026-08-23', locale: 'en' });
  check('English transactions SSR renders immutable ledger', txHtml.includes('Immutable event history') && txHtml.includes('Opening position import'));
  const viTxHtml = renderPage('transactions', { transactions: fixtures.transactions, today: '2026-08-23', locale: 'vi' });
  check('Vietnamese transactions SSR renders immutable ledger', viTxHtml.includes('Lịch sử sự kiện bất biến') && viTxHtml.includes('Nhập vị thế ban đầu'));

  const perfHtml = renderPage('performance', { performance: fixtures.performance, locale: 'en' });
  check('performance SSR renders TWR/XIRR', perfHtml.includes('TWR since inception') && perfHtml.includes('XIRR'));
  const viPerfHtml = renderPage('performance', { performance: fixtures.performance, locale: 'vi' });
  check('Vietnamese performance SSR renders translated headings', viPerfHtml.includes('Hiệu suất') && viPerfHtml.includes('Lịch sử NAV chính thức'));

  const riskHtml = renderPage('risk', { risk: fixtures.risk, locale: 'en' });
  check('risk SSR is informational', riskHtml.includes('Information only') && riskHtml.includes('ERC reference'));
  const viRiskHtml = renderPage('risk', { risk: fixtures.risk, locale: 'vi' });
  check('Vietnamese risk SSR is informational', viRiskHtml.includes('Rủi ro') && viRiskHtml.includes('Chỉ mang tính thông tin'));

  const snapshotsHtml = renderPage('snapshots', { snapshots: fixtures.snapshots, locale: 'en' });
  check('snapshot SSR renders official state', snapshotsHtml.includes('OFFICIAL') && snapshotsHtml.includes('2026-08-21'));
  const viSnapshotsHtml = renderPage('snapshots', { snapshots: fixtures.snapshots, locale: 'vi' });
  check('Vietnamese snapshot SSR renders official state', viSnapshotsHtml.includes('CHÍNH THỨC') && viSnapshotsHtml.includes('Ảnh chụp hằng ngày'));

  const settingsHtml = renderPage('settings', { dashboard, locale: 'en' });
  check('settings SSR is strategic-only', settingsHtml.includes('Strategic reference weights') && settingsHtml.includes('no annual allocation'));
  const viSettingsHtml = renderPage('settings', { dashboard, locale: 'vi' });
  check('Vietnamese settings SSR renders translated controls', viSettingsHtml.includes('Tỷ trọng tham chiếu chiến lược') && viSettingsHtml.includes('Cài đặt'));

  const guideHtml = renderPage('guide', { locale: 'en' });
  check('English guide SSR renders start-to-finish workflow', guideHtml.includes('Start-to-finish guide') && guideHtml.includes('Install and start'));
  const viGuideHtml = renderPage('guide', { locale: 'vi' });
  check('Vietnamese guide SSR renders start-to-finish workflow', viGuideHtml.includes('Hướng dẫn từ đầu đến cuối') && viGuideHtml.includes('Cài đặt và khởi động'));

  const researchHtml = renderPage('research', { experiments: [], runs: [], locale: 'en' });
  check('research SSR shows hard boundary', researchHtml.includes('Research Lab') && researchHtml.includes('Proposal only'));
  const viResearchHtml = renderPage('research', { experiments: [], runs: [], locale: 'vi' });
  check('Vietnamese research SSR shows hard boundary', viResearchHtml.includes('Phòng nghiên cứu') && viResearchHtml.includes('Chỉ là đề xuất'));
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
  const html = renderPage('portfolio', { dashboard, locale: 'vi' });
  window.document.getElementById('root').innerHTML = html;
  window.__PAGE__ = { page: 'portfolio', props: { dashboard, locale: 'vi' } };

  eval(readFileSync(clientJs, 'utf8')); // eslint-disable-line no-eval
  await new Promise((r) => setTimeout(r, 300));
  const text = window.document.getElementById('root').textContent;
  check('Vietnamese portfolio hydration rendered', text.includes('FPT') && text.includes('Danh mục'));
  check('no hydration errors', errors.length === 0);
  if (errors.length) console.log('errors:', errors);
}

console.log(pass ? '\nSMOKE TEST PASSED' : '\nSMOKE TEST FAILED');
process.exit(pass ? 0 : 1);
