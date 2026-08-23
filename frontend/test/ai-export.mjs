import { buildAIExportMarkdown } from '../src/lib/aiExport.js';

const dashboard = {
  philosophy: 'BUY_AND_HOLD_INFORMATION_SYSTEM',
  today: '2026-08-23',
  portfolio: {
    nav: 1_133_527_500,
    equity_value: 1_083_527_500,
    cash: 50_000_000,
    cost_value: 1_125_449_800,
    net_external_contributions: 1_175_449_800,
    total_pnl: -41_922_300,
    total_return: -0.035664,
    unrealized_pnl: -41_922_300,
    realized_pnl: 0,
    dividend_income: 0,
    fees_and_taxes: 0,
    reference_weights: {},
    positions: [
      {
        symbol: 'ACB', shares: 19_210, average_cost: 19_780, price: 22_750,
        cost_value: 379_973_800, market_value: 437_027_500,
        unrealized_pnl: 57_053_700, unrealized_return: 0.150153,
        weight: 0.38555, risk_contribution: 0.29699, erc_reference_weight: 0.33,
        status: 'HOLD', price_date: '2026-08-21', price_source: 'vndirect',
      },
      {
        symbol: 'DGC', shares: 10_000, average_cost: 52_340, price: 43_050,
        cost_value: 523_400_000, market_value: 430_500_000,
        unrealized_pnl: -92_900_000, unrealized_return: -0.177493,
        weight: 0.37978, risk_contribution: 0.55419, erc_reference_weight: 0.25,
        status: 'HOLD', price_date: '2026-08-21', price_source: 'vndirect',
      },
      {
        symbol: 'FPT', shares: 3_000, average_cost: 74_025, price: 72_000,
        cost_value: 222_075_000, market_value: 216_000_000,
        unrealized_pnl: -6_075_000, unrealized_return: -0.02736,
        weight: 0.19055, risk_contribution: 0.14909, erc_reference_weight: 0.42,
        status: 'HOLD', price_date: '2026-08-21', price_source: 'vndirect',
      },
    ],
  },
  health: {
    status: 'ATTENTION', current_drawdown: 0, max_drawdown: 0,
    flags: [{ level: 'WARNING', code: 'HHI', message: 'Portfolio concentration is high.' }],
  },
  market_data: { status: 'VALID', provider: { provider: 'auto' } },
  contribution_suggestions: {
    available_cash: 50_000_000, deployable_cash: 50_000_000,
    policy: 'EQUAL_WEIGHT_DEFICITS',
    suggestions: [{ symbol: 'FPT', action: 'ADD', amount: 50_000_000, current_weight: 0.19055, target_weight: 1 / 3 }],
  },
};

const performance = {
  first_date: '2026-08-21', latest_date: '2026-08-21', snapshot_count: 1, official_snapshot_count: 1,
  current_drawdown: 0, max_drawdown: 0, annualized_twr: null, xirr: null,
  returns: { daily: null, mtd: null, ytd: null, since_inception: 0 },
  best_day: null, worst_day: null, positive_day_ratio: null,
};

const risk = {
  status: 'VALID', volatility_63: 0.2188, volatility_252: 0.2577,
  max_position_weight: 0.38555, hhi: 0.36, effective_positions: 2.78,
  average_correlation: 0.31, max_correlation: 0.48, diversification_ratio: 1.24,
  largest_risk_symbol: 'DGC', largest_risk_contribution: 0.55419,
  risk_contribution_hhi: 0.42, daily_var_95: -0.021, daily_cvar_95: -0.031,
  max_daily_loss: -0.045, downside_volatility: 0.19, positive_day_ratio: 0.52,
  return_observations: 252, quality: { coverage_weight: 1 },
};

const snapshots = [{
  snapshot_date: '2026-08-21', official: true, data_quality: 'VALID',
  nav: 1_133_527_500, cash: 50_000_000, equity_value: 1_083_527_500,
  daily_pnl: null, daily_return: null, twr_index: 1, current_drawdown: 0,
}];

const transactions = [
  { id: 1, event_date: '2026-01-01', event_type: 'POSITION_IMPORT', symbol: 'ACB', quantity: 19_210, price: 19_780, amount: 0, fee: 0, tax: 0, ratio: 0, note: '', created_by: 'local' },
  { id: 2, event_date: '2026-08-20', event_type: 'CASH_DEPOSIT', symbol: null, quantity: 0, price: 0, amount: 50_000_000, fee: 0, tax: 0, ratio: 0, note: '', created_by: 'local' },
];

const markdown = buildAIExportMarkdown({
  dashboard, performance, risk, snapshots, transactions,
  generatedAt: '2026-08-23T04:49:00.000Z',
});

function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) process.exitCode = 1;
}

check('has stable schema', markdown.includes('qport-ai-export-v1'));
check('contains portfolio accounting', markdown.includes('1,133,527,500 VND') && markdown.includes('-41,922,300 VND'));
check('contains all holdings', markdown.includes('ACB') && markdown.includes('DGC') && markdown.includes('FPT'));
check('contains risk concentration', markdown.includes('DGC') && markdown.includes('55.42%'));
check('contains cash suggestion', markdown.includes('EQUAL_WEIGHT_DEFICITS') && markdown.includes('50,000,000 VND'));
check('contains immutable ledger', markdown.includes('POSITION_IMPORT') && markdown.includes('CASH_DEPOSIT'));
check('contains official snapshot history', markdown.includes('2026-08-21') && markdown.includes('TWR index'));
check('contains interpretation rules', markdown.includes('a loss alone is not a reason to average down'));
check('contains machine-readable JSON', markdown.includes('## Machine-readable payload') && markdown.includes('"schema_version": "qport-ai-export-v1"'));

if (!process.exitCode) console.log('\nAI EXPORT TEST PASSED');
