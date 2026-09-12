import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import SymbolSuggestInput from '../components/SymbolSuggestInput.jsx';
import ThesisChallengeSection from '../components/ThesisChallengeSection.jsx';
import { navigate } from '../lib/navigation.js';
import { downloadBusinessMungerAIExport } from '../lib/aiExport.js';
import { formatStatus, formatDecision, formatClassification, formatValueTrap, formatDeterioration, formatArchetype, formatMetricName, formatFindingNarrative, formatMarginTrend, formatFindingTitle, formatPct, formatVND, formatRatioX, formatDebtEquity, formatCfoPat } from '../utils/vietnameseSemantics.js';

export default function BusinessPage() {
  const [symbol, setSymbol] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [portfolioSymbols, setPortfolioSymbols] = useState(['ACB', 'DGC', 'FPT', 'VIX']);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exportingAI, setExportingAI] = useState(false);
  const [exportMsg, setExportMsg] = useState('');

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
          setError(res.error || `Không thể tải dữ liệu phân tích BCTC Munger cho ${sym}`);
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

  const handleExportAI = async () => {
    if (!data || exportingAI) return;
    setExportingAI(true);
    setExportMsg('');
    try {
      const filename = await downloadBusinessMungerAIExport(data);
      setExportMsg(`Đã xuất file báo cáo ${filename} thành công. Báo cáo chứa đầy đủ BCTC 12 chiều Munger, Bẫy giá trị, Định giá & JSON payload cho AI.`);
      setTimeout(() => setExportMsg(''), 6000);
    } catch (err) {
      setExportMsg(`Không thể xuất báo cáo cho AI: ${err.message}`);
    } finally {
      setExportingAI(false);
    }
  };

  const GOLDEN_CANDIDATES = ['ACB', 'FPT', 'DGC', 'VIX', 'AAA', 'AAH'];

  // Data helpers
  const munger = data?.munger_analysis || {};
  const archetype = munger.archetype || 'NORMAL_ENTERPRISE';
  const decision = munger.long_term_decision || {};
  const valuation = munger.valuation || data?.canonical_valuation || {};
  const quality = munger.overall_financial_quality || {};
  const valueTrap = munger.value_trap_assessment || {};
  const normPower = munger.normalized_earning_power || {};

  const renderBadge = (status) => {
    const s = String(status || '').toUpperCase();
    let bg = '#6b7280';
    let text = formatDecision(s) !== s ? formatDecision(s) : formatStatus(s);

    if (s === 'PASS' || s === 'CLEAR' || s === 'READY' || s === 'COMPOUNDER' || s === 'POTENTIAL_COMPOUNDER') {
      bg = '#16a34a';
    } else if (s === 'WATCH' || s === 'PARTIAL' || s === 'AVERAGE_BUSINESS') {
      bg = '#d97706';
    } else if (s === 'FAIL' || s === 'HIGH_RISK' || s === 'DETERIORATING_BUSINESS' || s === 'WEAK_BUSINESS' || s === 'AVOID') {
      bg = '#dc2626';
    } else if (s === 'WAIT_FOR_MOS') {
      bg = '#0284c7';
    } else if (s === 'BUY') {
      bg = '#15803d';
    } else if (s === 'REVIEW_BUSINESS') {
      bg = '#ea580c';
    }

    return (
      <span style={{
        padding: '3px 10px',
        borderRadius: '4px',
        background: bg,
        color: '#ffffff',
        fontSize: '0.82rem',
        fontWeight: 700,
        display: 'inline-block',
      }}>
        {text}
      </span>
    );
  };

  return (
    <div className="wealth-app-shell">
      <AppNav active="valuation" />
      <main className="wealth-main-content" style={{ maxWidth: '1380px', margin: '0 auto', padding: '84px 24px 48px 24px', boxSizing: 'border-box' }}>
        {!symbol ? (
          /* Landing Workspace View */
          <div className="business-landing-container">
            <header className="page-header">
              <div>
                <span className="eyebrow">QPort Munger Business Workspace</span>
                <h1>Phân Tích Báo Cáo Tài Chính Dài Hạn Munger</h1>
                <p className="muted" style={{ marginTop: '4px' }}>
                  Hệ thống phân tích 12 chiều BCTC, Bẫy giá trị và Định giá chuẩn mực cho 390+ mã cổ phiếu toàn thị trường (Finance DB).
                </p>
              </div>
            </header>

            {/* Symbol Search / Lookup Section */}
            <section className="card search-card" style={{ marginBottom: '24px', padding: '24px' }}>
              <div className="card-header" style={{ marginBottom: '12px' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Tra cứu mã chứng khoán hoặc tên công ty</h3>
              </div>
              <p className="muted" style={{ marginBottom: '16px', fontSize: '0.92rem' }}>
                Nhập bất kỳ mã chứng khoán nào trong vũ trụ Finance DB để thực thi phân tích BCTC Munger:
              </p>
              
              <form onSubmit={handleSearchSubmit} className="search-form" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: '240px' }}>
                  <SymbolSuggestInput
                    value={searchInput}
                    onChange={setSearchInput}
                    onSelectSecurity={handleSelectSymbol}
                    placeholder="Search company or ticker... (ví dụ: FPT, ACB, DGC, VIX, AAA, AAH)"
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
                  Phân Tích BCTC →
                </button>
              </form>

              {/* Sample Candidate Shortcuts */}
              <div className="candidate-shortcuts" style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border, #e5e7eb)' }}>
                <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-muted, #6b7280)', marginRight: '12px' }}>
                  Mã mẫu thử nghiệm:
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
                Chọn một vị thế trong danh mục để xem phân tích tài chính Munger & Biên an toàn:
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
                <h1 style={{ fontSize: '1.75rem', fontWeight: 800, margin: 0 }}>
                  Phân Tích BCTC Munger & Định Giá ({symbol})
                </h1>
                {munger.history_years > 0 && (
                  <p className="muted" style={{ margin: '4px 0 0 0', fontSize: '0.9rem' }}>
                    Loại hình kinh tế: <strong>{munger.archetype}</strong> | Lịch sử FY{munger.history_start}–FY{munger.history_end} ({munger.history_years} năm) | Nguồn: {munger.provider?.toUpperCase()}
                  </p>
                )}
              </div>

              {/* Action Buttons & Search */}
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary export-ai-btn"
                  onClick={handleExportAI}
                  disabled={exportingAI || loading || !data}
                  style={{
                    padding: '8px 16px',
                    background: '#0284c7',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.9rem',
                    whiteSpace: 'nowrap',
                    height: '42px',
                  }}
                >
                  <span aria-hidden="true">🤖</span> {exportingAI ? 'Đang xuất…' : 'Xuất dữ liệu cho AI'}
                </button>
                <div style={{ minWidth: '220px', maxWidth: '300px' }}>
                  <SymbolSuggestInput
                    value=""
                    onSelectSecurity={handleSelectSymbol}
                    placeholder="Tra cứu doanh nghiệp khác..."
                    holdingSymbols={portfolioSymbols}
                  />
                </div>
              </div>
            </header>

            {exportMsg && (
              <div
                className="export-status-banner"
                style={{
                  padding: '12px 16px',
                  marginBottom: '20px',
                  background: '#ecfdf5',
                  border: '1px solid #6ee7b7',
                  color: '#065f46',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.92rem',
                }}
              >
                {exportMsg}
              </div>
            )}

            {loading && <div className="loading-state" style={{ padding: '40px', textAlign: 'center', fontSize: '1.1rem' }}>Đang thực thi phân tích BCTC Munger cho {symbol}...</div>}
            {error && <div className="error-box" style={{ padding: '16px', background: '#fef2f2', border: '1px solid #fca5a5', color: '#991b1b', borderRadius: '6px' }}>Thông báo: {error}</div>}

            {data && munger && (
              <div className="business-grid" style={{ display: 'grid', gap: '24px' }}>
                
                {/* 2. KẾT LUẬN ĐẦU TƯ CÓ CẤU TRÚC 9 PHẦN */}
                <section className="card decision-header-card" style={{ padding: '24px', borderLeft: `6px solid ${decision.state === 'BUY' ? '#16a34a' : (decision.state === 'WAIT_FOR_MOS' ? '#0284c7' : '#dc2626')}` }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h2 style={{ fontSize: '1.4rem', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
                      Quyết Định BCTC Dài Hạn: {renderBadge(decision.state)}
                    </h2>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.85rem', color: '#6b7280', display: 'block' }}>Phân loại Doanh nghiệp</span>
                      <strong>{formatClassification(munger.compounder_classification)}</strong>
                    </div>
                  </div>

                  <p className="summary-text" style={{ fontSize: '1.05rem', lineHeight: 1.6, margin: '8px 0 16px 0', color: 'var(--text-main, #1f2937)' }}>
                    {decision.primary_reason}
                  </p>

                  {/* Structured 9-Part Conclusion Breakdown */}
                  {munger.evidence_based_conclusion && (
                    <div className="evidence-conclusion-box" style={{ background: 'var(--surface-soft, #f9fafb)', padding: '18px', borderRadius: '8px', marginBottom: '16px', border: '1px solid var(--border, #e5e7eb)', fontSize: '0.93rem', lineHeight: 1.6 }}>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '1.02rem', color: '#1f2937', fontWeight: 700 }}>Báo Cáo Đánh Giá Tổng Hợp BCTC (9 Yếu Tố Cốt Lõi):</h4>
                      <div style={{ display: 'grid', gap: '8px' }}>
                        <div><strong>1. Điểm mạnh tài chính:</strong> {munger.evidence_based_conclusion.diem_manh_tai_chinh?.join('; ')}</div>
                        <div><strong>2. Điểm yếu:</strong> {munger.evidence_based_conclusion.diem_yeu?.join('; ')}</div>
                        <div><strong>3. Warning quan trọng nhất:</strong> <span style={{ color: '#dc2626', fontWeight: 600 }}>{munger.evidence_based_conclusion.warning_quan_trong_nhat}</span></div>
                        <div><strong>4. Xu hướng dài hạn:</strong> {munger.evidence_based_conclusion.xu_huong_dai_han}</div>
                        <div><strong>5. Value-trap risk:</strong> {munger.evidence_based_conclusion.value_trap_risk}</div>
                        <div><strong>6. Điều có thể phá vỡ thesis:</strong> {munger.evidence_based_conclusion.dieu_co_the_pha_vo_thesis}</div>
                        <div><strong>7. Điều kiện củng cố thesis:</strong> {munger.evidence_based_conclusion.dieu_kien_cung_co_thesis}</div>
                        <div><strong>8. Valuation / MOS:</strong> {munger.evidence_based_conclusion.valuation_mos}</div>
                        <div><strong>9. Quyết định cuối cùng:</strong> <strong>{munger.evidence_based_conclusion.final_decision}</strong></div>
                      </div>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', paddingTop: '12px', borderTop: '1px solid var(--border, #e5e7eb)', fontSize: '0.92rem' }}>
                    <div>Biên An Toàn Thực Tế (Actual MOS): <strong style={{ color: (decision.actual_mos_pct ?? 0) >= (decision.required_mos_pct ?? 25) ? '#16a34a' : '#dc2626' }}>{formatPct(decision.actual_mos_pct)}</strong></div>
                    <div>Biên An Toàn Yêu Cầu (Required MOS): <strong>{decision.required_mos_pct !== undefined ? `${decision.required_mos_pct}%` : 'N/A'}</strong></div>
                    <div>Cổng MOS: {renderBadge(decision.mos_gate)}</div>
                  </div>
                </section>

                {/* 3. MA TRẬN CHẤT LƯỢNG TÀI CHÍNH 12 CHIỀU */}
                <section className="card quality-matrix-card" style={{ padding: '20px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '1.15rem', margin: 0 }}>Ma Trận Chất Lượng Tài Chính 12 Chiều Munger</h3>
                    <small style={{ color: '#6b7280' }}>Độ sẵn sàng dữ liệu: {renderBadge(munger.data_readiness)}</small>
                  </div>

                  <div className="dimension-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '14px' }}>
                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>1. Tăng Trưởng (Growth)</small>
                        {renderBadge(quality.growth)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Tăng trưởng Doanh thu: {formatPct(munger.growth_analysis?.metrics?.revenue_cagr !== null && munger.growth_analysis?.metrics?.revenue_cagr !== undefined ? munger.growth_analysis.metrics.revenue_cagr * 100 : null)}<br/>
                        Tăng trưởng LNST: {formatPct(munger.growth_analysis?.metrics?.net_profit_cagr !== null && munger.growth_analysis?.metrics?.net_profit_cagr !== undefined ? munger.growth_analysis.metrics.net_profit_cagr * 100 : null)}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>2. Sinh Lời (Profitability)</small>
                        {renderBadge(quality.profitability)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        ROE Trung Vị: {formatPct(munger.profitability_analysis?.metrics?.median_roe !== null && munger.profitability_analysis?.metrics?.median_roe !== undefined ? munger.profitability_analysis.metrics.median_roe * 100 : null)}<br/>
                        Xu hướng Biên LN: {formatMarginTrend(munger.profitability_analysis?.metrics?.margin_trend)}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>3. Độ Bền Lợi Nhuận</small>
                        {renderBadge(quality.durability)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Biến động LN: {formatPct(munger.earnings_durability?.metrics?.pat_volatility !== null && munger.earnings_durability?.metrics?.pat_volatility !== undefined ? munger.earnings_durability.metrics.pat_volatility * 100 : null, 'Chưa đủ chuỗi 3 năm')}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>4. Chất Lượng Lợi Nhuận</small>
                        {renderBadge(quality.earnings_quality)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Tỷ lệ CFO/PAT: {formatCfoPat(munger.earnings_quality?.metrics?.avg_cfo_pat)}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>5. Bảng Cân Đối Kế Toán</small>
                        {renderBadge(quality.balance_sheet)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Đánh giá TS & Nguồn vốn
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>6. Nợ & Thanh Khoản</small>
                        {renderBadge(quality.debt_liquidity)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Debt/Equity: {formatDebtEquity(munger.debt_liquidity?.metrics?.latest_debt_equity, archetype)}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>7. Hiệu Quả Sử Dụng Vốn</small>
                        {renderBadge(quality.capital_efficiency)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Tạo giá trị LN giữ lại
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>8. Phân Bổ Vốn Quản Trị</small>
                        {renderBadge(quality.capital_allocation)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        ROE & Tích lũy tài sản
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>9. Pha Loãng Cổ Phiếu</small>
                        {renderBadge(quality.dilution)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Tăng trưởng cổ phiếu/năm
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>10. Nhất Quán Kế Toán</small>
                        {renderBadge(quality.accounting_consistency)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Hằng đẳng thức BCTC
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>11. Điều Tra BCTC (Forensics)</small>
                        {renderBadge(quality.forensics)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Phát hiện bất thường
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>12. Dòng Tiền Thuần</small>
                        {renderBadge(quality.cash_flow_quality)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Chất lượng chuyển hóa tiền
                      </div>
                    </div>
                  </div>
                </section>

                {/* 4. CẢNH BÁO BẤT THƯỜNG TÀI CHÍNH (FORENSICS FINDINGS) */}
                <section className="card forensics-card" style={{ padding: '20px' }}>
                  <h3 style={{ fontSize: '1.15rem', marginTop: 0, marginBottom: '16px' }}>Cảnh Báo Bất Thường Tài Chính (Financial Forensics)</h3>
                  {munger.all_findings && munger.all_findings.length > 0 ? (
                    <div style={{ display: 'grid', gap: '12px' }}>
                      {munger.all_findings.map((f, idx) => {
                        const narrative = formatFindingNarrative(f) || {};
                        return (
                          <div key={idx} style={{ padding: '14px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px', background: f.severity === 'CRITICAL' || f.severity === 'HIGH' ? '#fef2f2' : 'var(--surface-soft, #f9fafb)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                              <strong style={{ color: f.severity === 'CRITICAL' || f.severity === 'HIGH' ? '#dc2626' : '#d97706', fontSize: '0.98rem' }}>
                                {narrative.tieu_de || formatFindingTitle(f.code)}
                              </strong>
                              {renderBadge(f.status || 'WATCH')}
                            </div>
                            <p style={{ margin: '4px 0', fontSize: '0.9rem', lineHeight: 1.5 }}>{narrative.dieu_gi_dang_xay_ra}</p>
                            <div style={{ fontSize: '0.84rem', color: '#6b7280', marginTop: '6px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                              <span>{narrative.xu_huong_keo_dai}</span>
                              <span>Tác động: {narrative.anh_huong_dai_han}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p style={{ color: '#16a34a', margin: 0, fontWeight: 600 }}>Chưa phát hiện dấu hiệu bất thường tài chính đáng kể.</p>
                  )}
                </section>

                {/* 5. ĐÁNH GIÁ BẪY GIÁ TRỊ */}
                <section className="card value-trap-card" style={{ padding: '20px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h3 style={{ fontSize: '1.15rem', margin: 0 }}>Đánh Giá Bẫy Giá Trị (Value Trap Gate)</h3>
                    {renderBadge(valueTrap.status)}
                  </div>
                  <div className="vt-details" style={{ lineHeight: 1.6, fontSize: '0.93rem' }}>
                    <p style={{ margin: '4px 0' }}>Trạng thái Bẫy giá trị: <strong>{formatValueTrap(valueTrap.status)}</strong></p>
                    <p style={{ margin: '4px 0' }}>Xu hướng nền tảng kinh doanh: <strong>{formatDeterioration(valueTrap.deterioration_classification)}</strong></p>
                    {valueTrap.hard_failures && valueTrap.hard_failures.length > 0 && (
                      <p style={{ margin: '4px 0', color: '#dc2626' }}>Rủi ro nghiêm trọng: <strong>{valueTrap.hard_failures.map(formatFindingTitle).join(', ')}</strong></p>
                    )}
                    {valueTrap.warnings && valueTrap.warnings.length > 0 && (
                      <p style={{ margin: '4px 0', color: '#d97706' }}>Cảnh báo cần lưu ý: <strong>{valueTrap.warnings.map(formatFindingTitle).join(', ')}</strong></p>
                    )}
                  </div>
                </section>

                {/* 6 & 7. ĐỊNH GIÁ & BIÊN AN TOÀN */}
                <section className="card valuation-card" style={{ padding: '20px' }}>
                  <h3 style={{ fontSize: '1.15rem', marginTop: 0, marginBottom: '16px' }}>Định Giá Chuẩn Mực & Biên An Toàn (MOS)</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '16px', textAlign: 'center' }}>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>Giá Thị Trường</small>
                      <strong style={{ fontSize: '1.1rem' }}>{formatVND(valuation.current_price)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>Bear IV (Thận trọng)</small>
                      <strong style={{ fontSize: '1.1rem' }}>{formatVND(valuation.bear_iv)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                      <small style={{ display: 'block', color: '#1d4ed8' }}>Base IV (Nội tại)</small>
                      <strong style={{ fontSize: '1.15rem', color: '#1e40af' }}>{formatVND(valuation.base_iv)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>Bull IV (Lạc quan)</small>
                      <strong style={{ fontSize: '1.1rem' }}>{formatVND(valuation.bull_iv)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>MOS Thực Tế</small>
                      <strong style={{ fontSize: '1.1rem', color: (valuation.actual_mos_pct ?? 0) >= (valuation.required_mos_pct ?? 25) ? '#16a34a' : '#dc2626' }}>{formatPct(valuation.actual_mos_pct)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>MOS Yêu Cầu</small>
                      <strong style={{ fontSize: '1.1rem' }}>{valuation.required_mos_pct ? `${valuation.required_mos_pct}%` : 'N/A'}</strong>
                    </div>
                  </div>
                </section>

                {/* 8. MUNGER PRE-MORTEM (8 CÂU HỎI PHẢN BIỆN) */}
                <ThesisChallengeSection challengeData={munger.thesis_challenge} decision={decision} />

                {/* 9. SỨC MẠNH LỢI NHUẬN & BẰNG CHỨNG LỊCH SỬ */}
                <section className="card earning-power-card" style={{ padding: '20px' }}>
                  <h3 style={{ fontSize: '1.15rem', marginTop: 0, marginBottom: '12px' }}>Sức Mạnh Lợi Nhuận Chuẩn Hóa & Bằng Chứng Lịch Sử</h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>LNST Gần Nhất (Reported)</small>
                      <strong style={{ fontSize: '1.05rem' }}>{formatVND(normPower.reported_latest)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>LNST Chuẩn Hóa 5 Năm</small>
                      <strong style={{ fontSize: '1.05rem' }}>{formatVND(normPower.normalized_5y)}</strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px' }}>
                      <small style={{ display: 'block', color: '#6b7280' }}>LNST Chuẩn Hóa 10 Năm</small>
                      <strong style={{ fontSize: '1.05rem' }}>{formatVND(normPower.normalized_10y)}</strong>
                    </div>
                  </div>
                  <p style={{ marginTop: '12px', marginBottom: 0, fontSize: '0.88rem', color: '#6b7280' }}>{normPower.explanation}</p>
                </section>

            </div>
          )}
        </div>
      )}
    </main>
  </div>
);
}

