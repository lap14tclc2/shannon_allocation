import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';

function money(v) { return v == null ? '-' : `${formatMoney(v)} VND`; }
function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

function Metric({ label, value, note, tone = '' }) {
  return (
    <div className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note && <div className="muted">{note}</div>}
    </div>
  );
}

export default function PortfolioDashboardPage({ dashboard: initialDashboard }) {
  const [dashboard, setDashboard] = useState(initialDashboard || {});
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const snapshot = dashboard.latest_snapshot || {};
  const risk = dashboard.risk || {};
  const market = dashboard.market_data || {};
  const suggestions = dashboard.contribution_suggestions || {};

  async function sync() {
    setSyncing(true);
    setMessage('');
    try {
      const result = await syncPortfolio();
      setMessage(result.message || 'Daily sync completed.');
      window.location.reload();
    } catch (err) {
      setMessage(`Sync failed: ${err.message}`);
      setSyncing(false);
    }
  }

  return (
    <div className="page">
      <AppNav active="Portfolio" />
      <header className="page-head portfolio-head">
        <div>
          <h1>Portfolio</h1>
          <p className="muted">Buy &amp; Hold portfolio information. Market data and risk signals never change holdings automatically.</p>
        </div>
        <button className="btn-export" type="button" onClick={sync} disabled={syncing}>
          {syncing ? 'Syncing market data…' : '↻ Sync daily prices'}
        </button>
      </header>

      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid portfolio-metrics">
        <Metric label="NAV" value={money(portfolio.nav || 0)} note={snapshot.snapshot_date ? `Snapshot ${snapshot.snapshot_date}` : 'No snapshot yet'} />
        <Metric label="Equity" value={money(portfolio.equity_value || 0)} note={`${positions.length} holding${positions.length === 1 ? '' : 's'}`} />
        <Metric label="Cash" value={money(portfolio.cash || 0)} note={portfolio.nav ? `${pct((portfolio.cash || 0) / portfolio.nav)} of NAV` : '—'} />
        <Metric label="Total P/L" value={money(snapshot.total_pnl ?? 0)} tone={Number(snapshot.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'} note={`Realized ${money(portfolio.realized_pnl || 0)}`} />
        <Metric label="Current drawdown" value={pct(snapshot.current_drawdown)} note={`Max ${pct(snapshot.max_drawdown)}`} />
        <Metric label="252D volatility" value={pct(risk.volatility_252)} note={`Risk data ${risk.status || 'UNAVAILABLE'}`} />
      </div>

      <div className="card">
        <div className="section-head">
          <div>
            <h3>Holdings</h3>
            <div className="muted">Shares come only from the immutable transaction ledger.</div>
          </div>
          <div className={`status-pill status-${String(market.status || 'MISSING').toLowerCase()}`}>
            Data {market.status || 'MISSING'}
          </div>
        </div>

        {positions.length === 0 ? (
          <div className="empty-state">
            <h3>No holdings yet</h3>
            <p>Import your opening positions or record cash/trades first. The system will not invent a portfolio.</p>
            <a className="btn-export" href="/transactions">Add opening positions</a>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="ranking portfolio-table">
              <thead><tr>
                <th>Ticker</th><th>Shares</th><th>Avg cost</th><th>Price</th><th>Value</th><th>Weight</th><th>Unrealized P/L</th><th>Risk contrib.</th><th>Status</th>
              </tr></thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.symbol}>
                    <td className="symbols-cell"><b>{p.symbol}</b><div className="muted">{p.price_date || '-'} · {p.price_source || '-'}</div></td>
                    <td>{formatShares(p.shares)}</td>
                    <td>{money(p.average_cost)}</td>
                    <td>{money(p.price)}</td>
                    <td>{money(p.market_value)}</td>
                    <td>{formatWeight(p.weight)}</td>
                    <td className={Number(p.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}>{money(p.unrealized_pnl)}<div className="muted">{pct(p.unrealized_return)}</div></td>
                    <td>{pct(p.risk_contribution)}</td>
                    <td><span className={`signal signal-${String(p.status || 'HOLD').toLowerCase()}`}>{p.status || 'HOLD'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="expand-grid">
        <div className="card">
          <h3>Portfolio health</h3>
          <div className="diag-row"><span>Risk status</span><b>{risk.status || 'UNAVAILABLE'}</b></div>
          <div className="diag-row"><span>63D volatility</span><b>{pct(risk.volatility_63)}</b></div>
          <div className="diag-row"><span>252D volatility</span><b>{pct(risk.volatility_252)}</b></div>
          <div className="diag-row"><span>Largest position</span><b>{pct(risk.max_position_weight)}</b></div>
          <div className="diag-row"><span>HHI concentration</span><b>{risk.hhi == null ? '-' : Number(risk.hhi).toFixed(3)}</b></div>
          <div className="muted" style={{ marginTop: 10 }}>Risk is informational only. It does not reduce equity exposure or create SELL orders.</div>
        </div>

        <div className="card">
          <h3>Deploy existing cash</h3>
          <div className="muted">BUY-only suggestion · {suggestions.policy || '—'} · no trade is created automatically.</div>
          {(suggestions.suggestions || []).length === 0 ? (
            <p>No contribution-directed additions are suggested.</p>
          ) : (
            <div className="suggestion-list">
              {suggestions.suggestions.slice(0, 6).map((s) => (
                <div className="diag-row" key={s.symbol}>
                  <span><b>{s.symbol}</b> · {pct(s.current_weight)} → ref {pct(s.target_weight)}</span>
                  <b>{money(s.amount)}</b>
                </div>
              ))}
            </div>
          )}
          <div className="diag-row"><span>Available cash</span><b>{money(suggestions.available_cash || 0)}</b></div>
        </div>
      </div>

      <div className="card invariant-card">
        <h3>Operational invariants</h3>
        <div className="invariant-grid">
          {(dashboard.invariants || []).map((x) => <div key={x}>✓ {x}</div>)}
        </div>
      </div>
    </div>
  );
}
