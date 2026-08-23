import {
  getActivityLog,
  getLatestDividend,
  getPortfolioDashboard,
  getPortfolioOperations,
  getPortfolioPerformance,
  getPortfolioRisk,
  listPortfolioSnapshots,
  listPortfolioTransactionAudit,
  listPortfolioTransactions,
  logClientActivity,
} from './api.js';

const EXPORT_SCHEMA = 'qport-ai-export-v5';

function finite(value) { const n = Number(value); return value == null || !Number.isFinite(n) ? null : n; }
function money(value) { const n = finite(value); return n == null ? '-' : `${n.toLocaleString('en-US', { maximumFractionDigits: 2 })} VND`; }
function pct(value) { const n = finite(value); return n == null ? '-' : `${(n * 100).toFixed(2)}%`; }
function num(value, digits = 4) { const n = finite(value); return n == null ? '-' : n.toFixed(digits); }
function cell(value) { return String(value ?? '-').replaceAll('|', '\\|').replaceAll('\n', ' '); }
function clean(value) {
  if (Array.isArray(value)) return value.map(clean);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, clean(v)]));
  return typeof value === 'number' && !Number.isFinite(value) ? null : value;
}
function table(headers, rows) {
  if (!rows.length) return '_No data._';
  return `| ${headers.map(cell).join(' | ')} |\n| ${headers.map(() => '---').join(' | ')} |\n${rows.map(r => `| ${r.map(cell).join(' | ')} |`).join('\n')}`;
}
function metadataSummary(metadata = {}) {
  try { return JSON.stringify(clean(metadata)); } catch { return '{}'; }
}

export function buildAIExportMarkdown({
  dashboard = {}, performance = {}, risk = {}, operations = {}, activity = {},
  snapshots = [], transactions = [], corrections = [], dividends = {}, generatedAt,
}) {
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const market = dashboard.market_data || {};
  const prefs = dashboard.preferences || {};
  const suggestions = dashboard.contribution_suggestions || {};
  const orderedSnapshots = [...snapshots].filter(Boolean).sort((a, b) => String(a.snapshot_date).localeCompare(String(b.snapshot_date)));
  const ledger = [...transactions].sort((a, b) => String(a.event_date).localeCompare(String(b.event_date)) || Number(a.id || 0) - Number(b.id || 0));
  const activityRows = activity.logs || [];

  const holdings = table(
    ['Ticker','Shares','Avg cost','Price','Cost value','Market value','P/L','NAV weight','Equity weight','Risk contrib.','Status'],
    positions.map(p => [String(p.symbol || '').toUpperCase(),num(p.shares),money(p.average_cost),money(p.price),money(p.cost_value),money(p.market_value),money(p.unrealized_pnl),pct(p.weight),pct(p.equity_weight),pct(p.risk_contribution),p.status]),
  );
  const lots = table(
    ['Lot','Ticker','Broker','Account','Acquired','Original qty','Remaining qty','Unit cost','Cost basis'],
    (operations.tax_lots || []).map(l => [l.lot_id,String(l.symbol || '').toUpperCase(),l.broker_code || 'UNASSIGNED',l.account_id || 'PRIMARY',l.acquisition_date,num(l.original_quantity),num(l.remaining_quantity),money(l.unit_cost),money(l.cost_basis)]),
  );
  const brokerDividends = table(
    ['Ticker','Broker','Account','Stock dividend shares received','Cash gross','Cash tax','Cash net','Last received','Ledger event IDs'],
    (operations.dividend_receipts_by_broker || []).map(r => [
      String(r.symbol || '').toUpperCase(), r.broker_code || 'UNASSIGNED', r.account_id || 'PRIMARY',
      num(r.stock_dividend_shares_received), money(r.cash_dividend_gross), money(r.cash_dividend_tax),
      money(r.cash_dividend_net), r.last_received_date || '-', (r.event_ids || []).join(','),
    ]),
  );
  const settlements = table(
    ['Event','Ticker','Broker','Account','Side','Trade date','Settlement date','Status','Cash effect'],
    (operations.settlement?.trades || []).map(t => [t.event_id,String(t.symbol || '').toUpperCase(),t.broker_code || 'UNASSIGNED',t.account_id || 'PRIMARY',t.side,t.trade_date,t.settlement_date,t.status,money(t.cash_effect)]),
  );
  const recs = table(
    ['Run','Broker','Account','As of','Status','QPort cash','Broker cash','Cash diff'],
    (operations.reconciliations || []).map(r => [r.id,r.broker_code || 'UNASSIGNED',r.account_id || 'PRIMARY',r.as_of_date,r.status,money(r.qport_cash),money(r.broker_cash),money(r.cash_difference)]),
  );
  const corp = table(
    ['ID','Ticker','Type','Ex date','Record date','Payment date','Expected cash','Expected shares','Verification','Status','Ledger posted'],
    (operations.corporate_actions || []).map(a => [a.id,String(a.symbol || '').toUpperCase(),a.action_type,a.ex_date || '-',a.record_date || '-',a.payment_date || '-',money(a.expected_cash),num(a.expected_shares),a.verification_status,a.status,String(Boolean(a.ledger_posted))]),
  );
  const securities = table(
    ['Security ID','Ticker','Name','Exchange','ISIN','Lot size','Master source','Master status'],
    (operations.securities || []).map(s => [s.security_id,String(s.symbol || '').toUpperCase(),s.name || '-',s.exchange,s.isin || 'UNRESOLVED',s.lot_size ?? '-',s.master_data_source || '-',s.master_data_status || 'UNRESOLVED']),
  );
  const exceptions = table(['Severity','Code','Message'], (operations.exceptions || []).map(e => [e.severity,e.code,e.message]));
  const attribution = table(
    ['Ticker','Unrealized','Realized','Dividends','Total contribution'],
    (operations.pnl_attribution || []).map(a => [String(a.symbol || '').toUpperCase(),money(a.unrealized_pnl),money(a.realized_pnl),money(a.dividend_income),money(a.total_contribution_vnd)]),
  );
  const effectiveLedger = table(
    ['ID','Date','Type','Ticker','Qty','Price','Amount','Fee','Tax','Broker','Account','Auto','Corporate action','Audit','Note','Metadata'],
    ledger.map(e => [
      e.id,e.event_date,e.event_type,String(e.symbol || '-').toUpperCase(),num(e.quantity),money(e.price),money(e.amount),
      money(e.fee),money(e.tax),e.metadata?.broker_code || 'UNASSIGNED',e.metadata?.account_id || 'PRIMARY',
      String(Boolean(e.metadata?.auto_generated)),e.metadata?.corporate_action_id ?? '-',e.correction?.action || 'ORIGINAL',
      e.note || '-',metadataSummary(e.metadata || {}),
    ]),
  );
  const correctionAudit = table(['Correction','Event','Action','Reason','Created by','Created at'], corrections.map(c => [c.id,c.event_id,c.action,c.reason,c.created_by || '-',c.created_at]));
  const snapTable = table(['Date','Official','NAV','Cash','Equity','Daily P/L','Daily return','Drawdown','Quality'], orderedSnapshots.map(s => [s.snapshot_date,String(Boolean(s.official)),money(s.nav),money(s.cash),money(s.equity_value),money(s.daily_pnl),pct(s.daily_return),pct(s.current_drawdown),s.data_quality]));
  const activityTable = table(['ID','Time UTC','Actor','Category','Action','Entity','Status','Summary'], activityRows.map(x => [x.id,x.occurred_at,`${x.actor_type}/${x.actor_id}`,x.category,x.action,`${x.entity_type || '-'}${x.entity_id ? `#${x.entity_id}` : ''}`,x.status,x.summary]));

  const dividendRows = [];
  for (const symbol of Object.keys(dividends).sort()) {
    const result = dividends[symbol] || {};
    if (result.error) {
      dividendRows.push([symbol,'ERROR','-','-','-','-','-','-',result.error]);
      continue;
    }
    for (const event of result.events || []) {
      dividendRows.push([
        symbol,event.dividend_type,event.effective_event_date || '-',event.ex_date || '-',event.record_date || '-',event.payment_date || '-',
        money(event.cash_per_share),event.stock_ratio_percent == null ? '-' : `${Number(event.stock_ratio_percent).toFixed(4)}%`,
        event.source || result.canonical_source || '-',
      ]);
    }
  }
  const dividendHistory = table(['Ticker','Type','Event date','Ex date','Record date','Payment date','Cash/share','Stock ratio','Canonical source'], dividendRows);

  const payload = clean({
    schema_version: EXPORT_SCHEMA,
    generated_at: generatedAt,
    portfolio_state_as_of: dashboard.today || null,
    market_data_as_of: market.market_date || null,
    performance_as_of: performance.latest_date || null,
    currency: 'VND',
    price_unit: 'full VND per share',
    export_coverage: {
      transactions: ledger.length,
      corrections: corrections.length,
      snapshots_returned_by_api: orderedSnapshots.length,
      activity_rows_returned_by_api: activityRows.length,
      dividend_symbols: Object.keys(dividends).length,
      broker_dividend_receipts: (operations.dividend_receipts_by_broker || []).length,
      note: 'Client-side export does not truncate API responses.',
    },
    dashboard,
    performance,
    risk,
    operations,
    dividend_history_by_symbol: dividends,
    activity_integrity: activity.integrity || {},
    activity: activityRows,
    transactions: ledger,
    transaction_correction_audit: corrections,
    snapshots: orderedSnapshots,
  });

  return `# QPort AI Audit Export\n\n` +
    `> Read-only audit evidence. QPort is a Buy & Hold portfolio information system; this export never creates a trade.\n\n` +
    `## Export metadata\n\n${table(['Field','Value'], [
      ['Schema',EXPORT_SCHEMA],['Generated at',generatedAt],['Portfolio state as of',dashboard.today || '-'],['Market data as of',market.market_date || '-'],['Performance as of',performance.latest_date || '-'],['Book type',operations.book_type || '-'],['Accounting cost method',operations.accounting_cost_method || '-'],['Position recognition',operations.position_recognition || '-'],['Activity chain',activity.integrity?.status || '-'],['Ledger rows',ledger.length],['Correction rows',corrections.length],['Snapshots returned',orderedSnapshots.length],['Activity rows returned',activityRows.length],['Dividend symbols audited',Object.keys(dividends).length]
    ])}\n\n` +
    `## Current accounting\n\n${table(['Metric','Value'], [
      ['NAV',money(portfolio.nav)],['Equity',money(portfolio.equity_value)],['Cash',money(portfolio.cash)],['Cost value',money(portfolio.cost_value)],['Total P/L',money(portfolio.total_pnl)],['Accounting return',pct(portfolio.accounting_return)],['Realized P/L',money(portfolio.realized_pnl)],['Unrealized P/L',money(portfolio.unrealized_pnl)],['Gross cash dividends',money(portfolio.dividend_income)],['Cash-dividend tax',money(performance.cash_dividend_tax)],['Net cash-dividend income',money(performance.net_dividend_income)],['Stock-dividend sale tax',money(performance.stock_dividend_sale_tax)],['Fees + taxes',money(portfolio.fees_and_taxes)],['Performance history',performance.history_status || '-'],['TWR',pct(performance.returns?.since_inception)],['XIRR',pct(performance.xirr)],['Drawdown',pct(performance.current_drawdown)]
    ])}\n\n## Holdings\n\n${holdings}` +
    `\n\n## Tax lots by broker/account\n\n${lots}` +
    `\n\n## Dividend receipts by broker/account\n\n${brokerDividends}` +
    `\n\n## Canonical dividend provider history\n\n${dividendHistory}` +
    `\n\n## Institutional cash & settlement\n\n${table(['Metric','Value'], [
      ['Settled cash',money(operations.settlement?.settled_cash)],['Projected cash',money(operations.settlement?.projected_cash)],['Unsettled receivable',money(operations.settlement?.unsettled_receivable)],['Unsettled payable',money(operations.settlement?.unsettled_payable)],['Strategic reserve',money(operations.settlement?.strategic_reserve)],['Available to invest',money(operations.settlement?.available_to_invest)]
    ])}\n\n${settlements}` +
    `\n\n## Broker reconciliation\n\n${recs}` +
    `\n\n## Security master\n\n${securities}` +
    `\n\n## Corporate actions\n\nProvider: **${cell(operations.corporate_action_provider?.provider || '-')}** · available=${String(operations.corporate_action_provider?.available ?? false)}\n\n${corp}` +
    `\n\n## Operations exceptions\n\n${exceptions}` +
    `\n\n## P/L attribution\n\n${attribution}` +
    `\n\n## Risk\n\n${table(['Metric','Value'], [
      ['Status',risk.status || '-'],['Risk coverage',pct(risk.quality?.coverage_weight)],['63D vol',pct(risk.volatility_63)],['252D vol',pct(risk.volatility_252)],['Average correlation',num(risk.average_correlation)],['Max correlation',num(risk.max_correlation)],['Equity HHI',num(risk.equity_hhi)],['Effective positions',num(risk.effective_positions,2)],['Diversification ratio',num(risk.diversification_ratio)],['Largest risk contributor',risk.largest_risk_symbol || '-'],['Largest risk contribution',pct(risk.largest_risk_contribution)],['VaR 95%',pct(risk.daily_var_95)],['CVaR 95%',pct(risk.daily_cvar_95)],['Worst observed day',pct(risk.max_daily_loss)]
    ])}` +
    `\n\n## Performance methodology\n\n\`\`\`json\n${JSON.stringify(clean(performance.methodology_policy || {}), null, 2)}\n\`\`\`` +
    `\n\n## Data lineage\n\n\`\`\`json\n${JSON.stringify(clean(dashboard.data_lineage || {}), null, 2)}\n\`\`\`` +
    `\n\n## Strategic cash policy\n\nCash reserve configured: **${String(prefs.cash_reserve_configured ?? false)}**  \nStrategic reserve: **${money(prefs.cash_reserve)}**  \nCash deployment policy: **${cell(suggestions.policy || '-')}**\n` +
    `\n\n## Effective ledger\n\n${effectiveLedger}` +
    `\n\n## Transaction correction audit\n\n${correctionAudit}` +
    `\n\n## Activity log returned by API\n\n${activityTable}` +
    `\n\n## Snapshot history returned by API\n\n${snapTable}` +
    `\n\n## Interpretation rules for AI\n\n` +
    `- Effective ledger = immutable source events plus append-only corrections and is the source of truth for Holdings.\n` +
    `- User transaction entry does not create dividend events. Dividend CASH_DIVIDEND/STOCK_DIVIDEND rows originate from the corporate-action workflow and are read-only in normal Transaction UI.\n` +
    `- Due dividend corporate actions auto-post idempotent ledger events on payment date when entitlement data is sufficient.\n` +
    `- broker_account_allocations on dividend ledger metadata attribute receipts from entitlement-date open lots; broker dividend tables are derived from that metadata.\n` +
    `- Cash dividends are recorded gross and 5% withholding reduces cash. Stock-dividend investment-income tax is deferred until taxable dividend shares are sold.\n` +
    `- Dividend provider history uses one canonical provider per normal refresh and suppresses duplicate economic events from stale/multiple-provider cache evidence.\n` +
    `- Broker/account identity is part of each event and tax lot; broker-assigned SELL disposes only matching broker/account FIFO lots.\n` +
    `- BUY can represent either a market purchase or a paid rights/new-issue subscription when the actual quantity, paid price, broker and account are recorded.\n` +
    `- ISIN is resolved from reference/master data and is never fabricated from ticker.\n` +
    `- Trade-date positions and settlement-aware cash are separate concepts.\n` +
    `- Broker reconciliation differences are exceptions, never auto-corrections.\n` +
    `- Activity records are append-only and hash chained; integrity status is included above.\n` +
    `- NAV restatements require review after historical corrections.\n` +
    `- Accounting return is not TWR/XIRR/CAGR. Missing performance evidence is N/A, never zero.\n` +
    `- Risk/portfolio guidance is informational and never creates a BUY/SELL transaction.\n` +
    `\n## Machine-readable payload\n\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\`\n`;
}

async function loadDividendAudit(symbols) {
  const output = {};
  for (let i = 0; i < symbols.length; i += 4) {
    const batch = symbols.slice(i, i + 4);
    const rows = await Promise.all(batch.map(async symbol => {
      try {
        return [symbol, await getLatestDividend(symbol)];
      } catch (err) {
        return [symbol, { ok: false, symbol, error: err.message }];
      }
    }));
    for (const [symbol, result] of rows) output[symbol] = result;
  }
  return output;
}

export async function downloadAIExport() {
  try { await logClientActivity('AI_EXPORT', { schema: EXPORT_SCHEMA }); } catch (_) { /* export must remain usable if audit endpoint is temporarily unavailable */ }
  const [dashboard, performance, risk, operations, activity, snapshots, transactions, corrections] = await Promise.all([
    getPortfolioDashboard(), getPortfolioPerformance(), getPortfolioRisk(), getPortfolioOperations(), getActivityLog(),
    listPortfolioSnapshots(), listPortfolioTransactions(), listPortfolioTransactionAudit(),
  ]);
  const symbols = [...new Set([
    ...(dashboard?.portfolio?.positions || []).map(row => String(row.symbol || '').toUpperCase()),
    ...transactions.map(row => String(row.symbol || '').toUpperCase()),
  ].filter(Boolean))].sort();
  const dividends = await loadDividendAudit(symbols);
  const generatedAt = new Date().toISOString();
  const markdown = buildAIExportMarkdown({ dashboard, performance, risk, operations, activity, snapshots, transactions, corrections, dividends, generatedAt });
  const date = String(dashboard?.today || generatedAt.slice(0, 10));
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `qport-ai-audit-${date}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return anchor.download;
}
