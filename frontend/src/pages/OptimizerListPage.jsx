import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  startOptimizerRun,
  getOptimizerStatus,
  deleteOptimizerExperiment,
  listAvailableSymbols,
  analyzeCombination,
} from '../lib/api.js';

const SEARCH_PRESETS = {
  fast: {
    label: 'Fast', note: 'Quick allocation-timing exploration',
    population: 24, generations: 10, random: 40,
    robustPool: 25, surrogatePool: 500,
    surrogateProposals: 8, earlyStop: 6,
  },
  balanced: {
    label: 'Balanced', note: 'Recommended for a fixed combination',
    population: 36, generations: 18, random: 80,
    robustPool: 50, surrogatePool: 1500,
    surrogateProposals: 16, earlyStop: 8,
  },
  thorough: {
    label: 'Thorough', note: 'More timing coverage and validation',
    population: 50, generations: 28, random: 140,
    robustPool: 80, surrogatePool: 3000,
    surrogateProposals: 24, earlyStop: 12,
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
      // Fall through to the permissive ticker parser below.
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
  const statusLabel = status === 'healthy' ? 'HEALTHY' : status === 'warning' ? 'WARNING' : 'INVALID';
  const statusColor = status === 'healthy' ? 'var(--success)' : status === 'warning' ? 'var(--warning)' : 'var(--danger)';
  const correlation = health.correlation || {};
  const diversification = health.diversification || {};
  const erc = health.erc || {};
  const score = health.score || {};
  const pairs = (correlation.high_pairs || []).slice(0, 10);
  const clusters = correlation.clusters || [];
  const suggestions = health.suggestions || [];

  return (
    <div className="sub-card" style={{ marginTop: 12, borderColor: statusColor }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h4 style={{ margin: 0 }}>Combination Health</h4>
          <div className="muted">Research only through {health.research_end}; final {health.reserved_holdout?.trading_days || 252} sessions are reserved and not inspected.</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <b style={{ color: statusColor, fontSize: 16 }}>{statusLabel}</b>
          <div className="muted">Health score {num(score.overall, 1)} / 100</div>
        </div>
      </div>

      <div className="diag-grid" style={{ marginTop: 14, marginBottom: 12 }}>
        <div><span>Average risk correlation</span><b>{num(correlation.average, 2)}</b></div>
        <div><span>Maximum risk correlation</span><b>{num(correlation.maximum, 2)}</b></div>
        <div><span>High-correlation pairs</span><b>{num(Number(correlation.high_pair_ratio || 0) * 100, 0)}%</b></div>
        <div><span>Largest corr cluster</span><b>{correlation.largest_cluster_size || 1}/{health.symbols?.length || 0}</b></div>
        <div><span>Diversification ratio</span><b>{num(diversification.ratio, 2)}</b></div>
        <div><span>ERC feasible</span><b style={{ color: erc.feasible ? 'var(--success)' : 'var(--danger)' }}>{erc.feasible ? 'YES' : 'NO'}</b></div>
        <div><span>ERC portfolio vol</span><b>{erc.portfolio_volatility_pct == null ? '-' : `${num(erc.portfolio_volatility_pct, 2)}%`}</b></div>
        <div><span>Aligned observations</span><b>{erc.observations || 0}</b></div>
      </div>

      <div className="diag-grid" style={{ marginBottom: 12 }}>
        <div><span>Data quality</span><b>{num(score.data_quality, 0)}/100</b></div>
        <div><span>Correlation quality</span><b>{num(score.correlation, 0)}/100</b></div>
        <div><span>Diversification</span><b>{num(score.diversification, 0)}/100</b></div>
        <div><span>ERC feasibility</span><b>{num(score.erc_feasibility, 0)}/100</b></div>
      </div>

      {(health.reasons || []).length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <b>{status === 'invalid' ? 'Blocking reasons' : 'Warnings'}</b>
          <ul style={{ margin: '6px 0 0 18px', padding: 0 }}>
            {health.reasons.map((reason, i) => <li key={`${reason}-${i}`}>{reason}</li>)}
          </ul>
        </div>
      )}

      <div className="expand-grid" style={{ marginBottom: 12 }}>
        <div className="sub-card">
          <h4>252D research diagnostic</h4>
          <div className="diag-row"><span>Equal-weight return ann.</span><b>{diversification.equal_weight_return_pct == null ? '-' : `${num(diversification.equal_weight_return_pct, 2)}%`}</b></div>
          <div className="diag-row"><span>Equal-weight volatility</span><b>{diversification.equal_weight_volatility_pct == null ? '-' : `${num(diversification.equal_weight_volatility_pct, 2)}%`}</b></div>
          <div className="diag-row"><span>Equal-weight Sharpe</span><b>{num(diversification.equal_weight_sharpe, 3)}</b></div>
          <div className="diag-row"><span>Equal-weight MDD</span><b>{diversification.equal_weight_mdd_pct == null ? '-' : `${num(diversification.equal_weight_mdd_pct, 2)}%`}</b></div>
          <div className="muted" style={{ marginTop: 6 }}>Diagnostic only — this is not the ERC/Shannon strategy result and is not a forecast.</div>
        </div>
        <div className="sub-card">
          <h4>Correlation structure</h4>
          <div className="diag-row"><span>Policy</span><b>{correlation.pair_policy || 'max(63D,252D)'}</b></div>
          <div className="diag-row"><span>Short / long window</span><b>{correlation.short_window_days || 63}D / {correlation.long_window_days || 252}D</b></div>
          <div className="diag-row"><span>Clusters</span><b>{clusters.length || 0}</b></div>
          <div className="muted" style={{ marginTop: 6 }}>
            {clusters.length ? clusters.map((c) => c.join(' · ')).join(' | ') : 'No high-correlation cluster >= 0.75.'}
          </div>
        </div>
      </div>

      {pairs.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <h4>High-correlation pairs</h4>
          <table className="ranking">
            <thead><tr><th>Pair</th><th>63D</th><th>252D</th><th>Risk corr</th></tr></thead>
            <tbody>
              {pairs.map((p) => (
                <tr key={`${p.a}-${p.b}`}>
                  <td>{p.a} / {p.b}</td>
                  <td>{num(p.corr_63d, 2)}</td>
                  <td>{num(p.corr_252d, 2)}</td>
                  <td><b>{num(p.risk_corr, 2)}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <h4>Data coverage</h4>
        <table className="ranking">
          <thead><tr><th>Symbol</th><th>History</th><th>Research coverage</th><th>Recent 252D</th></tr></thead>
          <tbody>
            {(health.data_quality || []).map((row) => (
              <tr key={row.symbol}>
                <td><b>{row.symbol}</b></td>
                <td>{num(row.history_years, 1)}y</td>
                <td>{num(Number(row.research_coverage || 0) * 100, 0)}%</td>
                <td>{num(Number(row.recent_252d_coverage || 0) * 100, 0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {status !== 'invalid' && (
        <div>
          <h4>Optional diversification suggestions</h4>
          {suggestions.length === 0 ? (
            <div className="muted">No replacement passed the research-only diversification + quality guard.</div>
          ) : (
            <div style={{ display: 'grid', gap: 9 }}>
              {suggestions.map((s) => (
                <div key={`${s.remove}-${s.add}`} style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <div>
                      <b>{s.remove} → {s.add}</b>
                      <div className="muted">{(s.reasons || []).join(' · ')}</div>
                    </div>
                    <button className="btn-variant" type="button" onClick={() => onApplySuggestion(s)}>
                      Apply suggestion
                    </button>
                  </div>
                  <div className="diag-grid" style={{ marginTop: 8, marginBottom: 0 }}>
                    <div><span>Avg corr</span><b>{num(s.before?.average_correlation, 2)} → {num(s.after?.average_correlation, 2)}</b></div>
                    <div><span>Max corr</span><b>{num(s.before?.max_correlation, 2)} → {num(s.after?.max_correlation, 2)}</b></div>
                    <div><span>Diversification</span><b>{num(s.before?.diversification_ratio, 2)} → {num(s.after?.diversification_ratio, 2)}</b></div>
                    <div><span>Largest cluster</span><b>{s.before?.largest_cluster_size ?? '-'} → {s.after?.largest_cluster_size ?? '-'}</b></div>
                    <div><span>EW return diag.</span><b>{num(s.before?.equal_weight_return_pct, 1)}% → {num(s.after?.equal_weight_return_pct, 1)}%</b></div>
                    <div><span>EW Sharpe diag.</span><b>{num(s.before?.equal_weight_sharpe, 2)} → {num(s.after?.equal_weight_sharpe, 2)}</b></div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="muted" style={{ marginTop: 8 }}>
            Suggestions only reduce research-period concentration subject to a quality guard. Nothing is replaced automatically; applying one requires a fresh health check.
          </div>
        </div>
      )}
    </div>
  );
}

export default function OptimizerListPage({ experiments }) {
  const [items, setItems] = useState(experiments || []);
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
  const [minEquityPct, setMinEquityPct] = useState(25);

  const [preset, setPreset] = useState('balanced');
  const [seed, setSeed] = useState(42);
  const [population, setPopulation] = useState(36);
  const [generations, setGenerations] = useState(18);
  const [random, setRandom] = useState(80);
  const [robustPool, setRobustPool] = useState(50);
  const [surrogatePool, setSurrogatePool] = useState(1500);
  const [surrogateProposals, setSurrogateProposals] = useState(16);
  const [earlyStop, setEarlyStop] = useState(8);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [message, setMessage] = useState('');
  const [removing, setRemoving] = useState('');
  const pollRef = useRef(null);
  const timerRef = useRef(null);

  const availableSet = useMemo(() => new Set(availableSymbols), [availableSymbols]);
  const selectedSet = useMemo(() => new Set(selectedSymbols), [selectedSymbols]);
  const selectionKey = useMemo(() => [...selectedSymbols].sort().join('|'), [selectedSymbols]);
  const filteredSymbols = useMemo(() => {
    const q = symbolQuery.trim().toUpperCase();
    return q ? availableSymbols.filter((s) => s.includes(q)) : availableSymbols;
  }, [availableSymbols, symbolQuery]);
  const minFeasiblePositionPct = selectedSymbols.length > 0 ? 100 / selectedSymbols.length : 100;
  const healthCurrent = Boolean(health && analyzedKey && analyzedKey === selectionKey);
  const optimizationAllowed = healthCurrent && health?.status !== 'invalid';

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
            const restored = saved
              .map((s) => String(s).toUpperCase())
              .filter((s) => data.symbols.includes(s))
              .slice(0, data.maxSelected);
            setSelectedSymbols([...new Set(restored)]);
          }
        } catch (_err) {
          // Ignore malformed local state.
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
      // Local persistence is convenience only.
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

  function applyPreset(key) {
    const p = SEARCH_PRESETS[key];
    if (!p) return;
    setPreset(key);
    setPopulation(p.population);
    setGenerations(p.generations);
    setRandom(p.random);
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
    if (!parsed.length) {
      window.alert('Enter ticker symbols to migrate, for example: ACB, FPT, REE, VCB, VNM');
      return;
    }
    const unknown = parsed.filter((s) => !availableSet.has(s));
    if (unknown.length) {
      window.alert(`These symbols do not exist in the loaded dataset: ${unknown.join(', ')}`);
      return;
    }
    if (parsed.length > maxSelected) {
      window.alert(`A combination can currently contain at most ${maxSelected} symbols.`);
      return;
    }
    setSelectedSymbols(parsed.sort());
    setSymbolQuery('');
  }

  function validateSelection() {
    if (selectedSymbols.length < minSelected || selectedSymbols.length > maxSelected) {
      return `Select ${minSelected}–${maxSelected} symbols.`;
    }
    if (new Set(selectedSymbols).size !== selectedSymbols.length) return 'Combination contains duplicate symbols.';
    const unknown = selectedSymbols.filter((s) => !availableSet.has(s));
    if (unknown.length) return `Unknown symbols: ${unknown.join(', ')}`;
    return '';
  }

  async function runHealthCheck() {
    const error = validateSelection();
    if (error) {
      window.alert(error);
      return;
    }
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
    if (next.length < minSelected || next.length > maxSelected) return;
    setSelectedSymbols(next);
    setSymbolQuery('');
  }

  function validate() {
    const selectionError = validateSelection();
    if (selectionError) return selectionError;
    if (!healthCurrent) return 'Analyze the current combination before running allocation optimization.';
    if (health?.status === 'invalid') return 'Combination health is INVALID. Fix the data/combination before optimization.';
    if (!Number.isFinite(Number(initialBalance)) || Number(initialBalance) <= 0) return 'Initial capital must be greater than 0 VND.';
    if (!Number.isFinite(Number(annualDeposit)) || Number(annualDeposit) < 0) return 'Annual contribution cannot be negative.';
    if (riskOverlay && (Number(targetVolPct) <= 0 || Number(targetVolPct) > 100)) return 'Target volatility must be between 0% and 100%.';
    if (Number(maxOosDrawdownPct) <= 0 || Number(maxOosDrawdownPct) > 100) return 'Max OOS drawdown must be between 0% and 100%.';
    if (riskOverlay && (Number(minEquityPct) < 0 || Number(minEquityPct) > 100)) return 'Minimum equity exposure must be between 0% and 100%.';
    if (riskOverlay && (Number(maxPositionPct) <= 0 || Number(maxPositionPct) > 100)) return 'Maximum single-stock weight must be between 0% and 100%.';
    if (riskOverlay && Number(maxPositionPct) + 1e-9 < minFeasiblePositionPct) {
      return `With ${selectedSymbols.length} symbols, max single-stock weight cannot be below ${minFeasiblePositionPct.toFixed(1)}%.`;
    }
    if (Number(robustPool) < 5) return 'Validation shortlist must contain at least 5 timing candidates.';
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
    const riskDesc = riskOverlay ? `risk target ${targetVolPct}% · OOS MDD gate ${maxOosDrawdownPct}%` : 'baseline 100% equity';
    setMessage(`${selectedSymbols.join(' ')} · health ${health?.status || '-'} ${num(health?.score?.overall, 0)}/100 · ${moneyShort(initialBalance)} initial · ${moneyShort(annualDeposit)}/year · ${riskDesc}`);

    try {
      const res = await startOptimizerRun({
        mode: 'timing',
        fixed_symbols: selectedSymbols,
        universe: 'all',
        seed: Number(seed),
        population: Number(population),
        generations: Number(generations),
        random: Number(random),
        finalists: 5,
        initial_balance: Number(initialBalance),
        annual_deposit: Number(annualDeposit),
        risk_overlay: Boolean(riskOverlay),
        target_volatility: Number(targetVolPct) / 100,
        max_oos_drawdown_pct: Number(maxOosDrawdownPct),
        max_position_weight: Number(maxPositionPct) / 100,
        min_equity_exposure: Number(minEquityPct) / 100,
        preselect_top: 0,
        robust_pool_size: Number(robustPool),
        surrogate_pool_size: Number(surrogatePool),
        surrogate_proposals: Number(surrogateProposals),
        early_stop_generations: Number(earlyStop),
        parallel_workers: 0,
      });
      if (!res.run_id) throw new Error(res.error || 'Allocation optimizer did not start.');
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
            setMessage('Done — opening allocation experiment…');
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
      <div className="breadcrumb"><a href="/">All runs</a> <span>/</span> Allocation Optimizer</div>
      <header className="page-head">
        <h1>Allocation Optimizer</h1>
        <p className="muted">
          You own the stock combination. First validate data/correlation/diversification, optionally review suggestions, then the system keeps the approved symbols fixed and optimizes only the four annual allocation times.
        </p>
      </header>

      {running && (
        <div className="card run-loading">
          <div className="run-loading-inner">
            <span className="spinner" aria-hidden="true" />
            <div>
              <b>Allocation optimizer is running · {elapsed}s</b>
              <div className="muted">{message}</div>
              <div className="muted">Selected symbols are frozen · Multi-core evaluation automatic · Run ID: {activeRun || '-'}</div>
            </div>
          </div>
        </div>
      )}

      <form className="card" onSubmit={runOptimizer}>
        <h3 style={{ marginBottom: 4 }}>1. Your combination</h3>
        <div className="muted" style={{ marginBottom: 12 }}>
          Choose {minSelected}–{maxSelected} symbols. The optimizer is not allowed to add, remove or replace a ticker.
        </div>

        <div className="sub-card" style={{ marginBottom: 14 }}>
          <h4 style={{ marginTop: 0 }}>Migrate an existing combination</h4>
          <div className="muted" style={{ marginBottom: 8 }}>
            Paste tickers from an existing portfolio. Commas, spaces, new lines and JSON arrays are accepted.
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <textarea
              value={migrateInput}
              onChange={(e) => setMigrateInput(e.target.value)}
              disabled={running}
              placeholder={'ACB, FPT, REE, VCB, VNM\n\nor ["ACB", "FPT", "REE", "VCB", "VNM"]'}
              style={{ minWidth: 420, minHeight: 72, flex: '1 1 420px' }}
            />
            <button className="btn-variant" type="button" disabled={running || symbolsLoading} onClick={importCombination}>
              Import combination
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
          <div>
            <b>Selected: {selectedSymbols.length}/{maxSelected}</b>
            <div className="muted">{selectedSymbols.length ? selectedSymbols.join(' · ') : 'No symbols selected yet.'}</div>
          </div>
          <button className="btn-variant" type="button" disabled={running || selectedSymbols.length === 0} onClick={() => setSelectedSymbols([])}>
            Clear selection
          </button>
        </div>

        <input
          type="text"
          value={symbolQuery}
          onChange={(e) => setSymbolQuery(e.target.value)}
          disabled={running || symbolsLoading}
          placeholder="Search ticker, e.g. FPT"
          style={{ width: '100%', maxWidth: 360, marginBottom: 10 }}
        />

        {symbolsLoading ? (
          <div className="muted">Loading available symbols…</div>
        ) : symbolsError ? (
          <div className="error">Could not load symbol list: {symbolsError}</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(92px, 1fr))', gap: 7, maxHeight: 310, overflowY: 'auto', padding: 8, border: '1px solid var(--border)', borderRadius: 8 }}>
            {filteredSymbols.map((symbol) => {
              const checked = selectedSet.has(symbol);
              const disabled = running || healthLoading || (!checked && selectedSymbols.length >= maxSelected);
              return (
                <label
                  key={symbol}
                  style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '7px 8px', border: '1px solid var(--border)', borderRadius: 7, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.45 : 1, textTransform: 'none', letterSpacing: 0 }}
                >
                  <input type="checkbox" checked={checked} disabled={disabled} onChange={() => toggleSymbol(symbol)} />
                  <b>{symbol}</b>
                </label>
              );
            })}
          </div>
        )}

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3 style={{ marginBottom: 4 }}>2. Combination validation</h3>
        <div className="muted" style={{ marginBottom: 10 }}>
          Fast research-only check: data coverage, 63D/252D correlation, high-correlation clusters, diversification and ERC feasibility. Suggestions never inspect the reserved final holdout.
        </div>
        <button
          className="btn-variant"
          type="button"
          disabled={running || healthLoading || symbolsLoading || selectedSymbols.length < minSelected || selectedSymbols.length > maxSelected}
          onClick={runHealthCheck}
          style={{ borderColor: 'var(--accent)' }}
        >
          {healthLoading ? 'Analyzing combination…' : 'Analyze combination'}
        </button>
        {healthError && <div className="error" style={{ marginTop: 10 }}>{healthError}</div>}
        {healthCurrent && <HealthPanel health={health} onApplySuggestion={applyHealthSuggestion} />}

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3 style={{ marginBottom: 4 }}>3. Capital plan</h3>
        <div className="muted" style={{ marginBottom: 12 }}>
          These values are part of every backtest. Annual money is added on the first trading session of each new year; the result records when cash is actually deployed.
        </div>
        <div className="run-form">
          <NumberField label="Initial balance (VND)" min={1_000_000} step={1_000_000} value={initialBalance} onChange={setInitialBalance} disabled={running} hint={moneyShort(initialBalance)} />
          <NumberField label="Money added each year (VND)" min={0} step={1_000_000} value={annualDeposit} onChange={setAnnualDeposit} disabled={running} hint={moneyShort(annualDeposit)} />
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3 style={{ marginBottom: 4 }}>4. Risk policy</h3>
        <div className="muted" style={{ marginBottom: 12 }}>
          ERC still determines relative stock weights. Risk-aware mode may scale total equity exposure; Shannon handles drift between allocation events.
        </div>
        <div className="run-form">
          <label>Risk policy
            <select value={riskOverlay ? 'on' : 'off'} onChange={(e) => setRiskOverlay(e.target.value === 'on')} style={{ width: 220 }} disabled={running}>
              <option value="on">Risk-aware · volatility target</option>
              <option value="off">Baseline · 100% equity</option>
            </select>
          </label>
          <NumberField label="Target volatility %" min={5} max={50} value={targetVolPct} onChange={setTargetVolPct} disabled={!riskOverlay || running} />
          <NumberField label="Max OOS drawdown %" min={10} max={80} value={maxOosDrawdownPct} onChange={setMaxOosDrawdownPct} disabled={running} />
          <NumberField label="Max stock weight %" min={selectedSymbols.length ? Math.ceil(minFeasiblePositionPct) : 10} max={100} value={maxPositionPct} onChange={setMaxPositionPct} disabled={!riskOverlay || running} />
          <NumberField label="Min equity exposure %" min={0} max={100} step={5} value={minEquityPct} onChange={setMinEquityPct} disabled={!riskOverlay || running} />
        </div>

        <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '18px 0' }} />

        <h3 style={{ marginBottom: 4 }}>5. Allocation search quality</h3>
        <div className="muted" style={{ marginBottom: 10 }}>
          Only four annual allocation positions are searched. Symbols remain fixed, so this is much cheaper than the retired joint symbol search.
        </div>
        <div className="universe-buttons" style={{ marginBottom: 12 }}>
          {Object.entries(SEARCH_PRESETS).map(([key, p]) => (
            <button
              key={key}
              className="btn-variant"
              type="button"
              disabled={running}
              onClick={() => applyPreset(key)}
              style={{ borderColor: preset === key ? 'var(--accent)' : 'var(--border)', minWidth: 170, textAlign: 'left' }}
            >
              <div>{preset === key ? '✓ ' : ''}{p.label}</div>
              <div className="muted" style={{ fontWeight: 400, fontSize: 11 }}>{p.note}</div>
            </button>
          ))}
        </div>

        <button type="button" className="btn-variant btn-all" disabled={running} onClick={() => setShowAdvanced((v) => !v)} style={{ marginBottom: 12 }}>
          {showAdvanced ? 'Hide advanced allocation settings' : 'Show advanced allocation settings'}
        </button>

        {showAdvanced && (
          <div className="sub-card" style={{ marginBottom: 14 }}>
            <div className="run-form">
              <NumberField label="Seed" min={0} value={seed} onChange={setSeed} disabled={running} />
              <NumberField label="Population" min={10} value={population} onChange={setCustom(setPopulation)} disabled={running} />
              <NumberField label="Generations" min={1} value={generations} onChange={setCustom(setGenerations)} disabled={running} />
              <NumberField label="Random timing backtests" min={20} value={random} onChange={setCustom(setRandom)} disabled={running} />
              <NumberField label="Validation shortlist" min={5} value={robustPool} onChange={setCustom(setRobustPool)} disabled={running} />
              <NumberField label="Surrogate timing pool" min={0} value={surrogatePool} onChange={setCustom(setSurrogatePool)} disabled={running} />
              <NumberField label="Real surrogate proposals" min={0} value={surrogateProposals} onChange={setCustom(setSurrogateProposals)} disabled={running} />
              <NumberField label="Early-stop patience" min={0} value={earlyStop} onChange={setCustom(setEarlyStop)} disabled={running} />
            </div>
          </div>
        )}

        <div className="sub-card" style={{ marginBottom: 14 }}>
          <div className="diag-grid" style={{ marginBottom: 0 }}>
            <div><span>Fixed combination</span><b>{selectedSymbols.length ? selectedSymbols.join(' ') : 'Select symbols'}</b></div>
            <div><span>Combination health</span><b>{healthCurrent ? `${String(health?.status || '').toUpperCase()} · ${num(health?.score?.overall, 0)}/100` : 'Analyze first'}</b></div>
            <div><span>Initial balance</span><b>{moneyShort(initialBalance)}</b></div>
            <div><span>Annual money</span><b>{moneyShort(annualDeposit)}</b></div>
            <div><span>Search target</span><b>4 allocation times / year</b></div>
            <div><span>Risk</span><b>{riskOverlay ? `${targetVolPct}% vol / ${maxOosDrawdownPct}% MDD` : '100% equity baseline'}</b></div>
            <div><span>Search quality</span><b>{SEARCH_PRESETS[preset]?.label || 'Custom'}</b></div>
          </div>
        </div>

        {!running && message && <div className="run-message" style={{ marginBottom: 10 }}>{message}</div>}
        <button
          className="btn-export"
          type="submit"
          disabled={running || symbolsLoading || healthLoading || !optimizationAllowed}
          style={{ border: 0, cursor: optimizationAllowed && !running ? 'pointer' : 'not-allowed', opacity: optimizationAllowed && !running ? 1 : 0.55, fontSize: 14, padding: '11px 20px' }}
        >
          {running ? 'Allocation optimizer running…' : !healthCurrent ? 'Analyze combination first' : health?.status === 'invalid' ? 'Combination invalid' : '▶ Optimize allocation'}
        </button>
        <div className="muted" style={{ marginTop: 10 }}>
          User symbols → health check → optional user-approved suggestion → fixed symbols → timing search → ERC → risk overlay → Shannon drift → rolling OOS validation → recent validation → untouched final holdout.
        </div>
      </form>

      <div className="card">
        <h3>Allocation experiments ({items.length})</h3>
        {items.length === 0 ? <div className="muted">No allocation experiments yet.</div> : (
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
