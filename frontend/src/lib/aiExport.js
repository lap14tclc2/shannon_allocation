import {
  getLatestDividend,
  getPortfolioDashboard,
  getPortfolioOperations,
  getPortfolioPerformance,
  getPortfolioRisk,
  getValuationReports,
  listPortfolioSnapshots,
  listPortfolioTransactionAudit,
  listPortfolioTransactions,
} from './api.js';

const EXPORT_SCHEMA = 'qport-ai-export-v6';

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
  dashboard = {}, performance = {}, risk = {}, operations = {},
  snapshots = [], transactions = [], corrections = [], dividends = {}, valuations = {}, generatedAt,
}) {
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const market = dashboard.market_data || {};
  const prefs = dashboard.preferences || {};
  const suggestions = dashboard.contribution_suggestions || {};
  const orderedSnapshots = [...snapshots].filter(Boolean).sort((a, b) => String(a.snapshot_date).localeCompare(String(b.snapshot_date)));
  const ledger = [...transactions].sort((a, b) => String(a.event_date).localeCompare(String(b.event_date)) || Number(a.id || 0) - Number(b.id || 0));

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

  // Fundamental Valuation & Value Investing Summary
  const valuationSummaryRows = [];
  const valuationPillarsRows = [];
  const valuationHistorySections = [];

  for (const symbol of Object.keys(valuations).sort()) {
    const rep = valuations[symbol] || {};
    const mult = rep.multiples || {};
    const pillars = rep.value_investor_pillars || {};
    // P0 audit (2026-08-29) + feedback 31/08: chỉ model verified VÀ đạt chuẩn
    // Buffett mới publish IV/MOS (public_* fields). Cổ phiếu bị chặn (hard reject
    // / điểm quá thấp) trả null kèm valuation_warning.
    const baseIV = rep.public_base_iv ?? null;
    const bearIV = rep.public_bear_iv ?? null;
    const bullIV = rep.public_bull_iv ?? null;
    const mos = rep.public_mos ?? null;
    const epv = rep.public_epv ?? null;
    const warning = rep.valuation_warning || null;
    const verified = rep.model_status === 'MODEL_VERIFIED' && !warning;

    valuationSummaryRows.push([
      symbol,
      rep.archetype_profile?.archetype || '-',
      rep.valuation_model || '-',
      rep.model_status || '-',
      money(rep.current_market_price),
      money(bearIV),
      money(baseIV),
      money(bullIV),
      mos != null ? `${mos > 0 ? '+' : ''}${num(mos, 1)}%` : (warning ? '⚠ Không công bố' : '-'),
      rep.margin_of_safety_analysis?.required_mos_pct != null ? `${num(rep.margin_of_safety_analysis.required_mos_pct, 1)}%` : '-',
      rep.confidence_level || '-',
      rep.valuation_pill || '-',
      money(epv),
      mult.pe != null ? `${num(mult.pe, 1)}x` : '-',
      mult.pb != null ? `${num(mult.pb, 2)}x` : '-',
      mult.roe != null ? `${num(mult.roe, 1)}%` : '-',
      warning || '-',
    ]);

    const confirmed = pillars.capital_allocation?.confirmed_economic_dilution_5y_pct ?? pillars.capital_allocation?.share_dilution_5y_pct ?? null;
      const unexplained = pillars.capital_allocation?.unexplained_share_change_5y_pct ?? pillars.capital_allocation?.unexplained_share_change_pct ?? null;
      const isUnknown = pillars.capital_allocation?.dilution_classification === 'UNEXPLAINED_SHARE_CHANGE';
      // P0/P1 audit (2026-08-29): unknown dilution renders as "N/A · X% unexplained",
      // never a misleading 0%.
      const dilutionCell = isUnknown && unexplained != null && Number.isFinite(Number(unexplained))
        ? `N/A · ${num(unexplained, 1)}% unexplained`
        : (confirmed != null && Number.isFinite(Number(confirmed)) ? `+${num(confirmed, 1)}%` : '0%');

    // Feedback 31/08 (P1): tách "5Y Avg ROE" (bản thân ROE không uncertain) khỏi
      // "Capital Allocation" status (cái mới uncertain khi unexplained >= 20%).
      const capStatusVi = {
        EXCELLENT: 'Xuất sắc',
        GOOD: 'Tốt',
        UNCERTAIN: 'Không chắc (chờ bằng chứng phát hành)',
        WATCH: 'Cần chú ý',
      };
      const capStatus = pillars.capital_allocation?.status || '';
      const capStatusCell = capStatus ? (capStatusVi[capStatus] || capStatus) : '-';

    valuationPillarsRows.push([
      symbol,
      pillars.earnings_quality?.avg_cash_conversion_5y != null ? `${num(pillars.earnings_quality.avg_cash_conversion_5y, 1)}% (${pillars.earnings_quality.status})` : '-',
      pillars.financial_fortress?.debt_payback_years == null ? '-' : `${pillars.financial_fortress.debt_payback_years === 0 ? '0 năm (FORTRESS)' : `${pillars.financial_fortress.debt_payback_years} năm (${pillars.financial_fortress.status})`}`,
      pillars.capital_allocation?.avg_roe_5y != null ? `${num(pillars.capital_allocation.avg_roe_5y, 1)}%` : '-',
      capStatusCell,
      dilutionCell,
      rep.cagr_5y_net_profit != null ? `+${num(rep.cagr_5y_net_profit, 1)}%` : '-',
    ]);

    if (Array.isArray(rep.financial_history_10y) && rep.financial_history_10y.length > 0) {
      const histTable = table(
        ['Year', 'Net Profit (VND)', 'Equity (VND)', 'ROE (%)', 'CFO (VND)', 'FCF (VND)', 'Cash Conversion (%)', 'Shares'],
        rep.financial_history_10y.map(h => [
          h.fiscal_year,
          money(h.net_profit),
          money(h.equity),
          h.roe != null ? `${num(h.roe, 1)}%` : '-',
          money(h.operating_cash_flow),
          money(h.free_cash_flow),
          h.cash_conversion_ratio != null ? `${num(h.cash_conversion_ratio, 1)}%` : '-',
          h.shares_outstanding != null ? num(h.shares_outstanding, 0) : '-',
        ]),
      );

      let sensTableStr = '';
      if (rep.sensitivity_matrix?.grid_values_per_share) {
        const discHeaders = ['Terminal Growth (g) \\ Discount (r)', ...rep.sensitivity_matrix.discount_rates.map(r => `${num(Number(r) * 100, 1)}%`)];
        const sensRows = rep.sensitivity_matrix.terminal_growth_rates.map((g, rIdx) => [
          `${num(Number(g) * 100, 1)}%`,
          ...rep.sensitivity_matrix.grid_values_per_share[rIdx].map(v => money(v)),
        ]);
        sensTableStr = `\n\n#### Sensitivity Matrix (r vs g) for ${symbol}\n\n${table(discHeaders, sensRows)}`;
      }

      const modelVerified = rep.model_status === 'MODEL_VERIFIED';
      // Feedback 31/08 (P1): tách bạch model-gating vs quality-gating. Khi model
      // VERIFIED nhưng bị chặn chất lượng (LOW_QUALITY/hard reject), IV/MOS bị ẩn
      // do QUALITY gate chứ KHÔNG phải vì "model chưa verified".
      const verdictLine = verified
        ? (rep.verdict || rep.analyst_verdict || '-')
        : (modelVerified
            ? `_Model VERIFIED nhưng không đạt chuẩn chất lượng Buffett/Munger → IV/MOS bị ẩn (quality gate). ${rep.valuation_warning || ''}_`
            : `_Mô hình chưa được xác thực (${rep.model_status || 'MODEL_*'}) – kết luận định giá chỉ dùng để kiểm toán (AUDIT_ONLY)._`);
      const bridgeLine = verified
        ? `Net Income: ${money(rep.owner_earnings_bridge?.net_income)} · D&A: ${money(rep.owner_earnings_bridge?.depreciation_amortization)} · Capex: ${money(rep.owner_earnings_bridge?.maintenance_capex)} $\\rightarrow$ Owner Earnings: ${money(rep.owner_earnings_bridge?.owner_earnings)}`
        : (modelVerified
            ? `_Ẩn theo nguyên tắc chất lượng (quality gate) – chỉ dùng để kiểm toán._`
            : `_Ẩn theo nguyên tắc model-verified (AUDIT_ONLY)._`);

      valuationHistorySections.push(`### ${symbol} — Financial History & Sensitivity\n\n` +
        `**Analyst Verdict:** ${verdictLine}\n\n` +
        `**Owner Earnings Bridge:** ${bridgeLine}\n\n` +
        `#### 10-Year Financial Ledger (${rep.financial_history_10y[0]?.fiscal_year} – ${rep.financial_history_10y[rep.financial_history_10y.length - 1]?.fiscal_year})\n\n${histTable}` +
        sensTableStr
      );
    }
  }

  const valuationOverviewTable = table(
    ['Ticker', 'Archetype', 'Model', 'Model Status', 'Price', 'Bear IV', 'Base IV', 'Bull IV', 'MOS', 'Required MOS', 'Confidence', 'Verdict', 'EPV', 'P/E', 'P/B', 'ROE', 'Warning'],
    valuationSummaryRows,
  );

  const valuationPillarsTable = table(
    ['Ticker', 'Cash Conversion 5Y', 'Debt Payback (Fortress)', '5Y Avg ROE', 'Capital Allocation', '5Y Dilution (Confirmed | Unexplained)', '5Y Profit CAGR'],
    valuationPillarsRows,
  );

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
      dividend_symbols: Object.keys(dividends).length,
      valuation_symbols: Object.keys(valuations).length,
      broker_dividend_receipts: (operations.dividend_receipts_by_broker || []).length,
      note: 'Client-side export does not truncate API responses.',
    },
    dashboard,
    performance,
    risk,
    operations,
    valuations,
    dividend_history_by_symbol: dividends,
    transactions: ledger,
    transaction_correction_audit: corrections,
    snapshots: orderedSnapshots,
  });

  return `# QPort AI Audit Export\n\n` +
    `> Read-only audit evidence. QPort is a Buy & Hold portfolio information system; this export never creates a trade.\n\n` +
    `## Export metadata\n\n${table(['Field','Value'], [
      ['Schema',EXPORT_SCHEMA],['Generated at',generatedAt],['Portfolio state as of',dashboard.today || '-'],['Market data as of',market.market_date || '-'],['Performance as of',performance.latest_date || '-'],['Book type',operations.book_type || '-'],['Accounting cost method',operations.accounting_cost_method || '-'],['Position recognition',operations.position_recognition || '-'],['Ledger rows',ledger.length],['Correction rows',corrections.length],['Snapshots returned',orderedSnapshots.length],['Dividend symbols audited',Object.keys(dividends).length],['Valuation symbols audited',Object.keys(valuations).length]
    ])}\n\n` +
    `## Current accounting\n\n${table(['Metric','Value'], [
      ['NAV',money(portfolio.nav)],['Equity',money(portfolio.equity_value)],['Cash',money(portfolio.cash)],['Cost value',money(portfolio.cost_value)],['Total P/L',money(portfolio.total_pnl)],['Accounting return',pct(portfolio.accounting_return)],['Realized P/L',money(portfolio.realized_pnl)],['Unrealized P/L',money(portfolio.unrealized_pnl)],['Gross cash dividends',money(portfolio.dividend_income)],['Cash-dividend tax',money(performance.cash_dividend_tax)],['Net cash-dividend income',money(performance.net_dividend_income)],['Stock-dividend sale tax',money(performance.stock_dividend_sale_tax)],['Fees + taxes',money(portfolio.fees_and_taxes)],['Performance history',performance.history_status || '-'],['TWR',pct(performance.returns?.since_inception)],['XIRR',pct(performance.xirr)],['Drawdown',pct(performance.current_drawdown)]
    ])}\n\n## Holdings\n\n${holdings}` +
    `\n\n## Fundamental Valuation & Value Investing Analysis\n\n` +
    `### Valuation & Margin of Safety Overview\n\n${valuationOverviewTable}\n\n` +
    `### Value Investor Health Pillars (Cash Quality, Fortress, Capital Allocation)\n\n${valuationPillarsTable}\n\n` +
    (valuationHistorySections.length ? `${valuationHistorySections.join('\n\n')}\n\n` : '') +
    `## Tax lots by broker/account\n\n${lots}` +
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
    `- NAV restatements require review after historical corrections.\n` +
    `- Accounting return is not TWR/XIRR/CAGR. Missing performance evidence is N/A, never zero.\n` +
    `- Risk/portfolio guidance is informational and never creates a BUY/SELL transaction.\n` +
    `- Fundamental valuation reports are built on 10-year audited canonical financial statements without speculative short-term price target extrapolation.\n` +
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
  // P0 audit (2026-08-29): the export is "Read-only audit evidence" and MUST be
  // side-effect free. It no longer POSTs an AI_EXPORT client activity record, so
  // repeated exports never grow the activity log (count_before == count_after).
  const [dashboard, performance, risk, operations, snapshots, transactions, corrections] = await Promise.all([
    getPortfolioDashboard(), getPortfolioPerformance(), getPortfolioRisk(), getPortfolioOperations(),
    listPortfolioSnapshots(), listPortfolioTransactions(), listPortfolioTransactionAudit(),
  ]);
  const symbols = [...new Set([
    ...(dashboard?.portfolio?.positions || []).map(row => String(row.symbol || '').toUpperCase()),
    ...transactions.map(row => String(row.symbol || '').toUpperCase()),
  ].filter(Boolean))].sort();

  const [dividends, valuationRes] = await Promise.all([
    loadDividendAudit(symbols),
    getValuationReports(symbols).catch(() => ({ reports: {} })),
  ]);

  const valuations = valuationRes.reports || {};
  const generatedAt = new Date().toISOString();
  const markdown = buildAIExportMarkdown({ dashboard, performance, risk, operations, snapshots, transactions, corrections, dividends, valuations, generatedAt });
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

// ---------------------------------------------------------------------------
// Screener AI export (feedback 31/08): gồm data chi tiết overlay của TẤT CẢ mã
// được gợi ý, chia 2 section: đạt chuẩn & đầy đủ dữ liệu / đạt chuẩn nhưng thiếu
// dữ liệu.
// ---------------------------------------------------------------------------
function screenerFullyValued(item) {
  return item.model_status === 'MODEL_VERIFIED' && item.margin_of_safety != null;
}

function screenerStockDetail(symbol, item, rep) {
  const lines = [`### ${symbol} — ${item?.company_name || ''}`];
  if (rep) {
    const scen = rep.scenarios || {};
    const base = scen.BASE || {};
    const bear = scen.BEAR || {};
    const bull = scen.BULL || {};
    const quality = rep.quality_scorecard || {};
    const pillars = rep.value_investor_pillars || {};
    const capAlloc = pillars.capital_allocation || {};
    const missing = Array.isArray(rep.missing_data) ? rep.missing_data : [];
    const warning = rep.valuation_warning;
    lines.push(`- Thị giá: ${money(rep.current_market_price)}`);
    lines.push(`- Archetype: ${rep.archetype_profile?.archetype || '-'} | Mô hình: ${rep.valuation_model || '-'} | Model status: ${rep.model_status || '-'} | Confidence: ${rep.confidence_level || '-'}`);
    lines.push(`- Điểm chất lượng: ${quality.total_score ?? '-'}/100 (${quality.tier || '-'})`);
    if (warning) {
      lines.push(`- ⚠️ Cảnh báo: ${warning}`);
    } else {
      const mos = rep.public_mos ?? rep.margin_of_safety_pct ?? null;
      lines.push(`- Base IV: ${money(rep.public_base_iv ?? base.intrinsic_value_per_share)}`);
      lines.push(`- Bear IV: ${money(rep.public_bear_iv ?? bear.intrinsic_value_per_share)} | Bull IV: ${money(rep.public_bull_iv ?? bull.intrinsic_value_per_share)}`);
      lines.push(`- MOS: ${mos != null ? `${(mos > 0 ? '+' : '')}${num(mos, 1)}%` : 'N/A'} | Required MOS: ${rep.margin_of_safety_analysis?.required_mos_pct != null ? `${num(rep.margin_of_safety_analysis.required_mos_pct, 1)}%` : '-'}`);
      lines.push(`- Verdict: ${rep.valuation_pill || '-'}`);
    }
    lines.push(`- Chất lượng tiền mặt: ${pillars.earnings_quality?.status || '-'} (cash conversion 5Y: ${pillars.earnings_quality?.avg_cash_conversion_5y != null ? `${num(pillars.earnings_quality.avg_cash_conversion_5y, 1)}%` : 'N/A'})`);
    lines.push(`- Nợ/VCSH: ${pillars.financial_fortress?.debt_to_equity_ratio != null ? `${num(pillars.financial_fortress.debt_to_equity_ratio, 2)}x` : 'N/A'} | Net debt: ${money(pillars.financial_fortress?.net_debt_vnd)} | Debt payback: ${pillars.financial_fortress?.debt_payback_years == null ? 'N/A' : `${pillars.financial_fortress.debt_payback_years} năm`}`);
    lines.push(`- Phân bổ vốn: ${capAlloc.status || '-'} | ROE 5Y: ${capAlloc.avg_roe_5y != null ? `${num(capAlloc.avg_roe_5y, 1)}%` : '-'} | Dilution: ${capAlloc.dilution_classification || '-'} (confirmed: ${capAlloc.confirmed_economic_dilution_5y_pct != null ? `${num(capAlloc.confirmed_economic_dilution_5y_pct, 1)}%` : 'N/A'}, unexplained: ${capAlloc.unexplained_share_change_5y_pct != null ? `${num(capAlloc.unexplained_share_change_5y_pct, 1)}%` : 'N/A'})`);
    if (missing.length) {
      lines.push(`- **Dữ liệu cần thiết để định giá:**`);
      missing.forEach(m => lines.push(`  - ${m}`));
    }
    if (Array.isArray(rep.confidence_reasons) && rep.confidence_reasons.length) {
      lines.push(`- Nguyên nhân engine: ${rep.confidence_reasons.join(' | ')}`);
    }
    if (Array.isArray(quality.hard_rejects) && quality.hard_rejects.length) {
      lines.push(`- Hard rejects: ${quality.hard_rejects.join(', ')}`);
    }
  } else {
    lines.push(`- (Chưa có báo cáo định giá chi tiết — dữ liệu từ screener)`);
    const refMos = item?.margin_of_safety != null ? item.margin_of_safety : item?.diagnostic_mos;
    lines.push(`- Thị giá: ${money(item?.current_price)} | MOS: ${refMos != null ? `${(refMos > 0 ? '+' : '')}${num(refMos, 1)}%${item?.margin_of_safety == null ? ' (tham khảo)' : ''}` : 'N/A'}`);
    lines.push(`- Điểm chất lượng: ${item?.total_score ?? '-'}/100 (${item?.tier || '-'}) | Model status: ${item?.model_status || '-'}`);
    if (item?.valuation_gap) {
      lines.push(`- ⚠️ ${item.valuation_gap}`);
    } else if (item?.archetype === 'ARCHETYPE_UNKNOWN') {
      lines.push(`- ⚠️ Chưa xác định được mô hình định giá (thiếu thông tin phân loại ngành).`);
    }
  }
  return lines.join('\n');
}

export async function downloadScreenerAIExport(items = []) {
  const symbols = [...new Set((items || []).map(it => String(it.symbol || '').toUpperCase()).filter(Boolean))].sort();
  const valuationRes = await getValuationReports(symbols).catch(() => ({ reports: {} }));
  const reports = valuationRes.reports || {};

  const section1 = (items || []).filter(screenerFullyValued);
  const section2 = (items || []).filter(it => !screenerFullyValued(it));

  const summaryRows = (items || []).map(it => [
    it.symbol,
    money(it.current_price),
    it.margin_of_safety != null ? `${(it.margin_of_safety > 0 ? '+' : '')}${num(it.margin_of_safety, 1)}%` : 'N/A',
    it.total_score ?? '-',
    it.tier_vi || it.tier || '-',
    it.archetype || '-',
    it.valuation_status_vi || it.valuation_status || '-',
    it.valuation_warning ? `⚠️ ${it.valuation_warning}` : '-',
  ]);
  const summaryTable = table(
    ['Mã CP', 'Thị giá', 'MOS', 'Điểm CL', 'Hạng', 'Archetype', 'Trạng thái', 'Ghi chú'],
    summaryRows,
  );

  const generatedAt = new Date().toISOString();
  const md = [
    `# QPort Bộ lọc Cổ phiếu — Export AI (${generatedAt.slice(0, 10)})`,
    ``,
    `Tổng số mã đạt bộ lọc: **${items.length}** | Đầy đủ dữ liệu định giá: **${section1.length}** | Thiếu dữ liệu định giá: **${section2.length}**`,
    ``,
    `## Bảng Tổng quan Kết quả Bộ lọc`,
    ``,
    summaryTable,
    ``,
    `## Section 1 — Đạt chuẩn & Đầy đủ dữ liệu định giá (${section1.length})`,
    ``,
    section1.length ? section1.map(it => screenerStockDetail(it.symbol, it, reports[it.symbol])).join('\n\n') : '_Không có mã nào._',
    ``,
    `## Section 2 — Đạt chuẩn nhưng Thiếu dữ liệu định giá (${section2.length})`,
    ``,
    section2.length ? section2.map(it => screenerStockDetail(it.symbol, it, reports[it.symbol])).join('\n\n') : '_Không có mã nào._',
    ``,
    `---`,
    `*Generated ${generatedAt} · QPort screener AI export — data chi tiết overlay của từng mã được gợi ý.*`,
  ].join('\n');

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `qport-screener-ai-${generatedAt.slice(0, 10)}.md`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
  return anchor.download;
}
