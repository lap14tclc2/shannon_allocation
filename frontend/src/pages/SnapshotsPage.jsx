import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney } from '../lib/format.js';

function money(v) { return v == null ? '-' : `${formatMoney(v)} VND`; }
function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function SnapshotsPage({ snapshots = [] }) {
  return (
    <div className="page">
      <AppNav active="Snapshots" />
      <header className="page-head">
        <h1>Daily snapshots</h1>
        <p className="muted">A snapshot is derived from the ledger plus stored market prices. Stale snapshots are visible but are not used as official performance evidence.</p>
      </header>

      <div className="card">
        {snapshots.length === 0 ? <div className="muted">No daily snapshots yet. Use “Sync daily prices” from Portfolio.</div> : (
          <div className="table-scroll"><table className="ranking">
            <thead><tr><th>Date</th><th>Status</th><th>NAV</th><th>Cash</th><th>Equity</th><th>Daily P/L</th><th>Daily return</th><th>Drawdown</th><th>Vol 252D</th><th>Positions</th></tr></thead>
            <tbody>{snapshots.map((s) => (
              <tr key={s.id || s.snapshot_date}>
                <td><b>{s.snapshot_date}</b></td>
                <td><span className={`status-pill status-${String(s.data_quality || 'missing').toLowerCase()}`}>{s.official ? 'OFFICIAL' : s.data_quality}</span></td>
                <td>{money(s.nav)}</td><td>{money(s.cash)}</td><td>{money(s.equity_value)}</td>
                <td className={Number(s.daily_pnl || 0) >= 0 ? 'pos' : 'neg'}>{money(s.daily_pnl)}</td>
                <td>{pct(s.daily_return)}</td><td>{pct(s.current_drawdown)}</td><td>{pct(s.volatility_252)}</td>
                <td>{(s.positions || []).length}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
