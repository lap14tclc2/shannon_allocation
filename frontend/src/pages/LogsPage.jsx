import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getActivityLog } from '../lib/api.js';

export default function LogsPage({ activity: initialActivity = {}, locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [activity, setActivity] = useState(initialActivity || {});
  const [category, setCategory] = useState('ALL');
  const [actor, setActor] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const logs = activity.logs || [];
  const integrity = activity.integrity || {};

  const categories = useMemo(() => ['ALL', ...Array.from(new Set(logs.map(x => x.category).filter(Boolean))).sort()], [logs]);
  const filtered = useMemo(() => logs.filter(row => {
    if (category !== 'ALL' && row.category !== category) return false;
    if (actor !== 'ALL' && row.actor_type !== actor) return false;
    if (status !== 'ALL' && row.status !== status) return false;
    if (query.trim()) {
      const haystack = `${row.action} ${row.summary} ${row.entity_type || ''} ${row.entity_id || ''} ${row.actor_id || ''}`.toLowerCase();
      if (!haystack.includes(query.trim().toLowerCase())) return false;
    }
    return true;
  }), [logs, category, actor, status, query]);

  async function refresh() {
    setLoading(true);
    try { setActivity(await getActivityLog()); }
    finally { setLoading(false); }
  }

  return <div className="page">
    <AppNav active="logs" locale={locale} />
    <header className="page-head"><div>
      <h1>{text('Activity Log', 'Nhật ký hoạt động')}</h1>
      <p className="muted">{text('Append-only audit trail for user actions, system jobs and ledger/control events.', 'Audit trail append-only cho thao tác người dùng, job hệ thống và các sự kiện ledger/kiểm soát.')}</p>
    </div><button className="btn-variant" onClick={refresh} disabled={loading}>{loading ? '…' : text('Refresh', 'Làm mới')}</button></header>

    <div className="metric-grid compact-metrics">
      <div className="metric-card"><span>{text('Integrity', 'Toàn vẹn')}</span><b className={integrity.status === 'VERIFIED' ? 'pos' : 'neg'}>{integrity.status || '-'}</b></div>
      <div className="metric-card"><span>{text('Records', 'Số bản ghi')}</span><b>{integrity.records ?? logs.length}</b></div>
      <div className="metric-card"><span>{text('Visible', 'Đang hiển thị')}</span><b>{filtered.length}</b></div>
      <div className="metric-card"><span>{text('Head hash', 'Hash cuối')}</span><b className="mono-small">{integrity.head_hash ? integrity.head_hash.slice(0, 14) + '…' : '-'}</b></div>
    </div>

    <section className="card">
      <div className="form-grid log-filters">
        <label>{text('Category', 'Nhóm')}<select value={category} onChange={e => setCategory(e.target.value)}>{categories.map(x => <option key={x}>{x}</option>)}</select></label>
        <label>{text('Actor', 'Tác nhân')}<select value={actor} onChange={e => setActor(e.target.value)}><option>ALL</option><option>USER</option><option>SYSTEM</option></select></label>
        <label>Status<select value={status} onChange={e => setStatus(e.target.value)}><option>ALL</option><option>SUCCESS</option><option>PARTIAL</option><option>FAILURE</option></select></label>
        <label>{text('Search', 'Tìm kiếm')}<input value={query} onChange={e => setQuery(e.target.value)} placeholder={text('action, entity, summary…', 'action, entity, nội dung…')} /></label>
      </div>
      <p className="muted">{text('The hash chain covers every stored record. QPort exposes no update/delete API for this log.', 'Hash chain bao phủ mọi bản ghi đã lưu. QPort không cung cấp API sửa/xóa nhật ký này.')}</p>
    </section>

    <section className="card">
      <div className="table-scroll"><table className="ranking activity-table"><thead><tr>
        <th>ID</th><th>{text('Time (UTC)', 'Thời gian (UTC)')}</th><th>{text('Actor', 'Tác nhân')}</th><th>{text('Category', 'Nhóm')}</th><th>Action</th><th>{text('Entity', 'Đối tượng')}</th><th>Status</th><th>{text('Summary / Details', 'Nội dung / Chi tiết')}</th>
      </tr></thead><tbody>{filtered.map(row => <tr key={row.id}>
        <td>{row.id}</td><td className="mono-small">{row.occurred_at}</td><td><b>{row.actor_type}</b><div className="muted">{row.actor_id}</div></td><td>{row.category}</td><td><code>{row.action}</code></td><td>{row.entity_type || '-'}{row.entity_id ? <div className="muted">#{row.entity_id}</div> : null}</td><td><span className={`status-pill ${row.status === 'FAILURE' ? 'status-missing' : row.status === 'PARTIAL' ? 'status-stale' : 'status-valid'}`}>{row.status}</span></td><td><div>{row.summary}</div>{row.details && Object.keys(row.details).length > 0 && <details className="log-details"><summary>{text('Details', 'Chi tiết')}</summary><pre>{JSON.stringify(row.details, null, 2)}</pre></details>}</td>
      </tr>)}</tbody></table></div>
      {filtered.length === 0 && <div className="empty-state">{text('No logs match the current filters.', 'Không có log phù hợp bộ lọc hiện tại.')}</div>}
    </section>
  </div>;
}
