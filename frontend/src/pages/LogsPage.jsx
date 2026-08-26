import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getActivityLog } from '../lib/api.js';

const PAGE_SIZE = 50;

function statusClass(status) {
  if (status === 'FAILURE') return 'status-missing';
  if (status === 'PARTIAL') return 'status-stale';
  return 'status-valid';
}

export default function LogsPage({ activity: initialActivity = {}, locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const [activity, setActivity] = useState(initialActivity || {});
  const [category, setCategory] = useState('ALL');
  const [actor, setActor] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const logs = activity.logs || [];
  const pagination = activity.pagination || { page: 1, page_size: PAGE_SIZE, total: logs.length, pages: 1 };
  const integrity = activity.integrity || {};
  const categories = useMemo(() => ['ALL', ...Array.from(new Set(logs.map(x => x.category).filter(Boolean))).sort()], [logs]);

  async function refresh(nextPage = page) {
    setLoading(true);
    setError('');
    try {
      const result = await getActivityLog({
        page: nextPage,
        page_size: PAGE_SIZE,
        category,
        actor_type: actor,
        status,
        q: query,
      });
      setActivity(result);
    } catch (err) {
      setError(err.message || text('Unable to load logs.', 'Không thể tải logs.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(page); }, [page, category, actor, status, query]);

  function changeFilter(setter) {
    return event => { setPage(1); setter(event.target.value); };
  }

  return <div className="page">
    <AppNav active="logs" locale={locale} />
    <header className="page-head">
      <div>
        <div className="eyebrow">OBSERVABILITY / ADMIN</div>
        <h1>{text('Activity Log', 'Nhật ký hoạt động')}</h1>
        <p className="muted">{text('Searchable, append-only request and audit events.', 'Nhật ký request và audit append-only, có thể tìm kiếm.')}</p>
      </div>
      <button className="btn-variant" onClick={() => refresh(page)} disabled={loading}>{loading ? '…' : text('Refresh', 'Làm mới')}</button>
    </header>

    {error && <div className="banner-message status-missing" role="alert">{error}</div>}

    <div className="metric-grid compact-metrics">
      <div className="metric-card"><span>{text('Integrity', 'Toàn vẹn')}</span><b className={integrity.status === 'VERIFIED' ? 'pos' : 'neg'}>{integrity.status || '-'}</b></div>
      <div className="metric-card"><span>{text('Total records', 'Tổng bản ghi')}</span><b>{integrity.records ?? pagination.total}</b></div>
      <div className="metric-card"><span>{text('Matching', 'Phù hợp')}</span><b>{pagination.total}</b></div>
      <div className="metric-card"><span>{text('Page', 'Trang')}</span><b>{pagination.page} / {pagination.pages}</b></div>
    </div>

    <section className="card log-console">
      <div className="log-console-toolbar">
        <div className="form-grid log-filters">
          <label>{text('Category', 'Nhóm')}<select value={category} onChange={changeFilter(setCategory)}>{categories.map(item => <option key={item}>{item}</option>)}</select></label>
          <label>{text('Actor', 'Tác nhân')}<select value={actor} onChange={changeFilter(setActor)}><option>ALL</option><option>USER</option><option>SYSTEM</option></select></label>
          <label>{text('Level', 'Mức độ')}<select value={status} onChange={changeFilter(setStatus)}><option>ALL</option><option>SUCCESS</option><option>PARTIAL</option><option>FAILURE</option></select></label>
          <label>{text('Search', 'Tìm kiếm')}<input value={query} onChange={event => { setPage(1); setQuery(event.target.value); }} placeholder={text('action, route, request id, entity…', 'action, route, request id, đối tượng…')} /></label>
        </div>
        <div className="log-console-caption"><span className="log-live-dot" />{text('Live query · newest first', 'Truy vấn trực tiếp · mới nhất trước')}</div>
      </div>
      <div className="table-scroll">
        <table className="ranking activity-table azure-log-table">
          <thead><tr><th>Time (UTC)</th><th>Level</th><th>Event</th><th>Request / entity</th><th>Actor</th><th>Message</th></tr></thead>
          <tbody>
            {loading ? <tr><td colSpan="6" className="log-loading">{text('Loading latest logs…', 'Đang tải logs mới nhất…')}</td></tr> :
              logs.map(row => <tr key={row.id} className={row.status === 'FAILURE' ? 'log-row-failure' : ''}>
                <td className="log-time"><span>{row.occurred_at || '-'}</span><small>{row.source || 'QPORT'}</small></td>
                <td><span className={`status-pill ${statusClass(row.status)}`}>{row.status || 'INFO'}</span></td>
                <td><code>{row.action || '-'}</code><small>{row.category || '-'}</small></td>
                <td><span className="mono-small">{row.request_id || row.entity_id || '-'}</span><small>{row.entity_type || '—'}</small></td>
                <td><b>{row.actor_type || '-'}</b><small>{row.username || row.actor_id || '-'}</small></td>
                <td><div className="log-message">{row.summary || '-'}</div>{row.details && Object.keys(row.details).length > 0 && <details className="log-details"><summary>{text('View details', 'Xem chi tiết')}</summary><pre>{JSON.stringify(row.details, null, 2)}</pre></details>}</td>
              </tr>)
            }
          </tbody>
        </table>
      </div>
      {!loading && logs.length === 0 && <div className="empty-state">{text('No logs match the current filters.', 'Không có log phù hợp bộ lọc hiện tại.')}</div>}
      <footer className="pagination-controls log-pagination">
        <span>{text('Showing', 'Hiển thị')} {logs.length ? ((pagination.page - 1) * pagination.page_size + 1) : 0}–{Math.min(pagination.page * pagination.page_size, pagination.total)} / {pagination.total}</span>
        <div><button className="btn-secondary" type="button" disabled={loading || page <= 1} onClick={() => setPage(value => value - 1)}>‹ {text('Previous', 'Trước')}</button><button className="btn-secondary" type="button" disabled={loading || page >= pagination.pages} onClick={() => setPage(value => value + 1)}>{text('Next', 'Sau')} ›</button></div>
      </footer>
    </section>
  </div>;
}
