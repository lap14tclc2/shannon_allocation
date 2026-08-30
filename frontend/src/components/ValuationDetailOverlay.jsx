import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { getValuationReport } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';
import {
  archetypeLabel,
  qualityTierLabel,
  valuationModelLabel,
  verdictLabel,
  verdictPillClass,
} from '../lib/valuationLabels.js';

function displayNumber(value, suffix = '', digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(digits)}${suffix}`;
}

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${formatMoney(value, false, locale)} ₫`;
}

export function ValuationStatusPill({ status, marginOfSafety }) {
  const map = {
    HIGH_CONVICTION_VALUE: { label: 'Đầu tư Giá trị Tuyệt vời', cls: 'v-pill-deep-value', icon: '✦' },
    ATTRACTIVE: { label: 'Vùng giá Hấp dẫn', cls: 'v-pill-undervalued', icon: '✓' },
    FAIRLY_VALUED: { label: 'Định giá Hợp lý', cls: 'v-pill-fair', icon: '⚖' },
    FAIR_VALUE: { label: 'Định giá Hợp lý', cls: 'v-pill-fair', icon: '⚖' },
    WATCH: { label: 'Cần Theo dõi thêm', cls: 'v-pill-watch', icon: '◷' },
    AVOID_QUALITY: { label: 'Thận trọng Chất lượng', cls: 'v-pill-distressed', icon: '⚠' },
    UNVALUABLE: { label: 'Ngoài Vòng Năng lực', cls: 'v-pill-distressed', icon: '⊗' },
    DEEP_VALUE: { label: 'Định giá Rất Rẻ', cls: 'v-pill-deep-value', icon: '✦' },
    UNDERVALUED: { label: 'Dưới Giá trị Thực', cls: 'v-pill-undervalued', icon: '✓' },
    OVERVALUED: { label: 'Định giá Cao hơn Giá trị', cls: 'v-pill-overvalued', icon: '↑' },
    GROWTH_PRICED_IN: { label: 'Đã phản ánh Tăng trưởng', cls: 'v-pill-overvalued', icon: '↑' },
  };
  const conf = map[status] || { label: 'Đang theo dõi', cls: 'v-pill-watch', icon: '◷' };
  return (
    <span className={`v-status-badge ${conf.cls}`}>
      <span className="v-status-icon">{conf.icon}</span>
      <span>{conf.label}</span>
    </span>
  );
}

export function ValuationSkeletonCard({ symbol }) {
  return (
    <div className="v-skeleton-wrapper" aria-busy="true">
      <div className="v-hero-grid">
        <div className="v-skeleton-box" style={{ height: '90px' }} />
        <div className="v-skeleton-box" style={{ height: '90px' }} />
        <div className="v-skeleton-box" style={{ height: '90px' }} />
      </div>
      <div className="v-multiples-grid" style={{ marginTop: '16px' }}>
        <div className="v-skeleton-box" style={{ height: '56px' }} />
        <div className="v-skeleton-box" style={{ height: '56px' }} />
        <div className="v-skeleton-box" style={{ height: '56px' }} />
        <div className="v-skeleton-box" style={{ height: '56px' }} />
      </div>
      <div className="v-skeleton-box" style={{ height: '220px', marginTop: '16px' }} />
    </div>
  );
}

export function ValuationReportBody({ symbol, report, locale = 'vi' }) {
  if (!report) return null;
  const multiples = report.valuation_multiples || {};
  const base = report.scenarios?.BASE || {};
  const bear = report.scenarios?.BEAR || {};
  const bull = report.scenarios?.BULL || {};
  const bridge = report.owner_earnings_bridge || {};
  const assessment = report.assessment || {};
  const quality = report.quality_scorecard || {};
  const arch = report.archetype_profile || {};
  const mosAnalysis = report.margin_of_safety_analysis || {};
  const mos = base.margin_of_safety_pct;
  const isVerifiedModel = report.model_status === 'MODEL_VERIFIED';
  const publicBaseIV = base.intrinsic_value_per_share != null ? base.intrinsic_value_per_share : null;
  const publicMos = mos != null ? mos : (publicBaseIV && report.current_market_price ? ((publicBaseIV - report.current_market_price) / publicBaseIV * 100) : null);

  const hasMultiples = multiples.pe != null || multiples.pb != null || multiples.eps != null || multiples.roe != null;
  const hasScenarios = bear.intrinsic_value_per_share != null && bull.intrinsic_value_per_share != null && base.intrinsic_value_per_share != null;
  const pillars = report.value_investor_pillars;
  const hasPillars = Boolean(
    pillars && (
      (pillars.earnings_quality && (pillars.earnings_quality.status || pillars.earnings_quality.diagnosis)) ||
      (pillars.financial_fortress && (pillars.financial_fortress.status || pillars.financial_fortress.diagnosis)) ||
      (pillars.capital_allocation && (pillars.capital_allocation.status || pillars.capital_allocation.diagnosis))
    )
  );
  const hasBridge = Boolean(bridge && bridge.net_profit != null);
  const hasMatrix = Boolean(report.sotp_sensitivity_matrix?.grid_values_per_share?.length > 0);
  const hasTechnical = hasBridge || hasMatrix;

  return (
    <div className="v-report-content">
      {/* Primary Price & Valuation 3-Card Hero Grid */}
      <div className="v-hero-grid">
        <div className="v-hero-card">
          <span className="v-hero-label">THỊ GIÁ HIỆN TẠI</span>
          <span className="v-hero-value">{money(report.current_market_price, locale)}</span>
          <span className="v-hero-sub">Thị giá sàn (VNDirect)</span>
        </div>

        <div className={`v-hero-card v-hero-intrinsic ${publicMos > 0 ? 'is-undervalued' : publicMos < 0 ? 'is-overvalued' : ''}`}>
          <span className="v-hero-label">GIÁ TRỊ THỰC CƠ SỞ</span>
          <span className="v-hero-value highlight">
            {publicBaseIV != null && Number.isFinite(Number(publicBaseIV)) ? money(publicBaseIV, locale) : 'N/A'}
          </span>
          <span className="v-hero-sub">
            {isVerifiedModel ? 'Mô hình Buffett-Munger chuẩn hóa' : 'Ước tính theo BCTC mới nhất'}
          </span>
        </div>

        <div className={`v-hero-card v-hero-mos ${publicMos > 0 ? 'is-pos' : publicMos < 0 ? 'is-neg' : ''}`}>
          <span className="v-hero-label">BIÊN AN TOÀN THỰC TẾ</span>
          <span className="v-hero-value mos-val">
            {publicMos != null && Number.isFinite(Number(publicMos)) ? `${publicMos > 0 ? '+' : ''}${Number(publicMos).toFixed(1)}%` : '—'}
          </span>
          <span className="v-hero-sub">
            {mosAnalysis.required_mos_pct != null ? `Yêu cầu tối thiểu: ≥ ${mosAnalysis.required_mos_pct}%` : 'Chuẩn giá trị an toàn'}
          </span>
        </div>
      </div>

      {/* Multiples 4-Card Grid - Only show if data exists */}
      {hasMultiples && (
        <div className="v-multiples-grid">
          {multiples.pe != null && (
            <div className="v-metric-card" title="P/E: Giá trên Lợi nhuận mỗi cổ phần">
              <span className="v-metric-label">P/E (GIÁ/LNST)</span>
              <span className="v-metric-value">{displayNumber(multiples.pe, ' lần')}</span>
            </div>
          )}
          {multiples.pb != null && (
            <div className="v-metric-card" title="P/B: Giá trên Giá trị sổ sách mỗi cổ phần">
              <span className="v-metric-label">P/B (GIÁ/SỔ SÁCH)</span>
              <span className="v-metric-value">{displayNumber(multiples.pb, ' lần', 2)}</span>
            </div>
          )}
          {multiples.eps != null && (
            <div className="v-metric-card" title="EPS: Lợi nhuận sau thuế tạo ra trên mỗi cổ phần">
              <span className="v-metric-label">LỢI NHUẬN/CP (EPS)</span>
              <span className="v-metric-value">{formatMoney(multiples.eps, false, locale)} ₫</span>
            </div>
          )}
          {multiples.roe != null && (
            <div className="v-metric-card" title="ROE: Tỷ suất sinh lời trên Vốn chủ sở hữu">
              <span className="v-metric-label">SINH LỜI VỐN (ROE)</span>
              <span className="v-metric-value highlight-roe">{displayNumber(multiples.roe, '%')}</span>
            </div>
          )}
        </div>
      )}

      {/* Expert Financial Analysis Narrative Card */}
      <div className="v-narrative-card">
        <div className="v-narrative-header">
          <div className="v-narrative-title-wrap">
            <span className="v-narrative-badge-icon">✦</span>
            <h3 className="v-narrative-title">NHẬN ĐỊNH CHUYÊN SÂU · BUFFETT–MUNGER</h3>
          </div>
          {assessment.valuation_status && (
            <span className={`v-verdict-pill ${verdictPillClass(assessment.valuation_status)}`}>
              {verdictLabel(assessment.valuation_status)}
            </span>
          )}
        </div>

        <div className="v-narrative-meta-grid">
          <div className="v-meta-item">
            <span className="v-meta-label">NGÀNH NGHỀ KINH DOANH</span>
            <span className="v-meta-value">{archetypeLabel(arch.archetype)}</span>
            {arch.recommended_model && (
              <span className="v-meta-sub">{valuationModelLabel(arch.recommended_model)}</span>
            )}
          </div>
          {quality.total_score != null && (
            <div className="v-meta-item">
              <span className="v-meta-label">ĐIỂM CHẤT LƯỢNG DOANH NGHIỆP</span>
              <span className="v-meta-value">{quality.total_score}/100</span>
              {quality.tier && (
                <span className="v-meta-sub">{qualityTierLabel(quality.tier)}</span>
              )}
            </div>
          )}
          {mos != null && Number.isFinite(Number(mos)) && (
            <div className="v-meta-item">
              <span className="v-meta-label">BIÊN AN TOÀN THỰC TẾ</span>
              <span className={`v-meta-value ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
                {mos > 0 ? '+' : ''}{Number(mos).toFixed(1)}%
              </span>
              {mosAnalysis.required_mos_pct != null && (
                <span className="v-meta-sub">
                  Yêu cầu ≥ {mosAnalysis.required_mos_pct}% · {mos >= mosAnalysis.required_mos_pct ? 'Đạt chuẩn' : 'Chưa đạt'}
                </span>
              )}
            </div>
          )}
        </div>

        {/* 3-Scenario Range Track - Only if scenarios exist */}
        {hasScenarios && (
          <div className="v-scenarios-panel">
            <div className="v-scenario-header-row">
              <span className="v-scenario-title">GIÁ TRỊ NỘI TẠI · KỊCH BẢN CƠ SỞ</span>
              <span className="v-scenario-base-num">{money(base.intrinsic_value_per_share, locale)}</span>
            </div>
            <div className="v-scenario-track">
              <div className="v-scenario-node node-bear">
                <span className="node-tag">THẬN TRỌNG (BEAR)</span>
                <span className="node-price">{money(bear.intrinsic_value_per_share, locale)}</span>
              </div>
              <div className="v-scenario-arrow">⟶</div>
              <div className="v-scenario-node node-base is-active">
                <span className="node-tag">CƠ SỞ (BASE)</span>
                <span className="node-price">{money(base.intrinsic_value_per_share, locale)}</span>
              </div>
              <div className="v-scenario-arrow">⟶</div>
              <div className="v-scenario-node node-bull">
                <span className="node-tag">LẠC QUAN (BULL)</span>
                <span className="node-price">{money(bull.intrinsic_value_per_share, locale)}</span>
              </div>
            </div>
          </div>
        )}

        {assessment.financial_resilience_diagnosis && (
          <div className="v-narrative-box">
            <h4 className="v-box-title">CẤU TRÚC VỐN & SỨC KHỎE TÀI CHÍNH</h4>
            <p className="v-box-text">{assessment.financial_resilience_diagnosis}</p>
          </div>
        )}

        {report.sector_conflict_warning && (
          <div className="v-narrative-box v-warning-box">
            <h4 className="v-box-title">⚠️ PHÂN LOẠI NGÀNH CHUYÊN BIỆT</h4>
            <p className="v-box-text">{report.sector_conflict_warning}</p>
          </div>
        )}
      </div>

      {/* Value Investor Health Pillars Accordion - Only if pillars exist */}
      {hasPillars && (
        <details className="v-accordion">
          <summary className="v-accordion-summary">
            <div className="v-accordion-title-wrap">
              <span className="v-accordion-badge">3 TRỤ CỘT</span>
              <span className="v-accordion-title">Sức Khỏe Doanh Nghiệp (Tiền mặt · Pháo đài · Phân bổ vốn)</span>
            </div>
            <span className="v-accordion-chevron">▾</span>
          </summary>
          <div className="v-accordion-content">
            <div className="v-pillars-grid">
              {pillars.earnings_quality && (
                <div className="v-pillar-card">
                  <div className="v-pillar-head">
                    <span className="v-pillar-name">1. Chất lượng Tiền mặt</span>
                    {pillars.earnings_quality.status && (
                      <span className="v-pillar-tag">
                        {pillars.earnings_quality.status === 'EXCEPTIONAL' ? 'Xuất sắc' : pillars.earnings_quality.status === 'GOOD' ? 'Tốt' : 'Cần chú ý'}
                      </span>
                    )}
                  </div>
                  {(pillars.earnings_quality.avg_cash_conversion_5y != null || pillars.earnings_quality.avg_roe_5y != null) && (
                    <div className="v-pillar-metric">
                      <span className="v-pillar-val">
                        {pillars.earnings_quality.avg_cash_conversion_5y != null
                          ? `${pillars.earnings_quality.avg_cash_conversion_5y}%`
                          : `${pillars.earnings_quality.avg_roe_5y}%`}
                      </span>
                      <span className="v-pillar-sub">
                        {pillars.earnings_quality.avg_cash_conversion_5y != null
                          ? 'Tỷ lệ đổi LNST ra Tiền mặt (5Y)'
                          : 'ROE chu kỳ 5 năm'}
                      </span>
                    </div>
                  )}
                  {pillars.earnings_quality.diagnosis && (
                    <p className="v-pillar-desc">{pillars.earnings_quality.diagnosis}</p>
                  )}
                </div>
              )}

              {pillars.financial_fortress && (
                <div className="v-pillar-card">
                  <div className="v-pillar-head">
                    <span className="v-pillar-name">2. Pháo đài Tài chính</span>
                    {pillars.financial_fortress.status && (
                      <span className="v-pillar-tag">
                        {pillars.financial_fortress.status === 'STRONG' ? 'Rất Vững' : pillars.financial_fortress.status === 'HEALTHY' ? 'Lành mạnh' : 'Cần chú ý'}
                      </span>
                    )}
                  </div>
                  {pillars.financial_fortress.debt_payback_years != null && (
                    <div className="v-pillar-metric">
                      <span className="v-pillar-val">
                        {pillars.financial_fortress.debt_payback_years === 0 ? '0 năm (Tiền mặt ròng)' : `${pillars.financial_fortress.debt_payback_years} năm`}
                      </span>
                      <span className="v-pillar-sub">Thời gian trả hết Nợ bằng Dòng tiền</span>
                    </div>
                  )}
                  {pillars.financial_fortress.diagnosis && (
                    <p className="v-pillar-desc">{pillars.financial_fortress.diagnosis}</p>
                  )}
                </div>
              )}

              {pillars.capital_allocation && (
                <div className="v-pillar-card">
                  <div className="v-pillar-head">
                    <span className="v-pillar-name">3. Hiệu quả Phân bổ Vốn</span>
                    {pillars.capital_allocation.status && (
                      <span className="v-pillar-tag">
                        {pillars.capital_allocation.status === 'EXCELLENT' ? 'Xuất sắc' : pillars.capital_allocation.status === 'GOOD' ? 'Tốt' : 'Cần chú ý'}
                      </span>
                    )}
                  </div>
                  {pillars.capital_allocation.avg_roe_5y != null && (
                    <div className="v-pillar-metric">
                      <span className="v-pillar-val">{pillars.capital_allocation.avg_roe_5y}%</span>
                      <span className="v-pillar-sub">
                        Pha loãng thực: {pillars.capital_allocation.share_dilution_5y_pct != null ? `${pillars.capital_allocation.share_dilution_5y_pct}%` : '0%'}
                      </span>
                    </div>
                  )}
                  {pillars.capital_allocation.diagnosis && (
                    <p className="v-pillar-desc">{pillars.capital_allocation.diagnosis}</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </details>
      )}

      {/* Technical Calculations & Sensitivity Matrix Accordion - Only if data exists */}
      {hasTechnical && (
        <details className="v-accordion">
          <summary className="v-accordion-summary">
            <div className="v-accordion-title-wrap">
              <span className="v-accordion-badge">CHI TIẾT</span>
              <span className="v-accordion-title">Bóc tách Lợi nhuận Chủ doanh nghiệp (Owner Earnings) & Độ nhạy</span>
            </div>
            <span className="v-accordion-chevron">▾</span>
          </summary>
          <div className="v-accordion-content">
            {/* Owner Earnings Bridge */}
            {hasBridge && (
              <div className="v-tech-box">
                <h4 className="v-tech-title">BÓC TÁCH LỢI NHUẬN THỰC CỦA CHỦ DOANH NGHIỆP (5 NĂM CHU KỲ)</h4>
                <div className="v-bridge-grid">
                  <div className="v-bridge-item">
                    <span className="b-label">LNST Báo cáo</span>
                    <span className="b-val">{money(bridge.net_profit, locale)}</span>
                  </div>
                  <div className="v-bridge-item">
                    <span className="b-label">+ Khấu hao (D&A)</span>
                    <span className="b-val">+{money(bridge.depreciation, locale)}</span>
                  </div>
                  <div className="v-bridge-item">
                    <span className="b-label">- CapEx Bảo trì</span>
                    <span className="b-val neg">-{money(bridge.maintenance_capex, locale)}</span>
                  </div>
                  <div className="v-bridge-item is-result">
                    <span className="b-label">= Owner Earnings</span>
                    <span className="b-val highlight">{money(bridge.owner_earnings, locale)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* SOTP / DCF Sensitivity Matrix */}
            {hasMatrix && (
              <div className="v-tech-box">
                <h4 className="v-tech-title">
                  BẢNG ĐỘ NHẠY ĐỊNH GIÁ SOTP ({report.sotp_sensitivity_matrix.row_label || 'Hệ số Cấu phần'} \ {report.sotp_sensitivity_matrix.col_label || 'Chiết khấu'})
                </h4>
                <div className="v-table-scroll">
                  <table className="v-matrix-table">
                    <thead>
                      <tr>
                        <th>{report.sotp_sensitivity_matrix.row_label} \ {report.sotp_sensitivity_matrix.col_label}</th>
                        {report.sotp_sensitivity_matrix.discount_rates.map(r => (
                          <th key={r} className={Number(r) === 0.15 ? 'is-base-col' : ''}>{Number(r) * 100}%</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {report.sotp_sensitivity_matrix.terminal_growth_rates.map((g, rowIdx) => (
                        <tr key={g}>
                          <td><strong>{Number(g)}x</strong></td>
                          {report.sotp_sensitivity_matrix.grid_values_per_share[rowIdx].map((cellVal, colIdx) => {
                            const isBase = Number(report.sotp_sensitivity_matrix.discount_rates[colIdx]) === 0.15 && Number(g) === 1.0;
                            return (
                              <td key={colIdx} className={isBase ? 'is-base-cell' : ''}>
                                {cellVal > 0 ? `${Math.round(cellVal).toLocaleString('vi-VN')} ₫` : '—'}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}

export default function ValuationDetailOverlay({ symbol, report: initialReport, error: initialError, locale = 'vi', onClose }) {
  const [report, setReport] = useState(initialReport || null);
  const [error, setError] = useState(initialError || null);
  const [loading, setLoading] = useState(!initialReport && !initialError);

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    document.body.classList.add('modal-open');
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.classList.remove('modal-open');
    };
  }, [onClose]);

  useEffect(() => {
    if (!symbol) return undefined;
    if (initialReport || initialError) {
      setReport(initialReport || null);
      setError(initialError || null);
      setLoading(false);
      return undefined;
    }
    let active = true;
    setLoading(true);
    setError(null);
    getValuationReport(symbol)
      .then(res => {
        if (!active) return;
        const rep = res?.report || res;
        if (res?.ok === false || !rep) {
          setError({ code: res?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: res?.error || 'Không thể tải dữ liệu định giá.' });
        } else {
          setReport(rep);
        }
      })
      .catch(err => {
        if (!active) return;
        setError({
          code: err?.code || 'VALUATION_SOURCE_UNAVAILABLE',
          message: err?.message || 'Không thể tải dữ liệu định giá.',
        });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [symbol, initialReport, initialError]);

  if (!symbol) return null;
  const multiples = report?.valuation_multiples || {};
  const assessment = report?.assessment || {};
  const quality = report?.quality_scorecard || {};
  const base = report?.scenarios?.BASE || {};
  const mos = base.margin_of_safety_pct;

  const overlayElement = (
    <div
      className="v-overlay-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby={`valuation-modal-title-${symbol}`}
    >
      <style>{`
        .v-overlay-backdrop {
          position: fixed;
          inset: 0;
          z-index: 99999;
          background: rgba(14, 18, 24, 0.76);
          backdrop-filter: blur(5px);
          -webkit-backdrop-filter: blur(5px);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          box-sizing: border-box;
          animation: vFadeIn 0.2s ease-out;
        }
        @keyframes vFadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes vSlideUp { from { transform: translateY(20px) scale(0.98); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }

        .v-overlay-modal {
          position: relative;
          z-index: 100000;
          width: 100%;
          max-width: 960px;
          max-height: 90vh;
          display: flex;
          flex-direction: column;
          background: var(--surface-bg, var(--retro-bg, #fbf7ee));
          color: var(--text, var(--retro-ink, #201d18));
          border: 1.5px solid var(--retro-border, #9c927f);
          border-radius: 10px;
          box-shadow: 0 24px 64px rgba(0, 0, 0, 0.35);
          overflow: hidden;
          box-sizing: border-box;
          animation: vSlideUp 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .v-overlay-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 24px;
          border-bottom: 1.5px solid var(--retro-border, #9c927f);
          background: var(--surface-soft, var(--retro-panel-subtle, #f4ecd9));
          flex-shrink: 0;
          gap: 16px;
        }

        .v-header-left {
          display: flex;
          flex-direction: column;
          gap: 6px;
          min-width: 0;
        }

        .v-header-title-row {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .v-header-ticker {
          margin: 0;
          font-size: 1.6rem;
          font-weight: 800;
          letter-spacing: -0.02em;
          color: var(--retro-ink, #201d18);
          line-height: 1;
        }

        .v-tag {
          font-size: 0.8rem;
          font-weight: 600;
          padding: 3px 9px;
          border-radius: 4px;
          background: var(--surface-bg, #fbf7ee);
          border: 1px solid var(--retro-border, #9c927f);
          color: var(--retro-muted, #5f574a);
          white-space: nowrap;
        }

        .v-tag.v-tag-quality {
          background: color-mix(in srgb, var(--retro-indigo, #2b4c7e) 10%, transparent);
          border-color: color-mix(in srgb, var(--retro-indigo, #2b4c7e) 30%, transparent);
          color: var(--retro-indigo, #2b4c7e);
          font-weight: 700;
        }

        .v-header-sub-row {
          font-size: 0.82rem;
          color: var(--retro-muted, #736b5e);
        }

        .v-header-actions {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-shrink: 0;
        }

        .v-status-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 6px;
          font-size: 0.85rem;
          font-weight: 700;
          white-space: nowrap;
          border: 1.5px solid currentColor;
        }
        .v-pill-undervalued { background: #eafaf1; color: #1e7e46; border-color: #27ae60; }
        .v-pill-deep-value { background: #e8f8f5; color: #117a65; border-color: #16a085; }
        .v-pill-fair { background: #fef9e7; color: #b7950b; border-color: #d4ac0d; }
        .v-pill-watch { background: #fdf2e9; color: #af601a; border-color: #e67e22; }
        .v-pill-overvalued { background: #fdedec; color: #b03a2e; border-color: #e74c3c; }
        .v-pill-distressed { background: #f4ecf7; color: #6c3483; border-color: #8e44ad; }

        .v-close-btn {
          width: 36px;
          height: 36px;
          border-radius: 6px;
          background: var(--surface-bg, #fbf7ee);
          border: 1.5px solid var(--retro-border, #9c927f);
          color: var(--retro-ink, #201d18);
          font-size: 1.1rem;
          font-weight: 700;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .v-close-btn:hover {
          background: #a63f30;
          color: #ffffff;
          border-color: #a63f30;
        }

        .v-overlay-body {
          flex: 1;
          overflow-y: auto;
          padding: 24px;
          -webkit-overflow-scrolling: touch;
        }

        /* 3-Card Hero */
        .v-hero-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 16px;
          margin-bottom: 16px;
        }
        .v-hero-card {
          background: var(--surface-soft, #f4ecd9);
          border: 1.5px solid var(--retro-border, #9c927f);
          border-radius: 8px;
          padding: 16px 18px;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .v-hero-card.is-undervalued {
          border-color: #27ae60;
          background: color-mix(in srgb, #27ae60 8%, var(--surface-soft, #f4ecd9));
        }
        .v-hero-card.is-overvalued {
          border-color: #e74c3c;
          background: color-mix(in srgb, #e74c3c 8%, var(--surface-soft, #f4ecd9));
        }
        .v-hero-label {
          font-size: 0.72rem;
          font-weight: 800;
          letter-spacing: 0.06em;
          color: var(--retro-muted, #736b5e);
        }
        .v-hero-value {
          font-size: 1.65rem;
          font-weight: 800;
          font-family: var(--font-mono-num, monospace);
          color: var(--retro-ink, #201d18);
          line-height: 1.2;
        }
        .v-hero-value.highlight {
          color: var(--retro-indigo, #2b4c7e);
        }
        .v-hero-card.is-pos .mos-val { color: #1e7e46; }
        .v-hero-card.is-neg .mos-val { color: #b03a2e; }
        .v-hero-sub {
          font-size: 0.75rem;
          color: var(--retro-muted, #736b5e);
          margin-top: 2px;
        }

        /* 4-Card Multiples Grid */
        .v-multiples-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }
        .v-metric-card {
          background: var(--surface-soft, #f4ecd9);
          border: 1px solid var(--retro-border, #9c927f);
          border-radius: 6px;
          padding: 10px 14px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .v-metric-label {
          font-size: 0.68rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: var(--retro-muted, #736b5e);
        }
        .v-metric-value {
          font-size: 1.15rem;
          font-weight: 700;
          font-family: var(--font-mono-num, monospace);
          color: var(--retro-ink, #201d18);
        }
        .v-metric-value.highlight-roe {
          color: var(--retro-indigo, #2b4c7e);
        }

        /* Narrative Section */
        .v-narrative-card {
          background: var(--surface-soft, #f4ecd9);
          border: 1.5px solid var(--retro-border, #9c927f);
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 16px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .v-narrative-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
          gap: 10px;
        }
        .v-narrative-title-wrap {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .v-narrative-badge-icon {
          color: #a63f30;
          font-size: 1.1rem;
        }
        .v-narrative-title {
          margin: 0;
          font-size: 0.95rem;
          font-weight: 800;
          letter-spacing: 0.04em;
          color: var(--retro-ink, #201d18);
        }
        .v-verdict-pill {
          font-size: 0.8rem;
          font-weight: 700;
          padding: 4px 10px;
          border-radius: 4px;
          border: 1px solid currentColor;
        }

        .v-narrative-meta-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          background: var(--surface-bg, #fbf7ee);
          border: 1px solid var(--retro-border, #9c927f);
          border-radius: 6px;
          padding: 12px 16px;
        }
        .v-meta-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .v-meta-label {
          font-size: 0.68rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: var(--retro-muted, #736b5e);
        }
        .v-meta-value {
          font-size: 1.05rem;
          font-weight: 700;
          color: var(--retro-ink, #201d18);
        }
        .v-meta-value.pos { color: #1e7e46; }
        .v-meta-value.neg { color: #b03a2e; }
        .v-meta-sub {
          font-size: 0.72rem;
          color: var(--retro-muted, #736b5e);
        }

        /* Scenario Track */
        .v-scenarios-panel {
          background: var(--surface-bg, #fbf7ee);
          border: 1px solid var(--retro-border, #9c927f);
          border-radius: 6px;
          padding: 14px 18px;
        }
        .v-scenario-header-row {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 12px;
        }
        .v-scenario-title {
          font-size: 0.75rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: var(--retro-muted, #736b5e);
        }
        .v-scenario-base-num {
          font-size: 1.4rem;
          font-weight: 800;
          font-family: var(--font-mono-num, monospace);
          color: var(--retro-indigo, #2b4c7e);
        }
        .v-scenario-track {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
        }
        .v-scenario-node {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 8px 12px;
          border-radius: 6px;
          background: var(--surface-soft, #f4ecd9);
          border: 1px solid var(--retro-border, #9c927f);
        }
        .v-scenario-node.is-active {
          border-color: var(--retro-indigo, #2b4c7e);
          background: color-mix(in srgb, var(--retro-indigo, #2b4c7e) 10%, var(--surface-soft, #f4ecd9));
        }
        .node-tag {
          font-size: 0.68rem;
          font-weight: 700;
          color: var(--retro-muted, #736b5e);
        }
        .node-price {
          font-size: 0.95rem;
          font-weight: 700;
          font-family: var(--font-mono-num, monospace);
          color: var(--retro-ink, #201d18);
          margin-top: 2px;
        }
        .v-scenario-arrow {
          color: var(--retro-border, #9c927f);
          font-weight: 700;
        }

        .v-narrative-box {
          border-top: 1px dashed var(--retro-border, #9c927f);
          padding-top: 12px;
        }
        .v-box-title {
          margin: 0 0 6px 0;
          font-size: 0.78rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          color: #a63f30;
        }
        .v-box-text {
          margin: 0;
          font-size: 0.88rem;
          line-height: 1.5;
          color: var(--retro-ink, #201d18);
        }
        .v-warning-box {
          background: #fff8e1;
          border: 1px solid #ffe082;
          padding: 10px 14px;
          border-radius: 6px;
        }

        /* Accordion */
        .v-accordion {
          border: 1.5px solid var(--retro-border, #9c927f);
          border-radius: 8px;
          background: var(--surface-soft, #f4ecd9);
          margin-bottom: 12px;
          overflow: hidden;
        }
        .v-accordion-summary {
          padding: 14px 18px;
          cursor: pointer;
          user-select: none;
          display: flex;
          align-items: center;
          justify-content: space-between;
          list-style: none;
          font-weight: 700;
        }
        .v-accordion-summary::-webkit-details-marker { display: none; }
        .v-accordion-title-wrap {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .v-accordion-badge {
          font-size: 0.7rem;
          font-weight: 800;
          padding: 2px 6px;
          border-radius: 3px;
          background: var(--retro-ink, #201d18);
          color: #ffffff;
        }
        .v-accordion-title {
          font-size: 0.88rem;
          color: var(--retro-ink, #201d18);
        }
        .v-accordion-chevron {
          font-size: 0.9rem;
          color: var(--retro-muted, #736b5e);
          transition: transform 0.2s ease;
        }
        .v-accordion[open] .v-accordion-chevron {
          transform: rotate(180deg);
        }
        .v-accordion-content {
          padding: 0 18px 18px 18px;
        }

        /* Pillars 3 Grid */
        .v-pillars-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        .v-pillar-card {
          background: var(--surface-bg, #fbf7ee);
          border: 1px solid var(--retro-border, #9c927f);
          border-radius: 6px;
          padding: 12px 14px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .v-pillar-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .v-pillar-name {
          font-size: 0.78rem;
          font-weight: 800;
          color: var(--retro-ink, #201d18);
        }
        .v-pillar-tag {
          font-size: 0.7rem;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 3px;
          background: #eafaf1;
          color: #1e7e46;
        }
        .v-pillar-metric {
          display: flex;
          flex-direction: column;
        }
        .v-pillar-val {
          font-size: 1.15rem;
          font-weight: 800;
          font-family: var(--font-mono-num, monospace);
          color: var(--retro-indigo, #2b4c7e);
        }
        .v-pillar-sub {
          font-size: 0.7rem;
          color: var(--retro-muted, #736b5e);
        }
        .v-pillar-desc {
          margin: 4px 0 0 0;
          font-size: 0.78rem;
          line-height: 1.4;
          color: var(--retro-ink, #201d18);
        }

        /* Tech Boxes & Tables */
        .v-tech-box {
          background: var(--surface-bg, #fbf7ee);
          border: 1px solid var(--retro-border, #9c927f);
          border-radius: 6px;
          padding: 14px;
          margin-top: 10px;
        }
        .v-tech-title {
          margin: 0 0 10px 0;
          font-size: 0.78rem;
          font-weight: 800;
          letter-spacing: 0.04em;
          color: var(--retro-muted, #736b5e);
        }
        .v-bridge-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
        }
        .v-bridge-item {
          background: var(--surface-soft, #f4ecd9);
          border: 1px solid var(--retro-border, #9c927f);
          border-radius: 4px;
          padding: 8px 10px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .v-bridge-item.is-result {
          border-color: var(--retro-indigo, #2b4c7e);
          background: color-mix(in srgb, var(--retro-indigo, #2b4c7e) 10%, var(--surface-soft, #f4ecd9));
        }
        .b-label { font-size: 0.7rem; font-weight: 700; color: var(--retro-muted, #736b5e); }
        .b-val { font-size: 0.95rem; font-weight: 700; font-family: var(--font-mono-num, monospace); }
        .b-val.neg { color: #b03a2e; }
        .b-val.highlight { color: var(--retro-indigo, #2b4c7e); }

        .v-table-scroll {
          overflow-x: auto;
        }
        .v-matrix-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.8rem;
          font-family: var(--font-mono-num, monospace);
        }
        .v-matrix-table th, .v-matrix-table td {
          border: 1px solid var(--retro-border, #9c927f);
          padding: 6px 10px;
          text-align: right;
        }
        .v-matrix-table th {
          background: var(--surface-soft, #f4ecd9);
          font-weight: 700;
        }
        .v-matrix-table th:first-child, .v-matrix-table td:first-child {
          text-align: left;
        }
        .is-base-col, .is-base-cell {
          background: #fef9e7 !important;
          font-weight: 800;
          color: var(--retro-indigo, #2b4c7e);
        }

        /* Skeleton loader */
        .v-skeleton-box {
          background: linear-gradient(90deg, #f4ecd9 25%, #eae0ca 50%, #f4ecd9 75%);
          background-size: 200% 100%;
          animation: vShimmer 1.5s infinite;
          border-radius: 6px;
        }
        @keyframes vShimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

        /* Responsive Mobile Sheet (< 720px) */
        @media (max-width: 719px) {
          .v-overlay-backdrop {
            padding: 0;
            align-items: flex-end;
            background: rgba(0, 0, 0, 0.7);
          }
          .v-overlay-modal {
            width: 100%;
            max-width: 100%;
            max-height: 92vh;
            border-radius: 16px 16px 0 0;
            border-bottom: none;
            border-left: none;
            border-right: none;
            box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.4);
          }
          .v-modal-grabber {
            width: 38px;
            height: 4px;
            background: var(--retro-border, #9c927f);
            border-radius: 2px;
            margin: 8px auto 2px;
            opacity: 0.6;
          }
          .v-overlay-header {
            padding: 10px 14px;
            gap: 8px;
            flex-wrap: wrap;
          }
          .v-header-title-row {
            gap: 6px;
            flex-wrap: wrap;
          }
          .v-header-ticker { font-size: 1.3rem; }
          .v-tag { font-size: 0.72rem; padding: 2px 6px; }
          .v-header-actions {
            width: 100%;
            justify-content: space-between;
          }
          .v-close-btn {
            min-width: 44px;
            min-height: 44px;
            font-size: 1.2rem;
          }
          .v-overlay-body { padding: 12px; }
          .v-hero-grid { grid-template-columns: 1fr; gap: 8px; }
          .v-hero-card { padding: 12px 14px; }
          .v-hero-value { font-size: 1.35rem; }
          .v-multiples-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
          .v-metric-card { padding: 8px 10px; }
          .v-narrative-card { padding: 12px; }
          .v-narrative-meta-grid { grid-template-columns: 1fr; gap: 6px; }
          .v-scenario-track { flex-direction: column; gap: 6px; }
          .v-scenario-arrow { display: none; }
          .v-pillars-grid { grid-template-columns: 1fr; gap: 8px; }
          .v-bridge-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
        }
      `}</style>

      <div className="v-overlay-modal" onClick={e => e.stopPropagation()}>
        <div className="v-modal-grabber" aria-hidden="true" />
        {/* Sleek Top Header Bar */}
        <header className="v-overlay-header">
          <div className="v-header-left">
            <div className="v-header-title-row">
              <h2 id={`valuation-modal-title-${symbol}`} className="v-header-ticker">{symbol}</h2>
              <span className="v-tag">{multiples.sector || 'Doanh nghiệp niêm yết'}</span>
              {quality.total_score != null && (
                <span className="v-tag v-tag-quality">
                  ✦ {quality.total_score}/100 · {qualityTierLabel(quality.tier)}
                </span>
              )}
            </div>
            <div className="v-header-sub-row">
              Kỳ Báo cáo Tài chính: <strong>{report?.fiscal_period_latest || 'Năm 2025'}</strong>
            </div>
          </div>

          <div className="v-header-actions">
            {assessment.valuation_status && (
              <ValuationStatusPill status={assessment.valuation_status} marginOfSafety={mos} />
            )}
            <button
              className="v-close-btn"
              type="button"
              onClick={onClose}
              aria-label="Đóng chi tiết định giá"
              title="Đóng (Phím ESC)"
            >
              ✕
            </button>
          </div>
        </header>

        {/* Scrollable Body */}
        <main className="v-overlay-body">
          {error ? (
            <div className="valuation-card-error" style={{ padding: '24px', textAlign: 'center', background: '#fdedec', borderRadius: '8px', border: '1px solid #e74c3c' }}>
              <p role="alert" style={{ fontWeight: 'bold', color: '#b03a2e', margin: '0 0 8px 0' }}>{error.message}</p>
              <code style={{ fontSize: '0.8rem', color: '#78281f' }}>{error.code}</code>
            </div>
          ) : loading || !report ? (
            <ValuationSkeletonCard symbol={symbol} />
          ) : (
            <ValuationReportBody symbol={symbol} report={report} locale={locale} />
          )}
        </main>
      </div>
    </div>
  );

  if (typeof document !== 'undefined' && document.body) {
    return createPortal(overlayElement, document.body);
  }
  return overlayElement;
}
