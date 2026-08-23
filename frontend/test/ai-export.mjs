import { buildAIExportMarkdown } from '../src/lib/aiExport.js';

const dashboard = {
  today: '2026-08-23',
  preferences: { cash_reserve_configured: true, cash_reserve: 20_000_000 },
  portfolio: {
    nav: 1_133_527_500, equity_value: 1_083_527_500, cash: 50_000_000,
    cost_value: 1_125_449_800, total_pnl: -41_922_300, accounting_return: -0.035664,
    unrealized_pnl: -41_922_300, realized_pnl: 0, dividend_income: 0,
    positions: [{ symbol: 'DGC', shares: 10_000, average_cost: 52_340, price: 43_050, cost_value: 523_400_000, market_value: 430_500_000, unrealized_pnl: -92_900_000, weight: .38, equity_weight: .397, risk_contribution: .5541, status: 'MONITOR' }],
  },
  market_data: { market_date: '2026-08-21' },
  data_lineage: { analytics: { status: 'UNVERIFIED' } },
  contribution_suggestions: { policy: 'NO_ALLOCATION_POLICY' },
};
const performance = { history_status: 'NO_HISTORY', latest_date: null, returns: { since_inception: null }, xirr: null, current_drawdown: null, methodology_policy: { policy_version: 'QPORT_PERF_V2', cost_method: 'FIFO_TAX_LOTS' } };
const risk = { status: 'VALID', volatility_252: .2577, equity_hhi: .3603, effective_positions: 2.78, largest_risk_symbol: 'DGC', largest_risk_contribution: .5541, daily_var_95: -.028, daily_cvar_95: -.037 };
const operations = {
  book_type: 'INSTITUTIONAL_LITE_IBOR', accounting_cost_method: 'FIFO_TAX_LOTS', position_recognition: 'TRADE_DATE',
  settlement: { settled_cash: 50_000_000, projected_cash: 50_000_000, unsettled_receivable: 0, unsettled_payable: 0, strategic_reserve: 20_000_000, available_to_invest: 30_000_000, trades: [] },
  tax_lots: [{ lot_id: 'DGC:1', symbol: 'DGC', acquisition_date: '2026-01-02', original_quantity: 10000, remaining_quantity: 10000, unit_cost: 52340, cost_basis: 523400000, account_id: 'PRIMARY' }],
  reconciliations: [{ id: 1, as_of_date: '2026-08-23', status: 'MATCH', qport_cash: 50000000, broker_cash: 50000000, cash_difference: 0 }],
  corporate_action_provider: { provider: 'vnstock_data', available: true },
  corporate_actions: [{ id: 7, symbol: 'DGC', action_type: 'CASH_DIVIDEND', record_date: '2026-09-01', expected_cash: 30000000, expected_shares: null, verification_status: 'VERIFIED', status: 'ENTITLEMENT_READY' }],
  exceptions: [{ severity: 'WARNING', code: 'RISK_CONCENTRATION', message: 'DGC concentration.' }],
  pnl_attribution: [{ symbol: 'DGC', unrealized_pnl: -92900000, realized_pnl: 0, dividend_income: 0, total_contribution_vnd: -92900000 }],
};
const transactions = [{ id: 1, event_date: '2026-08-23', event_type: 'POSITION_IMPORT', symbol: 'DGC', quantity: 10000, price: 52340, correction: { action: 'EDIT' } }];
const corrections = [{ id: 1, event_id: 1, action: 'EDIT', reason: 'Correct broker cost', created_at: '2026-08-23T05:00:00Z' }];

const markdown = buildAIExportMarkdown({ dashboard, performance, risk, operations, snapshots: [], transactions, corrections, generatedAt: '2026-08-23T05:00:00.000Z' });
function check(name, ok) { console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`); if (!ok) process.exitCode = 1; }
check('has v3 schema', markdown.includes('qport-ai-export-v3'));
check('contains institutional book identity', markdown.includes('INSTITUTIONAL_LITE_IBOR') && markdown.includes('FIFO_TAX_LOTS'));
check('contains settlement cash', markdown.includes('Settled cash') && markdown.includes('Available to invest'));
check('contains tax lots', markdown.includes('## Tax lots') && markdown.includes('DGC:1'));
check('contains reconciliation', markdown.includes('## Broker reconciliation') && markdown.includes('MATCH'));
check('contains corporate actions', markdown.includes('## Corporate actions') && markdown.includes('VERIFIED'));
check('contains operations exceptions', markdown.includes('## Operations exceptions'));
check('contains performance policy', markdown.includes('QPORT_PERF_V2'));
check('contains correction audit', markdown.includes('## Transaction correction audit') && markdown.includes('Correct broker cost'));
check('contains machine-readable institutional payload', markdown.includes('"operations"') && markdown.includes('"schema_version": "qport-ai-export-v3"'));
if (!process.exitCode) console.log('\nAI EXPORT V3 TEST PASSED');
