import React, { useState } from 'react';

export default function RunList({ runs }) {
  const [items, setItems] = useState(runs || []);
  const [removing, setRemoving] = useState('');

  async function removeRun(rid) {
    if (!window.confirm(`Delete run ${rid}?\nThis removes its data and exported reports.`)) return;
    setRemoving(rid);
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(rid)}`, { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        window.alert(data.error || 'Delete failed.');
        return;
      }
      setItems((xs) => xs.filter((x) => x.run_id !== rid));
    } catch (err) {
      window.alert(err.message);
    } finally {
      setRemoving('');
    }
  }

  if (items.length === 0) {
    return <div className="muted">No runs found. Run the backtest first (see python/README.md).</div>;
  }

  return (
    <ul className="run-list">
      {items.map((r) => (
        <li key={r.run_id} className={removing === r.run_id ? 'run-removing' : ''}>
          <div className="run-link">
            <a href={`/runs/${r.run_id}`}>{r.run_id}</a>
            <span className="muted">{r.generated_at}</span>
          </div>
          <button
            className="btn-remove"
            disabled={removing === r.run_id}
            onClick={() => removeRun(r.run_id)}
            title={`Delete run ${r.run_id}`}
          >
            {removing === r.run_id ? '…' : '✕ Remove'}
          </button>
        </li>
      ))}
    </ul>
  );
}