import React from 'react';
import RunList from '../components/RunList.jsx';

export default function HomePage({ runs }) {
  return (
    <div className="page">
      <div className="page-topbar">
        <header className="page-head">
          <h1>Shannon / ERC — Combination Backtest</h1>
          <p className="muted">
            Random 5–10 symbol portfolios allocated with Equal Risk Contribution and managed
            with Shannon drift-band rebalancing, starting 200M VND with 20M VND/year deposits.
          </p>
        </header>
        <a className="btn-export" href="/optimizer">Optimizer experiments →</a>
      </div>
      <div className="card">
        <h3>Runs ({runs.length})</h3>
        <RunList runs={runs} />
      </div>
    </div>
  );
}