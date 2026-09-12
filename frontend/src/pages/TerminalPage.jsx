import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getBuffettTerminalData } from '../lib/api.js';

export default function TerminalPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getBuffettTerminalData()
      .then((res) => {
        if (res.ok) setData(res);
        else setError(res.error || 'Failed to load terminal data');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);


  return (
    <div className="wealth-app-shell">
      <AppNav active="portfolio" />
      <main className="wealth-main-content" style={{ maxWidth: '1380px', margin: '0 auto', padding: '84px 24px 48px 24px', boxSizing: 'border-box' }}>
        <header className="page-header">
          <div>
            <span className="eyebrow">QPort Buffett Terminal</span>
            <h1>Trung Tâm Quyết Định Vốn Cá Nhân</h1>
          </div>
        </header>

        {loading && <div className="loading-state">Đang tải dữ liệu Pháo đài và Ma trận quyết định...</div>}
        {error && <div className="error-box">Lỗi: {error}</div>}

        {data && (
          <div className="terminal-grid">
            {/* Section D: Coach Summary */}
            <section className="card coach-summary-card">
              <div className="card-header">
                <h3>Huấn Luyện Viên Buffett & Munger</h3>
              </div>
              <div className="coach-narrative">
                <p><strong>{data.coach_summary}</strong></p>
              </div>
            </section>

            {/* Section A: Personal Fortress */}
            <section className="card fortress-card">
              <div className="card-header">
                <h3>Pháo Đài Tài Chính Cá Nhân</h3>
                <span className={`status-badge ${data.fortress.status}`}>
                  Dự phòng: {data.fortress.survival_reserve_status}
                </span>
              </div>
              <div className="metric-grid">
                <div className="metric-item">
                  <small>Tháng sinh tồn (Survival Months)</small>
                  <strong>{data.fortress.survival_months} tháng</strong>
                </div>
                <div className="metric-item">
                  <small>Vốn khả dụng dài hạn</small>
                  <strong>{Number(data.fortress.available_long_term_capital || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item">
                  <small>Tiền mặt cơ hội</small>
                  <strong>{Number(data.fortress.opportunity_cash || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item">
                  <small>Trạng thái nợ ngắn hạn</small>
                  <strong>{data.fortress.near_term_liability_status}</strong>
                </div>
              </div>
              {data.fortress.survival_reserve_status === 'UNKNOWN' && (
                <div style={{ marginTop: '16px' }}>
                  <a href="/capital" className="btn btn-primary" style={{ display: 'inline-block', padding: '8px 16px', background: '#0284c7', color: '#fff', borderRadius: '4px', textDecoration: 'none', fontWeight: 600 }}>
                    [Cấu hình tài chính cá nhân]
                  </a>
                </div>
              )}
            </section>

            {/* Section C: Attention Required Exceptions */}
            {data.exceptions && data.exceptions.length > 0 && (
              <section className="card attention-card">
                <div className="card-header">
                  <h3>Cần Chú Ý Đặc Biệt ({data.exceptions.length})</h3>
                </div>
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Mã</th>
                        <th>Chất lượng</th>
                        <th>Quyết định</th>
                        <th>Lý do chính</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.exceptions.map((exc) => (
                        <tr key={exc.symbol}>
                          <td><strong>{exc.symbol}</strong></td>
                          <td>{exc.quality_tier}</td>
                          <td><span className={`decision-tag ${exc.decision}`}>{exc.decision}</span></td>
                          <td>{exc.evidence.summary}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Section B: Holdings Decision Matrix */}
            <section className="card holdings-matrix-card">
              <div className="card-header">
                <h3>Ma Trận Quyết Định Danh Mục</h3>
              </div>
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Mã</th>
                      <th>Tỷ trọng</th>
                      <th>Chất lượng</th>
                      <th>Giá thị trường</th>
                      <th>Base IV</th>
                      <th>Biên an toàn</th>
                      <th>Bẫy giá trị</th>
                      <th>Quyết định</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.holdings_matrix.map((h) => (
                      <tr key={h.symbol}>
                        <td><a href={`/business/${h.symbol}`}><strong>{h.symbol}</strong></a></td>
                        <td>{(Number(h.weight || 0) * 100).toFixed(1)}%</td>
                        <td>{h.quality_tier}</td>
                        <td>{h.price ? `${Number(h.price).toLocaleString()} VND` : '—'}</td>
                        <td>{h.base_iv ? `${Number(h.base_iv).toLocaleString()} VND` : '—'}</td>
                        <td>{h.actual_mos_pct != null ? `${Number(h.actual_mos_pct).toFixed(1)}%` : '—'}</td>
                        <td><span className={`vt-badge ${h.value_trap_status}`}>{h.value_trap_status}</span></td>
                        <td><span className={`decision-tag ${h.decision}`}>{h.decision}</span></td>
                      </tr>
                    ))}
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
