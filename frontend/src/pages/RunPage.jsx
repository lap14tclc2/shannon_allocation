import React from 'react';
import RankingBoard from '../components/RankingBoard.jsx';
import RunHeader from '../components/RunHeader.jsx';

export default function RunPage({ meta, index }) {
  const rows = (index?.combinations || []).filter((c) => !c.error);
  const runId = meta?.run_id;
  return (
    <div className="page">
      <div className="page-topbar">
        <div className="breadcrumb">
          <a href="/">All runs</a> <span>/</span> {runId}
        </div>
        <div className="run-actions">
          <a className="btn-export" href={`/api/runs/${runId}/export`} download>
            ⬇ Export run (Markdown ZIP)
          </a>
          <button
            className="btn-remove"
            onClick={async (e) => {
              e.preventDefault();
              if (!window.confirm(`Delete run ${runId}?\nThis removes its data and exported reports.`)) return;
              try {
                const res = await fetch(`/api/runs/${runId}`, { method: 'DELETE' });
                if (res.ok) window.location.href = '/';
                else window.alert((await res.json().catch(() => ({}))).error || 'Delete failed.');
              } catch (err) {
                window.alert(err.message);
              }
            }}
          >
            ✕ Remove
          </button>
        </div>
      </div>
      <RunHeader meta={meta} />
      <h2>Ranking board ({rows.length} combinations)</h2>
      <RankingBoard rows={rows} hrefFor={(slug) => `/runs/${runId}/combinations/${slug}`} />
    </div>
  );
}