import {
  getPortfolioDashboard,
  getPortfolioPerformance,
  getPortfolioRisk,
  listPortfolioSnapshots,
  listPortfolioTransactions,
} from './api.js';

const EXPORT_SCHEMA = 'qport-ai-export-v1';
const MAX_SNAPSHOTS = 90;

function finite(value) {
  const n = Number(value);
  return value == null || !Number.isFinite(n) ? null : n;
}

function money(value) {
  const n = finite(value);
  return n == null ? '-' : `${n.toLocaleString('en-US', { maximumFractionDigits: 2 })} VND`;
}

function pct(value) {
  const n = finite(value);
  return n == null ? '-' : `${(n * 100).toFixed(2)}%`;
}

function num(value, digits = 4) {
  const n = finite(value);
  return n == null ? '-' : n.toFixed(digits);
}

function cell(value) {
  return String(value ?? '-').replaceAll('|', '\\|').replaceAll('\n', ' ');
}

function clean(value) {
  if (Array.isArray(value)) return value.map(clean);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, clean(item)]));
  }
  if (typeof value === 'number' && !Number.isFinite(value)) return null;
  return value;
}

function table(headers, rows) {
  if (!rows.length) return '_No data._';
  const head = `| ${headers.map(cell).join(' | ')} |`;
  const divider = `| ${headers.map(() => '---').join(' | ')} |`;
  const body = rows.map((row) => `| ${row.map(cell).join(' | ')} |`).join('\n');
  return `${head}\n${divider}\n${body}`;
}

function summaryRows(portfolio, performance) {
  return [
    ['NAV', money(portfolio.nav)],
    ['Equity value', money(portfolio.equity_value)],
    ['Cash', money(portfolio.cash)],
    ['Cash weight', portfolio.nav ? pct(Number(portfolio.cash || 0) / Number(portfolio.nav)) : '-'],
    ['Cost value', money(portfolio.cost_value)],
    ['Net external contributions', money(portfolio.net_external_contributions)],
    ['Total P/L', money(portfolio.total_pnl)],
    ['Total return', pct(portfolio.total_return)],
    ['Unrealized P/L', money(portfolio.unrealized_pnl)],
    ['Realized P/L', money(portfolio.realized_pnl)],
    ['Dividend income', money(portfolio.dividend_income)],
    ['Fees & taxes', money(portfolio.fees_and_taxes)],
    ['Current drawdown', pct(performance.current_drawdown)],
    ['Maximum drawdown', pct(performance.max_drawdown)],
  ];
}

export function buildAIExportMarkdown({ dashboard, performance, risk, snapshots, transactions, generatedAt }) {
  const portfolio = dashboard?.portfolio || {};
  const positions = portfolio.positions || [];
  const health = dashboard?.health || {};
  const market = dashboard?.market_data || {};
  const suggestions = dashboard?.contribution_suggestions || {};
  const refs = portfolio.reference_weights || {};
  const orderedSnapshots = [...(snapshots || [])]
    .filter((s) => s?.official)
    .sort((a, b) => String(a.snapshot_date).localeCompare(String(b.snapshot_date)))
    .slice(-MAX_SNAPSHOTS);
  const ledger = [...(transactions || [])].sort((a, b) => {
    const byDate = String(a.event_date).localeCompare(String(b.event_date));
    return byDate || Number(a.id || 0) - Number(b.id || 0);
  });

  const provider = market.provider || {};
  const asOf = performance?.latest_date
    || positions.map((p) => p.price_date).filter(Boolean).sort().at(-1)
    || dashboard?.today
    || null;

  const holdingsTable = table(
    ['Ticker', 'Shares', 'Avg cost', 'Price', 'Cost value', 'Market value', 'Unrealized P/L', 'Return', 'NAV weight', 'Risk contribution', 'ERC reference', 'Status', 'Price date', 'Source'],
    positions.map((p) => [
      p.symbol,
      num(p.shares, 4),
      money(p.average_cost),
      money(p.price),
      money(p.cost_value),
      money(p.market_value),
      money(p.unrealized_pnl),
      pct(p.unrealized_return),
      pct(p.weight),
      pct(p.risk_contribution),
      pct(p.erc_reference_weight),
      p.status || '-',
      p.price_date || '-',
      p.price_source || '-',
    ]),
  );

  const healthTable = table(['Metric', 'Value'], [
    ['Health status', health.status || '-'],
    ['Risk status', risk?.status || '-'],
    ['63D volatility', pct(risk?.volatility_63)],
    ['252D volatility', pct(risk?.volatility_252)],
    ['Largest position', pct(risk?.max_position_weight)],
    ['HHI concentration', num(risk?.hhi)],
    ['Effective positions', num(risk?.effective_positions, 2)],
    ['Average correlation', num(risk?.average_correlation)],
    ['Maximum correlation', num(risk?.max_correlation)],
    ['Diversification ratio', num(risk?.diversification_ratio)],
    ['Largest risk contributor', risk?.largest_risk_symbol || '-'],
    ['Largest risk contribution', pct(risk?.largest_risk_contribution)],
    ['Risk contribution HHI', num(risk?.risk_contribution_hhi)],
    ['Daily VaR 95%', pct(risk?.daily_var_95)],
    ['Daily CVaR 95%', pct(risk?.daily_cvar_95)],
    ['Worst observed daily return', pct(risk?.max_daily_loss)],
    ['Downside volatility', pct(risk?.downside_volatility)],
    ['Positive-day ratio', pct(risk?.positive_day_ratio)],
    ['Risk data coverage', pct(risk?.quality?.coverage_weight)],
    ['Return observations', risk?.return_observations ?? '-'],
  ]);

  const performanceTable = table(['Metric', 'Value'], [
    ['Tracking start', performance?.first_date || '-'],
    ['Latest official date', performance?.latest_date || '-'],
    ['Stored snapshots', performance?.snapshot_count ?? 0],
    ['Official snapshots', performance?.official_snapshot_count ?? 0],
    ['Daily TWR', pct(performance?.returns?.daily)],
    ['MTD TWR', pct(performance?.returns?.mtd)],
    ['YTD TWR', pct(performance?.returns?.ytd)],
    ['TWR since inception', pct(performance?.returns?.since_inception)],
    ['Annualized TWR', pct(performance?.annualized_twr)],
    ['XIRR', pct(performance?.xirr)],
    ['Best day', pct(performance?.best_day)],
    ['Worst day', pct(performance?.worst_day)],
    ['Positive-day ratio', pct(performance?.positive_day_ratio)],
  ]);

  const referenceTable = table(
    ['Ticker', 'Strategic reference weight'],
    Object.entries(refs).sort(([a], [b]) => a.localeCompare(b)).map(([symbol, weight]) => [symbol, pct(weight)]),
  );

  const suggestionTable = table(
    ['Ticker', 'Action', 'Suggested amount', 'Current weight', 'Reference/target weight'],
    (suggestions.suggestions || []).map((s) => [s.symbol, s.action || 'ADD', money(s.amount), pct(s.current_weight), pct(s.target_weight)]),
  );

  const ledgerTable = table(
    ['ID', 'Date', 'Type', 'Ticker', 'Quantity', 'Price', 'Amount', 'Fee', 'Tax', 'Ratio', 'Note', 'Created by'],
    ledger.map((e) => [
      e.id ?? '-', e.event_date || '-', e.event_type || '-', e.symbol || '-', num(e.quantity, 4), money(e.price), money(e.amount), money(e.fee), money(e.tax), num(e.ratio, 6), e.note || '-', e.created_by || '-',
    ]),
  );

  const snapshotTable = table(
    ['Date', 'NAV', 'Cash', 'Equity', 'Daily P/L', 'Daily return', 'TWR index', 'Drawdown', 'Data quality'],
    orderedSnapshots.map((s) => [
      s.snapshot_date, money(s.nav), money(s.cash), money(s.equity_value), money(s.daily_pnl), pct(s.daily_return), num(s.twr_index, 6), pct(s.current_drawdown), s.data_quality || '-',
    ]),
  );

  const flags = health.flags || [];
  const flagsText = flags.length
    ? flags.map((f) => `- **${cell(f.level || 'WARNING')} / ${cell(f.code || 'UNKNOWN')}**: ${cell(f.message || '')}`).join('\n')
    : '- None.';

  const payload = clean({
    schema_version: EXPORT_SCHEMA,
    generated_at: generatedAt,
    as_of: asOf,
    currency: 'VND',
    price_unit: 'full VND per share',
    dashboard,
    performance: { ...performance, series: orderedSnapshots },
    risk,
    transactions: ledger,
    recent_official_snapshots: orderedSnapshots,
  });

  return `# QPort AI Context Export\n\n` +
    `> Generated for direct AI analysis. This file is read-only evidence from QPort; it does not create or imply a trade. Missing values are shown as null or \`-\`.\n\n` +
    `## Export metadata\n\n` +
    table(['Field', 'Value'], [
      ['Schema', EXPORT_SCHEMA],
      ['Generated at', generatedAt],
      ['As of', asOf || '-'],
      ['Currency', 'VND'],
      ['Price unit', 'Full VND per share'],
      ['Portfolio philosophy', dashboard?.philosophy || 'BUY_AND_HOLD_INFORMATION_SYSTEM'],
      ['Market data status', market.status || '-'],
      ['Market provider', provider.provider || provider.name || JSON.stringify(provider)],
    ]) +
    `\n\n## Current portfolio accounting\n\n${table(['Metric', 'Value'], summaryRows(portfolio, performance || {}))}` +
    `\n\n## Holdings\n\n${holdingsTable}` +
    `\n\n## Portfolio health and risk\n\n${healthTable}` +
    `\n\n### Health warnings\n\n${flagsText}` +
    `\n\n## Performance\n\n${performanceTable}` +
    `\n\n## Strategic reference weights\n\n${referenceTable}` +
    `\n\n## Current BUY-only cash deployment information\n\n` +
    `Available cash: **${money(suggestions.available_cash)}**  \n` +
    `Deployable cash reported by current policy: **${money(suggestions.deployable_cash)}**  \n` +
    `Policy: **${cell(suggestions.policy || '-')}**\n\n${suggestionTable}` +
    `\n\n## Immutable ledger\n\n${ledgerTable}` +
    `\n\n## Recent official daily snapshots (up to ${MAX_SNAPSHOTS})\n\n${snapshotTable}` +
    `\n\n## Interpretation rules for AI\n\n` +
    `- Treat the immutable ledger as the source of truth for shares and cash.\n` +
    `- Price movement, risk metrics, model output and time do not change holdings.\n` +
    `- Total P/L is accounting output; a loss alone is not a reason to average down.\n` +
    `- Drawdown is measured from QPort's tracked TWR history. Always consider the tracking start and official snapshot count.\n` +
    `- Risk metrics are informational. ERC reference weights are not mandatory allocation targets.\n` +
    `- BUY-only cash suggestions are informational and are not executed automatically.\n` +
    `- Distinguish current NAV weights from equity-normalized concentration when interpreting cash-heavy portfolios.\n` +
    `- Do not infer missing fundamentals or market data. State explicitly when additional data is required.\n` +
    `\n## Machine-readable payload\n\n` +
    `\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\`\n`;
}

export async function downloadAIExport() {
  const [dashboard, performance, risk, snapshots, transactions] = await Promise.all([
    getPortfolioDashboard(),
    getPortfolioPerformance(),
    getPortfolioRisk(),
    listPortfolioSnapshots(),
    listPortfolioTransactions(),
  ]);
  const now = new Date();
  const generatedAt = now.toISOString();
  const markdown = buildAIExportMarkdown({ dashboard, performance, risk, snapshots, transactions, generatedAt });
  const date = String(performance?.latest_date || dashboard?.today || generatedAt.slice(0, 10));
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `qport-ai-export-${date}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return anchor.download;
}
