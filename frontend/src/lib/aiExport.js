import {
  getActivityLog,
  getPortfolioDashboard,
  getPortfolioOperations,
  getPortfolioPerformance,
  getPortfolioRisk,
  listPortfolioSnapshots,
  listPortfolioTransactionAudit,
  listPortfolioTransactions,
  logClientActivity,
} from './api.js';

const EXPORT_SCHEMA = 'qport-ai-export-v4';
const MAX_SNAPSHOTS = 90;
const MAX_ACTIVITY = 100;

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

export function buildAIExportMarkdown({ dashboard = {}, performance = {}, risk = {}, operations = {}, activity = {}, snapshots = [], transactions = [], corrections = [], generatedAt }) {
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const market = dashboard.market_data || {};
  const prefs = dashboard.preferences || {};
  const suggestions = dashboard.contribution_suggestions || {};
  const orderedSnapshots = [...snapshots].filter(s => s?.official).sort((a, b) => String(a.snapshot_date).localeCompare(String(b.snapshot_date))).slice(-MAX_SNAPSHOTS);
  const ledger = [...transactions].sort((a, b) => String(a.event_date).localeCompare(String(b.event_date)) || Number(a.id || 0) - Number(b.id || 0));
  const recentActivity = (activity.logs || []).slice(0, MAX_ACTIVITY);

  const holdings = table(['Ticker','Shares','Avg cost','Price','Cost value','Market value','P/L','NAV weight','Equity weight','Risk contrib.','Status'], positions.map(p => [p.symbol,num(p.shares),money(p.average_cost),money(p.price),money(p.cost_value),money(p.market_value),money(p.unrealized_pnl),pct(p.weight),pct(p.equity_weight),pct(p.risk_contribution),p.status]));
  const lots = table(['Lot','Ticker','Broker','Account','Acquired','Original qty','Remaining qty','Unit cost','Cost basis'], (operations.tax_lots || []).map(l => [l.lot_id,l.symbol,l.broker_code || 'UNASSIGNED',l.account_id,l.acquisition_date,num(l.original_quantity),num(l.remaining_quantity),money(l.unit_cost),money(l.cost_basis)]));
  const settlements = table(['Event','Ticker','Broker','Account','Side','Trade date','Settlement date','Status','Cash effect'], (operations.settlement?.trades || []).map(t => [t.event_id,t.symbol,t.broker_code || 'UNASSIGNED',t.account_id || 'PRIMARY',t.side,t.trade_date,t.settlement_date,t.status,money(t.cash_effect)]));
  const recs = table(['Run','Broker','Account','As of','Status','QPort cash','Broker cash','Cash diff'], (operations.reconciliations || []).map(r => [r.id,r.broker_code || 'UNASSIGNED',r.account_id || 'PRIMARY',r.as_of_date,r.status,money(r.qport_cash),money(r.broker_cash),money(r.cash_difference)]));
  const corp = table(['ID','Ticker','Type','Record date','Expected cash','Expected shares','Verification','Status'], (operations.corporate_actions || []).map(a => [a.id,a.symbol,a.action_type,a.record_date || '-',money(a.expected_cash),num(a.expected_shares),a.verification_status,a.status]));
  const securities = table(['Security ID','Ticker','Name','Exchange','ISIN','Lot size','Master source','Master status'], (operations.securities || []).map(s => [s.security_id,s.symbol,s.name || '-',s.exchange,s.isin || 'UNRESOLVED',s.lot_size ?? '-',s.master_data_source || '-',s.master_data_status || 'UNRESOLVED']));
  const exceptions = table(['Severity','Code','Message'], (operations.exceptions || []).map(e => [e.severity,e.code,e.message]));
  const attribution = table(['Ticker','Unrealized','Realized','Dividends','Total contribution'], (operations.pnl_attribution || []).map(a => [a.symbol,money(a.unrealized_pnl),money(a.realized_pnl),money(a.dividend_income),money(a.total_contribution_vnd)]));
  const effectiveLedger = table(['ID','Date','Type','Ticker','Qty','Price','Amount','Broker','Account','Audit','Note'], ledger.map(e => [e.id,e.event_date,e.event_type,e.symbol || '-',num(e.quantity),money(e.price),money(e.amount),e.metadata?.broker_code || 'UNASSIGNED',e.metadata?.account_id || 'PRIMARY',e.correction?.action || 'ORIGINAL',e.note || '-']));
  const correctionAudit = table(['Correction','Event','Action','Reason','Created at'], corrections.map(c => [c.id,c.event_id,c.action,c.reason,c.created_at]));
  const snapTable = table(['Date','NAV','Cash','Equity','Daily return','Drawdown','Quality'], orderedSnapshots.map(s => [s.snapshot_date,money(s.nav),money(s.cash),money(s.equity_value),pct(s.daily_return),pct(s.current_drawdown),s.data_quality]));
  const activityTable = table(['ID','Time UTC','Actor','Category','Action','Entity','Status','Summary'], recentActivity.map(x => [x.id,x.occurred_at,`${x.actor_type}/${x.actor_id}`,x.category,x.action,`${x.entity_type || '-'}${x.entity_id ? `#${x.entity_id}` : ''}`,x.status,x.summary]));

  const payload = clean({
    schema_version: EXPORT_SCHEMA,
    generated_at: generatedAt,
    portfolio_state_as_of: dashboard.today || null,
    market_data_as_of: market.market_date || null,
    performance_as_of: performance.latest_date || null,
    currency: 'VND', price_unit: 'full VND per share',
    dashboard, performance, risk, operations,
    activity_integrity: activity.integrity || {},
    recent_activity: recentActivity,
    transactions: ledger,
    transaction_correction_audit: corrections,
    recent_official_snapshots: orderedSnapshots,
  });

  return `# QPort AI Context Export\n\n` +
    `> Read-only evidence. QPort is an institutional-lite Buy & Hold portfolio book; no section in this export creates a trade.\n\n` +
    `## Export metadata\n\n${table(['Field','Value'], [
      ['Schema',EXPORT_SCHEMA],['Generated at',generatedAt],['Portfolio state as of',dashboard.today || '-'],['Market data as of',market.market_date || '-'],['Performance as of',performance.latest_date || '-'],['Book type',operations.book_type || '-'],['Accounting cost method',operations.accounting_cost_method || '-'],['Position recognition',operations.position_recognition || '-'],['Activity chain',activity.integrity?.status || '-']
    ])}\n\n` +
    `## Current accounting\n\n${table(['Metric','Value'], [
      ['NAV',money(portfolio.nav)],['Equity',money(portfolio.equity_value)],['Projected/economic cash',money(portfolio.cash)],['Cost value',money(portfolio.cost_value)],['Total P/L',money(portfolio.total_pnl)],['Accounting return',pct(portfolio.accounting_return)],['Realized P/L',money(portfolio.realized_pnl)],['Unrealized P/L',money(portfolio.unrealized_pnl)],['Dividends',money(portfolio.dividend_income)],['Performance history',performance.history_status || '-'],['TWR',pct(performance.returns?.since_inception)],['XIRR',pct(performance.xirr)],['Drawdown',pct(performance.current_drawdown)]
    ])}\n\n## Holdings\n\n${holdings}` +
    `\n\n## Institutional cash & settlement\n\n${table(['Metric','Value'], [
      ['Settled cash',money(operations.settlement?.settled_cash)],['Projected cash',money(operations.settlement?.projected_cash)],['Unsettled receivable',money(operations.settlement?.unsettled_receivable)],['Unsettled payable',money(operations.settlement?.unsettled_payable)],['Strategic reserve',money(operations.settlement?.strategic_reserve)],['Available to invest',money(operations.settlement?.available_to_invest)]
    ])}\n\n${settlements}` +
    `\n\n## Tax lots by broker/account\n\n${lots}` +
    `\n\n## Broker reconciliation\n\n${recs}` +
    `\n\n## Security master\n\n${securities}` +
    `\n\n## Corporate actions\n\nProvider: **${cell(operations.corporate_action_provider?.provider || '-')}** · available=${String(operations.corporate_action_provider?.available ?? false)}\n\n${corp}` +
    `\n\n## Operations exceptions\n\n${exceptions}` +
    `\n\n## P/L attribution\n\n${attribution}` +
    `\n\n## Risk\n\n${table(['Metric','Value'], [
      ['Status',risk.status || '-'],['63D vol',pct(risk.volatility_63)],['252D vol',pct(risk.volatility_252)],['Equity HHI',num(risk.equity_hhi)],['Effective positions',num(risk.effective_positions,2)],['Largest risk contributor',risk.largest_risk_symbol || '-'],['Largest risk contribution',pct(risk.largest_risk_contribution)],['VaR 95%',pct(risk.daily_var_95)],['CVaR 95%',pct(risk.daily_cvar_95)]
    ])}` +
    `\n\n## Performance methodology\n\n\`\`\`json\n${JSON.stringify(clean(performance.methodology_policy || {}), null, 2)}\n\`\`\`` +
    `\n\n## Data lineage\n\n\`\`\`json\n${JSON.stringify(clean(dashboard.data_lineage || {}), null, 2)}\n\`\`\`` +
    `\n\n## Strategic cash policy\n\nCash reserve configured: **${String(prefs.cash_reserve_configured ?? false)}**  \nStrategic reserve: **${money(prefs.cash_reserve)}**  \nCash deployment policy: **${cell(suggestions.policy || '-')}**\n` +
    `\n\n## Effective ledger\n\n${effectiveLedger}` +
    `\n\n## Transaction correction audit\n\n${correctionAudit}` +
    `\n\n## Recent activity log (latest ${MAX_ACTIVITY})\n\n${activityTable}` +
    `\n\n## Recent official snapshots\n\n${snapTable}` +
    `\n\n## Interpretation rules for AI\n\n` +
    `- Effective ledger = immutable source events plus append-only corrections.\n` +
    `- Broker/account identity is part of each event and tax lot; broker-assigned SELL disposes only matching broker/account FIFO lots.\n` +
    `- ISIN is resolved from reference/master data and is never fabricated from ticker.\n` +
    `- Trade-date positions and settlement-aware cash are separate concepts.\n` +
    `- Broker reconciliation differences are exceptions, never auto-corrections.\n` +
    `- Corporate-action discovery is provisional until verified against an authoritative source; detected events never auto-post cash/shares.\n` +
    `- Activity records are append-only and hash chained; integrity status is included above.\n` +
    `- NAV restatements require review after historical corrections.\n` +
    `- Accounting return is not TWR/XIRR/CAGR. Missing performance evidence is N/A, never zero.\n` +
    `- Risk/portfolio guidance is informational and never creates a trade.\n` +
    `\n## Machine-readable payload\n\n\`\`\`json\n${JSON.stringify(payload, null, 2)}\n\`\`\`\n`;
}

export async function downloadAIExport() {
  try { await logClientActivity('AI_EXPORT', { schema: EXPORT_SCHEMA }); } catch (_) { /* export must remain usable if audit endpoint is temporarily unavailable */ }
  const [dashboard, performance, risk, operations, activity, snapshots, transactions, corrections] = await Promise.all([
    getPortfolioDashboard(), getPortfolioPerformance(), getPortfolioRisk(), getPortfolioOperations(), getActivityLog(),
    listPortfolioSnapshots(), listPortfolioTransactions(), listPortfolioTransactionAudit(),
  ]);
  const generatedAt = new Date().toISOString();
  const markdown = buildAIExportMarkdown({ dashboard, performance, risk, operations, activity, snapshots, transactions, corrections, generatedAt });
  const date = String(dashboard?.today || generatedAt.slice(0, 10));
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = `qport-ai-export-${date}.md`; document.body.appendChild(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return anchor.download;
}
