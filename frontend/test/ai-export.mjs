import { buildAIExportMarkdown } from '../src/lib/aiExport.js';

const dashboard = {
  philosophy: 'BUY_AND_HOLD_INFORMATION_SYSTEM',
  today: '2026-08-23',
  preferences: { cash_reserve_configured: false, cash_reserve: null, reference_weights: {} },
  portfolio: {
    nav: 1_133_527_500, equity_value: 1_083_527_500, cash: 50_000_000,
    cost_value: 1_125_449_800, net_external_contributions: 1_175_449_800,
    total_pnl: -41_922_300, accounting_return: -0.035664,
    unrealized_pnl: -41_922_300, realized_pnl: 0, dividend_income: 0, fees_and_taxes: 0,
    reference_weights: {},
    positions: [
      { symbol: 'ACB', shares: 19_210, average_cost: 19_780, price: 22_750, cost_value: 379_973_800, market_value: 437_027_500, unrealized_pnl: 57_053_700, unrealized_return: 0.150153, weight: 0.38555, equity_weight: 0.4033, risk_contribution: 0.29699, erc_reference_weight: 0.40, status: 'MONITOR', price_date: '2026-08-21', price_source: 'vndirect' },
      { symbol: 'DGC', shares: 10_000, average_cost: 52_340, price: 43_050, cost_value: 523_400_000, market_value: 430_500_000, unrealized_pnl: -92_900_000, unrealized_return: -0.177493, weight: 0.37978, equity_weight: 0.3973, risk_contribution: 0.55419, erc_reference_weight: 0.267, status: 'MONITOR', price_date: '2026-08-21', price_source: 'vndirect' },
      { symbol: 'FPT', shares: 3_000, average_cost: 74_025, price: 72_000, cost_value: 222_075_000, market_value: 216_000_000, unrealized_pnl: -6_075_000, unrealized_return: -0.02736, weight: 0.19055, equity_weight: 0.1994, risk_contribution: 0.14909, erc_reference_weight: 0.333, status: 'MONITOR', price_date: '2026-08-21', price_source: 'vndirect' },
    ],
  },
  health: {
    status: 'ATTENTION', current_drawdown: null, max_drawdown: null,
    flags: [{ level: 'WARNING', code: 'RISK_CONCENTRATION', message: 'DGC contributes 55.4% of portfolio risk.' }],
  },
  market_data: { status: 'VALID', market_date: '2026-08-21', aligned: true, calendar_age_days: 2, provider: { provider: 'auto' } },
  data_lineage: { analytics: { status: 'UNVERIFIED', corporate_action_adjusted: null } },
  contribution_suggestions: {
    available_cash: 50_000_000, strategic_cash_reserve: null, deployable_cash: null,
    policy: 'NO_ALLOCATION_POLICY', reason: 'Configure explicit strategic reference weights.', suggestions: [],
  },
};

const performance = {
  history_status: 'NO_HISTORY', first_date: null, latest_date: null,
  snapshot_count: 0, official_snapshot_count: 0,
  current_drawdown: null, max_drawdown: null, annualized_twr: null, xirr: null,
  xirr_status: 'UNAVAILABLE_OPENING_BALANCE', cashflow_history_quality: 'OPENING_BALANCE_ONLY',
  returns: { daily: null, mtd: null, ytd: null, since_inception: null },
};

const risk = {
  status: 'VALID', volatility_63: 0.2188, volatility_252: 0.2577,
  max_position_weight: 0.38555, max_equity_weight: 0.4033,
  equity_hhi: 0.3603, effective_positions: 2.78, effective_position_ratio: 0.926,
  average_correlation: 0.31, max_correlation: 0.48, diversification_ratio: 1.24,
  largest_risk_symbol: 'DGC', largest_risk_contribution: 0.55419,
  equal_risk_contribution: 1 / 3, risk_concentration_ratio: 1.6626,
  daily_var_95: -0.021, daily_cvar_95: -0.031, max_daily_loss: -0.045,
  downside_volatility: 0.19, return_observations: 252, quality: { coverage_weight: 1 },
  methodology: { concentration_basis: 'equity_normalized', annualization: 252 },
};

const transactions = [
  { id: 1, event_date: '2026-08-23', event_type: 'POSITION_IMPORT', symbol: 'ACB', quantity: 19_210, price: 19_780, amount: 0, fee: 0, tax: 0, ratio: 0, note: '', created_by: 'local', correction: { action: 'EDIT', reason: 'Correct price' } },
];
const corrections = [
  { id: 1, event_id: 1, action: 'EDIT', reason: 'Correct price', created_at: '2026-08-23T05:00:00Z', created_by: 'local', original: { event_type: 'POSITION_IMPORT', symbol: 'ACB', price: 19_700 } },
];

const markdown = buildAIExportMarkdown({
  dashboard, performance, risk, snapshots: [], transactions, corrections,
  generatedAt: '2026-08-23T05:00:00.000Z',
});

function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) process.exitCode = 1;
}

check('has v2 schema', markdown.includes('qport-ai-export-v2'));
check('separates as-of dates', markdown.includes('Portfolio state as of') && markdown.includes('Market data as of') && markdown.includes('Performance as of'));
check('uses accounting-return terminology', markdown.includes('Accounting return vs recorded capital'));
check('contains equity-normalized concentration', markdown.includes('Equity HHI') && markdown.includes('Effective-position ratio'));
check('contains DGC risk concentration', markdown.includes('DGC') && markdown.includes('55.42%'));
check('does not invent deployable cash', markdown.includes('NO_ALLOCATION_POLICY') && markdown.includes('Deployable cash: **-**'));
check('contains history and XIRR quality', markdown.includes('NO_HISTORY') && markdown.includes('UNAVAILABLE_OPENING_BALANCE'));
check('contains lineage and methodology', markdown.includes('## Data lineage') && markdown.includes('equity_normalized'));
check('explains MONITOR semantics', markdown.includes('MONITOR means no explicit strategic target'));
check('contains correction audit', markdown.includes('## Transaction correction audit') && markdown.includes('Correct price') && markdown.includes('"transaction_correction_audit"'));
check('contains machine-readable JSON', markdown.includes('## Machine-readable payload') && markdown.includes('"schema_version": "qport-ai-export-v2"'));

if (!process.exitCode) console.log('\nAI EXPORT V2 TEST PASSED');
