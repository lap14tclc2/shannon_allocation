import React, { useEffect, useRef, useState } from 'react';
import { startOptimizerRun, getOptimizerStatus, deleteOptimizerExperiment } from '../lib/api.js';

export default function OptimizerListPage({ experiments }) {
  const [items, setItems] = useState(experiments || []);
  const [seed, setSeed] = useState(42);
  const [population, setPopulation] = useState(60);
  const [generations, setGenerations] = useState(30);
  const [random, setRandom] = useState(400);
  const [universe, setUniverse] = useState('all');
  const [mode, setMode] = useState('joint');
  const [fixedSymbols, setFixedSymbols] = useState('');
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
    const effectiveMode = overrideUniverse ? mode : mode;
    const symbols = fixedSymbols.trim().split(/[\s,]+/).filter(Boolean).map((s) => s.toUpperCase());
    if (effectiveMode === 'timing' && symbols.length < 5) {
      window.alert('Timing-only mode needs a fixed portfolio set: at least 5 tickers in "Fixed symbols".');
      return;
    }
    setUniverse(activeUniverse);
    setRunning(true);
    setElapsed(0);
    const modeDesc = effectiveMode === 'timing' ? `timing-only on FIXED ${symbols.join(' ')}` : 'symbols + timing';
    setMessage(`Starting optimizer run on ${activeUniverse.toUpperCase()} (${modeDesc}, ${population} pop, ${generations} gen, ${random} random, seed ${seed})…`);
    try {
      const res = await startOptimizerRun({
        seed: Number(seed),
        population: Number(population),
        generations: Number(generations),
        random: Number(random),
        universe: activeUniverse,
        mode: effectiveMode,
        fixed_symbols: effectiveMode === 'timing' ? symbols : undefined,
      });
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
            setMessage(`Done in ${elapsed}s — opening experiment…`);
            window.location.href = `/optimizer/${run.experiment_id}`;
          } else if (run.status === 'failed') {
            clearInterval(pollRef.current);
            clearInterval(timerRef.current);
            setRunning(false);
            setActiveRun(null);
            setMessage(`Run failed: ${run.error || 'unknown error'}`);
          } else {
            setMessage(`Optimizer running… ${elapsed}s elapsed (${modeDesc}).`);
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
        <h1>Joint Portfolio + Allocation-Time Optimizer</h1>
        <p className="muted">
          Searches the four annual ERC allocation times for the most robust out-of-sample
          risk-adjusted NET performance — either jointly with the stock subset, or against a
          FIXED portfolio (timing-only mode) so symbol selection cannot contaminate the timing result.
        </p>
      </header>

      {running && (
        <div className="card run-loading">
          <div className="run-loading-inner">
            <span className="spinner" aria-hidden="true" />
            <div>
              <b>Running optimizer… {elapsed}s elapsed</b>
              <div className="muted">{message}</div>
              <div className="muted">Running in the background — you can keep browsing. This page will open the result when done.</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Run a new optimizer experiment</h3>
        <div className="universe-buttons">
          <button
            className="btn-variant btn-vn30"
            disabled={running}
            type="button"
            onClick={() => runOptimizer(null, 'vn30')}
          >
            ▶ Run on VN30
          </button>
          <button
            className="btn-variant btn-vn50"
            disabled={running}
            type="button"
            onClick={() => runOptimizer(null, 'vn50')}
          >
            ▶ Run on VN50
          </button>
          <button
            className="btn-variant btn-vn100"
            disabled={running}
            type="button"
            onClick={() => runOptimizer(null, 'vn100')}
          >
            ▶ Run on VN100
          </button>
          <button
            className="btn-variant btn-all"
            disabled={running}
            type="button"
            onClick={() => runOptimizer(null, 'all')}
          >
            All data symbols
          </button>
        </div>
        <div className="run-form" style={{ marginTop: 14 }}>
          <label>Mode
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="joint">Joint (symbols + timing)</option>
              <option value="timing">Timing-only (fixed portfolio)</option>
            </select>
          </label>
          {mode === 'timing' && (
            <label className="fixed-symbols">
              Fixed portfolio (tickers, comma/space separated)
              <input
                type="text"
                value={fixedSymbols}
                onChange={(e) => setFixedSymbols(e.target.value)}
                placeholder="CTG GVR HDB LPB MWG STB VIB"
              />
            </label>
          )}
          <label>Seed <input type="number" value={seed} onChange={(e) => setSeed(e.target.value)} /></label>
          <label>Population <input type="number" value={population} onChange={(e) => setPopulation(e.target.value)} /></label>
          <label>Generations <input type="number" value={generations} onChange={(e) => setGenerations(e.target.value)} /></label>
          <label>Random search <input type="number" value={random} onChange={(e) => setRandom(e.target.value)} /></label>
        </div>
        {!running && message && <div className="run-message">{message}</div>}
        <div className="muted">Runs on the server (costs + no look-ahead, net performance). Walk-forward windows are ≥ 1 year, ERC is warmed up before each window, and 100% window coverage is required. A run of 60/30/400 takes a few minutes.</div>
      </div>

      <div className="card">
        <h3>Experiments ({items.length})</h3>
        {items.length === 0 ? (
          <div className="muted">No optimizer experiments yet — click “Run optimizer”.</div>
        ) : (
          <ul className="run-list">
            {items.map((e) => (
              <li key={e.experiment_id} className={removing === e.experiment_id ? 'run-removing' : ''}>
                <div className="run-link">
                  <a href={`/optimizer/${e.experiment_id}`}>{e.experiment_id}</a>
                  <span className="muted">{e.generated_at}</span>
                </div>
                <button
                  className="btn-remove"
                  disabled={removing === e.experiment_id}
                  onClick={() => removeExperiment(e.experiment_id)}
                  title={`Delete experiment ${e.experiment_id}`}
                >
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