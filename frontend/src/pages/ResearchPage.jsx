import React from 'react';
import AppNav from '../components/AppNav.jsx';

export default function ResearchPage({ experiments = [], runs = [] }) {
  return (
    <div className="page">
      <AppNav active="Research" />
      <header className="page-head">
        <h1>Research Lab</h1>
        <p className="muted">Backtests, Dynamic Alpha and optimizers are isolated research tools. They can produce evidence or proposals, but cannot mutate the operational portfolio ledger.</p>
      </header>

      <div className="card research-boundary">
        <h3>Research → Human approval → Portfolio</h3>
        <div className="boundary-flow">
          <span>Backtest / Optimizer</span><b>→</b><span>Proposal only</span><b>→</b><span>User decision</span><b>→</b><span>Explicit ledger event</span>
        </div>
        <p className="muted">There is deliberately no API from research results to automatic BUY/SELL execution.</p>
      </div>

      <div className="expand-grid">
        <div className="card">
          <div className="section-head"><div><h3>Optimizer experiments</h3><div className="muted">Legacy quant research retained for analysis.</div></div><a className="btn-export" href="/research/optimizer">Open optimizer</a></div>
          {experiments.length === 0 ? <p className="muted">No optimizer experiments.</p> : (
            <ul className="run-list">{experiments.slice(0, 10).map((e) => (
              <li key={e.experiment_id}><div className="run-link"><a href={`/research/optimizer/${e.experiment_id}`}>{e.experiment_id}</a><span className="muted">{e.generated_at || '-'} · {e.mode || 'research'}</span></div></li>
            ))}</ul>
          )}
        </div>

        <div className="card">
          <h3>Historical backtest runs</h3>
          {runs.length === 0 ? <p className="muted">No legacy backtest runs.</p> : (
            <ul className="run-list">{runs.slice(0, 10).map((r) => (
              <li key={r.run_id}><div className="run-link"><a href={`/runs/${r.run_id}`}>{r.run_id}</a><span className="muted">{r.generated_at || '-'}</span></div></li>
            ))}</ul>
          )}
        </div>
      </div>
    </div>
  );
}
