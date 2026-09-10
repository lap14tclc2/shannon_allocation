import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { navigate } from '../lib/navigation.js';

export default function BusinessPage() {
  const [symbol, setSymbol] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [portfolioSymbols, setPortfolioSymbols] = useState(['ACB', 'DGC', 'FPT']);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const pathParts = window.location.pathname.split('/');
    const targetSym = pathParts.length > 2 && pathParts[2] ? pathParts[2].trim().toUpperCase() : null;
    setSymbol(targetSym);

    if (targetSym) {
      fetchBusinessData(targetSym);
    } else {
      fetchPortfolioSymbols();
    }
  }, []);

  const fetchPortfolioSymbols = () => {
    fetch('/api/portfolio/terminal')
      .then((res) => res.json())
      .then((res) => {
        if (res.ok && res.holdings_matrix && res.holdings_matrix.length > 0) {
          const syms = res.holdings_matrix.map((h) => h.symbol).filter(Boolean);
          if (syms.length > 0) setPortfolioSymbols(syms);
        }
      })
      .catch(() => {});
  };

  const fetchBusinessData = (sym) => {
    setLoading(true);
    setError(null);
    fetch(`/api/portfolio/business/${sym}`)
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) {
          setData(res);
        } else {
          setError(res.error || `Không thể tải dữ liệu phân tích doanh nghiệp cho ${sym}`);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const cleanSym = searchInput.trim().toUpperCase();
    if (cleanSym) {
      navigate(`/business/${cleanSym}`);
    }
  };

  return (
    <div className="wealth-app-shell">
      <AppNav active="valuation" />
      <main className="wealth-main-content">
        {!symbol ? (
          /* Landing Workspace View */
          <div className="business-landing-container">
            <header className="page-header">
              <div>
                <span className="eyebrow">QPort Business Workspace</span>
                <h1>Phân Tích Doanh Nghiệp</h1>
              </div>
            </header>

            {/* Symbol Search / Lookup Section */}
            <section className="card search-card" style={{ marginBottom: '24px' }}>
              <div className="card-header">
                <h3>Tìm kiếm & Chọn mã phân tích</h3>
              </div>
              <form onSubmit={handleSearchSubmit} className="search-form" style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                <input
                  type="text"
                  placeholder="Nhập mã cổ phiếu (ví dụ: FPT, ACB, DGC)..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  style={{ flex: 1, padding: '10px 14px', borderRadius: '4px', border: '1px solid #ccc', fontSize: '1rem' }}
                />
                <button type="submit" className="btn btn-primary" style={{ padding: '10px 20px', background: '#0284c7', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 600, cursor: 'pointer' }}>
                  Xem phân tích
                </button>
              </form>
            </section>

            {/* Current Portfolio Section */}
            <section className="card portfolio-symbols-card">
              <div className="card-header">
                <h3>Danh mục hiện tại</h3>
              </div>
              <p className="muted" style={{ marginBottom: '16px' }}>
                Chọn một mã cổ phiếu trong danh mục để xem phân tích 7 chiều Buffett-Munger & Cổng Bẫy Giá Trị:
              </p>
              <div className="symbol-buttons-grid" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                {portfolioSymbols.map((sym) => (
                  <button
                    key={sym}
                    type="button"
                    onClick={() => navigate(`/business/${sym}`)}
                    className="btn btn-outline"
                    style={{ padding: '12px 24px', fontSize: '1.1rem', fontWeight: 700, borderRadius: '6px', cursor: 'pointer' }}
                  >
                    {sym} →
                  </button>
                ))}
              </div>
            </section>
          </div>
        ) : (
          /* Detail Workspace View */
          <div className="business-detail-container">
            <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <a href="/business" style={{ textDecoration: 'none', color: '#0284c7', fontSize: '0.9rem', fontWeight: 600, marginBottom: '4px', display: 'inline-block' }}>
                  ← Tất cả doanh nghiệp
                </a>
                <h1>Đánh Giá 7 Chiều & Bẫy Giá Trị ({symbol})</h1>
              </div>
              <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Mã khác..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  style={{ width: '120px', padding: '6px 10px', borderRadius: '4px', border: '1px solid #ccc' }}
                />
                <button type="submit" className="btn btn-primary" style={{ padding: '6px 12px', background: '#0284c7', color: '#fff', border: 'none', borderRadius: '4px' }}>
                  Xem
                </button>
              </form>
            </header>

            {loading && <div className="loading-state">Đang tải phân tích doanh nghiệp {symbol}...</div>}
            {error && <div className="error-box">Thông báo: {error}</div>}

            {data && (
              <div className="business-grid">
                {/* Decision & Evidence Header */}
                <section className="card decision-header-card">
                  <div className="card-header">
                    <h2>Quyết Định Hiện Tại: <span className={`decision-tag ${data.decision?.decision}`}>{data.decision?.decision}</span></h2>
                    <small>Độ tin cậy: {data.decision?.confidence}</small>
                  </div>
                  <p className="summary-text">{data.decision?.summary}</p>
                </section>

                {/* 7-Dimension Business Review */}
                <section className="card business-review-card">
                  <div className="card-header">
                    <h3>Đánh Giá 7 Chiều Buffett-Munger</h3>
                    <span className={`status-badge ${data.business_review?.overall_status}`}>{data.business_review?.overall_status}</span>
                  </div>
                  <div className="dimension-grid">
                    <div className="dim-item"><small>1. Vùng hiểu biết</small><strong>{data.business_review?.understandability}</strong></div>
                    <div className="dim-item"><small>2. Chất lượng doanh nghiệp</small><strong>{data.business_review?.business_quality}</strong></div>
                    <div className="dim-item"><small>3. Sức mạnh tài chính</small><strong>{data.business_review?.financial_strength}</strong></div>
                    <div className="dim-item"><small>4. Độ bền lợi nhuận</small><strong>{data.business_review?.earnings_durability}</strong></div>
                    <div className="dim-item"><small>5. Moat / Lợi thế cạnh tranh</small><strong>{data.business_review?.moat}</strong></div>
                    <div className="dim-item"><small>6. Phân bổ vốn quản trị</small><strong>{data.business_review?.management_capital_allocation}</strong></div>
                    <div className="dim-item"><small>7. Độ tin cậy BCTC</small><strong>{data.business_review?.accounting_reliability}</strong></div>
                  </div>
                </section>

                {/* Value Trap Gate */}
                <section className="card value-trap-card">
                  <div className="card-header">
                    <h3>Cổng Bẫy Giá Trị (Value Trap Gate)</h3>
                    <span className={`vt-badge ${data.value_trap?.status}`}>{data.value_trap?.status}</span>
                  </div>
                  <div className="vt-details">
                    <p>Phân loại suy giảm: <strong>{data.value_trap?.deterioration_classification}</strong></p>
                    <p>Chất lượng lợi nhuận: <strong>{data.value_trap?.earnings_quality}</strong></p>
                    <p>Bảo vệ kịch bản Thận trọng (Bear IV): <strong>{data.value_trap?.bear_case_protection}</strong></p>
                  </div>
                </section>

                {/* Munger Pre-Commitment Checklist */}
                {data.munger_checklist && (
                  <section className="card munger-checklist-card">
                    <div className="card-header">
                      <h3>Checklist Phản Phản Biện Munger (Pre-Commitment)</h3>
                    </div>
                    <ul className="checklist-list">
                      {data.munger_checklist.map((item, idx) => (
                        <li key={item.key}>
                          <strong>{idx + 1}. {item.question}</strong>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
