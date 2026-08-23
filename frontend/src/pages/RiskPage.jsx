import React from 'react';
import AppNav from '../components/AppNav.jsx';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function RiskPage({ risk = {} }) {
  const contributions = risk.risk_contributions || {};
  const erc = risk.erc_reference_weights || {};
  const symbols = [...new Set([...Object.keys(contributions), ...Object.keys(erc)])].sort();
  const quality = risk.quality || {};

  return (
    <div className="page">
      <AppNav active="Risk" />
      <header className="page-head">
        <h1>Risk</h1>
        <p className="muted">Information only. Risk metrics may trigger REVIEW, but never automatic deleveraging or SELL.</p>
      </header>

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">Risk status</div><div className="metric-value">{risk.status || 'UNAVAILABLE'}</div></div>
        <div className="metric-card"><div className="metric-label">63D volatility</div><div className="metric-value">{pct(risk.volatility_63)}</div></div>
        <div className="metric-card"><div className="metric-label">252D volatility</div><div className="metric-value">{pct(risk.volatility_252)}</div></div>
        <div className="metric-card"><div className="metric-label">Largest position</div><div className="metric-value">{pct(risk.max_position_weight)}</div></div>
        <div className="metric-card"><div className="metric-label">HHI</div><div className="metric-value">{risk.hhi == null ? '-' : Number(risk.hhi).toFixed(3)}</div></div>
        <div className="metric-card"><div className="metric-label">Coverage</div><div className="metric-value">{pct(quality.coverage_weight)}</div></div>
      </div>

      <div className="card">
        <h3>Risk contribution &amp; ERC reference</h3>
        <p className="muted">ERC is a diagnostic reference only; it is not an allocation schedule and does not create trades.</p>
        {symbols.length === 0 ? <div className="muted">Not enough stored market history for portfolio risk decomposition.</div> : (
          <table className="ranking">
            <thead><tr><th>Ticker</th><th>Current risk contribution</th><th>Equal-risk reference</th><th>Interpretation</th></tr></thead>
            <tbody>{symbols.map((s) => {
              const rc = contributions[s];
              const ew = erc[s];
              const interpretation = rc == null ? 'NO DATA' : Number(rc) > 0.35 ? 'HIGH RISK CONTRIBUTION' : 'NORMAL';
              return <tr key={s}><td><b>{s}</b></td><td>{pct(rc)}</td><td>{pct(ew)}</td><td>{interpretation}</td></tr>;
            })}</tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h3>Data quality</h3>
        <div className="diag-row"><span>As of</span><b>{risk.as_of || '-'}</b></div>
        <div className="diag-row"><span>Requested symbols</span><b>{quality.requested_symbols ?? '-'}</b></div>
        <div className="diag-row"><span>Eligible symbols</span><b>{quality.eligible_symbols ?? '-'}</b></div>
        <div className="diag-row"><span>Missing covariance cells</span><b>{quality.missing_covariance_cells ?? '-'}</b></div>
        {(quality.missing_symbols || []).length > 0 && <div className="run-message">Missing history: {quality.missing_symbols.join(', ')}</div>}
      </div>
    </div>
  );
}
