import React, { useEffect, useMemo, useRef, useState } from 'react';
import { startOptimizerRun, getOptimizerStatus, deleteOptimizerExperiment } from '../lib/api.js';

const SEARCH_PRESETS = {
  fast: {
    label: 'Fast', note: 'Quick exploration for a large universe',
    population: 40, generations: 18, random: 150,
    preselectTop: 40, robustPool: 100, surrogatePool: 3000,
    surrogateProposals: 25, earlyStop: 10,
  },
  balanced: {
    label: 'Balanced', note: 'Recommended for ~90 symbols',
    population: 60, generations: 30, random: 250,
    preselectTop: 45, robustPool: 180, surrogatePool: 5000,
    surrogateProposals: 40, earlyStop: 15,
  },
  thorough: {
    label: 'Thorough', note: 'More coverage and more real backtests',
    population: 90, generations: 45, random: 500,
    preselectTop: 60, robustPool: 300, surrogatePool: 10000,
    surrogateProposals: 80, earlyStop: 20,
  },
};

const UNIVERSES = [
  { value: 'all', label: 'All data symbols', note: 'Full dataset; intended for the ~90-symbol search.' },
  { value: 'vn100', label: 'VN100', note: 'VN100 universe available in the dataset.' },
  { value: 'vn50', label: 'VN50', note: 'Smaller search universe.' },
  { value: 'vn30', label: 'VN30', note: 'Smallest predefined universe.' },
];

function NumberField({ label, value, onChange, min, max, step = 1, disabled = false, hint }) {
  return (
    <label>
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint && <span style={{ textTransform: 'none', letterSpacing: 0, fontSize: 10 }}>{hint}</span>}
    </label>
  );
}

export default function OptimizerListPage({ experiments }) {
  const [items, setItems] = useState(experiments || []);
  const [universe, setUniverse] = useState('all');
  const [mode, setMode] = useState('joint');
  const [fixedSymbols, setFixedSymbols] = useState('');
  const [portfolioSize, setPortfolioSize] = useState(7);

  const [riskOverlay, setRiskOverlay] = useState(true);
  const [targetVolPct, setTargetVolPct] = useState(18);
  const [maxOosDrawdownPct, setMaxOosDrawdownPct] = useState(35);
  const [maxPositionPct, setMaxPositionPct] = useState(30);
  const [minEquityPct, setMinEquityPct] = useState(25);

  const [preset, setPreset] = useState('balanced');
  const [seed, setSeed] = useState(42);
  const [population, setPopulation] = useState(60);
  const [generations, setGenerations] = useState(30);
  const [random, setRandom] = useState(250);
  const [preselectTop, setPreselectTop] = useState(45);
  const [robustPool, setRobustPool] = useState(180);
  const [surrogatePool, setSurrogatePool] = useState(5000);
  const [surrogateProposals, setSurrogateProposals] = useState(40);
  const [earlyStop, setEarlyStop] = useState(15);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('');
  const [removing, setRemoving] = useState('');
  const pollRef = useRef(null);
  const timerRef = useRef(null);

  const fixedList = useMemo(
    () => fixedSymbols.trim().split(/[\s,]+/).filter(Boolean).map((s) => s.toUpperCase()),
    [fixedSymbols]
  );
  const effectiveSize = mode === 'timing' ? fixedList.length : Number(portfolioSize);
  const minFeasiblePositionPct = effectiveSize > 0 ? 100 / effectiveSize : 100;
  const selectedUniverse = UNIVERSES.find((u) => u.value === universe) || UNIVERSES[0];

  useEffect(() => () => {
    clearInterval(pollRef.current);
    clearInterval(timerRef.current);
  }, []);

  function applyPreset(key) {
    const p = SEARCH_PRESETS[key];
    if (!p) return;
    setPreset(key);
    setPopulation(p.population);
    setGenerations(p.generations);
    setRandom(p.random);
    setPreselectTop(p.preselectTop);
    setRobustPool(p.robustPool);
    setSurrogatePool(p.surrogatePool);
    setSurrogateProposals(p.surrogateProposals);
    setEarlyStop(p.earlyStop);
  }

  function setCustom(setter) {
    return (value) => {
      setter(value);
      setPreset('custom');
    };
  }

  function validate() {
    if (mode === 'joint' && (!Number.isInteger(Number(portfolioSize)) || Number(portfolioSize) < 5 || Number(portfolioSize) > 10)) {
      return 'Portfolio size must be an integer between 5 and 10.';
    }
    if (mode === 'timing' && (fixedList.length < 5 || fixedList.length > 10)) {
      return 'Timing-only mode needs 5–10 fixed tickers.';
    }
    if (new Set(fixedList).size !== fixedList.length) return 'Fixed portfolio contains duplicate tickers.';
    if (riskOverlay && (Number(targetVolPct) <= 0 || Number(targetVolPct) > 100)) return 'Target volatility must be between 0% and 100%.';
    if (Number(maxOosDrawdownPct) <= 0 || Number(maxOosDrawdownPct) > 100) return 'Max OOS drawdown must be between 0% and 100%.';
    if (riskOverlay && (Number(minEquityPct) < 0 || Number(minEquityPct) > 100)) return 'Minimum equity exposure must be between 0% and 100%.';
    if (riskOverlay && (Number(maxPositionPct) <= 0 || Number(maxPositionPct) > 100)) return 'Maximum single-stock weight must be between 0% and 100%.';
    if (riskOverlay && Number(maxPositionPct) + 1e-9 < minFeasiblePositionPct) {
      return `With ${effectiveSize} symbols, max single-stock weight cannot be below ${minFeasiblePositionPct.toFixed(1)}%.`;
    }
    if (Number(preselectTop) > 0 && mode === 'joint' && Number(preselectTop) < Number(portfolioSize)) return 'TRAIN preselect must be at least the portfolio size.';
    if (Number(robustPool) < 5) return 'Validation shortlist must contain at least 5 candidates.';
    return '';
  }

  async function runOptimizer(e) {
    if (e) e.preventDefault();
    const error = validate();
    if (error) {
      window.alert(error);
      return;
    }

    setRunning(true);
    setElapsed(0);
    const sizeDesc = mode === 'timing' ? `${fixedList.length} fixed symbols` : `exactly ${portfolioSize} symbols`;
    const riskDesc = riskOverlay ? `risk target ${targetVolPct}% · OOS MDD gate ${maxOosDrawdownPct}%` : 'legacy 100% equity baseline';
    setMessage(`${selectedUniverse.label} · ${sizeDesc} · ${riskDesc}`);

    try {
      const res = await startOptimizerRun({
        seed: Number(seed),
        population: Number(population),
        generations: Number(generations),
        random: Number(random),
        universe,
        mode,
        fixed_symbols: mode === 'timing' ? fixedList : undefined,
        portfolio_size: mode === 'joint' ? Number(portfolioSize) : undefined,
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
      <div className="breadcrumb"><a href="/">All runs</a> <span>/</span> Optimizer</div>
      <header className="page-head">
        <h1>Portfolio Optimizer</h1>
        <p className="muted">
          Configure and launch everything here: universe, exact portfolio size, risk policy, and search budget.
          No command line is required.
        </p>
      </header>

      {running && (
        <div className="card run-loading">
          <div className="run-loading-inner">
            <span className="spinner" aria-hidden="true" />
            <div>
              <b>Optimizer is running · {elapsed}s</b>
              <div className="muted">{message}</div>
              <div className="muted">Run ID: {activeRun || '-'}</div>
            </div>
          </div>
        </div>
      )}

      <form className="card" onSubmit={runOptimizer}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <h3 style={{ marginBottom: 4 }}>1. Portfolio search</h3>
            <div className="muted">Define what the optimizer may build.</div>
          </div>
          <span className="universe-pill pill-vn100">Recommended: All data + 7 symbols</span>
        </div>

        <div className="run-form" style={{ marginTop: 14 }}>
          <label>Universe
            <select value={universe} onChange={(e) => setUniverse(e.target.value)} style={{ width: 190 }} disabled={running}>
              {UNIVERSES.map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
            </select>
            <span style={{ textTransform: 'none', letterSpacing: 0, fontSize: 10, maxWidth: 220 }}>{selectedUniverse.note}</span>
          </label>
          <label>Optimization mode
            <select value={mode} onChange={(e) => setMode(e.target.value)} style={{ width: 220 }} disabled={running}>
              <option value="joint">Build portfolio + optimize timing</option>
              <option value="timing">Optimize timing for fixed portfolio</option>
            </select>
          </label>
          {mode === 'joint' ? (
            <label>Portfolio size
              <select value={portfolioSize} onChange={(e) => setPortfolioSize(Number(e.target.value))} style={{ width: 150 }} disabled={running}>
                {[5, 6, 7, 8, 9, 10].map((n) => <option key={n} value={n}>{n} symbols</option>)}
              </select>
            </label>
          ) : (
            <label className="fixed-symbols">Fixed portfolio (5–10)
              <input
                type="text"
                value={fixedSymbols}
                onChange={(e) => setFixedSymbols(e.target.value)}
                placeholder="ACB FPT HPG MBB MWG VCB VNM"
                disabled={running}
                style={{ width: 360 }}
              />
              <span style={{ textTransform: 'none', letterSpacing: 0, fontSize: 10 }}>{fixedList.length} ticker(s)</span>
            </label>
          )}
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3 style={{ marginBottom: 4 }}>2. Drawdown / exposure policy</h3>
        <div className="muted" style={{ marginBottom: 12 }}>
          ERC controls relative stock weights. Risk-aware mode can reduce total equity exposure and keep the balance in cash.
          Risk exposure is refreshed weekly while Shannon drift checks remain daily.
        </div>
        <div className="run-form">
          <label>Risk policy
            <select value={riskOverlay ? 'on' : 'off'} onChange={(e) => setRiskOverlay(e.target.value === 'on')} style={{ width: 220 }} disabled={running}>
              <option value="on">Risk-aware · volatility target</option>
              <option value="off">Baseline · 100% equity</option>
            </select>
          </label>
          <NumberField label="Target volatility %" min={5} max={50} value={targetVolPct} onChange={setTargetVolPct} disabled={!riskOverlay || running} hint="Default 18%" />
          <NumberField label="Max OOS drawdown %" min={10} max={80} value={maxOosDrawdownPct} onChange={setMaxOosDrawdownPct} disabled={running} hint="Hard validation gate" />
          <NumberField label="Max stock weight %" min={Math.ceil(minFeasiblePositionPct)} max={100} value={maxPositionPct} onChange={setMaxPositionPct} disabled={!riskOverlay || running} />
          <NumberField label="Min equity exposure %" min={0} max={100} step={5} value={minEquityPct} onChange={setMinEquityPct} disabled={!riskOverlay || running} />
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3 style={{ marginBottom: 4 }}>3. Search budget</h3>
        <div className="muted" style={{ marginBottom: 10 }}>
          Balanced is the default for the full ~90-symbol universe. Fast is useful for exploration; Thorough spends more real evaluations.
        </div>
        <div className="universe-buttons" style={{ marginBottom: 12 }}>
          {Object.entries(SEARCH_PRESETS).map(([key, p]) => (
            <button
              key={key}
              className="btn-variant"
              type="button"
              disabled={running}
              onClick={() => applyPreset(key)}
              style={{ borderColor: preset === key ? 'var(--accent)' : 'var(--border)', minWidth: 160, textAlign: 'left' }}
            >
              <div>{preset === key ? '✓ ' : ''}{p.label}</div>
              <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>{p.note}</div>
            </button>
          ))}
        </div>

        <button type="button" className="btn-variant btn-all" disabled={running} onClick={() => setShowAdvanced((v) => !v)} style={{ marginBottom: 12 }}>
          {showAdvanced ? 'Hide advanced search settings' : 'Show advanced search settings'}
        </button>

        {showAdvanced && (
          <div className="sub-card" style={{ marginBottom: 14 }}>
            <div className="run-form">
              <NumberField label="Seed" min={0} value={seed} onChange={setSeed} disabled={running} />
              <NumberField label="Population" min={10} value={population} onChange={setCustom(setPopulation)} disabled={running} />
              <NumberField label="Generations" min={1} value={generations} onChange={setCustom(setGenerations)} disabled={running} />
              <NumberField label="Random real backtests" min={20} value={random} onChange={setCustom(setRandom)} disabled={running} />
              <NumberField label="TRAIN preselect" min={0} value={preselectTop} onChange={setCustom(setPreselectTop)} disabled={running} />
              <NumberField label="Validation shortlist" min={5} value={robustPool} onChange={setCustom(setRobustPool)} disabled={running} />
              <NumberField label="Surrogate pool" min={0} value={surrogatePool} onChange={setCustom(setSurrogatePool)} disabled={running} />
              <NumberField label="Real surrogate proposals" min={0} value={surrogateProposals} onChange={setCustom(setSurrogateProposals)} disabled={running} />
              <NumberField label="Early-stop patience" min={0} value={earlyStop} onChange={setCustom(setEarlyStop)} disabled={running} />
            </div>
          </div>
        )}

        <div className="sub-card" style={{ marginBottom: 14 }}>
          <div className="diag-grid" style={{ marginBottom: 0 }}>
            <div><span>Universe</span><b>{selectedUniverse.label}</b></div>
            <div><span>Portfolio</span><b>{mode === 'joint' ? `${portfolioSize} symbols` : `${fixedList.length} fixed symbols`}</b></div>
            <div><span>Risk</span><b>{riskOverlay ? `${targetVolPct}% vol / ${maxOosDrawdownPct}% MDD` : 'Baseline 100% equity'}</b></div>
            <div><span>Search</span><b>{SEARCH_PRESETS[preset]?.label || 'Custom'}</b></div>
            <div><span>TRAIN preselect</span><b>{preselectTop || 'OFF'}</b></div>
            <div><span>Validation shortlist</span><b>{robustPool}</b></div>
          </div>
        </div>

        {!running && message && <div className="run-message" style={{ marginBottom: 10 }}>{message}</div>}
        <button
          className="btn-export"
          type="submit"
          disabled={running}
          style={{ border: 0, cursor: running ? 'not-allowed' : 'pointer', opacity: running ? 0.55 : 1, fontSize: 14, padding: '11px 20px' }}
        >
          {running ? 'Optimizer running…' : '▶ Run optimizer'}
        </button>
        <div className="muted" style={{ marginTop: 10 }}>
          TRAIN-only screening → real random baseline → NSGA-II → surrogate ranking → validation shortlist → robustness → untouched final holdout.
        </div>
      </form>

      <div className="card">
        <h3>Experiments ({items.length})</h3>
        {items.length === 0 ? <div className="muted">No optimizer experiments yet.</div> : (
          <ul className="run-list">
            {items.map((e) => (
              <li key={e.experiment_id} className={removing === e.experiment_id ? 'run-removing' : ''}>
                <div className="run-link">
                  <a href={`/optimizer/${e.experiment_id}`}>{e.experiment_id}</a>
                  <span className="muted">{e.generated_at}</span>
                </div>
                <button className="btn-remove" type="button" disabled={removing === e.experiment_id} onClick={() => removeExperiment(e.experiment_id)}>
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
