import React, { useEffect, useMemo, useState } from 'react';
import { formatMoney, formatPercent } from '../lib/format.js';
import { getCandidateHistory, optimizerDownloadAllUrl, deleteOptimizerExperiment } from '../lib/api.js';
import EquityChart from '../components/EquityChart.jsx';
import AllocationTable from '../components/AllocationTable.jsx';
import YearlyAllocationTable from '../components/YearlyAllocationTable.jsx';

function isDynamicItem(item) {
  return Boolean(item?.dynamic_alpha || item?.metrics?.dynamic_alpha);
}

function itemKey(item) {
  const prefix = isDynamicItem(item) ? 'DYNAMIC_ALPHA' : (item?.symbols || []).join('|');
  return `${prefix}::${(item?.allocation_days || []).join(',')}`;
}

function itemName(item) {
  return isDynamicItem(item) ? 'Dynamic Alpha' : ((item?.symbols || []).join(' ') || '-');
}

function allocationLabel(item) {
  const days = item?.allocation_days || [];
  return `${days.length}x/year · [${days.join(', ')}]`;
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
          <thead><tr><th>Date</th><th>Type</th><th>Amount</th><th>Cash immediately after</th><th>Note</th></tr></thead>
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
          <thead><tr><th>Signal</th><th>Execution</th><th>Event</th><th>BUY cash deployed</th><th>SELL cash released</th><th>Net deployed</th><th>Cash after</th></tr></thead>
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

function AlphaMembershipTable({ item }) {
  if (!isDynamicItem(item)) return null;
  const testPeriod = (item?.test?.per_window || [])[0] || {};
  const sources = [
    ['TRAIN', item?.metrics?.alpha_selection_history || []],
    ['RECENT', item?.recent_validation?.alpha_selection_history || []],
    ['FINAL', testPeriod?.alpha_selection_history || []],
  ];
  const rows = sources.flatMap(([windowName, values]) =>
    values.map((x, i) => ({ ...x, windowName, rowKey: `${windowName}-${x.date}-${i}` }))
  );

  return (
    <div className="card">
      <h3>Dynamic Alpha membership history</h3>
      <p className="muted">
        Each row is the stock set selected using data strictly before that signal. TRAIN, recent validation and final assessment are shown separately so the holdout is visibly an assessment window rather than a source of research selections.
      </p>
      <div className="diag-grid" style={{ marginBottom: 14 }}>
        <div><span>Active stocks/event</span><b>{item.n_symbols || '-'}</b></div>
        <div><span>Unique TRAIN symbols</span><b>{item.metrics?.alpha_unique_symbol_count ?? '-'}</b></div>
        <div><span>TRAIN membership turnover</span><b>{item.metrics?.alpha_membership_turnover != null ? `${(Number(item.metrics.alpha_membership_turnover) * 100).toFixed(1)}%` : '-'}</b></div>
        <div><span>TRAIN selections</span><b>{item.metrics?.alpha_selection_count ?? '-'}</b></div>
      </div>
      {rows.length === 0 ? <div className="muted">No membership rows exported for this candidate.</div> : (
        <table className="ranking">
          <thead><tr><th>Window</th><th>Date</th><th>Role</th><th>Selected stocks</th><th>Max pair corr</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.rowKey}>
                <td>{r.windowName}</td>
                <td>{r.date}</td>
                <td>{r.role === 'INITIAL_DEPLOYMENT' ? 'Initial deployment' : 'Recalibration'}</td>
                <td className="symbols-cell">{(r.selected_symbols || []).join(' ')}</td>
                <td>{r.max_selected_correlation != null ? Number(r.max_selected_correlation).toFixed(2) : '-'}</td>
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
  const quality = item.live_quality || {};
  const dynamic = isDynamicItem(item);

  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="candidate-head">
        <span className="candidate-symbols">{itemName(item)}</span>
        <span className="muted">N={item.n_symbols} active stocks · recalibration {allocationLabel(item)}</span>
      </div>
      {dynamic && <div className="muted" style={{ marginTop: 5 }}>Membership is re-ranked from the configured universe at every recalibration; this is not a frozen ticker combination.</div>}

      <div className="sub-card" style={{ marginBottom: 14, marginTop: 14 }}>
        <h4>Pre-holdout live eligibility</h4>
        <div className="diag-row">
          <span>Hard research-to-live gates</span>
          <b className={item.live_eligible ? 'pos' : 'neg'}>{item.live_eligible ? 'PASS' : 'FAIL'}</b>
        </div>
        <MetricRow label="Soft risk/reward quality" value={quality.overall} digits={1} />
        <MetricRow label="TRAIN Calmar quality" value={quality.train_calmar} digits={3} />
        <MetricRow label="Validation return / drawdown" value={quality.validation_return_to_drawdown} digits={3} />
        <MetricRow label="Recent Calmar quality" value={quality.recent_calmar} digits={3} />
        <div className="muted" style={{ marginTop: 6 }}>
          Calmar and return-to-drawdown are smooth ranking quality, not pass/fail cliffs. OOS tail return, OOS drawdown ceiling and catastrophic recent deterioration remain hard gates.
        </div>
        {!item.live_eligible && eligibilityReasons.length > 0 && <div className="muted" style={{ marginTop: 6 }}>Reasons: {eligibilityReasons.join(' · ')}</div>}
      </div>

      <div className="expand-grid">
        <div className="sub-card">
          <h4>TRAIN (growth search window)</h4>
          <MetricRow label="Net TWR annualized" value={m.net_twr_annualized_pct} pct />
          <MetricRow label="Net XIRR (window anchored)" value={m.net_xirr_pct} pct />
          <MetricRow label="Gross TWR annualized" value={m.gross_twr_annualized_pct} pct />
          <MetricRow label="Growth search score" value={m.score} digits={3} />
          <MetricRow label="Sharpe" value={m.sharpe} digits={3} />
          <MetricRow label="Sortino" value={m.sortino} digits={3} />
          <MetricRow label="Calmar" value={m.calmar} digits={3} />
          <MetricRow label="Max drawdown" value={m.max_drawdown_pct} pct />
          <MetricRow label="Worst year" value={m.worst_year} pct />
          <MetricRow label="Measured profit" value={m.measurement_profit} money />
          <MetricRow label="Final NAV" value={m.final_nav} money />
          {dynamic && <MetricRow label="Unique alpha symbols" value={m.alpha_unique_symbol_count} digits={0} />}
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
          <div className="diag-row"><span>Timing neighbourhood</span><b>{tr.mean != null ? `${tr.mean}%` : (tr.note || '-')} {tr.isolated_spike ? '(⚠ spike)' : ''}</b></div>
          <div className="diag-row"><span>Symbol neighbourhood</span><b>{dynamic ? 'N/A · membership is dynamic' : (sr.mean != null ? `${sr.mean}%` : (sr.note || '-'))}</b></div>
          <div className="diag-row"><span>Concentration</span><b>{conc.single_stock ? 'single-stock!' : 'ok'} / {conc.single_year ? 'single-year!' : 'ok'}</b></div>
        </div>
      </div>

      <div className="expand-grid" style={{ marginTop: 14 }}>
        <div className="sub-card">
          <h4>Recent pre-holdout validation</h4>
          <div className="muted" style={{ marginBottom: 8 }}>Used for pre-holdout regime evidence. A loss below the catastrophic floor is a hard failure; ordinary Calmar variation is soft quality.</div>
          <MetricRow label="Net TWR annualized" value={recent.net_twr_annualized_pct} pct />
          <MetricRow label="Net XIRR" value={recent.net_xirr_pct} pct />
          <MetricRow label="Sharpe" value={recent.sharpe} digits={3} />
          <MetricRow label="MDD" value={recent.max_drawdown_pct} pct />
          <MetricRow label="CDaR95" value={recent.cdar95_pct} pct />
        </div>
        <div className="sub-card">
          <h4>Final assessment holdout</h4>
          <MetricRow label="Net TWR annualized" value={test.median_net_twr} pct />
          <MetricRow label="Net XIRR (window anchored)" value={testPeriod.net_xirr_pct} pct />
          <MetricRow label="Measurement start NAV" value={testPeriod.measurement_start_nav} money />
          <MetricRow label="External contributions" value={testPeriod.measurement_external_contributions} money />
          <MetricRow label="Measured profit" value={testPeriod.measurement_profit} money />
          <MetricRow label="Final NAV" value={testPeriod.final_nav} money />
          <MetricRow label="MDD" value={test.worst_mdd} pct />
          <MetricRow label="CDaR95" value={test.worst_cdar95} pct />
          <div className="diag-row"><span>Holdout valid</span><b>{test.valid ? `${test.n_test_windows}/${test.required_test_windows} PASS` : `${test.n_test_windows || 0}/${test.required_test_windows || 1} INVALID`}</b></div>
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
        <thead><tr><th>Portfolio</th><th>N</th><th>Live</th><th>Quality</th><th>Events/y</th><th>Allocation days</th><th>Net TWR ann</th><th>Sharpe</th><th>MDD</th><th>Robust return</th></tr></thead>
        <tbody>
          {items.map((it) => {
            const key = itemKey(it);
            const m = it.metrics || {};
            const r = it.robust || {};
            return (
              <tr key={key} className={selected === key ? 'row-selected' : ''} onClick={() => onSelect(key)}>
                <td className="symbols-cell">{itemName(it)}</td>
                <td>{it.n_symbols}</td>
                <td className={it.live_eligible ? 'pos' : 'neg'}>{it.live_eligible ? 'PASS' : 'FAIL'}</td>
                <td>{it.live_quality?.overall != null ? Number(it.live_quality.overall).toFixed(1) : '-'}</td>
                <td className="num">{it.allocation_days?.length || 0}</td>
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
  const isDynamicExperiment = Boolean(experiment.meta?.mode === 'alpha' || experiment.meta?.dynamic_alpha?.enabled);
  const [selected, setSelected] = useState(() => {
    const wr = experiment.winners?.best_live_eligible || experiment.winners?.best_robust;
    return wr ? itemKey(wr) : '';
  });
  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState('');

  const lookup = useMemo(() => {
    const map = {};
    const add = (it) => { if (it) map[itemKey(it)] = it; };
    (experiment.winners ? Object.values(experiment.winners) : []).forEach(add);
    (experiment.pareto || []).forEach(add);
    (experiment.top_candidates || []).forEach(add);
    return map;
  }, [experiment]);

  useEffect(() => {
    const it = lookup[selected];
    if (!it || isDynamicItem(it)) {
      setHistory(null);
      setHistoryError('');
      return undefined;
    }
    const controller = new AbortController();
    setHistory(null);
    setHistoryError('');
    getCandidateHistory(experiment.experiment_id, it.symbols, it.allocation_days, controller.signal)
      .then((h) => setHistory(h))
      .catch((err) => { if (err.name !== 'AbortError') setHistoryError(err.message); });
    return () => controller.abort();
  }, [experiment, selected, lookup]);

  const chartData = useMemo(() => (history?.nav_history || []).map(([date, nav]) => ({ date, nav })), [history]);
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
        <div className="breadcrumb"><a href="/">Optimizer</a> <span>/</span> {experiment.experiment_id}</div>
        <button className="btn-remove" onClick={async () => {
          if (!window.confirm(`Delete optimizer experiment ${experiment.experiment_id}?\nThis removes its reports and data.`)) return;
          try {
            const res = await deleteOptimizerExperiment(experiment.experiment_id);
            if (res.ok) window.location.href = '/';
            else window.alert(res.error || 'Delete failed.');
          } catch (err) { window.alert(err.message); }
        }}>✕ Remove experiment</button>
      </div>

      <header className="page-head">
        <h1>
          Optimizer experiment {experiment.experiment_id}
          {(() => {
            const v = experiment.meta?.universe_variant || (experiment.meta?.universe?.length === 30 ? 'vn30' : experiment.meta?.universe?.length === 50 ? 'vn50' : experiment.meta?.universe?.length >= 80 ? 'vn100' : 'all');
            const label = v === 'all' ? `All data (${experiment.meta?.universe?.length})` : v.toUpperCase();
            return <span className={`universe-pill${v === 'all' ? '' : ` pill-${v}`}`}>{label}</span>;
          })()}
        </h1>
        <p className="muted">
          seed {experiment.meta?.seed} · {experiment.meta?.universe?.length} universe symbols · {experiment.meta?.n_windows} rolling windows · {isDynamicExperiment ? `Dynamic Alpha · ${experiment.meta?.dynamic_alpha?.portfolio_size || '-'} active stocks + frequency/timing search` : 'fixed symbols + frequency/timing search'} · CPU workers {experiment.meta?.parallel_workers || 1} · initial {formatMoney(capitalConfig.initial_balance || 0)} · annual {formatMoney(capitalConfig.annual_deposit || 0)}
        </p>
        {isDynamicExperiment ? (
          <p className="muted">
            Hard gates: {(eligibilityConfig.hard_gates || []).join(' · ') || 'OOS tail / MDD / catastrophic recent loss'} · soft quality: {(eligibilityConfig.soft_quality || []).join(' · ') || 'Calmar + return/drawdown'} · eligible {eligibilityConfig.eligible_candidates ?? 0} candidate(s).
          </p>
        ) : (
          <p className="muted">Live eligibility is pre-holdout only; the final assessment can reject the frozen winner but cannot replace it.</p>
        )}
        <div className="report-links"><a className="btn-export" href={optimizerDownloadAllUrl(experiment.experiment_id)}>⬇ Download all data (ZIP)</a></div>
      </header>

      <div className="metric-grid">
        {Object.entries(winners).map(([key, it]) => {
          const keyValue = itemKey(it);
          return (
            <div key={key} className={`metric-card winner-card ${selected === keyValue ? 'winner-selected' : ''}`} onClick={() => setSelected(keyValue)}>
              <div className="metric-label">{winnerLabels[key] || key}</div>
              <div className="candidate-head"><span className="candidate-symbols">{itemName(it)}</span><span className="muted">{allocationLabel(it)}</span></div>
              <div className="metric-value" style={{ color: 'var(--accent)' }}>{formatPercent(it.robust?.robust_return ?? it.metrics?.net_twr_annualized_pct)}</div>
              <div className="muted">Live {it.live_eligible ? 'PASS' : 'FAIL'} · quality {it.live_quality?.overall != null ? Number(it.live_quality.overall).toFixed(1) : '-'} · OOS med {formatPercent(it.robust?.median_net_twr)} · MDD {formatPercent(it.metrics?.max_drawdown_pct)}</div>
            </div>
          );
        })}
      </div>

      {selectedItem && <CandidatePanel item={selectedItem} title="Selected candidate" />}
      {selectedItem && <AlphaMembershipTable item={selectedItem} />}

      {(() => {
        const br = experiment.winners?.best_live_eligible || experiment.winners?.best_robust;
        if (!experiment.baseline || !br) return null;
        return (
          <div className="card">
            <h3>Quarterly baseline comparison ({isDynamicExperiment ? 'same Dynamic Alpha methodology' : 'same symbols'})</h3>
            <p className="muted">Standard 4x/year benchmark <code>[{(experiment.baseline.allocation_days || []).join(', ')}]</code> uses the same costs, risk overlay, validation and final holdout. Only recalibration timing differs.</p>
            <div className="expand-grid">
              <div className="sub-card">
                <h4>Optimized — {allocationLabel(br)} ({br.live_eligible ? 'Live-Eligible' : 'Research only'})</h4>
                <MetricRow label="Robust return" value={br?.robust?.robust_return} pct />
                <MetricRow label="Median OOS TWR" value={br?.robust?.median_net_twr} pct />
                <MetricRow label="Recent validation TWR" value={br?.recent_validation?.net_twr_annualized_pct} pct />
                <MetricRow label="Holdout TWR" value={br?.test?.median_net_twr} pct />
                <div className="diag-row"><span>Holdout valid</span><b>{br?.test?.valid ? 'PASS' : 'INVALID'}</b></div>
              </div>
              <div className="sub-card">
                <h4>Baseline quarterly · 4x/year</h4>
                <MetricRow label="Robust return" value={experiment.baseline.robust?.robust_return} pct />
                <MetricRow label="Median OOS TWR" value={experiment.baseline.robust?.median_net_twr} pct />
                <MetricRow label="Holdout TWR" value={experiment.baseline.test?.median_net_twr} pct />
                <div className="diag-row"><span>Holdout valid</span><b>{experiment.baseline.test?.valid ? 'PASS' : 'INVALID'}</b></div>
              </div>
            </div>
          </div>
        );
      })()}

      {selectedItem && !isDynamicItem(selectedItem) && (
        <div className="card">
          <h3>Portfolio history — {itemName(selectedItem)}</h3>
          {historyError ? <div className="error">Failed to load history: {historyError}</div> : !history ? <div className="muted">Generating portfolio history…</div> : (
            <>
              <CapitalDeploymentPanel history={history} capitalConfig={history.capital_config || capitalConfig} />
              <div className="chart"><EquityChart data={chartData} /></div>
              <YearlyAllocationTable allocations={history.allocations || []} />
              <AllocationTable allocations={history.allocations || []} />
            </>
          )}
        </div>
      )}

      {selectedItem && isDynamicItem(selectedItem) && (
        <div className="card">
          <h3>Dynamic portfolio audit</h3>
          <p className="muted">The exported experiment stores window-safe NAV/risk metrics plus the exact stock membership selected in TRAIN, recent validation and final assessment. Use the ZIP for the complete audit artifacts. Membership is intentionally not represented as one frozen ticker list.</p>
        </div>
      )}

      <CandidateTable items={experiment.pareto || []} selected={selected} onSelect={setSelected} title="Pareto frontier (non-dominated growth research candidates)" />
      <CandidateTable items={(experiment.top_candidates || []).slice(0, 25)} selected={selected} onSelect={setSelected} title="Top research candidates (by robust return)" />
    </div>
  );
}
