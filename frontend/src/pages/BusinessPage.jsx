import React, { useEffect, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import SymbolSuggestInput from '../components/SymbolSuggestInput.jsx';
import ThesisChallengeSection from '../components/ThesisChallengeSection.jsx';
import { navigate } from '../lib/navigation.js';
import { downloadBusinessMungerAIExport } from '../lib/aiExport.js';
import { getMungerCandidates } from '../lib/api.js';
import { formatStatus, formatDecision, formatClassification, formatValueTrap, formatDeterioration, formatArchetype, formatMetricName, formatFindingNarrative, formatMarginTrend, formatFindingTitle, formatPct, formatVND, formatRatioX, formatDebtEquity, formatCfoPat } from '../utils/vietnameseSemantics.js';

export default function BusinessPage() {
  const [symbol, setSymbol] = useState(null);
  const [searchInput, setSearchInput] = useState('');
  const [portfolioSymbols, setPortfolioSymbols] = useState(['ACB', 'DGC', 'FPT', 'VIX']);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exportingAI, setExportingAI] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);
  const [exportMsg, setExportMsg] = useState('');

  // Candidates state
  const [candidatesData, setCandidatesData] = useState(null);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [selectedCandidateTier, setSelectedCandidateTier] = useState('all');
  const [selectedLiquidityFilter, setSelectedLiquidityFilter] = useState('all');
  const [showAllCandidates, setShowAllCandidates] = useState(false);

  useEffect(() => {
    const pathParts = window.location.pathname.split('/');
    const targetSym = pathParts.length > 2 && pathParts[2] ? pathParts[2].trim().toUpperCase() : null;
    setSymbol(targetSym);

    if (targetSym) {
      fetchBusinessData(targetSym);
    } else {
      fetchPortfolioSymbols();
      fetchCandidates('all', 'all');
    }
  }, [window.location.pathname]);

  const fetchCandidates = (tier = 'all', liq = 'all') => {
    setCandidatesLoading(true);
    getMungerCandidates(tier, liq)
      .then((res) => {
        if (res && res.ok) setCandidatesData(res);
      })
      .catch(() => {})
      .finally(() => setCandidatesLoading(false));
  };

  const fetchPortfolioSymbols = () => {
    fetch('/api/portfolio/holding-symbols')
      .then((res) => res.json())
      .then((res) => {
        if (res.ok && res.symbols && res.symbols.length > 0) {
          setPortfolioSymbols(res.symbols);
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

  const handleExportPDF = async () => {
    if (!data || exportingPDF) return;
    setExportingPDF(true);
    setExportMsg('Đang tạo và tải về tệp PDF báo cáo BCTC...');
    try {
      const cleanSym = String(symbol || 'BUSINESS').toUpperCase();
      const dateStr = new Date().toISOString().slice(0, 10);
      const filename = `Bao_Cao_BCTC_Munger_${cleanSym}_${dateStr}.pdf`;

      const element = document.getElementById('business-detail-report') || document.querySelector('.business-detail-container');
      if (!element) {
        throw new Error('Không tìm thấy nội dung báo cáo.');
      }

      // Small delay to ensure React state (forceExpand=true) fully updates DOM before canvas capture
      await new Promise((resolve) => setTimeout(resolve, 150));

      const { exportElementToPDF } = await import('../lib/pdfExport.js');
      await exportElementToPDF(element, filename);

      setExportMsg(`Đã tải về tệp PDF ${filename} thành công.`);
      setTimeout(() => setExportMsg(''), 6000);
    } catch (err) {
      console.error('Direct PDF export error:', err);
      setExportMsg(`Không thể xuất tệp PDF: ${err.message}`);
    } finally {
      setExportingPDF(false);
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
            <section className="card portfolio-symbols-card" style={{ marginBottom: '24px', padding: '24px' }}>
              <div className="card-header" style={{ marginBottom: '12px' }}>
                <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Danh mục hiện tại ({portfolioSymbols.length} vị thế)</h3>
              </div>
              <p className="muted" style={{ marginBottom: '16px', fontSize: '0.9rem' }}>
                Chọn một vị thế trong danh mục để xem phân tích tài chính Munger &amp; Biên an toàn:
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

            {/* Munger Investment Candidates Section */}
            <section className="card candidates-section-card" style={{ padding: '24px' }}>
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <span className="eyebrow" style={{ fontSize: '0.78rem', textTransform: 'uppercase', color: '#0284c7', fontWeight: 700, letterSpacing: '0.05em' }}>
                    Sàng lọc cơ hội đầu tư dài hạn
                  </span>
                  <h2 style={{ fontSize: '1.45rem', margin: '4px 0 6px 0', fontWeight: 800 }}>
                    Cổ phiếu tiềm năng theo tiêu chuẩn Munger
                  </h2>
                  <p className="muted" style={{ margin: 0, fontSize: '0.92rem' }}>
                    Doanh nghiệp có chất lượng tài chính vượt trội, sức mạnh bảng cân đối an toàn và không phát hiện dấu hiệu bẫy giá trị (Nguồn BCTC: SSI).
                  </p>
                </div>
                {candidatesData?.summary && (
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '12px', padding: '4px 10px', background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0', borderRadius: '4px', fontWeight: 600 }}>
                      {candidatesData.summary.exceptional_count} Xuất sắc
                    </span>
                    <span style={{ fontSize: '12px', padding: '4px 10px', background: '#eff6ff', color: '#1e40af', border: '1px solid #bfdbfe', borderRadius: '4px', fontWeight: 600 }}>
                      {candidatesData.summary.high_quality_count} Chất lượng cao
                    </span>
                    <span style={{ fontSize: '12px', padding: '4px 10px', background: '#f8fafc', color: '#475569', border: '1px solid #cbd5e0', borderRadius: '4px', fontWeight: 600 }}>
                      {candidatesData.summary.investable_count} Đáng xem xét
                    </span>
                  </div>
                )}
              </div>

              {/* Tier & Liquidity Filter Tabs */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                <div className="candidate-tier-tabs" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted, #718096)', marginRight: '4px' }}>Chất lượng:</span>
                  {[
                    { key: 'all', label: 'Tất cả chất lượng' },
                    { key: 'exceptional', label: 'Chất lượng xuất sắc' },
                    { key: 'high_quality', label: 'Chất lượng cao' },
                    { key: 'investable', label: 'Đáng xem xét' },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => {
                        setSelectedCandidateTier(tab.key);
                        fetchCandidates(tab.key, selectedLiquidityFilter);
                      }}
                      style={{
                        padding: '6px 14px',
                        fontSize: '12px',
                        fontWeight: selectedCandidateTier === tab.key ? 700 : 500,
                        borderRadius: '4px',
                        border: selectedCandidateTier === tab.key ? '1px solid #0284c7' : '1px solid var(--border, #cbd5e0)',
                        background: selectedCandidateTier === tab.key ? '#0284c7' : 'var(--panel-subtle, #f7fafc)',
                        color: selectedCandidateTier === tab.key ? '#ffffff' : 'inherit',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="candidate-liquidity-tabs" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted, #718096)', marginRight: '4px' }}>Thanh khoản:</span>
                  {[
                    { key: 'all', label: 'Tất cả thanh khoản' },
                    { key: 'LIQUIDITY_STRONG', label: 'Thanh khoản tốt' },
                    { key: 'LIQUIDITY_ACCEPTABLE', label: 'Thanh khoản đủ' },
                    { key: 'LIQUIDITY_WEAK', label: 'Thanh khoản thấp' },
                    { key: 'LIQUIDITY_INSUFFICIENT_DATA', label: 'Chưa đủ dữ liệu' },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => {
                        setSelectedLiquidityFilter(tab.key);
                        fetchCandidates(selectedCandidateTier, tab.key);
                      }}
                      style={{
                        padding: '4px 12px',
                        fontSize: '11px',
                        fontWeight: selectedLiquidityFilter === tab.key ? 700 : 500,
                        borderRadius: '4px',
                        border: selectedLiquidityFilter === tab.key ? '1px solid #059669' : '1px solid var(--border, #e2e8f0)',
                        background: selectedLiquidityFilter === tab.key ? '#059669' : 'var(--panel-subtle, #f8fafc)',
                        color: selectedLiquidityFilter === tab.key ? '#ffffff' : 'inherit',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {candidatesLoading && (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted, #718096)', fontSize: '0.95rem' }}>
                  Đang quét và tính toán ứng viên Munger từ cơ sở dữ liệu BCTC chuẩn hóa…
                </div>
              )}

              {!candidatesLoading && (!candidatesData?.candidates || candidatesData.candidates.length === 0) && (
                <div style={{ padding: '24px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px', textAlign: 'center', color: 'var(--text-muted, #718096)', fontSize: '0.92rem' }}>
                  Chưa có mã nào đáp ứng đủ tiêu chuẩn lọc trong nhóm này.
                </div>
              )}

              {/* Candidates Grid */}
              {!candidatesLoading && candidatesData?.candidates && candidatesData.candidates.length > 0 && (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '18px' }}>
                    {(showAllCandidates ? candidatesData.candidates : candidatesData.candidates.slice(0, 6)).map((c) => (
                      <div
                        key={c.symbol}
                        className="candidate-card"
                        style={{
                          border: '1px solid var(--border, #e2e8f0)',
                          borderRadius: '8px',
                          padding: '18px',
                          background: 'var(--panel, #ffffff)',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '14px',
                        }}
                      >
                        <div>
                          {/* Card Header: Symbol & Badges */}
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <strong style={{ fontSize: '1.25rem', color: 'var(--text, #1a202c)' }}>{c.symbol}</strong>
                                <span style={{ fontSize: '11px', color: 'var(--text-muted, #718096)' }}>{c.archetype_vi}</span>
                              </div>
                              <div style={{ fontSize: '12px', color: 'var(--text-muted, #718096)', marginTop: '2px' }}>
                                {c.company_name}
                              </div>
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                              <div style={{ display: 'flex', gap: '4px' }}>
                                <span style={{
                                  padding: '2px 8px',
                                  borderRadius: '4px',
                                  fontSize: '11px',
                                  fontWeight: 700,
                                  background: c.candidate_tier_code === 'EXCEPTIONAL' ? '#f0fdf4' : (c.candidate_tier_code === 'HIGH_QUALITY' ? '#eff6ff' : '#f8fafc'),
                                  color: c.candidate_tier_code === 'EXCEPTIONAL' ? '#15803d' : (c.candidate_tier_code === 'HIGH_QUALITY' ? '#1d4ed8' : '#475569'),
                                  border: `1px solid ${c.candidate_tier_code === 'EXCEPTIONAL' ? '#86efac' : (c.candidate_tier_code === 'HIGH_QUALITY' ? '#93c5fd' : '#cbd5e0')}`,
                                }}>
                                  {c.quality_tier_vi}
                                </span>
                                <span style={{
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  background: c.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#f0fdf4' : (c.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#eff6ff' : '#fffbeb'),
                                  color: c.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#166534' : (c.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#1e40af' : '#92400e'),
                                  border: `1px solid ${c.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#bbf7d0' : (c.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#bfdbfe' : '#fef08a')}`,
                                }}>
                                  {c.liquidity?.classification_vi || 'Thanh khoản'}
                                </span>
                              </div>
                              <span style={{
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontSize: '10px',
                                fontWeight: 600,
                                background: c.value_trap_status === 'CLEAR' ? '#f0fdf4' : '#fffbeb',
                                color: c.value_trap_status === 'CLEAR' ? '#166534' : '#92400e',
                                border: `1px solid ${c.value_trap_status === 'CLEAR' ? '#bbf7d0' : '#fef08a'}`,
                              }}>
                                {c.value_trap_status_vi}
                              </span>
                            </div>
                          </div>

                          {/* 6 Key Financial Metrics Grid */}
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(3, 1fr)',
                            gap: '8px',
                            background: 'var(--surface-soft, #f8fafc)',
                            padding: '10px 12px',
                            borderRadius: '6px',
                            margin: '10px 0',
                            border: '1px solid var(--border-subtle, #f1f5f9)',
                            fontSize: '11px',
                          }}>
                            <div>
                              <div style={{ color: 'var(--text-muted, #718096)' }}>ROE Trung Vị</div>
                              <strong style={{ fontSize: '13px', color: c.roe_pct >= 18 ? '#15803d' : 'inherit' }}>
                                {c.roe_pct != null ? `${c.roe_pct}%` : 'Chưa đủ dữ liệu'}
                              </strong>
                            </div>
                            <div>
                              <div style={{ color: 'var(--text-muted, #718096)' }}>Tăng Trưởng LNST</div>
                              <strong style={{ fontSize: '13px', color: (c.net_profit_cagr_pct || 0) > 10 ? '#15803d' : 'inherit' }}>
                                {c.net_profit_cagr_pct != null ? `${c.net_profit_cagr_pct > 0 ? '+' : ''}${c.net_profit_cagr_pct}%` : 'Chưa tính'}
                              </strong>
                            </div>
                            <div>
                              <div style={{ color: 'var(--text-muted, #718096)' }}>CFO / PAT</div>
                              <strong style={{ fontSize: '13px' }}>
                                {c.cfo_to_pat_display}
                              </strong>
                            </div>
                            <div>
                              <div style={{ color: 'var(--text-muted, #718096)' }}>
                                {c.solvency_metric_label || (c.archetype === 'BANK' ? 'Đòn bẩy TS (TS/VCSH)' : 'Nợ / Vốn CSH')}
                              </div>
                              <strong style={{ fontSize: '12px' }}>
                                {c.solvency_metric_display || c.debt_to_equity_display}
                              </strong>
                            </div>
                            <div>
                              <div style={{ color: 'var(--text-muted, #718096)' }}>Giá / Base IV</div>
                              <strong style={{ fontSize: '12px' }}>
                                {c.current_price ? `${(c.current_price / 1000).toFixed(1)}k` : '—'} / {c.base_iv ? `${(c.base_iv / 1000).toFixed(1)}k` : '—'}
                              </strong>
                            </div>
                            <div>
                              <div style={{ color: 'var(--text-muted, #718096)' }}>Biên An Toàn (MOS)</div>
                              <strong style={{ fontSize: '13px', color: (c.actual_mos_pct || 0) >= (c.required_mos_pct || 25) ? '#15803d' : '#dd6b20' }}>
                                {c.actual_mos_pct != null ? `${c.actual_mos_pct.toFixed(1)}%` : '—'}
                              </strong>
                            </div>
                          </div>

                          {/* Liquidity info snippet */}
                          {c.liquidity && (
                            <div style={{ fontSize: '11px', color: '#475569', margin: '4px 0 8px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                              <span><strong>GTGD 20 phiên:</strong> {c.liquidity.avg_trading_value_20d_billion != null ? `${c.liquidity.avg_trading_value_20d_billion} tỷ/ngày` : 'Chưa đủ dữ liệu'}</span>
                              <span><strong>Khối lượng 20D:</strong> {c.liquidity.avg_volume_20d != null ? `${(c.liquidity.avg_volume_20d / 1e3).toFixed(0)}k cp` : 'Chưa đủ'}</span>
                            </div>
                          )}

                          {/* Synthesis Conclusion */}
                          {c.synthesis_conclusion_vi && (
                            <div style={{ fontSize: '12px', lineHeight: 1.4, color: '#0f766e', background: '#f0fdfa', border: '1px solid #ccfbf1', padding: '6px 10px', borderRadius: '4px', marginBottom: '8px' }}>
                              <strong>Kết luận:</strong> {c.synthesis_conclusion_vi}
                            </div>
                          )}

                          {/* Recommendation Rationale */}
                          <div style={{ fontSize: '12px', lineHeight: 1.5, color: '#334155', marginTop: '6px' }}>
                            <strong>Lý do đề xuất:</strong> {c.recommendation_reason_vi}
                          </div>

                          {/* Top Warning if any */}
                          {c.top_warning_vi && c.top_warning_vi !== 'Không có cảnh báo tài chính trọng yếu' && (
                            <div style={{ fontSize: '11px', color: '#c2410c', marginTop: '6px', display: 'flex', gap: '4px' }}>
                              <span>⚠️</span>
                              <span><strong>Cảnh báo:</strong> {c.top_warning_vi}</span>
                            </div>
                          )}
                        </div>

                        {/* Card Footer: Navigation button */}
                        <div style={{ borderTop: '1px solid var(--border-subtle, #f1f5f9)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted, #94a3b8)' }}>
                            {c.data_source}
                          </span>
                          <button
                            type="button"
                            onClick={() => navigate(`/business/${c.symbol}`)}
                            style={{
                              padding: '6px 14px',
                              fontSize: '12px',
                              fontWeight: 700,
                              borderRadius: '4px',
                              border: 'none',
                              background: '#0284c7',
                              color: '#ffffff',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                            }}
                          >
                            Xem phân tích chi tiết →
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Toggle view all button */}
                  {candidatesData.candidates.length > 6 && (
                    <div style={{ textAlign: 'center', marginTop: '20px' }}>
                      <button
                        type="button"
                        onClick={() => setShowAllCandidates(!showAllCandidates)}
                        style={{
                          padding: '8px 24px',
                          fontSize: '13px',
                          fontWeight: 700,
                          borderRadius: '6px',
                          border: '1px solid #0284c7',
                          background: 'transparent',
                          color: '#0284c7',
                          cursor: 'pointer',
                        }}
                      >
                        {showAllCandidates ? '↑ Thu gọn danh sách' : `↓ Xem tất cả (${candidatesData.candidates.length} mã ứng viên)`}
                      </button>
                    </div>
                  )}
                </>
              )}
            </section>
          </div>
        ) : (
          /* Detail Workspace View */
          <div className="business-detail-container" id="business-detail-report">
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
              <div className="no-print" style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
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
                <button
                  type="button"
                  className="btn btn-secondary export-pdf-btn"
                  onClick={handleExportPDF}
                  disabled={exportingPDF || loading || !data}
                  style={{
                    padding: '8px 16px',
                    background: '#0f766e',
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
                    transition: 'all 0.15s ease',
                  }}
                >
                  <span aria-hidden="true">📄</span> {exportingPDF ? 'Đang chuẩn bị PDF…' : 'Xuất PDF'}
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

                  {/* Explicit Decision Conditions (if CONDITIONAL_BUY) */}
                  {decision.conditions && decision.conditions.length > 0 && (
                    <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', padding: '12px 16px', marginBottom: '16px', fontSize: '0.9rem' }}>
                      <strong style={{ color: '#92400e', display: 'block', marginBottom: '6px' }}>Điều kiện phân bổ / theo dõi cụ thể:</strong>
                      <ul style={{ margin: 0, paddingLeft: '20px', color: '#78350f' }}>
                        {decision.conditions.map((cond, cIdx) => (
                          <li key={cIdx} style={{ marginBottom: '4px' }}>
                            <strong>{cond.metric}:</strong> {cond.reason} (Thực tế: {typeof cond.actual === 'number' ? cond.actual.toLocaleString('vi-VN') : cond.actual} vs Ngưỡng: {typeof cond.threshold === 'number' ? cond.threshold.toLocaleString('vi-VN') : cond.threshold})
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Monitoring Signals / Watch Points */}
                  {decision.monitoring_reasons && decision.monitoring_reasons.length > 0 && (
                    <div style={{ background: 'var(--surface-soft, #f9fafb)', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px', padding: '12px 16px', marginBottom: '16px', fontSize: '0.88rem' }}>
                      <strong style={{ color: '#4b5563', display: 'block', marginBottom: '6px' }}>Chỉ tiêu giám sát định kỳ (Monitoring Signals — Không phải lỗi chặn mua):</strong>
                      <ul style={{ margin: 0, paddingLeft: '20px', color: '#4b5563' }}>
                        {decision.monitoring_reasons.map((mr, mIdx) => (
                          <li key={mIdx} style={{ marginBottom: '3px' }}>{mr}</li>
                        ))}
                      </ul>
                    </div>
                  )}

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
                        Tính bền bỉ: {munger.earnings_durability?.metrics?.profitable_years != null && munger.earnings_durability?.metrics?.total_years != null ? `Dương ${munger.earnings_durability.metrics.profitable_years}/${munger.earnings_durability.metrics.total_years} năm` : 'Chưa đủ chuỗi năm'}<br/>
                        Hệ số biến động CV: {formatPct(munger.earnings_durability?.metrics?.pat_volatility !== null && munger.earnings_durability?.metrics?.pat_volatility !== undefined ? munger.earnings_durability.metrics.pat_volatility * 100 : null, 'Chưa đủ chuỗi 3 năm')}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>4. Chất Lượng Lợi Nhuận</small>
                        {renderBadge(quality.earnings_quality)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        Tỷ lệ CFO/PAT: {formatCfoPat(munger.earnings_quality?.metrics?.median_cfo_pat ?? munger.earnings_quality?.metrics?.avg_cfo_pat ?? munger.earnings_quality?.metrics?.mean_cfo_pat)}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>5. Bảng Cân Đối Kế Toán</small>
                        {renderBadge(quality.balance_sheet)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        {munger.balance_sheet_strength?.explanation || 'Cơ cấu Tài sản & Nguồn vốn'}
                      </div>
                    </div>

                    <div className="dim-card" style={{ padding: '12px', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <small style={{ color: '#6b7280' }}>6. Nợ & Thanh Khoản</small>
                        {renderBadge(quality.debt_liquidity)}
                      </div>
                      <div style={{ fontSize: '0.88rem' }}>
                        {archetype === 'BANK' ? 'Đòn bẩy TS: ' : 'Nợ/VCSH (D/E): '}
                        <strong>{formatDebtEquity(munger.debt_liquidity?.metrics?.latest_debt_equity, archetype)}</strong>
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

                {/* 5. ĐIỀU TRA PHÁP Y BẪY GIÁ TRỊ (MUNGER VALUE TRAP FORENSICS) */}
                <section className="card value-trap-card" style={{ padding: '22px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: 12 }}>
                    <div>
                      <h3 style={{ fontSize: '1.2rem', margin: 0 }}>Điều Tra Pháp Y Bẫy Giá Trị (Munger Financial Forensics)</h3>
                      <small style={{ color: 'var(--text-muted, #718096)' }}>Đánh giá toàn diện chuỗi BCTC lịch sử đa năm nhằm phát hiện rủi ro xói mòn vốn</small>
                    </div>
                    {renderBadge(valueTrap.status)}
                  </div>

                  {/* Summary & Munger Final Action */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '20px' }}>
                    <div style={{ padding: '14px', borderRadius: '8px', background: 'var(--surface-soft, #f9fafb)', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ color: 'var(--text-muted, #718096)', display: 'block', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px' }}>Trạng thái bẫy giá trị</small>
                      <strong style={{ fontSize: '1.05rem', color: valueTrap.status === 'CLEAR' ? '#16a34a' : (valueTrap.status === 'WATCH' ? '#d97706' : '#dc2626') }}>
                        {formatValueTrap(valueTrap.status)}
                      </strong>
                    </div>
                    <div style={{ padding: '14px', borderRadius: '8px', background: 'var(--surface-soft, #f9fafb)', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ color: 'var(--text-muted, #718096)', display: 'block', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px' }}>Phân loại suy giảm</small>
                      <strong style={{ fontSize: '1.05rem' }}>
                        {formatDeterioration(valueTrap.deterioration_classification)}
                      </strong>
                    </div>
                    <div style={{ padding: '14px', borderRadius: '8px', background: 'var(--surface-soft, #f9fafb)', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ color: 'var(--text-muted, #718096)', display: 'block', fontSize: '11px', textTransform: 'uppercase', marginBottom: '4px' }}>Hành động khuyến nghị Munger</small>
                      <strong style={{ fontSize: '1.05rem', color: '#0284c7' }}>
                        {decision.state_vietnamese || valueTrap.munger_action?.action_vi || 'Xem xét Biên an toàn'}
                      </strong>
                    </div>
                  </div>

                  {/* Rationale explanation */}
                  {(decision.primary_reason || valueTrap.munger_action?.munger_rationale_vi) && (
                    <div style={{ padding: '12px 16px', background: '#eff6ff', borderRadius: '6px', borderLeft: '4px solid #3b82f6', marginBottom: '20px', fontSize: '0.92rem', lineHeight: 1.5 }}>
                      <strong>Kết luận điều tra:</strong> {decision.primary_reason || valueTrap.munger_action?.munger_rationale_vi}
                    </div>
                  )}

                  {/* Top 3 Financial Risks */}
                  <div style={{ marginBottom: '20px' }}>
                    <h4 style={{ fontSize: '1.02rem', margin: '0 0 12px', fontWeight: 700 }}>
                      3 RỦI RO TÀI CHÍNH QUAN TRỌNG NHẤT
                    </h4>
                    {valueTrap.top_risks && valueTrap.top_risks.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {valueTrap.top_risks.map((r, rIdx) => (
                          <div key={rIdx} style={{ padding: '12px 16px', borderRadius: '6px', border: '1px solid #fed7aa', background: '#fffbeb', fontSize: '0.9rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                              <strong style={{ color: '#c2410c' }}>Rủi ro #{r.rank}: {r.title_vi}</strong>
                              <span style={{ fontSize: '11px', padding: '2px 6px', background: '#ffedd5', borderRadius: '4px', fontWeight: 600, color: '#9a3412' }}>
                                Mức độ: {r.severity_vi} ({r.period_vi})
                              </span>
                            </div>
                            <div style={{ color: '#4b5563', margin: '3px 0' }}>{r.evidence_vi}</div>
                            {r.consequence_vi && (
                              <div style={{ fontSize: '0.84rem', color: '#6b7280', marginTop: '4px' }}>
                                <strong>Hệ quả:</strong> {r.consequence_vi}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ padding: '12px 16px', borderRadius: '6px', background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: '0.92rem' }}>
                        {valueTrap.top_risks_summary_vi || 'Không phát hiện bằng chứng tài chính đáng kể của bẫy giá trị trong dữ liệu lịch sử hiện có.'}
                      </div>
                    )}
                  </div>

                  {/* Counter-Evidence (Bằng chứng phản bác) */}
                  {valueTrap.counter_evidence && valueTrap.counter_evidence.length > 0 && (
                    <div style={{ marginBottom: '20px', padding: '14px 16px', borderRadius: '6px', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                      <h4 style={{ fontSize: '0.95rem', margin: '0 0 8px', fontWeight: 700, color: '#334155' }}>
                        Bằng Chứng Phản Bác & Yếu Tố Bù Đắp An Toàn ({valueTrap.counter_evidence.length}):
                      </h4>
                      <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.88rem', color: '#475569', lineHeight: 1.6 }}>
                        {valueTrap.counter_evidence.map((c, cIdx) => (
                          <li key={cIdx}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* 14-Point Value Trap Scorecard */}
                  {valueTrap.scorecard && valueTrap.scorecard.length > 0 && (
                    <div>
                      <h4 style={{ fontSize: '1.02rem', margin: '0 0 12px', fontWeight: 700 }}>
                        Bảng Điểm Pháp Y Tài Chính Tổng Hợp (14 Tiêu Chí)
                      </h4>
                      <div className="table-responsive">
                        <table className="data-table" style={{ fontSize: '12px' }}>
                          <thead>
                            <tr>
                              <th style={{ width: '40px' }}>#</th>
                              <th>Hạng mục đánh giá</th>
                              <th style={{ width: '100px' }}>Trạng thái</th>
                              <th style={{ width: '90px' }}>Mức độ</th>
                              <th style={{ width: '100px' }}>Giai đoạn</th>
                              <th>Bằng chứng & Dữ liệu ghi nhận</th>
                            </tr>
                          </thead>
                          <tbody>
                            {valueTrap.scorecard.map((item) => (
                              <tr key={item.index}>
                                <td>{item.index}</td>
                                <td><strong>{item.name_vi}</strong></td>
                                <td>
                                  <span style={{
                                    display: 'inline-block',
                                    padding: '2px 6px',
                                    borderRadius: '4px',
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    background: item.status_vi === 'Đạt' || item.status_vi === 'Không suy giảm' ? '#f0fdf4' : (item.status_vi === 'Không áp dụng' ? '#f8fafc' : (item.status_vi === 'Cần theo dõi' || item.status_vi === 'Suy giảm chu kỳ' ? '#fffbeb' : '#fef2f2')),
                                    color: item.status_vi === 'Đạt' || item.status_vi === 'Không suy giảm' ? '#166534' : (item.status_vi === 'Không áp dụng' ? '#64748b' : (item.status_vi === 'Cần theo dõi' || item.status_vi === 'Suy giảm chu kỳ' ? '#92400e' : '#991b1b')),
                                    border: `1px solid ${item.status_vi === 'Đạt' || item.status_vi === 'Không suy giảm' ? '#bbf7d0' : (item.status_vi === 'Không áp dụng' ? '#e2e8f0' : (item.status_vi === 'Cần theo dõi' || item.status_vi === 'Suy giảm chu kỳ' ? '#fef08a' : '#fecaca'))}`,
                                  }}>
                                    {item.status_vi}
                                  </span>
                                </td>
                                <td>{item.severity_vi}</td>
                                <td>{item.period_vi}</td>
                                <td style={{ whiteSpace: 'normal', minWidth: '280px', lineHeight: 1.4 }}>
                                  {item.evidence_vi}
                                  {item.reason_not_applicable && (
                                    <span style={{ display: 'block', fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
                                      ({item.reason_not_applicable})
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </section>

                {/* 6. THANH KHOẢN GIAO DỊCH THỰC TẾ (MUNGER LIQUIDITY GATE) */}
                <section className="card liquidity-card" style={{ padding: '20px' }}>
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: 8 }}>
                    <h3 style={{ fontSize: '1.15rem', margin: 0 }}>Thanh Khoản Giao Dịch Thực Tế (Cổng Kiểm Tra Khả Thi Giao Dịch)</h3>
                    <span style={{
                      display: 'inline-block',
                      padding: '4px 10px',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 700,
                      background: munger.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#f0fdf4' : (munger.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#eff6ff' : (munger.liquidity?.classification === 'LIQUIDITY_WEAK' ? '#fffbeb' : '#f8fafc')),
                      color: munger.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#166534' : (munger.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#1e40af' : (munger.liquidity?.classification === 'LIQUIDITY_WEAK' ? '#92400e' : '#64748b')),
                      border: `1px solid ${munger.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#bbf7d0' : (munger.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#bfdbfe' : (munger.liquidity?.classification === 'LIQUIDITY_WEAK' ? '#fef08a' : '#e2e8f0'))}`,
                    }}>
                      {munger.liquidity?.classification_vi || 'Chưa đủ dữ liệu thanh khoản'}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px', marginBottom: '16px' }}>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ display: 'block', color: 'var(--text-muted, #718096)', fontSize: '11px', textTransform: 'uppercase' }}>Giá Giao Dịch Gần Nhất</small>
                      <strong style={{ fontSize: '1.1rem', color: '#1e40af' }}>
                        {munger.liquidity?.latest_price != null ? `${munger.liquidity.latest_price.toLocaleString('vi-VN')} đ` : 'Chưa có dữ liệu'}
                      </strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ display: 'block', color: 'var(--text-muted, #718096)', fontSize: '11px', textTransform: 'uppercase' }}>KLGD Bình Quân 20 Phiên</small>
                      <strong style={{ fontSize: '1.1rem' }}>
                        {munger.liquidity?.avg_volume_20d != null ? `${munger.liquidity.avg_volume_20d.toLocaleString('vi-VN')} cp/ngày` : 'Chưa đủ dữ liệu'}
                      </strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ display: 'block', color: 'var(--text-muted, #718096)', fontSize: '11px', textTransform: 'uppercase' }}>Giá Trị GD Bình Quân 20 Phiên</small>
                      <strong style={{ fontSize: '1.1rem', color: ((munger.liquidity?.avg_trading_value_20d_billion ?? munger.liquidity?.avg_trading_value_20d) || 0) >= 5 ? '#15803d' : '#b45309' }}>
                        {(munger.liquidity?.avg_trading_value_20d_billion ?? munger.liquidity?.avg_trading_value_20d) != null ? `${munger.liquidity.avg_trading_value_20d_billion ?? munger.liquidity.avg_trading_value_20d} tỷ đ/ngày` : 'Chưa đủ dữ liệu'}
                      </strong>
                    </div>
                    <div style={{ padding: '12px', background: 'var(--surface-soft, #f9fafb)', borderRadius: '6px', border: '1px solid var(--border, #e5e7eb)' }}>
                      <small style={{ display: 'block', color: 'var(--text-muted, #718096)', fontSize: '11px', textTransform: 'uppercase' }}>Mật Độ Phiên Có GD (20 Phiên)</small>
                      <strong style={{ fontSize: '1.1rem' }}>
                        {munger.liquidity?.trading_day_coverage_pct != null ? `${munger.liquidity.trading_day_coverage_pct}% (${munger.liquidity.trading_days_found ?? munger.liquidity.trading_days_observed ?? 0}/${munger.liquidity.trading_days_observed ?? 20})` : (munger.liquidity?.trading_day_coverage != null ? `${Math.round(munger.liquidity.trading_day_coverage * 100)}%` : 'Chưa đủ dữ liệu')}
                      </strong>
                    </div>
                  </div>

                  <div style={{
                    padding: '12px 16px',
                    borderRadius: '6px',
                    background: munger.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#f0fdf4' : (munger.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#eff6ff' : '#fffbeb'),
                    borderLeft: `4px solid ${munger.liquidity?.classification === 'LIQUIDITY_STRONG' ? '#16a34a' : (munger.liquidity?.classification === 'LIQUIDITY_ACCEPTABLE' ? '#3b82f6' : '#d97706')}`,
                    fontSize: '0.92rem',
                    lineHeight: 1.5,
                  }}>
                    <strong>Nhận xét khả năng giao dịch:</strong> {munger.liquidity?.commentary_vi || 'Chưa đủ dữ liệu thanh khoản để đánh giá.'}
                  </div>
                </section>

                {/* 7. ĐỊNH GIÁ & BIÊN AN TOÀN */}
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
                      <strong style={{ fontSize: '1.1rem' }}>{valuation.required_mos_pct ? `${valuation.required_mos_pct}%` : 'Chưa có'}</strong>
                    </div>
                  </div>
                </section>

                {/* 8. MUNGER PRE-MORTEM (8 CÂU HỎI PHẢN BIỆN) */}
                <ThesisChallengeSection challengeData={munger.thesis_challenge} decision={decision} forceExpand={exportingPDF} />

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

