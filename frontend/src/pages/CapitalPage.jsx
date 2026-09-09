import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';

export default function CapitalPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/portfolio/capital')
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) setData(res);
        else setError(res.error || 'Failed to load capital data');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="wealth-app-shell">
      <AppNav active="allocation" />
      <main className="wealth-main-content">
        <header className="page-header">
          <div>
            <span className="eyebrow">Không Gian Quản Lý Vốn Cá Nhân</span>
            <h1>Phân Bổ Vốn & Độ Bền Pháo Đài</h1>
          </div>
        </header>

        {loading && <div className="loading-state">Đang tải cấu trúc nguồn vốn cá nhân...</div>}
        {error && <div className="error-box">Lỗi: {error}</div>}

        {data && (
          <div className="capital-grid">
            {/* Buckets Card */}
            <section className="card buckets-card">
              <div className="card-header">
                <h3>4 Ngăn Vốn Cá Nhân</h3>
              </div>
              <div className="metric-grid">
                <div className="metric-item">
                  <small>Dự phòng sinh tồn (Survival Reserve)</small>
                  <strong>{Number(data.buckets.survival_reserve || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item">
                  <small>Tài sản tích sản (Compounding Asset)</small>
                  <strong>{Number(data.buckets.compounding_asset || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item">
                  <small>Quỹ nghĩa vụ ngắn hạn</small>
                  <strong>{Number(data.buckets.near_term_liability_fund || 0).toLocaleString()} VND</strong>
                </div>
                <div className="metric-item highlight">
                  <small>Vốn khả dụng dài hạn (Buy Capital)</small>
                  <strong>{Number(data.buckets.available_long_term_capital || 0).toLocaleString()} VND</strong>
                </div>
              </div>
            </section>

            {/* Invariant Note */}
            <section className="card invariant-note-card">
              <div className="card-header">
                <h3>Quy Tắc Quản Lý Vốn Bất Biến</h3>
              </div>
              <p>
                <strong>Vốn khả dụng dài hạn</strong> = (Tiền mặt khả dụng + Thu nhập mới + Cổ tức) - (Mục tiêu Quỹ dự phòng sinh tồn + Nghĩa vụ ngắn hạn).
                QPort đảm bảo tiền mặt dự phòng không bao giờ bị sử dụng nhầm làm vốn mua cổ phiếu.
              </p>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
