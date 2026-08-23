import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { setReferenceWeights } from '../lib/api.js';

export default function SettingsPage({ dashboard = {} }) {
  const positions = dashboard.portfolio?.positions || [];
  const current = dashboard.portfolio?.reference_weights || {};
  const [weights, setWeights] = useState(() => Object.fromEntries(
    positions.map((p) => [p.symbol, current[p.symbol] != null ? Number(current[p.symbol]) * 100 : ''])
  ));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const total = useMemo(
    () => Object.values(weights).reduce((sum, v) => sum + (v === '' ? 0 : Number(v || 0)), 0),
    [weights]
  );

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const nonEmpty = Object.entries(weights).filter(([, v]) => String(v).trim() !== '' && Number(v) > 0);
      if (nonEmpty.length && Math.abs(total - 100) > 0.001) {
        throw new Error(`Reference weights must total 100%. Current total: ${total.toFixed(2)}%.`);
      }
      const payload = Object.fromEntries(nonEmpty.map(([s, v]) => [s, Number(v) / 100]));
      await setReferenceWeights(payload);
      setMessage(payload && Object.keys(payload).length ? 'Strategic reference weights saved.' : 'Strategic reference weights cleared.');
      setSaving(false);
    } catch (err) {
      setMessage(err.message);
      setSaving(false);
    }
  }

  function clear() {
    setWeights(Object.fromEntries(positions.map((p) => [p.symbol, ''])));
  }

  return (
    <div className="page">
      <AppNav active="Settings" />
      <header className="page-head">
        <h1>Settings</h1>
        <p className="muted">Only long-lived portfolio information preferences live here. There are no annual allocation or optimizer settings in the operational product.</p>
      </header>

      <form className="card" onSubmit={save}>
        <h3>Strategic reference weights <span className="muted">optional</span></h3>
        <p className="muted">References do not expire or recalculate annually. They only drive HOLD / ADD / REVIEW information and BUY-only cash-deployment suggestions.</p>
        {positions.length === 0 ? (
          <p className="muted">Add/import holdings before defining references.</p>
        ) : (
          <div className="reference-grid">
            {positions.map((p) => (
              <label key={p.symbol}>
                <span><b>{p.symbol}</b> <span className="muted">current {(Number(p.weight || 0) * 100).toFixed(1)}%</span></span>
                <div className="reference-input"><input type="number" min="0" max="100" step="0.01" value={weights[p.symbol] ?? ''} onChange={(e) => setWeights((x) => ({ ...x, [p.symbol]: e.target.value }))} /><span>%</span></div>
              </label>
            ))}
          </div>
        )}
        <div className="diag-row" style={{ marginTop: 12 }}><span>Total configured</span><b>{total.toFixed(2)}%</b></div>
        <div className="button-row">
          <button className="btn-export" type="submit" disabled={saving || positions.length === 0}>{saving ? 'Saving…' : 'Save references'}</button>
          <button className="btn-variant" type="button" onClick={clear} disabled={saving || positions.length === 0}>Clear fields</button>
        </div>
        {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
      </form>

      <div className="card">
        <h3>Market-data policy</h3>
        <div className="diag-row"><span>Configured provider boundary</span><b>AUTO</b></div>
        <div className="diag-row"><span>Optional primary</span><b>Vnstock</b></div>
        <div className="diag-row"><span>Fallback</span><b>VNDIRECT</b></div>
        <div className="diag-row"><span>EOD sync</span><b>15:30 Asia/Ho_Chi_Minh</b></div>
        <p className="muted">Provider failure is surfaced as stale/missing information and never changes portfolio holdings.</p>
      </div>
    </div>
  );
}
