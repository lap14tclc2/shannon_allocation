import React, { useMemo } from 'react';
import { formatMoney, formatPercent } from '../lib/format.js';
import EquityChart from './EquityChart.jsx';
import AllocationTable from './AllocationTable.jsx';
import YearlyAllocationTable from './YearlyAllocationTable.jsx';

const METRICS = [
  { label: 'Score', key: 'score', num: true, color: 'var(--accent)' },
  { label: 'Final NAV', key: 'final_nav', money: true, color: 'var(--success)' },
  { label: 'TWR ann', key: 'twr_annualized_pct', pct: true, color: 'var(--success)' },
  { label: 'XIRR', key: 'xirr_pct', pct: true },
  { label: 'Absolute Profit', key: 'absolute_profit', money: true, color: 'var(--success)' },
  { label: 'Sharpe', key: 'sharpe', num: true },
  { label: 'Sortino', key: 'sortino', num: true },
  { label: 'Calmar', key: 'calmar', num: true },
  { label: 'Max Drawdown', key: 'max_drawdown_pct', pct: true, color: 'var(--danger)' },
];

export default function CombinationDetail({ combo }) {
  const chartData = useMemo(
    () => (combo.nav_history || []).map(([date, nav]) => ({ date, nav })),
    [combo]
  );

  return (
    <div className="detail">
      <div className="detail-header">
        <h2>{combo.symbols.join(' ')}</h2>
        <div className="metric-grid">
          {METRICS.map((m) => (
            <div className="metric-card" key={m.key}>
              <div className="metric-label">{m.label}</div>
              <div className="metric-value" style={{ color: m.color }}>
                {m.money ? formatMoney(combo[m.key], true) : m.pct ? formatPercent(combo[m.key]) : combo[m.key]?.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
        {combo.annual_returns && Object.keys(combo.annual_returns).length > 0 && (
          <div className="annual-strip">
            <span className="annual-label">Annual returns (TWR)</span>
            {Object.entries(combo.annual_returns)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([y, v]) => (
                <span key={y} className={`tag tag-${Number(v) >= 0 ? 'buy' : 'sell'}`}>
                  {y}: {formatPercent(v)}
                </span>
              ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3>NAV over time</h3>
        <div className="chart">
          <EquityChart data={chartData} />
        </div>
      </div>

      <YearlyAllocationTable allocations={combo.allocations || []} />
      <AllocationTable allocations={combo.allocations || []} />
    </div>
  );
}