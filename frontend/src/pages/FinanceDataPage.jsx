import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { crawlAdminFinanceData, crawlAdminFinanceUniverse, getAdminFinanceData, queueAdminFinanceCrawl, retryAdminFinanceData } from '../lib/api.js';

const PAGE_SIZE = 50;

const DOCUMENT_GROUPS = [
  { key: 'FINANCIAL_STATEMENTS', label: 'Báo cáo tài chính' },
  { key: 'INCOME_STATEMENT', label: 'Kết quả kinh doanh' },
  { key: 'CASH_FLOW', label: 'Lưu chuyển tiền tệ' },
  { key: 'DIVIDEND', label: 'Cổ tức' },
];

function documentLabel(type, periodType, year, quarter) {
  const label = {
    FINANCIAL_STATEMENTS: 'Báo cáo tài chính',
    CASH_FLOW: 'Lưu chuyển tiền tệ',
    INCOME_STATEMENT: 'Kết quả kinh doanh',
    DIVIDEND: 'Cổ tức',
  }[type] || type;
  const period = periodType === 'QUARTER' ? `Q${quarter} ${year}` : `Năm ${year}`;
  return `${label} · ${period}`;
}

export default function FinanceDataPage({ locale = 'vi' }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [exchange, setExchange] = useState('');
  const [expanded, setExpanded] = useState('');
  const [loading, setLoading] = useState(true);
  const [busySymbol, setBusySymbol] = useState('');
  const [message, setMessage] = useState('');
  const [runtime, setRuntime] = useState({ name: 'unknown', can_crawl: false, read_only: true, message: 'Đang kiểm tra capability…' });

  async function refresh() {
    setLoading(true);
    setMessage('');
    try {
      const result = await getAdminFinanceData({ offset: page * PAGE_SIZE, limit: PAGE_SIZE, exchange });
      setItems(result.items || []);
      setTotal(Number(result.total || 0));
      setRuntime(result.runtime || { name: 'unknown', can_crawl: false, read_only: true, message: 'Crawl chạy bằng Local/Worker; production chỉ đọc database.' });
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); }, [page, exchange]);

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const expandedItem = useMemo(() => items.find(item => item.symbol === expanded), [expanded, items]);

  async function syncUniverse() {
    if (!runtime.can_crawl) { setMessage(runtime.message); return; }
    setBusySymbol('*');
    setMessage('');
    try {
      const result = await crawlAdminFinanceUniverse();
      setMessage(result.message || 'Đã cập nhật danh sách mã.');
      setPage(0);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusySymbol('');
    }
  }

  async function queueCrawl() {
    if (!runtime.can_crawl) { setMessage(runtime.message); return; }
    setBusySymbol('*');
    setMessage('');
    try {
      const result = await queueAdminFinanceCrawl(exchange);
      setMessage(result.message || 'Đã xếp hàng crawl dữ liệu.');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusySymbol('');
    }
  }

  async function crawl(symbol, retry = false) {
    if (!runtime.can_crawl) { setMessage(runtime.message); return; }
    setBusySymbol(symbol);
    setMessage('');
    try {
      const result = retry ? await retryAdminFinanceData(symbol) : await crawlAdminFinanceData(symbol);
      setMessage(result.message || `Đã crawl ${symbol}: ${result.success_count || 0} file thành công, ${result.failure_count || 0} file thất bại.`);
      await refresh();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusySymbol('');
    }
  }

  return (
    <div className="page">
      <AppNav active="admin-finance-data" locale={locale} />
      <header className="page-header admin-header">
        <div>
          <div className="eyebrow">Quản trị dữ liệu</div>
          <h1>Finance Data</h1>
          <p className="muted">Catalog BCTC dùng chung. User chỉ đọc dữ liệu đã lưu trong database, không tự crawl provider.</p>
        </div>
        <div className="finance-data-actions">
          <button className="btn-secondary" type="button" disabled={Boolean(busySymbol) || !runtime.can_crawl} onClick={syncUniverse}>
            {busySymbol === '*' ? 'Đang cập nhật danh sách…' : 'Cập nhật danh sách mã'}
          </button>
          <button className="btn-primary" type="button" disabled={Boolean(busySymbol) || !total || !runtime.can_crawl} onClick={queueCrawl}>
            Xếp hàng crawl {exchange || 'tất cả'}
          </button>
        </div>
      </header>

      {message && <div className="run-message banner-message" role="status">{message}</div>}
      <div className={`runtime-banner ${runtime.can_crawl ? 'runtime-worker' : 'runtime-readonly'}`} role="note">
        <strong>{runtime.can_crawl ? 'Local/Worker runtime' : 'Production read-only'}</strong>
        <span>{runtime.message}</span>
      </div>

      <section className="card finance-data-toolbar">
        <label><span>Sàn</span><select value={exchange} onChange={event => { setPage(0); setExchange(event.target.value); }}><option value="">Tất cả sàn</option><option value="HOSE">HOSE</option><option value="HNX">HNX</option><option value="UPCOM">UPCOM</option></select></label>
        <span className="muted">{total.toLocaleString('vi-VN')} mã</span>
      </section>

      <section className="card finance-data-card">
        <div className="table-scroll">
          <table className="ranking finance-data-table">
            <thead><tr><th>Mã</th><th>Sàn</th><th>Tên công ty</th><th>Nhóm ngành</th><th>Trạng thái</th><th className="num">Chi tiết</th></tr></thead>
            <tbody>
              {loading ? <tr><td colSpan="6">Đang tải danh sách mã…</td></tr> : items.length === 0 ? <tr><td colSpan="6">Chưa có danh sách mã. Hãy chạy external finance worker để đồng bộ universe.</td></tr> : items.map(item => {
                const success = (item.documents || []).filter(doc => doc.status === 'SUCCESS').length;
                const failed = (item.documents || []).filter(doc => doc.status === 'FAILED').length;
                const isOpen = expanded === item.symbol;
                return <React.Fragment key={item.symbol}>
                  <tr className={isOpen ? 'is-expanded' : ''}>
                    <td><b>{item.symbol}</b></td><td>{item.exchange || 'UNKNOWN'}</td><td>{item.company_name || '-'}</td><td>{item.industry || '-'}</td>
                    <td><span className={`status-pill ${failed ? 'status-attention' : success ? 'status-valid' : ''}`}>{success ? `${success} thành công` : 'Chưa crawl'}{failed ? ` · ${failed} lỗi` : ''}</span></td>
                    <td className="num"><button className="btn-secondary btn-small" type="button" onClick={() => setExpanded(isOpen ? '' : item.symbol)}>{isOpen ? 'Thu gọn' : 'Mở rộng'}</button></td>
                  </tr>
                  {isOpen && <tr><td colSpan="6"><div className="finance-document-list">
                    <div className="section-head"><strong>File đã crawl: {item.symbol}</strong><button className="btn-primary btn-small" type="button" onClick={() => crawl(item.symbol)} disabled={Boolean(busySymbol) || !runtime.can_crawl}>Crawl lại</button></div>
                    {(item.documents || []).length === 0 ? <p className="muted">Chưa có file trong database.</p> : DOCUMENT_GROUPS.map(group => {
                      const docs = (item.documents || []).filter(doc => doc.document_type === group.key);
                      return <section className="finance-document-group" key={group.key}>
                        <h4>{group.label}</h4>
                        {docs.length === 0 ? <p className="muted">Chưa có tài liệu.</p> : <ul>{docs.map((doc, index) => <li key={doc.provider + '-' + doc.document_type + '-' + doc.period_type + '-' + doc.fiscal_year + '-' + (doc.fiscal_quarter || 'fy') + '-' + index}><span><b>{documentLabel(doc.document_type, doc.period_type, doc.fiscal_year, doc.fiscal_quarter)}</b><small>{doc.provider.toUpperCase()} · {doc.fetched_at || '-'}</small></span><span className={doc.status === 'SUCCESS' ? 'status-valid' : 'status-attention'}>{doc.status === 'SUCCESS' ? 'Thành công' : 'Thất bại'}{doc.status === 'FAILED' && <button className="btn-secondary btn-small" type="button" onClick={() => crawl(item.symbol, true)} disabled={Boolean(busySymbol) || !runtime.can_crawl}>Retry</button>}</span></li>)}</ul>}
                      </section>;
                    })}
                  </div></td></tr>}
                </React.Fragment>;
              })}
            </tbody>
          </table>
        </div>
        <footer className="pagination-controls"><button className="btn-secondary" type="button" disabled={page === 0 || loading} onClick={() => setPage(value => value - 1)}>Trước</button><span>Trang {page + 1} / {pageCount}</span><button className="btn-secondary" type="button" disabled={page + 1 >= pageCount || loading} onClick={() => setPage(value => value + 1)}>Sau</button></footer>
      </section>
    </div>
  );
}
