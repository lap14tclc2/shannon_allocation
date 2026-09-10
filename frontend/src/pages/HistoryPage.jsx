import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';

export default function HistoryPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/portfolio/history')
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) {
          setData(res);
        } else {
          setError(res.error || 'Không thể tải lịch sử tích sản.');
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="wealth-app-shell">
      <AppNav active="performance" />
      <main className="wealth-main-content">
        <header className="page-header">
          <div>
            <span className="eyebrow">Không Gian Lịch Sử Tích Sản</span>
            <h1>Nhật Ký Tăng Trưởng & Nhật Ký Giao Dịch</h1>
          </div>
        </header>

        {loading && <div className="loading-state">Đang tải lịch sử NAV và nhật ký giao dịch...</div>}
        {error && <div className="error-box">Lỗi: {error}</div>}

        {data && (
          <div className="history-grid">
            {/* Summary Metrics */}
            <section className="card history-summary-card">
              <div className="card-header">
                <h3>Tổng Quan Giá Trị Danh Mục</h3>
              </div>
              <div className="metric-grid">
                <div className="metric-item">
                  <small>Tổng giá trị NAV hiện tại</small>
                  <strong>{data.summary?.total_nav != null ? `${Number(data.summary.total_nav).toLocaleString()} VND` : '—'}</strong>
                </div>
                <div className="metric-item">
                  <small>Tổng giá vốn tích lũy</small>
                  <strong>{data.summary?.total_cost != null ? `${Number(data.summary.total_cost).toLocaleString()} VND` : '—'}</strong>
                </div>
                <div className="metric-item">
                  <small>Lợi nhuận chưa thực hiện</small>
                  <strong>{data.summary?.unrealized_pnl != null ? `${Number(data.summary.unrealized_pnl).toLocaleString()} VND` : '—'}</strong>
                </div>
                <div className="metric-item">
                  <small>Tỷ lệ sinh lời %</small>
                  <strong>{data.summary?.return_pct != null ? `${Number(data.summary.return_pct).toFixed(2)}%` : '—'}</strong>
                </div>
              </div>
            </section>

            {/* Transactions Log */}
            <section className="card transactions-card">
              <div className="card-header">
                <h3>Nhật Ký Hoạt Động Danh Mục</h3>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Thời gian</th>
                      <th>Loại giao dịch</th>
                      <th>Chi tiết</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.transactions && data.transactions.length > 0 ? (
                      data.transactions.map((tx) => (
                        <tr key={tx.id || Math.random()}>
                          <td>{tx.occurred_at || tx.created_at || '—'}</td>
                          <td><strong>{tx.action || tx.category || 'GIAO DỊCH'}</strong></td>
                          <td>{typeof tx.details === 'object' ? JSON.stringify(tx.details) : String(tx.details || '—')}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="3" style={{ textAlign: 'center', padding: '16px' }} className="muted">
                          Chưa có nhật ký giao dịch nào được ghi nhận.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
