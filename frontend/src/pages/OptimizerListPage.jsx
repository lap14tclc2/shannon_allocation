import React, { useEffect, useRef, useState } from 'react';
import { startOptimizerRun, getOptimizerStatus, deleteOptimizerExperiment } from '../lib/api.js';

export default function OptimizerListPage({ experiments }) {
  const [items, setItems] = useState(experiments || []);
  const [seed, setSeed] = useState(42);
  const [population, setPopulation] = useState(60);
  const [generations, setGenerations] = useState(30);
  const [random, setRandom] = useState(250);
  const [universe, setUniverse] = useState('all');
  const [mode, setMode] = useState('joint');
  const [fixedSymbols, setFixedSymbols] = useState('');
  const [portfolioSize, setPortfolioSize] = useState(7);

  const [riskOverlay, setRiskOverlay] = useState(true);
  const [targetVolPct, setTargetVolPct] = useState(18);
  const [maxOosDrawdownPct, setMaxOosDrawdownPct] = useState(35);
  const [maxPositionPct, setMaxPositionPct] = useState(30);
  const [minEquityPct, setMinEquityPct] = useState(25);

  const [preselectTop, setPreselectTop] = useState(45);
  const [robustPool, setRobustPool] = useState(180);
  const [surrogatePool, setSurrogatePool] = useState(5000);
  const [surrogateProposals, setSurrogateProposals] = useState(40);
  const [earlyStop, setEarlyStop] = useState(15);

  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('');
  const [removing, setRemoving] = useState('');
  const pollRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => () => {
    clearInterval(pollRef.current);
    clearInterval(timerRef.current);
  }, []);

  async function runOptimizer(e, overrideUniverse) {
    if (e) e.preventDefault();
    const activeUniverse = overrideUniverse || universe;
    const effectiveMode = mode;
    const symbols = fixedSymbols.trim().split(/[\s,]+/).filter(Boolean).map((s) => s.toUpperCase());

    if (effectiveMode === 'timing' && symbols.length < 5) {
      window.alert('Timing-only mode needs at least 5 fixed tickers.');
      return;
    }
    if (effectiveMode === 'joint' && (Number(portfolioSize) < 5 || Number(portfolioSize) > 10)) {
      window.alert('Portfolio size must be between 5 and 10 symbols.');
      return;
    }
    if (riskOverlay && Number(targetVolPct) <= 0) {
      window.alert('Target volatility must be greater than 0%.');
      return;
    }

    setUniverse(activeUniverse);
    setRunning(true);
    setElapsed(0);
    const sizeDesc = effectiveMode === 'timing' ? `${symbols.length} fixed symbols` : `${portfolioSize} symbols`;
    const modeDesc = effectiveMode === 'timing' ? `timing-only on ${symbols.join(' ')}` : `joint ${sizeDesc}`;
    const riskDesc = riskOverlay ? `risk target ${targetVolPct}% / MDD gate ${maxOosDrawdownPct}%` : 'risk overlay OFF';
    setMessage(`Starting ${activeUniverse.toUpperCase()} optimizer (${modeDesc}, ${riskDesc})…`);

    try {
      const res = await startOptimizerRun({
        seed: Number(seed),
        population: Number(population),
        generations: Number(generations),
        random: Number(random),
        universe: activeUniverse,
        mode: effectiveMode,
        fixed_symbols: effectiveMode === 'timing' ? symbols : undefined,
        portfolio_size: effectiveMode === 'joint' ? Number(portfolioSize) : undefined,

        risk_overlay: Boolean(riskOverlay),
        target_volatility: Number(targetVolPct) / 100,
        max_oos_drawdown_pct: Number(maxOosDrawdownPct),
        max_position_weight: Number(maxPositionPct) / 100,
        min_equity_exposure: Number(minEquityPct) / 100,

        preselect_top: Number(preselectTop),
        robust_pool_size: Number(robustPool),
        surrogate_pool_size: Number(surrogatePool),
        surrogate_proposals: Number(surrogateProposals),
        early_stop_generations: Number(earlyStop),
      });
      if (!res.run_id) throw new Error(res.error || 'Optimizer did not start.');
      const runId = res.run_id;
      setActiveRun(runId);
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
      pollRef.current = setInterval(async () => {
        try {
          const runs = await getOptimizerStatus();
          const run = runs.find((r) => r.run_id === runId);
          if (!run) return;
          if (run.status === 'done') {
            clearInterval(pollRef.current);
            clearInterval(timerRef.current);
            setRunning(false);
            setActiveRun(null);
            setMessage('Done — opening experiment…');
            window.location.href = `/optimizer/${run.experiment_id}`;
          } else if (run.status === 'failed') {
            clearInterval(pollRef.current);
            clearInterval(timerRef.current);
            setRunning(false);
            setActiveRun(null);
            setMessage(`Run failed: ${run.error || 'unknown error'}`);
          }
        } catch (err) {
          clearInterval(pollRef.current);
          clearInterval(timerRef.current);
          setRunning(false);
          setActiveRun(null);
          setMessage(`Status check failed: ${err.message}`);
        }
      }, 3000);
    } catch (err) {
      setRunning(false);
      setMessage(`Failed to start run: ${err.message}`);
    }
  }

  async function removeExperiment(eid) {
    if (!window.confirm(`Delete optimizer experiment ${eid}?\nThis removes its reports and data.`)) return;
    setRemoving(eid);
    try {
      const res = await deleteOptimizerExperiment(eid);
      if (res.ok) setItems((xs) => xs.filter((x) => x.experiment_id !== eid));
      else window.alert(res.error || 'Delete failed.');
    } catch (err) {
      window.alert(err.message);
    } finally {
      setRemoving('');
    }
  }

  return (
    <div className="page">
      <div className="breadcrumb">
        <a href="/">All runs</a> <span>/</span> Optimizer
      </div>
      <header className="page-head">
        <h1>Risk-Aware Portfolio + Allocation Optimizer</h1>
        <p className="muted">
          Choose the exact portfolio size, search a large universe efficiently, and rank only candidates
          that survive walk-forward drawdown controls. ERC still determines relative allocation; the risk
          overlay can reduce total equity exposure and keep the remainder in cash.
        </p>
      </header>

      {running && (
        <div className="card run-loading">
          <div className="run-loading-inner">
            <span className="spinner" aria-hidden="true" />
            <div>
              <b>Running optimizer… {elapsed}s elapsed</b>
              <div className="muted">{message}</div>
              <div className="muted">You can keep browsing; this page opens the result when finished.</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Run a new optimizer experiment</h3>
        <div className="universe-buttons">
          <button className="btn-variant btn-vn30" disabled={running} type="button" onClick={() => runOptimizer(null, 'vn30')}>▶ Run on VN30</button>
          <button className="btn-variant btn-vn50" disabled={running} type="button" onClick={() => runOptimizer(null, 'vn50')}>▶ Run on VN50</button>
          <button className="btn-variant btn-vn100" disabled={running} type="button" onClick={() => runOptimizer(null, 'vn100')}>▶ Run on VN100</button>
          <button className="btn-variant btn-all" disabled={running} type="button" onClick={() => runOptimizer(null, 'all')}>All data symbols</button>
        </div>

        <div className="run-form" style={{ marginTop: 14 }}>
          <label>Mode
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="joint">Joint (symbols + timing)</option>
              <option value="timing">Timing-only (fixed portfolio)</option>
            </select>
          </label>
          {mode === 'joint' && (
            <label>Portfolio size
              <input type="number" min="5" max="10" value={portfolioSize} onChange={(e) => setPortfolioSize(e.target.value)} />
            </label>
          )}
          {mode === 'timing' && (
            <label className="fixed-symbols">Fixed portfolio
              <input type="text" value={fixedSymbols} onChange={(e) => setFixedSymbols(e.target.value)} placeholder="CTG GVR HDB LPB MWG STB VIB" />
            </label>
          )}
          <label>Seed <input type="number" value={seed} onChange={(e) => setSeed(e.target.value)} /></label>
          <label>Population <input type="number" min="10" value={population} onChange={(e) => setPopulation(e.target.value)} /></label>
          <label>Generations <input type="number" min="1" value={generations} onChange={(e) => setGenerations(e.target.value)} /></label>
          <label>Random real backtests <input type="number" min="20" value={random} onChange={(e) => setRandom(e.target.value)} /></label>
        </div>

        <h4 style={{ marginTop: 18 }}>Drawdown / exposure controls</h4>
        <div className="run-form">
          <label>Risk overlay
            <select value={riskOverlay ? 'on' : 'off'} onChange={(e) => setRiskOverlay(e.target.value === 'on')}>
              <option value="on">ON — volatility target + cash</option>
              <option value="off">OFF — 100% equity baseline</option>
            </select>
          </label>
          <label>Target volatility % <input type="number" min="5" max="50" step="1" value={targetVolPct} onChange={(e) => setTargetVolPct(e.target.value)} /></label>
          <label>Max OOS drawdown % <input type="number" min="10" max="80" step="1" value={maxOosDrawdownPct} onChange={(e) => setMaxOosDrawdownPct(e.target.value)} /></label>
          <label>Max single stock % <input type="number" min="10" max="100" step="1" value={maxPositionPct} onChange={(e) => setMaxPositionPct(e.target.value)} /></label>
          <label>Min equity exposure % <input type="number" min="0" max="100" step="5" value={minEquityPct} onChange={(e) => setMinEquityPct(e.target.value)} /></label>
        </div>

        <h4 style={{ marginTop: 18 }}>Fast search for large universes</h4>
        <div className="run-form">
          <label>TRAIN preselect top <input type="number" min="0" value={preselectTop} onChange={(e) => setPreselectTop(e.target.value)} /></label>
          <label>Validation shortlist <input type="number" min="20" value={robustPool} onChange={(e) => setRobustPool(e.target.value)} /></label>
          <label>Surrogate cheap pool <input type="number" min="0" value={surrogatePool} onChange={(e) => setSurrogatePool(e.target.value)} /></label>
          <label>Surrogate real proposals <input type="number" min="0" value={surrogateProposals} onChange={(e) => setSurrogateProposals(e.target.value)} /></label>
          <label>NSGA early-stop patience <input type="number" min="0" value={earlyStop} onChange={(e) => setEarlyStop(e.target.value)} /></label>
        </div>

        {!running && message && <div className="run-message">{message}</div>}
        <div className="muted">
          Large-universe speed path: TRAIN-only screening → random baseline → NSGA-II → surrogate ranking → diverse shortlist → full validation → finalists/test.
          Validation/test data never participates in screening or surrogate training.
        </div>
      </div>

      <div className="card">
        <h3>Experiments ({items.length})</h3>
        {items.length === 0 ? (
          <div className="muted">No optimizer experiments yet.</div>
        ) : (
          <ul className="run-list">
            {items.map((e) => (
              <li key={e.experiment_id} className={removing === e.experiment_id ? 'run-removing' : ''}>
                <div className="run-link">
                  <a href={`/optimizer/${e.experiment_id}`}>{e.experiment_id}</a>
                  <span className="muted">{e.generated_at}</span>
                </div>
                <button className="btn-remove" disabled={removing === e.experiment_id} onClick={() => removeExperiment(e.experiment_id)} title={`Delete experiment ${e.experiment_id}`}>
                  {removing === e.experiment_id ? '…' : '✕ Remove'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
