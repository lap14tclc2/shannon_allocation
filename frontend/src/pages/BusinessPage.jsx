import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import SymbolSuggestInput from '../components/SymbolSuggestInput.jsx';
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
  }, [window.location.pathname]);

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

  const handleSelectSymbol = (item) => {
    const cleanSym = String(item?.symbol || '').trim().toUpperCase();
    if (cleanSym) {
      navigate(`/business/${cleanSym}`);
    }
  };

  const handleSearchSubmit = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const cleanSym = searchInput.trim().toUpperCase();
    if (cleanSym) {
      navigate(`/business/${cleanSym}`);
    }
  };

  const GOLDEN_CANDIDATES = ['ACB', 'FPT', 'DGC', 'VIX'];

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
                <h1>Phân Tích Doanh Nghiệp & Ứng Viên Đầu Tư</h1>
                <p className="muted" style={{ marginTop: '4px' }}>
                  Điểm tra cứu và nghiên cứu mô hình 7 chiều, Moat, Bẫy giá trị cho mọi cổ phiếu trong thị trường (Finance DB catalog).
                </p>
              </div>
            </header>

            {/* Symbol Search / Lookup Section */}
            <section className="card search-card" style={{ marginBottom: '24px', padding: '24px' }}>
              <div className="card-header" style={{ marginBottom: '12px' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Tra cứu mã chứng khoán hoặc tên công ty</h3>
              </div>
              <p className="muted" style={{ marginBottom: '16px', fontSize: '0.92rem' }}>
                Nghiên cứu bất kỳ cổ phiếu nào trong vũ trụ Finance DB (cả mã đang giữ lẫn mã ứng viên chưa có trong danh mục):
              </p>
              
              <form onSubmit={handleSearchSubmit} className="search-form" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <SymbolSuggestInput
                    value={searchInput}
                    onChange={setSearchInput}
                    onSelectSecurity={handleSelectSymbol}
                    placeholder="Search company or ticker... (ví dụ: FPT, ACB, DGC, VIX)"
                    holdingSymbols={portfolioSymbols}
                    autoFocus
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{
                    padding: '10px 22px',
                    background: '#0284c7',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    height: '42px',
                  }}
                >
                  Nghiên cứu →
                </button>
              </form>

              {/* Sample Candidate Shortcuts */}
              <div className="candidate-shortcuts" style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border, #e5e7eb)' }}>
                <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-muted, #6b7280)', marginRight: '12px' }}>
                  Mã mẫu nghiên cứu nhanh:
                </span>
                <div style={{ display: 'inline-flex', gap: '8px', flexWrap: 'wrap' }}>
                  {GOLDEN_CANDIDATES.map((cand) => (
                    <button
                      key={cand}
                      type="button"
                      onClick={() => navigate(`/business/${cand}`)}
                      className="btn btn-sm"
                      style={{
                        padding: '4px 12px',
                        fontSize: '0.85rem',
                        fontWeight: 700,
                        borderRadius: '4px',
                        border: '1px solid var(--border, #d1d5db)',
                        background: 'var(--surface-soft, #f9fafb)',
                        cursor: 'pointer',
                      }}
                    >
                      {cand}
                    </button>
                  ))}
                </div>
              </div>
            </section>

            {/* Current Portfolio Section */}
            <section className="card portfolio-symbols-card" style={{ padding: '24px' }}>
              <div className="card-header" style={{ marginBottom: '12px' }}>
                <h3>Danh mục hiện tại ({portfolioSymbols.length} vị thế)</h3>
              </div>
              <p className="muted" style={{ marginBottom: '16px', fontSize: '0.9rem' }}>
                Chọn một mã cổ phiếu trong danh mục để xem phân tích 7 chiều Buffett-Munger & Cổng Bẫy Giá Trị:
              </p>
              <div className="symbol-buttons-grid" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {portfolioSymbols.map((sym) => (
                  <button
                    key={sym}
                    type="button"
                    onClick={() => navigate(`/business/${sym}`)}
                    className="btn btn-outline"
                    style={{
                      padding: '10px 20px',
                      fontSize: '1rem',
                      fontWeight: 700,
                      borderRadius: '6px',
                      cursor: 'pointer',
                      border: '1px solid #0284c7',
                      color: '#0284c7',
                      background: 'transparent',
                    }}
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
            <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
              <div>
                <a
                  href="/business"
                  onClick={(e) => {
                    e.preventDefault();
                    navigate('/business');
                  }}
                  style={{ textDecoration: 'none', color: '#0284c7', fontSize: '0.9rem', fontWeight: 600, marginBottom: '4px', display: 'inline-block' }}
                >
                  ← Tra cứu mã khác
                </a>
                <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                  Đánh Giá 7 Chiều & Bẫy Giá Trị ({symbol})
                </h1>
              </div>

              {/* Quick switch search bar */}
              <div style={{ minWidth: '260px', maxWidth: '320px' }}>
                <SymbolSuggestInput
                  value=""
                  onSelectSecurity={handleSelectSymbol}
                  placeholder="Tra cứu doanh nghiệp khác..."
                  holdingSymbols={portfolioSymbols}
                />
              </div>
            </header>

            {loading && <div className="loading-state" style={{ padding: '30px', textAlign: 'center' }}>Đang tải dữ liệu phân tích doanh nghiệp {symbol}...</div>}
            {error && <div className="error-box" style={{ padding: '16px', background: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', borderRadius: '6px' }}>Thông báo: {error}</div>}

            {data && (
              <div className="business-grid" style={{ display: 'grid', gap: '20px' }}>
                {/* Decision & Evidence Header */}
                <section className="card decision-header-card" style={{ padding: '20px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h2 style={{ fontSize: '1.35rem', margin: 0 }}>
                      Quyết Định Hiện Tại:{' '}
                      <span className={`decision-tag ${data.decision?.decision}`} style={{ padding: '4px 12px', borderRadius: '4px', background: '#0284c7', color: '#fff', fontSize: '1.1rem' }}>
                        {data.decision?.decision}
                      </span>
                    </h2>
                    <small style={{ color: '#6b7280' }}>Độ tin cậy: {data.decision?.confidence}</small>
                  </div>
                  <p className="summary-text" style={{ fontSize: '1rem', lineHeight: 1.5, margin: 0 }}>
                    {data.decision?.summary}
                  </p>
                </section>

                {/* 7-Dimension Business Review */}
                <section className="card business-review-card" style={{ padding: '20px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '1.15rem', margin: 0 }}>Đánh Giá 7 Chiều Buffett-Munger</h3>
                    <span className={`status-badge ${data.business_review?.overall_status}`} style={{ fontWeight: 700 }}>
                      {data.business_review?.overall_status}
                    </span>
                  </div>
                  <div className="dimension-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>1. Vùng hiểu biết</small><strong>{data.business_review?.understandability}</strong></div>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>2. Chất lượng doanh nghiệp</small><strong>{data.business_review?.business_quality}</strong></div>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>3. Sức mạnh tài chính</small><strong>{data.business_review?.financial_strength}</strong></div>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>4. Độ bền lợi nhuận</small><strong>{data.business_review?.earnings_durability}</strong></div>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>5. Moat / Lợi thế cạnh tranh</small><strong>{data.business_review?.moat}</strong></div>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>6. Phân bổ vốn quản trị</small><strong>{data.business_review?.management_capital_allocation}</strong></div>
                    <div className="dim-item"><small style={{ display: 'block', color: '#6b7280' }}>7. Độ tin cậy BCTC</small><strong>{data.business_review?.accounting_reliability}</strong></div>
                  </div>
                </section>

                {/* Value Trap Gate */}
                <section className="card value-trap-card" style={{ padding: '20px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h3 style={{ fontSize: '1.15rem', margin: 0 }}>Cổng Bẫy Giá Trị (Value Trap Gate)</h3>
                    <span className={`vt-badge ${data.value_trap?.status}`} style={{ fontWeight: 700 }}>
                      {data.value_trap?.status}
                    </span>
                  </div>
                  <div className="vt-details" style={{ lineHeight: 1.6 }}>
                    <p>Phân loại suy giảm: <strong>{data.value_trap?.deterioration_classification}</strong></p>
                    <p>Chất lượng lợi nhuận: <strong>{data.value_trap?.earnings_quality}</strong></p>
                    <p>Bảo vệ kịch bản Thận trọng (Bear IV): <strong>{data.value_trap?.bear_case_protection}</strong></p>
                  </div>
                </section>

                {/* Munger Pre-Commitment Checklist */}
                {data.munger_checklist && (
                  <section className="card munger-checklist-card" style={{ padding: '20px' }}>
                    <div className="card-header" style={{ marginBottom: '12px' }}>
                      <h3 style={{ fontSize: '1.15rem', margin: 0 }}>Checklist Phản Phản Biện Munger (Pre-Commitment)</h3>
                    </div>
                    <ul className="checklist-list" style={{ paddingLeft: '20px', margin: 0, lineHeight: 1.8 }}>
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
