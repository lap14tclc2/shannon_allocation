import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';

export default function BusinessPage() {
  const [symbol, setSymbol] = useState('FPT');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchBusinessData = (sym) => {
    setLoading(true);
    setError(null);
    fetch(`/api/portfolio/business/${sym}`)
      .then((res) => res.json())
      .then((res) => {
        if (res.ok) setData(res);
        else setError(res.error || 'Failed to load business data');
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const pathParts = window.location.pathname.split('/');
    const targetSym = pathParts.length > 2 && pathParts[2] ? pathParts[2].toUpperCase() : 'FPT';
    setSymbol(targetSym);
    fetchBusinessData(targetSym);
  }, []);

  return (
    <div className="wealth-app-shell">
      <AppNav active="valuation" />
      <main className="wealth-main-content">
        <header className="page-header">
          <div>
            <span className="eyebrow">Không Gian Phân Tích Doanh Nghiệp</span>
            <h1>Đánh Giá 7 Chiều & Bẫy Giá Trị ({symbol})</h1>
          </div>
        </header>

        {loading && <div className="loading-state">Đang tải phân tích doanh nghiệp {symbol}...</div>}
        {error && <div className="error-box">Lỗi: {error}</div>}

        {data && (
          <div className="business-grid">
            {/* Decision & Evidence Header */}
            <section className="card decision-header-card">
              <div className="card-header">
                <h2>Quyết Định Hiện Tại: <span className={`decision-tag ${data.decision.decision}`}>{data.decision.decision}</span></h2>
                <small>Độ tin cậy: {data.decision.confidence}</small>
              </div>
              <p className="summary-text">{data.decision.summary}</p>
            </section>

            {/* 7-Dimension Business Review */}
            <section className="card business-review-card">
              <div className="card-header">
                <h3>Đánh Giá 7 Chiều Buffett-Munger</h3>
                <span className={`status-badge ${data.business_review.overall_status}`}>{data.business_review.overall_status}</span>
              </div>
              <div className="dimension-grid">
                <div className="dim-item"><small>1. Vùng hiểu biết</small><strong>{data.business_review.understandability}</strong></div>
                <div className="dim-item"><small>2. Chất lượng doanh nghiệp</small><strong>{data.business_review.business_quality}</strong></div>
                <div className="dim-item"><small>3. Sức mạnh tài chính</small><strong>{data.business_review.financial_strength}</strong></div>
                <div className="dim-item"><small>4. Độ bền lợi nhuận</small><strong>{data.business_review.earnings_durability}</strong></div>
                <div className="dim-item"><small>5. Moat / Lợi thế cạnh tranh</small><strong>{data.business_review.moat}</strong></div>
                <div className="dim-item"><small>6. Phân bổ vốn quản trị</small><strong>{data.business_review.management_capital_allocation}</strong></div>
                <div className="dim-item"><small>7. Độ tin cậy BCTC</small><strong>{data.business_review.accounting_reliability}</strong></div>
              </div>
            </section>

            {/* Value Trap Gate */}
            <section className="card value-trap-card">
              <div className="card-header">
                <h3>Cổng Bẫy Giá Trị (Value Trap Gate)</h3>
                <span className={`vt-badge ${data.value_trap.status}`}>{data.value_trap.status}</span>
              </div>
              <div className="vt-details">
                <p>Phân loại suy giảm: <strong>{data.value_trap.deterioration_classification}</strong></p>
                <p>Chất lượng lợi nhuận: <strong>{data.value_trap.earnings_quality}</strong></p>
                <p>Bảo vệ kịch bản Thận trọng (Bear IV): <strong>{data.value_trap.bear_case_protection}</strong></p>
              </div>
            </section>

            {/* Munger Pre-Commitment Checklist */}
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
          </div>
        )}
      </main>
    </div>
  );
}
