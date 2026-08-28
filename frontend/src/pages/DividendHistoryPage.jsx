import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import DividendTree from '../components/DividendTree.jsx';
import { getDividendHistories } from '../lib/api.js';

export default function DividendHistoryPage({ symbols: initialSymbols = [], locale = 'vi' }) {
  const symbols = useMemo(
    () => [...new Set((initialSymbols || []).map(symbol => String(symbol || '').toUpperCase()).filter(Boolean))],
    [initialSymbols],
  );
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  async function load(refresh = false) {
    if (!symbols.length) return;
    refresh ? setRefreshing(true) : setLoading(true);
    setRows(symbols.map(symbol => ({ symbol, result: null, error: null, loading: true })));

    try {
      await getDividendHistories(symbols, {
        refresh,
        concurrency: 6,
        onResult: completed => {
          setRows(current => current.map(row => row.symbol === completed.symbol ? { ...completed, loading: false } : row));
        },
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbols.join('|')]);

  const totalEvents = rows.reduce((sum, row) => sum + Number(row.result?.events?.length || 0), 0);
  const failedSymbols = rows.filter(row => row.error).map(row => row.symbol);
  const treeRows = rows.map(row => ({
    symbol: row.symbol,
    events: row.result?.events || [],
    error: row.error,
    loading: row.loading,
  }));

  return <div className="page dividend-history-page">
    <AppNav active="dividends" locale={locale} />

    <header className="page-head">
      <div>
        <div className="eyebrow">Cổ tức & quyền</div>
        <h1>Lịch sử cổ tức</h1>
        <p className="muted">Chi tiết lịch sử chi trả cổ tức tiền mặt và cổ tức cổ phiếu theo từng mã trong danh mục.</p>
      </div>
      <button className="btn-secondary" type="button" onClick={() => load(true)} disabled={loading || refreshing || !symbols.length}>
        {refreshing ? 'Đang cập nhật…' : '↻ Cập nhật dữ liệu'}
      </button>
    </header>

    {failedSymbols.length > 0 && <div className="data-error-message" role="alert">
      Không thể tải lịch sử cổ tức cho <b>{failedSymbols.join(', ')}</b>. Các mã tải thành công vẫn được hiển thị bên dưới.
    </div>}

    {symbols.length === 0 ? <section className="card empty-state">
      <h2>Chưa có cổ phiếu trong danh mục</h2>
      <p>Hãy nhập danh mục trước khi xem lịch sử cổ tức.</p>
      <a className="btn-primary" href="/transactions">Nhập danh mục ban đầu</a>
    </section> : <>
      <div className="dividend-history-summary">
        <span><b>{symbols.length}</b> mã đang nắm giữ</span>
        <span><b>{loading && totalEvents === 0 ? '-' : totalEvents}</b> sự kiện đã tải</span>
      </div>

      <section className="card dividend-tree-card">
        <DividendTree rows={treeRows} locale={locale} root="symbol" openLatest />
      </section>
    </>}
  </div>;
}
