import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  startOptimizerRun,
  getOptimizerStatus,
  deleteOptimizerExperiment,
  listAvailableSymbols,
  analyzeCombination,
} from '../lib/api.js';

const JOINT_PRESETS = {
  fast: {
    label: 'Fast', note: 'Quick growth search',
    population: 40, generations: 18, random: 150, preselect: 40,
    robustPool: 100, surrogatePool: 3000, surrogateProposals: 25, earlyStop: 10,
  },
  balanced: {
    label: 'Balanced', note: 'Recommended joint search',
    population: 60, generations: 30, random: 250, preselect: 45,
    robustPool: 180, surrogatePool: 5000, surrogateProposals: 40, earlyStop: 15,
  },
  thorough: {
    label: 'Thorough', note: 'More combination + timing coverage',
    population: 90, generations: 45, random: 500, preselect: 60,
    robustPool: 300, surrogatePool: 10000, surrogateProposals: 80, earlyStop: 20,
  },
};

const TIMING_PRESETS = {
  fast: {
    label: 'Fast', note: 'Quick schedule exploration',
    population: 24, generations: 10, random: 40, preselect: 0,
    robustPool: 25, surrogatePool: 500, surrogateProposals: 8, earlyStop: 6,
  },
  balanced: {
    label: 'Balanced', note: 'Recommended fixed-combination search',
    population: 36, generations: 18, random: 80, preselect: 0,
    robustPool: 50, surrogatePool: 1500, surrogateProposals: 16, earlyStop: 8,
  },
  thorough: {
    label: 'Thorough', note: 'More timing coverage',
    population: 50, generations: 28, random: 140, preselect: 0,
    robustPool: 80, surrogatePool: 3000, surrogateProposals: 24, earlyStop: 12,
  },
};

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

function moneyShort(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  if (Math.abs(n) >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B VND`;
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(0)}M VND`;
  return `${n.toLocaleString('en-US')} VND`;
}

function num(value, digits = 2) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : '-';
}

function parseImportedSymbols(raw) {
  const text = String(raw || '').trim();
  if (!text) return [];
  if (text.startsWith('[')) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        return parsed.map((s) => String(s).trim().toUpperCase()).filter(Boolean);
      }
    } catch (_err) {
      // Fall through.
    }
  }
  return text
    .toUpperCase()
    .split(/[^A-Z0-9]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function HealthPanel({ health, onApplySuggestion }) {
  if (!health) return null;
  const status = health.status || 'invalid';
  const statusLabel = status.toUpperCase();
  const statusColor = status === 'healthy' ? 'var(--success)' : status === 'warning' ? 'var(--warning)' : 'var(--danger)';
  const correlation = health.correlation || {};
  const diversification = health.diversification || {};
  const erc = health.erc || {};
  const score = health.score || {};
  const suggestions = health.suggestions || [];

  return (
    <div className="sub-card" style={{ marginTop: 12, borderColor: statusColor }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <h4 style={{ margin: 0 }}>Combination Health</h4>
          <div className="muted">Research through {health.research_end}; reserved final holdout is not inspected.</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <b style={{ color: statusColor }}>{statusLabel}</b>
          <div className="muted">{num(score.overall, 1)} / 100</div>
        </div>
      </div>

      <div className="diag-grid" style={{ marginTop: 12, marginBottom: 12 }}>
        <div><span>Average risk correlation</span><b>{num(correlation.average, 2)}</b></div>
        <div><span>Maximum risk correlation</span><b>{num(correlation.maximum, 2)}</b></div>
        <div><span>Largest corr cluster</span><b>{correlation.largest_cluster_size || 1}/{health.symbols?.length || 0}</b></div>
        <div><span>Diversification ratio</span><b>{num(diversification.ratio, 2)}</b></div>
        <div><span>ERC feasible</span><b>{erc.feasible ? 'YES' : 'NO'}</b></div>
        <div><span>Aligned observations</span><b>{erc.observations || 0}</b></div>
      </div>

      {(health.reasons || []).length > 0 && (
        <ul style={{ marginTop: 0 }}>
          {health.reasons.map((reason, i) => <li key={`${reason}-${i}`}>{reason}</li>)}
        </ul>
      )}

      {status !== 'invalid' && suggestions.length > 0 && (
        <div>
          <h4>Optional diversification suggestions</h4>
          <div style={{ display: 'grid', gap: 8 }}>
            {suggestions.slice(0, 5).map((s) => (
              <div key={`${s.remove}-${s.add}`} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                  <div>
                    <b>{s.remove} → {s.add}</b>
                    <div className="muted">Avg corr {num(s.before?.average_correlation, 2)} → {num(s.after?.average_correlation, 2)} · Diversification {num(s.before?.diversification_ratio, 2)} → {num(s.after?.diversification_ratio, 2)}</div>
                  </div>
                  <button className="btn-variant" type="button" onClick={() => onApplySuggestion(s)}>Apply</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function OptimizerListPage({ experiments }) {
  const [items, setItems] = useState(experiments || []);
  const [mode, setMode] = useState('joint');
  const [universe, setUniverse] = useState('all');
  const [portfolioSize, setPortfolioSize] = useState(7);

  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [symbolsLoading, setSymbolsLoading] = useState(true);
  const [symbolsError, setSymbolsError] = useState('');
  const [minSelected, setMinSelected] = useState(5);
  const [maxSelected, setMaxSelected] = useState(10);
  const [selectedSymbols, setSelectedSymbols] = useState([]);
  const [symbolQuery, setSymbolQuery] = useState('');
  const [migrateInput, setMigrateInput] = useState('');

  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState('');
  const [analyzedKey, setAnalyzedKey] = useState('');

  const [initialBalance, setInitialBalance] = useState(1_000_000_000);
  const [annualDeposit, setAnnualDeposit] = useState(20_000_000);
  const [riskOverlay, setRiskOverlay] = useState(true);
  const [targetVolPct, setTargetVolPct] = useState(18);
  const [maxOosDrawdownPct, setMaxOosDrawdownPct] = useState(35);
  const [maxPositionPct, setMaxPositionPct] = useState(30);
  const [minEquityPct, setMinEquityPct] = useState(0);

  const [preset, setPreset] = useState('balanced');
  const [seed, setSeed] = useState(42);
  const [population, setPopulation] = useState(JOINT_PRESETS.balanced.population);
  const [generations, setGenerations] = useState(JOINT_PRESETS.balanced.generations);
  const [random, setRandom] = useState(JOINT_PRESETS.balanced.random);
  const [preselect, setPreselect] = useState(JOINT_PRESETS.balanced.preselect);
  const [robustPool, setRobustPool] = useState(JOINT_PRESETS.balanced.robustPool);
  const [surrogatePool, setSurrogatePool] = useState(JOINT_PRESETS.balanced.surrogatePool);
  const [surrogateProposals, setSurrogateProposals] = useState(JOINT_PRESETS.balanced.surrogateProposals);
  const [earlyStop, setEarlyStop] = useState(JOINT_PRESETS.balanced.earlyStop);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('');
  const [removing, setRemoving] = useState('');
  const pollRef = useRef(null);
  const timerRef = useRef(null);

  const presets = mode === 'joint' ? JOINT_PRESETS : TIMING_PRESETS;
  const availableSet = useMemo(() => new Set(availableSymbols), [availableSymbols]);
  const selectedSet = useMemo(() => new Set(selectedSymbols), [selectedSymbols]);
  const selectionKey = useMemo(() => [...selectedSymbols].sort().join('|'), [selectedSymbols]);
  const filteredSymbols = useMemo(() => {
    const q = symbolQuery.trim().toUpperCase();
    return q ? availableSymbols.filter((s) => s.includes(q)) : availableSymbols;
  }, [availableSymbols, symbolQuery]);
  const effectiveN = mode === 'joint' ? Number(portfolioSize) : selectedSymbols.length;
  const minFeasiblePositionPct = effectiveN > 0 ? 100 / effectiveN : 100;
  const healthCurrent = Boolean(health && analyzedKey && analyzedKey === selectionKey);

  useEffect(() => {
    let active = true;
    listAvailableSymbols()
      .then((data) => {
        if (!active) return;
        setAvailableSymbols(data.symbols);
        setMinSelected(data.minSelected);
        setMaxSelected(data.maxSelected);
        setSymbolsLoading(false);
        try {
          const saved = JSON.parse(window.localStorage.getItem('shannon.fixedCombination') || '[]');
          if (Array.isArray(saved)) {
            setSelectedSymbols([...new Set(saved.map((s) => String(s).toUpperCase()).filter((s) => data.symbols.includes(s)))].slice(0, data.maxSelected));
          }
        } catch (_err) {
          // Optional persistence only.
        }
      })
      .catch((err) => {
        if (!active) return;
        setSymbolsLoading(false);
        setSymbolsError(err.message);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (symbolsLoading) return;
    try {
      window.localStorage.setItem('shannon.fixedCombination', JSON.stringify(selectedSymbols));
    } catch (_err) {
      // Optional persistence only.
    }
  }, [selectedSymbols, symbolsLoading]);

  useEffect(() => {
    setHealth(null);
    setHealthError('');
    setAnalyzedKey('');
  }, [selectionKey]);

  useEffect(() => () => {
    clearInterval(pollRef.current);
    clearInterval(timerRef.current);
  }, []);

  function applyPreset(key, source = presets) {
    const p = source[key];
    if (!p) return;
    setPreset(key);
    setPopulation(p.population);
    setGenerations(p.generations);
    setRandom(p.random);
    setPreselect(p.preselect);
    setRobustPool(p.robustPool);
    setSurrogatePool(p.surrogatePool);
    setSurrogateProposals(p.surrogateProposals);
    setEarlyStop(p.earlyStop);
  }

  function changeMode(next) {
    setMode(next);
    applyPreset('balanced', next === 'joint' ? JOINT_PRESETS : TIMING_PRESETS);
    setMessage('');
  }

  function setCustom(setter) {
    return (value) => {
      setter(value);
      setPreset('custom');
    };
  }

  function toggleSymbol(symbol) {
    if (running) return;
    setSelectedSymbols((current) => {
      if (current.includes(symbol)) return current.filter((s) => s !== symbol);
      if (current.length >= maxSelected) return current;
      return [...current, symbol].sort();
    });
  }

  function importCombination() {
    const parsed = [...new Set(parseImportedSymbols(migrateInput))];
    if (!parsed.length) return window.alert('Enter ticker symbols, e.g. ACB, FPT, REE, VCB, VNM');
    const unknown = parsed.filter((s) => !availableSet.has(s));
    if (unknown.length) return window.alert(`Symbols not in loaded data: ${unknown.join(', ')}`);
    if (parsed.length < minSelected || parsed.length > maxSelected) return window.alert(`Combination must contain ${minSelected}–${maxSelected} symbols.`);
    setSelectedSymbols(parsed.sort());
  }

  function validateFixedSelection() {
    if (selectedSymbols.length < minSelected || selectedSymbols.length > maxSelected) return `Select ${minSelected}–${maxSelected} symbols.`;
    const unknown = selectedSymbols.filter((s) => !availableSet.has(s));
    if (unknown.length) return `Unknown symbols: ${unknown.join(', ')}`;
    return '';
  }

  async function runHealthCheck() {
    const error = validateFixedSelection();
    if (error) return window.alert(error);
    setHealthLoading(true);
    setHealthError('');
    setHealth(null);
    try {
      const result = await analyzeCombination([...selectedSymbols].sort(), true);
      setHealth(result);
      setAnalyzedKey([...selectedSymbols].sort().join('|'));
    } catch (err) {
      setHealthError(err.message);
      setAnalyzedKey('');
    } finally {
      setHealthLoading(false);
    }
  }

  function applyHealthSuggestion(suggestion) {
    const next = [...(suggestion.symbols || [])].sort();
    if (next.length >= minSelected && next.length <= maxSelected) setSelectedSymbols(next);
  }

  function validate() {
    if (mode === 'joint') {
      if (Number(portfolioSize) < 5 || Number(portfolioSize) > 10) return 'Portfolio size must be 5–10.';
    } else {
      const selectionError = validateFixedSelection();
      if (selectionError) return selectionError;
      if (!healthCurrent) return 'Analyze the current fixed combination first.';
      if (health?.status === 'invalid') return 'Fixed combination is INVALID.';
    }
    if (!Number.isFinite(Number(initialBalance)) || Number(initialBalance) <= 0) return 'Initial capital must be > 0.';
    if (!Number.isFinite(Number(annualDeposit)) || Number(annualDeposit) < 0) return 'Annual contribution cannot be negative.';
    if (riskOverlay && Number(maxPositionPct) + 1e-9 < minFeasiblePositionPct) return `With ${effectiveN} symbols, max stock weight cannot be below ${minFeasiblePositionPct.toFixed(1)}%.`;
    if (Number(maxOosDrawdownPct) <= 0 || Number(maxOosDrawdownPct) > 100) return 'Max OOS drawdown must be 0–100%.';
    if (Number(minEquityPct) < 0 || Number(minEquityPct) > 100) return 'Strategic minimum market exposure must be 0–100%.';
    return '';
  }

  async function runOptimizer(e) {
    if (e) e.preventDefault();
    const error = validate();
    if (error) return window.alert(error);

    setRunning(true);
    setElapsed(0);
    const desc = mode === 'joint'
      ? `Joint growth search · ${portfolioSize} stocks · universe ${universe.toUpperCase()} · allocation frequency + timing 1–6/year`
      : `Fixed ${selectedSymbols.join(' ')} · allocation frequency + timing 1–6/year`;
    setMessage(`${desc} · ${moneyShort(initialBalance)} initial · ${moneyShort(annualDeposit)}/year`);

    try {
      const payload = {
        mode,
        universe,
        portfolio_size: Number(portfolioSize),
        fixed_symbols: mode === 'timing' ? selectedSymbols : null,
        seed: Number(seed),
        population: Number(population),
        generations: Number(generations),
        random: Number(random),
        preselect_top: Number(preselect),
        finalists: 5,
        robust_pool_size: Number(robustPool),
        surrogate_pool_size: Number(surrogatePool),
        surrogate_proposals: Number(surrogateProposals),
        early_stop_generations: Number(earlyStop),
        parallel_workers: 0,
        initial_balance: Number(initialBalance),
        annual_deposit: Number(annualDeposit),
        risk_overlay: Boolean(riskOverlay),
        target_volatility: Number(targetVolPct) / 100,
        max_oos_drawdown_pct: Number(maxOosDrawdownPct),
        max_position_weight: Number(maxPositionPct) / 100,
        min_equity_exposure: Number(minEquityPct) / 100,
      };
      const res = await startOptimizerRun(payload);
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
    if (!window.confirm(`Delete optimizer experiment ${eid}?`)) return;
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
      <div className="breadcrumb"><a href="/">All runs</a> <span>/</span> Growth Optimizer</div>
      <header className="page-head">
        <h1>Growth Optimizer</h1>
        <p className="muted">
          Growth-first search with hard OOS risk gates. ERC, Shannon drift, transaction costs and the untouched final holdout remain in place.
        </p>
      </header>

      {running && (
        <div className="card run-loading">
          <div className="run-loading-inner">
            <span className="spinner" aria-hidden="true" />
            <div>
              <b>Optimizer running · {elapsed}s</b>
              <div className="muted">{message}</div>
              <div className="muted">Multi-core automatic · Run ID: {activeRun || '-'}</div>
            </div>
          </div>
        </div>
      )}

      <form className="card" onSubmit={runOptimizer}>
        <h3>1. Search mode</h3>
        <div className="universe-buttons" style={{ marginBottom: 12 }}>
          <button type="button" className="btn-variant" disabled={running} onClick={() => changeMode('joint')} style={{ borderColor: mode === 'joint' ? 'var(--accent)' : 'var(--border)', minWidth: 260 }}>
            <b>{mode === 'joint' ? '✓ ' : ''}Optimize combination + allocation</b>
            <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>Machine selects stocks, allocation frequency and timing.</div>
          </button>
          <button type="button" className="btn-variant" disabled={running} onClick={() => changeMode('timing')} style={{ borderColor: mode === 'timing' ? 'var(--accent)' : 'var(--border)', minWidth: 260 }}>
            <b>{mode === 'timing' ? '✓ ' : ''}Use my own combination</b>
            <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>You select stocks; machine optimizes frequency and timing.</div>
          </button>
        </div>

        {mode === 'joint' ? (
          <div className="sub-card">
            <div className="run-form">
              <label>Search universe
                <select value={universe} onChange={(e) => setUniverse(e.target.value)} disabled={running} style={{ width: 170 }}>
                  <option value="all">All data</option>
                  <option value="vn100">VN100</option>
                  <option value="vn50">VN50</option>
                  <option value="vn30">VN30</option>
                </select>
              </label>
              <NumberField label="Exact portfolio size" min={5} max={10} value={portfolioSize} onChange={setPortfolioSize} disabled={running} />
            </div>
            <div className="muted">
              The machine searches the stock combination and automatically searches 1–6 annual ERC/risk recalibration events plus their trading-session positions. Quarterly is only a benchmark now.
            </div>
          </div>
        ) : (
          <div className="sub-card">
            <h4 style={{ marginTop: 0 }}>Your fixed combination</h4>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              <textarea value={migrateInput} onChange={(e) => setMigrateInput(e.target.value)} disabled={running} placeholder="ACB, FPT, REE, VCB, VNM" style={{ minWidth: 360, minHeight: 60, flex: '1 1 360px' }} />
              <button className="btn-variant" type="button" disabled={running || symbolsLoading} onClick={importCombination}>Import</button>
            </div>
            <input type="text" value={symbolQuery} onChange={(e) => setSymbolQuery(e.target.value)} placeholder="Search ticker" disabled={running || symbolsLoading} style={{ width: '100%', maxWidth: 320, marginBottom: 8 }} />
            {symbolsLoading ? <div className="muted">Loading symbols…</div> : symbolsError ? <div className="error">{symbolsError}</div> : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(92px, 1fr))', gap: 6, maxHeight: 260, overflowY: 'auto', padding: 8, border: '1px solid var(--border)', borderRadius: 8 }}>
                {filteredSymbols.map((symbol) => {
                  const checked = selectedSet.has(symbol);
                  const disabled = running || (!checked && selectedSymbols.length >= maxSelected);
                  return (
                    <label key={symbol} style={{ display: 'flex', gap: 6, alignItems: 'center', padding: 6, border: '1px solid var(--border)', borderRadius: 6, opacity: disabled ? 0.45 : 1, textTransform: 'none', letterSpacing: 0 }}>
                      <input type="checkbox" checked={checked} disabled={disabled} onChange={() => toggleSymbol(symbol)} /> <b>{symbol}</b>
                    </label>
                  );
                })}
              </div>
            )}
            <div style={{ marginTop: 10 }}><b>Selected {selectedSymbols.length}/{maxSelected}:</b> {selectedSymbols.join(' · ') || '-'}</div>
            <button className="btn-variant" type="button" disabled={running || healthLoading || selectedSymbols.length < minSelected} onClick={runHealthCheck} style={{ marginTop: 10, borderColor: 'var(--accent)' }}>
              {healthLoading ? 'Analyzing…' : 'Analyze combination'}
            </button>
            {healthError && <div className="error" style={{ marginTop: 8 }}>{healthError}</div>}
            {healthCurrent && <HealthPanel health={health} onApplySuggestion={applyHealthSuggestion} />}
          </div>
        )}

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3>2. Capital plan</h3>
        <div className="run-form">
          <NumberField label="Initial balance (VND)" min={1_000_000} step={1_000_000} value={initialBalance} onChange={setInitialBalance} disabled={running} hint={moneyShort(initialBalance)} />
          <NumberField label="Money added each year (VND)" min={0} step={1_000_000} value={annualDeposit} onChange={setAnnualDeposit} disabled={running} hint={moneyShort(annualDeposit)} />
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3>3. Risk policy</h3>
        <div className="muted" style={{ marginBottom: 10 }}>Growth is the search priority; risk remains a hard validation constraint.</div>
        <div className="run-form">
          <label>Risk policy
            <select value={riskOverlay ? 'on' : 'off'} onChange={(e) => setRiskOverlay(e.target.value === 'on')} disabled={running} style={{ width: 220 }}>
              <option value="on">Risk-aware · volatility target</option>
              <option value="off">Baseline · 100% equity</option>
            </select>
          </label>
          <NumberField label="Target volatility %" min={5} max={50} value={targetVolPct} onChange={setTargetVolPct} disabled={!riskOverlay || running} />
          <NumberField label="Max OOS drawdown %" min={10} max={80} value={maxOosDrawdownPct} onChange={setMaxOosDrawdownPct} disabled={running} />
          <NumberField label="Max stock weight %" min={Math.ceil(minFeasiblePositionPct)} max={100} value={maxPositionPct} onChange={setMaxPositionPct} disabled={!riskOverlay || running} />
        </div>
        <div className="muted" style={{ marginTop: 8 }}>
          Default risk policy has no forced equity floor: valid volatility targeting may de-risk all the way to cash. If risk data is unavailable, the system separately fails closed to 0% equity.
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3>4. Search quality</h3>
        <div className="universe-buttons" style={{ marginBottom: 12 }}>
          {Object.entries(presets).map(([key, p]) => (
            <button key={key} type="button" className="btn-variant" disabled={running} onClick={() => applyPreset(key)} style={{ borderColor: preset === key ? 'var(--accent)' : 'var(--border)', minWidth: 170, textAlign: 'left' }}>
              <div>{preset === key ? '✓ ' : ''}{p.label}</div>
              <div className="muted" style={{ fontSize: 11, fontWeight: 400 }}>{p.note}</div>
            </button>
          ))}
        </div>

        <button type="button" className="btn-variant btn-all" disabled={running} onClick={() => setShowAdvanced((v) => !v)} style={{ marginBottom: 12 }}>
          {showAdvanced ? 'Hide advanced settings' : 'Show advanced settings'}
        </button>

        {showAdvanced && (
          <div className="sub-card" style={{ marginBottom: 14 }}>
            <h4 style={{ marginTop: 0 }}>Advanced risk</h4>
            <div className="run-form" style={{ marginBottom: 12 }}>
              <NumberField
                label="Strategic minimum market exposure %"
                min={0}
                max={100}
                step={5}
                value={minEquityPct}
                onChange={setMinEquityPct}
                disabled={!riskOverlay || running}
                hint="0% recommended; this floor applies only when risk is valid"
              />
            </div>
            <div className="muted" style={{ marginBottom: 14 }}>
              Missing/invalid risk data is not overridden by this floor: the fail-closed exposure remains 0%.
            </div>

            <h4>Advanced search</h4>
            <div className="run-form">
              <NumberField label="Seed" min={0} value={seed} onChange={setSeed} disabled={running} />
              <NumberField label="Population" min={10} value={population} onChange={setCustom(setPopulation)} disabled={running} />
              <NumberField label="Generations" min={1} value={generations} onChange={setCustom(setGenerations)} disabled={running} />
              <NumberField label="Random backtests" min={20} value={random} onChange={setCustom(setRandom)} disabled={running} />
              <NumberField label="TRAIN preselect" min={0} value={preselect} onChange={setCustom(setPreselect)} disabled={running || mode !== 'joint'} />
              <NumberField label="Validation shortlist" min={5} value={robustPool} onChange={setCustom(setRobustPool)} disabled={running} />
              <NumberField label="Surrogate pool" min={0} value={surrogatePool} onChange={setCustom(setSurrogatePool)} disabled={running} />
              <NumberField label="Real surrogate proposals" min={0} value={surrogateProposals} onChange={setCustom(setSurrogateProposals)} disabled={running} />
              <NumberField label="Early-stop patience" min={0} value={earlyStop} onChange={setCustom(setEarlyStop)} disabled={running} />
            </div>
          </div>
        )}

        <div className="sub-card" style={{ marginBottom: 14 }}>
          <div className="diag-grid" style={{ marginBottom: 0 }}>
            <div><span>Mode</span><b>{mode === 'joint' ? 'Joint growth' : 'Fixed combination'}</b></div>
            <div><span>Portfolio</span><b>{mode === 'joint' ? `${portfolioSize} stocks from ${universe.toUpperCase()}` : selectedSymbols.join(' ') || '-'}</b></div>
            <div><span>Allocation search</span><b>1–6 events/year + timing</b></div>
            <div><span>Initial balance</span><b>{moneyShort(initialBalance)}</b></div>
            <div><span>Annual money</span><b>{moneyShort(annualDeposit)}</b></div>
            <div><span>Risk</span><b>{riskOverlay ? `${targetVolPct}% vol / ${maxOosDrawdownPct}% MDD${Number(minEquityPct) > 0 ? ` / ${minEquityPct}% floor` : ''}` : '100% equity'}</b></div>
          </div>
        </div>

        {!running && message && <div className="run-message" style={{ marginBottom: 10 }}>{message}</div>}
        <button
          className="btn-export"
          type="submit"
          disabled={running || symbolsLoading || (mode === 'timing' && (!healthCurrent || health?.status === 'invalid'))}
          style={{ border: 0, cursor: running ? 'not-allowed' : 'pointer', opacity: running ? 0.55 : 1, fontSize: 14, padding: '11px 20px' }}
        >
          {running ? 'Optimizer running…' : mode === 'joint' ? '▶ Find best growth combination + allocation' : '▶ Optimize my combination'}
        </button>
        <div className="muted" style={{ marginTop: 10 }}>
          Growth-first TRAIN search → rolling OOS risk gate → recent pre-holdout validation → untouched final holdout. Final holdout is never used to generate candidates.
        </div>
      </form>

      <div className="card">
        <h3>Optimizer experiments ({items.length})</h3>
        {items.length === 0 ? <div className="muted">No optimizer experiments yet.</div> : (
          <ul className="run-list">
            {items.map((e) => (
              <li key={e.experiment_id} className={removing === e.experiment_id ? 'run-removing' : ''}>
                <div className="run-link">
                  <a href={`/optimizer/${e.experiment_id}`}>{e.experiment_id}</a>
                  <span className="muted">{e.generated_at} · {e.mode || '-'}{e.portfolio_size ? ` · N=${e.portfolio_size}` : ''}</span>
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
