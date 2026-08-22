import React, { useEffect, useMemo, useState } from 'react';
import { formatMoney, formatPercent } from '../lib/format.js';
import { getCandidateHistory, optimizerFileUrl, deleteOptimizerExperiment } from '../lib/api.js';
import EquityChart from '../components/EquityChart.jsx';
import AllocationTable from '../components/AllocationTable.jsx';
import YearlyAllocationTable from '../components/YearlyAllocationTable.jsx';

function allocationLabel(item) {
  return `[${(item.allocation_days || []).join(', ')}]`;
}

function MetricRow({ label, value, digits = 2, pct = false }) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return (
    <div className="diag-row">
      <span>{label}</span>
      <b>{pct ? formatPercent(value, digits) : Number(value).toFixed(digits)}</b>
    </div>
  );
}

function CandidatePanel({ item, title }) {
  const m = item.metrics || {};
  const r = item.robust || {};
  const tr = item.timing_robust || {};
  const sr = item.symbol_robust || {};
  const conc = item.concentration || {};
  const test = item.test || {};
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="candidate-head">
        <span className="candidate-symbols">{item.symbols.join(' ')}</span>
        <span className="muted">N={item.n_symbols} · allocation {allocationLabel(item)}</span>
      </div>
      <div className="expand-grid">
        <div className="sub-card">
          <h4>Performance (NET)</h4>
          <MetricRow label="Net TWR annualized" value={m.net_twr_annualized_pct} pct />
          <MetricRow label="Net XIRR" value={m.net_xirr_pct} pct />
          <MetricRow label="Gross TWR annualized" value={m.gross_twr_annualized_pct} pct />
          <MetricRow label="Sharpe" value={m.sharpe} digits={3} />
          <MetricRow label="Sortino" value={m.sortino} digits={3} />
          <MetricRow label="Calmar" value={m.calmar} digits={3} />
          <MetricRow label="Max drawdown" value={m.max_drawdown_pct} pct />
          <MetricRow label="Worst year" value={m.worst_year} pct />
          <MetricRow label="Positive-year ratio" value={m.positive_year_ratio} digits={3} />
          <MetricRow label="Final NAV" value={m.final_nav} pct={false} digits={0} />
        </div>
        <div className="sub-card">
          <h4>Robustness (OOS validation)</h4>
          <MetricRow label="Median OOS net TWR" value={r.median_net_twr} pct />
          <MetricRow label="P10 OOS net TWR" value={r.p10_net_twr} pct />
          <MetricRow label="Worst OOS net TWR" value={r.worst_net_twr} pct />
          <MetricRow label="Return std" value={r.return_std} />
          <MetricRow label="Median OOS Sharpe" value={r.median_sharpe} digits={3} />
          <MetricRow label="Worst OOS MDD" value={r.worst_mdd} pct />
          <MetricRow label="Positive-window ratio" value={r.positive_window_ratio} digits={3} />
          <MetricRow label="Robust return" value={r.robust_return} pct />
          <MetricRow label="Test median net TWR" value={test.median_net_twr} pct />
          <div className="diag-row">
            <span>Timing neighbourhood</span>
            <b>{tr.mean != null ? `${tr.mean}%` : '-'} {tr.isolated_spike ? '(⚠ spike)' : ''}</b>
          </div>
          <div className="diag-row">
            <span>Symbol neighbourhood</span>
            <b>{sr.mean != null ? `${sr.mean}%` : '-'}</b>
          </div>
          <div className="diag-row">
            <span>Concentration</span>
            <b>{conc.single_stock ? 'single-stock!' : 'ok'} / {conc.single_year ? 'single-year!' : 'ok'}</b>
          </div>
        </div>
      </div>
      <div className="diag-grid">
        <div className="sub-card">
          <h4>Trading</h4>
          <MetricRow label="Turnover" value={m.turnover_pct} pct />
          <MetricRow label="Trade count" value={m.trade_count} digits={0} />
          <MetricRow label="Transaction cost" value={m.transaction_cost} digits={0} />
          <MetricRow label="Cost % of NAV" value={m.cost_pct_of_nav} pct />
        </div>
        <div className="sub-card">
          <h4>Test windows (untouched OOS)</h4>
          <MetricRow label="Median net TWR" value={test.median_net_twr} pct />
          <MetricRow label="Windows" value={test.n_test_windows} digits={0} />
        </div>
      </div>
    </div>
  );
}

function CandidateTable({ items, selected, onSelect, title }) {
  return (
    <div className="card">
      <h3>{title} ({items.length})</h3>
      <table className="ranking">
        <thead>
          <tr>
            <th>Symbols</th>
            <th>N</th>
            <th>Allocation days</th>
            <th>Net TWR ann</th>
            <th>Sharpe</th>
            <th>MDD</th>
            <th>Robust return</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it, i) => {
            const key = `${it.symbols.join('|')}::${it.allocation_days.join(',')}`;
            const m = it.metrics || {};
            const r = it.robust || {};
            return (
              <tr key={key} className={selected === key ? 'row-selected' : ''} onClick={() => onSelect(key)}>
                <td className="symbols-cell">{it.symbols.join(' ')}</td>
                <td>{it.n_symbols}</td>
                <td>{it.allocation_days.join(', ')}</td>
                <td className={Number(m.net_twr_annualized_pct) >= 0 ? 'pos' : 'neg'}>{formatPercent(m.net_twr_annualized_pct)}</td>
                <td className="num">{m.sharpe?.toFixed(2)}</td>
                <td className="neg">{formatPercent(m.max_drawdown_pct)}</td>
                <td className={Number(r.robust_return) >= 0 ? 'pos' : 'neg'}>{r.robust_return != null ? formatPercent(r.robust_return) : '-'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function OptimizerDetailPage({ experiment }) {
  const [selected, setSelected] = useState(() => {
    const wr = experiment.winners?.best_robust;
    return wr ? `${wr.symbols.join('|')}::${wr.allocation_days.join(',')}` : '';
  });
  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState('');

  const lookup = useMemo(() => {
    const map = {};
    const add = (it) => {
      map[`${it.symbols.join('|')}::${it.allocation_days.join(',')}`] = it;
    };
    (experiment.winners ? Object.values(experiment.winners) : []).forEach(add);
    (experiment.pareto || []).forEach(add);
    (experiment.top_candidates || []).forEach(add);
    return map;
  }, [experiment]);

  useEffect(() => {
    const it = lookup[selected];
    if (!it) {
      setHistory(null);
      return;
    }
    let cancelled = false;
    setHistory(null);
    setHistoryError('');
    getCandidateHistory(experiment.experiment_id, it.symbols, it.allocation_days)
      .then((h) => !cancelled && setHistory(h))
      .catch((err) => !cancelled && setHistoryError(err.message));
    return () => {
      cancelled = true;
    };
  }, [experiment, selected, lookup]);

  const chartData = useMemo(
    () => (history?.nav_history || []).map(([date, nav]) => ({ date, nav })),
    [history]
  );

  const selectedItem = lookup[selected];

  const winners = experiment.winners || {};
  const winnerLabels = {
    best_return: 'Best Return',
    best_risk_adjusted: 'Best Risk-Adjusted',
    best_low_drawdown: 'Best Low-Drawdown',
    best_robust: 'Best Robust',
  };

  return (
    <div className="page">
      <div className="page-topbar">
        <div className="breadcrumb">
          <a href="/">All runs</a> <span>/</span>
          <a href="/optimizer">Optimizer</a> <span>/</span> {experiment.experiment_id}
        </div>
        <button
          className="btn-remove"
          onClick={async () => {
            if (!window.confirm(`Delete optimizer experiment ${experiment.experiment_id}?\nThis removes its reports and data.`)) return;
            try {
              const res = await deleteOptimizerExperiment(experiment.experiment_id);
              if (res.ok) window.location.href = '/optimizer';
              else window.alert(res.error || 'Delete failed.');
            } catch (err) {
              window.alert(err.message);
            }
          }}
        >
          ✕ Remove experiment
        </button>
      </div>
      <header className="page-head">
        <h1>Optimizer experiment {experiment.experiment_id}</h1>
        <p className="muted">
          seed {experiment.meta?.seed} · {experiment.meta?.universe?.length} symbols ·
          {experiment.meta?.n_windows} windows · costs{' '}
          {JSON.stringify(experiment.meta?.cost_config || {})}
        </p>
        <div className="report-links">
          <a href={optimizerFileUrl(experiment.experiment_id, 'candidate_metrics.csv')} download>candidate_metrics.csv</a>
          <a href={optimizerFileUrl(experiment.experiment_id, 'pareto_frontier.csv')} download>pareto_frontier.csv</a>
          <a href={optimizerFileUrl(experiment.experiment_id, 'optimizer_config.json')} download>optimizer_config.json</a>
          <a href={optimizerFileUrl(experiment.experiment_id, 'optimizer_summary.csv')} download>optimizer_summary.csv</a>
        </div>
      </header>

      <div className="metric-grid">
        {Object.entries(winners).map(([key, it]) => (
          <div
            key={key}
            className={`metric-card winner-card ${selected && selected.startsWith(it.symbols.join('|')) ? 'winner-selected' : ''}`}
            onClick={() => setSelected(`${it.symbols.join('|')}::${it.allocation_days.join(',')}`)}
          >
            <div className="metric-label">{winnerLabels[key] || key}</div>
            <div className="candidate-head">
              <span className="candidate-symbols">{it.symbols.join(' ')}</span>
              <span className="muted">{allocationLabel(it)}</span>
            </div>
            <div className="metric-value" style={{ color: 'var(--accent)' }}>
              {formatPercent(it.robust?.robust_return ?? it.metrics?.net_twr_annualized_pct)}
            </div>
            <div className="muted">
              OOS med {formatPercent(it.robust?.median_net_twr)} · MDD {formatPercent(it.metrics?.max_drawdown_pct)} · Sharpe {it.metrics?.sharpe?.toFixed(2)}
            </div>
          </div>
        ))}
      </div>

      {selectedItem && <CandidatePanel item={selectedItem} title="Selected candidate" />}

      {selectedItem && (
        <div className="card">
          <h3>Allocation history — {selectedItem.symbols.join(' ')}</h3>
          {historyError ? (
            <div className="error">Failed to load history: {historyError}</div>
          ) : !history ? (
            <div className="muted">Generating allocation history…</div>
          ) : (
            <>
              <div className="chart">
                <EquityChart data={chartData} />
              </div>
              <YearlyAllocationTable allocations={history.allocations || []} />
              <AllocationTable allocations={history.allocations || []} />
            </>
          )}
        </div>
      )}

      <CandidateTable
        items={experiment.pareto || []}
        selected={selected}
        onSelect={setSelected}
        title="Pareto frontier (non-dominated)"
      />
      <CandidateTable
        items={(experiment.top_candidates || []).slice(0, 25)}
        selected={selected}
        onSelect={setSelected}
        title="Top candidates (by robust return)"
      />
    </div>
  );
}