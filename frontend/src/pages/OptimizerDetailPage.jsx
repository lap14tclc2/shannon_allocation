import React, { useEffect, useMemo, useState } from 'react';
import { formatMoney, formatPercent } from '../lib/format.js';
import { getCandidateHistory, optimizerDownloadAllUrl, deleteOptimizerExperiment } from '../lib/api.js';
import EquityChart from '../components/EquityChart.jsx';
import AllocationTable from '../components/AllocationTable.jsx';
import YearlyAllocationTable from '../components/YearlyAllocationTable.jsx';

function allocationLabel(item) {
  return `[${(item.allocation_days || []).join(', ')}]`;
}

function MetricRow({ label, value, digits = 2, pct = false, money = false }) {
  if (value == null || Number.isNaN(Number(value))) return null;
  let rendered = Number(value).toFixed(digits);
  if (pct) rendered = formatPercent(value, digits);
  if (money) rendered = formatMoney(value);
  return (
    <div className="diag-row">
      <span>{label}</span>
      <b>{rendered}</b>
    </div>
  );
}

function CapitalDeploymentPanel({ history, capitalConfig }) {
  const contributions = history?.capital_events || [];
  const deployments = history?.deployment_events || [];
  const totalContributed = contributions.reduce((sum, e) => sum + Number(e.amount || 0), 0);
  const initial = Number(capitalConfig?.initial_balance || 0);
  const annual = Number(capitalConfig?.annual_deposit || 0);

  return (
    <div className="sub-card" style={{ marginBottom: 16 }}>
      <h4>Capital contributions & deployment</h4>
      <p className="muted">
        A contribution date means cash became available. A deployment date means an order actually executed and moved cash into or out of equities. They are intentionally tracked separately.
      </p>
      <div className="diag-grid" style={{ marginBottom: 14 }}>
        <div><span>Initial capital</span><b>{formatMoney(initial)}</b></div>
        <div><span>Annual contribution</span><b>{formatMoney(annual)}</b></div>
        <div><span>Total contributed in history</span><b>{formatMoney(totalContributed)}</b></div>
        <div><span>Final NAV</span><b>{formatMoney(history?.metrics?.final_nav || 0)}</b></div>
      </div>

      <h4>Money added</h4>
      {contributions.length === 0 ? <div className="muted">No contribution events recorded.</div> : (
        <table className="ranking" style={{ marginBottom: 16 }}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Cash immediately after</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {contributions.map((e, i) => (
              <tr key={`${e.date}-${e.type}-${i}`}>
                <td>{e.date}</td>
                <td>{e.type === 'INITIAL_CAPITAL' ? 'Initial capital' : 'Annual contribution'}</td>
                <td>{formatMoney(e.amount)}</td>
                <td>{formatMoney(e.cash_after)}</td>
                <td className="muted">{e.note || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Money actually deployed / released</h4>
      {deployments.length === 0 ? <div className="muted">No executed deployment events recorded.</div> : (
        <table className="ranking">
          <thead>
            <tr>
              <th>Signal</th>
              <th>Execution</th>
              <th>Event</th>
              <th>BUY cash deployed</th>
              <th>SELL cash released</th>
              <th>Net deployed</th>
              <th>Cash after</th>
            </tr>
          </thead>
          <tbody>
            {deployments.map((e, i) => (
              <tr key={`${e.execution_date}-${e.kind}-${i}`}>
                <td>{e.signal_date}</td>
                <td>{e.execution_date}</td>
                <td>{e.kind}</td>
                <td>{formatMoney(e.buy_cash_deployed)}</td>
                <td>{formatMoney(e.sell_cash_released)}</td>
                <td className={Number(e.net_cash_deployed) >= 0 ? 'pos' : 'neg'}>{formatMoney(e.net_cash_deployed)}</td>
                <td>{formatMoney(e.cash_after)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function CandidatePanel({ item, title }) {
  const m = item.metrics || {};
  const r = item.robust || {};
  const recent = item.recent_validation || {};
  const tr = item.timing_robust || {};
  const sr = item.symbol_robust || {};
  const conc = item.concentration || {};
  const test = item.test || {};
  const testPeriod = (test.per_window || [])[0] || {};
  const eligibilityReasons = item.eligibility_reasons || [];

  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="candidate-head">
        <span className="candidate-symbols">{item.symbols.join(' ')}</span>
        <span className="muted">N={item.n_symbols} · allocation {allocationLabel(item)}</span>
      </div>

      <div className="sub-card" style={{ marginBottom: 14 }}>
        <h4>Live eligibility</h4>
        <div className="diag-row">
          <span>Research-to-live gate</span>
          <b className={item.live_eligible ? 'pos' : 'neg'}>{item.live_eligible ? 'PASS' : 'FAIL'}</b>
        </div>
        <div className="muted" style={{ marginTop: 6 }}>
          This gate does not change ERC, Shannon, volatility targeting, NSGA-II objectives, or robust-return ranking. It only blocks weak research candidates from being proposed for live deployment.
        </div>
        {!item.live_eligible && eligibilityReasons.length > 0 && (
          <div className="muted" style={{ marginTop: 6 }}>Reasons: {eligibilityReasons.join(' · ')}</div>
        )}
      </div>

      <div className="expand-grid">
        <div className="sub-card">
          <h4>TRAIN (optimization window)</h4>
          <MetricRow label="Net TWR annualized" value={m.net_twr_annualized_pct} pct />
          <MetricRow label="Net XIRR (window anchored)" value={m.net_xirr_pct} pct />
          <MetricRow label="Gross TWR annualized" value={m.gross_twr_annualized_pct} pct />
          <MetricRow label="Sharpe" value={m.sharpe} digits={3} />
          <MetricRow label="Sortino" value={m.sortino} digits={3} />
          <MetricRow label="Calmar" value={m.calmar} digits={3} />
          <MetricRow label="Max drawdown" value={m.max_drawdown_pct} pct />
          <MetricRow label="Worst year" value={m.worst_year} pct />
          <MetricRow label="Positive-year ratio" value={m.positive_year_ratio} digits={3} />
          <MetricRow label="Measurement start NAV" value={m.measurement_start_nav} money />
          <MetricRow label="External contributions" value={m.measurement_external_contributions} money />
          <MetricRow label="Measured profit" value={m.measurement_profit} money />
          <MetricRow label="Final NAV" value={m.final_nav} money />
        </div>
        <div className="sub-card">
          <h4>Rolling OOS validation</h4>
          <MetricRow label="Median OOS net TWR" value={r.median_net_twr} pct />
          <MetricRow label="P10 OOS net TWR" value={r.p10_net_twr} pct />
          <MetricRow label="Worst OOS net TWR" value={r.worst_net_twr} pct />
          <MetricRow label="Return std" value={r.return_std} />
          <MetricRow label="Median OOS Sharpe" value={r.median_sharpe} digits={3} />
          <MetricRow label="Worst OOS MDD" value={r.worst_mdd} pct />
          <MetricRow label="Positive-window ratio" value={r.positive_window_ratio} digits={3} />
          <MetricRow label="Robust return" value={r.robust_return} pct />
          <div className="diag-row">
            <span>Timing neighbourhood</span>
            <b>{tr.mean != null ? `${tr.mean}%` : (tr.note || '-')} {tr.isolated_spike ? '(⚠ spike)' : ''}</b>
          </div>
          <div className="diag-row">
            <span>Symbol neighbourhood</span>
            <b>{sr.mean != null ? `${sr.mean}%` : (sr.note || '-')}</b>
          </div>
          <div className="diag-row">
            <span>Concentration</span>
            <b>{conc.single_stock ? 'single-stock!' : 'ok'} / {conc.single_year ? 'single-year!' : 'ok'}</b>
          </div>
        </div>
      </div>

      <div className="expand-grid" style={{ marginTop: 14 }}>
        <div className="sub-card">
          <h4>Recent pre-holdout validation</h4>
          <div className="muted" style={{ marginBottom: 8 }}>Eligibility-only window ending immediately before the untouched final holdout. It is not added to the robust-return score.</div>
          <MetricRow label="Net TWR annualized" value={recent.net_twr_annualized_pct} pct />
          <MetricRow label="Net XIRR" value={recent.net_xirr_pct} pct />
          <MetricRow label="Sharpe" value={recent.sharpe} digits={3} />
          <MetricRow label="MDD" value={recent.max_drawdown_pct} pct />
          <MetricRow label="CDaR95" value={recent.cdar95_pct} pct />
        </div>
        <div className="sub-card">
          <h4>Final untouched holdout</h4>
          <MetricRow label="Net TWR annualized" value={test.median_net_twr} pct />
          <MetricRow label="Net XIRR (window anchored)" value={testPeriod.net_xirr_pct} pct />
          <MetricRow label="Measurement start NAV" value={testPeriod.measurement_start_nav} money />
          <MetricRow label="External contributions" value={testPeriod.measurement_external_contributions} money />
          <MetricRow label="Measured profit" value={testPeriod.measurement_profit} money />
          <MetricRow label="Final NAV" value={testPeriod.final_nav} money />
          <MetricRow label="MDD" value={test.worst_mdd} pct />
          <MetricRow label="CDaR95" value={test.worst_cdar95} pct />
          <div className="diag-row">
            <span>Holdout valid</span>
            <b>{test.valid ? `${test.n_test_windows}/${test.required_test_windows} PASS` : `${test.n_test_windows || 0}/${test.required_test_windows || 1} INVALID`}</b>
          </div>
        </div>
      </div>

      <div className="diag-grid" style={{ marginTop: 14 }}>
        <div className="sub-card">
          <h4>Trading</h4>
          <MetricRow label="Turnover" value={m.turnover_pct} pct />
          <MetricRow label="Trade count" value={m.trade_count} digits={0} />
          <MetricRow label="Transaction cost" value={m.transaction_cost} money />
          <MetricRow label="Cost % of NAV" value={m.cost_pct_of_nav} pct />
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
            <th>Live</th>
            <th>Allocation days</th>
            <th>Net TWR ann</th>
            <th>Sharpe</th>
            <th>MDD</th>
            <th>Robust return</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => {
            const key = `${it.symbols.join('|')}::${it.allocation_days.join(',')}`;
            const m = it.metrics || {};
            const r = it.robust || {};
            return (
              <tr key={key} className={selected === key ? 'row-selected' : ''} onClick={() => onSelect(key)}>
                <td className="symbols-cell">{it.symbols.join(' ')}</td>
                <td>{it.n_symbols}</td>
                <td className={it.live_eligible ? 'pos' : 'neg'}>{it.live_eligible ? 'PASS' : 'FAIL'}</td>
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
    const wr = experiment.winners?.best_live_eligible || experiment.winners?.best_robust;
    return wr ? `${wr.symbols.join('|')}::${wr.allocation_days.join(',')}` : '';
  });
  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState('');

  const lookup = useMemo(() => {
    const map = {};
    const add = (it) => {
      if (!it) return;
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
    const controller = new AbortController();
    setHistory(null);
    setHistoryError('');
    getCandidateHistory(experiment.experiment_id, it.symbols, it.allocation_days, controller.signal)
      .then((h) => setHistory(h))
      .catch((err) => {
        if (err.name !== 'AbortError') setHistoryError(err.message);
      });
    return () => controller.abort();
  }, [experiment, selected, lookup]);

  const chartData = useMemo(
    () => (history?.nav_history || []).map(([date, nav]) => ({ date, nav })),
    [history]
  );

  const selectedItem = lookup[selected];
  const capitalConfig = experiment.meta?.capital_config || {};
  const eligibilityConfig = experiment.meta?.live_eligibility || {};
  const winners = experiment.winners || {};
  const winnerLabels = {
    best_return: 'Best Return',
    best_risk_adjusted: 'Best Risk-Adjusted',
    best_low_drawdown: 'Best Low-Drawdown',
    best_robust: 'Best Robust (Research)',
    best_live_eligible: 'Best Live-Eligible',
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
        <h1>
          Optimizer experiment {experiment.experiment_id}
          {(() => {
            const v = experiment.meta?.universe_variant
              || (experiment.meta?.universe?.length === 30 ? 'vn30'
                : experiment.meta?.universe?.length === 50 ? 'vn50'
                : experiment.meta?.universe?.length >= 80 ? 'vn100' : 'all');
            const label = v === 'all' ? `All data (${experiment.meta?.universe?.length})` : v.toUpperCase();
            const pill = v === 'all' ? '' : ` pill-${v}`;
            return <span className={`universe-pill${pill}`}>{label}</span>;
          })()}
        </h1>
        <p className="muted">
          seed {experiment.meta?.seed} · {experiment.meta?.universe?.length} symbols ·
          {experiment.meta?.n_windows} rolling windows · {experiment.meta?.mode === 'timing' ? 'timing-only' : 'joint (symbols+timing)'} ·
          CPU workers {experiment.meta?.parallel_workers || 1} · initial {formatMoney(capitalConfig.initial_balance || 0)} · annual {formatMoney(capitalConfig.annual_deposit || 0)}
        </p>
        <p className="muted">
          Live gate: TRAIN ≥ {formatPercent(eligibilityConfig.min_train_twr_pct ?? 0)} · validation P10 ≥ {formatPercent(eligibilityConfig.min_validation_p10_twr_pct ?? 0)} · recent validation ≥ {formatPercent(eligibilityConfig.min_recent_twr_pct ?? 0)} · eligible {eligibilityConfig.eligible_candidates ?? 0} candidate(s).
        </p>
        <div className="report-links">
          <a className="btn-export" href={optimizerDownloadAllUrl(experiment.experiment_id)}>
            ⬇ Download all data (ZIP)
          </a>
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
              Live {it.live_eligible ? 'PASS' : 'FAIL'} · OOS med {formatPercent(it.robust?.median_net_twr)} · MDD {formatPercent(it.metrics?.max_drawdown_pct)} · Sharpe {it.metrics?.sharpe?.toFixed(2)}
            </div>
          </div>
        ))}
      </div>

      {selectedItem && <CandidatePanel item={selectedItem} title="Selected candidate" />}

      {(() => {
        const br = experiment.winners?.best_live_eligible || experiment.winners?.best_robust;
        if (!experiment.baseline || !br) return null;
        return (
          <div className="card">
            <h3>Quarterly baseline comparison (same symbols)</h3>
            <p className="muted">
              Standard four-times-per-year schedule <code>[{(experiment.baseline.allocation_days || []).join(', ')}]</code>{' '}
              evaluated with the same portfolio, costs, risk overlay, rolling validation and untouched holdout.
            </p>
            <div className="expand-grid">
              <div className="sub-card">
                <h4>Optimized ({br.live_eligible ? 'Live-Eligible' : 'Research only'})</h4>
                <MetricRow label="Robust return" value={br?.robust?.robust_return} pct />
                <MetricRow label="Median OOS TWR" value={br?.robust?.median_net_twr} pct />
                <MetricRow label="Recent validation TWR" value={br?.recent_validation?.net_twr_annualized_pct} pct />
                <MetricRow label="Holdout TWR" value={br?.test?.median_net_twr} pct />
                <div className="diag-row"><span>Holdout valid</span><b>{br?.test?.valid ? 'PASS' : 'INVALID'}</b></div>
              </div>
              <div className="sub-card">
                <h4>Baseline quarterly</h4>
                <MetricRow label="Robust return" value={experiment.baseline.robust?.robust_return} pct />
                <MetricRow label="Median OOS TWR" value={experiment.baseline.robust?.median_net_twr} pct />
                <MetricRow label="Holdout TWR" value={experiment.baseline.test?.median_net_twr} pct />
                <div className="diag-row"><span>Holdout valid</span><b>{experiment.baseline.test?.valid ? 'PASS' : 'INVALID'}</b></div>
              </div>
            </div>
          </div>
        );
      })()}

      {selectedItem && (
        <div className="card">
          <h3>Portfolio history — {selectedItem.symbols.join(' ')}</h3>
          {historyError ? (
            <div className="error">Failed to load history: {historyError}</div>
          ) : !history ? (
            <div className="muted">Generating portfolio history…</div>
          ) : (
            <>
              <CapitalDeploymentPanel history={history} capitalConfig={history.capital_config || capitalConfig} />
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
        title="Pareto frontier (non-dominated research candidates)"
      />
      <CandidateTable
        items={(experiment.top_candidates || []).slice(0, 25)}
        selected={selected}
        onSelect={setSelected}
        title="Top research candidates (by robust return)"
      />
    </div>
  );
}
