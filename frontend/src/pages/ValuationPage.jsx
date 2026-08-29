import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getValuationReports } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { formatMoney } from '../lib/format.js';
import {
  archetypeLabel,
  modelStatusLabel,
  publicValuation,
  qualityTierLabel,
  valuationModelLabel,
  verdictLabel,
  verdictPillClass,
} from '../lib/valuationLabels.js';

function displayNumber(value, suffix = '', digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(digits)}${suffix}`;
}

function money(value, locale) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${formatMoney(value, false, locale)} ₫`;
}

function MethodologyGuide() {
  return (
    <details className="valuation-methodology-accordion">
      <summary className="methodology-summary">
        <div className="summary-left">
          <span className="summary-icon">📐</span>
          <span className="summary-title">Quy trình Định giá 4 Bước theo Bản chất Kinh tế (Buffett–Munger)</span>
        </div>
        <span className="summary-badge">Xem Infographic Phương pháp luận ▾</span>
      </summary>
      <div className="valuation-methodology-body">
        <div className="valuation-pipeline-grid">
          {/* Step 1 */}
          <div className="pipeline-step-card">
            <div className="step-header">
              <span className="step-number">BƯỚC 01</span>
              <span className="step-icon">🏷️</span>
            </div>
            <h4 className="step-title">Phân loại 40 Archetypes & Chuẩn hóa 10 Năm</h4>
            <div className="step-tags">
              <span className="step-tag">40 Mô hình ngành</span>
              <span className="step-tag">BCTC 10 năm</span>
            </div>
            <div className="step-flow-box">
              <div className="flow-badge">Lọc nhiễu Đỉnh/Đáy</div>
              <div className="flow-arrow">↓</div>
              <div className="flow-result">Trung vị Chu kỳ (Mid-Cycle Median)</div>
            </div>
            <p className="step-desc">Loại bỏ lợi nhuận bất thường, phản ánh đúng năng lực tạo tiền dài hạn qua cả chu kỳ suy thoái & hưng thịnh.</p>
          </div>

          {/* Step 2 */}
          <div className="pipeline-step-card">
            <div className="step-header">
              <span className="step-number">BƯỚC 02</span>
              <span className="step-icon">💰</span>
            </div>
            <h4 className="step-title">Bóc tách Dòng tiền Lợi nhuận Thực</h4>
            <div className="step-tags">
              <span className="step-tag">Lợi nhuận Thực</span>
              <span className="step-tag">RIM Ngân hàng</span>
            </div>
            <div className="step-formula-box">
              <code>LNST + Khấu hao − CapEx Duy trì</code>
            </div>
            <p className="step-desc">Tự động định tuyến: Tiền thuê đất (KCN), Khai thác hữu hạn TV=0 (Điện/Khí) hoặc Thu nhập thặng dư (Ngân hàng).</p>
          </div>

          {/* Step 3 */}
          <div className="pipeline-step-card">
            <div className="step-header">
              <span className="step-number">BƯỚC 03</span>
              <span className="step-icon">🎯</span>
            </div>
            <h4 className="step-title">Dải 3 Kịch bản & Ma trận Độ nhạy</h4>
            <div className="step-tags">
              <span className="step-tag">3 Kịch bản IV</span>
              <span className="step-tag">Stress-Test 2D</span>
            </div>
            <div className="step-scenarios-badge-row">
              <span className="scen-badge bear">🐻 Bear IV</span>
              <span className="scen-badge base">🎯 Base IV</span>
              <span className="scen-badge bull">🐂 Bull IV</span>
            </div>
            <p className="step-desc">Quét ma trận độ nhạy theo chiết khấu <i>r</i> (10–15%) và tăng trưởng <i>g</i> (2–4%), không phụ thuộc một con số cố định.</p>
          </div>

          {/* Step 4 */}
          <div className="pipeline-step-card">
            <div className="step-header">
              <span className="step-number">BƯỚC 04</span>
              <span className="step-icon">🛡️</span>
            </div>
            <h4 className="step-title">Thước đo Biên An Toàn (MOS 20%–50%)</h4>
            <div className="step-tags">
              <span className="step-tag">Biên An Toàn</span>
              <span className="step-tag">16 Lớp rủi ro</span>
            </div>
            <div className="step-rule-box">
              <span className="rule-label">Vùng Mua An Toàn:</span>
              <code className="rule-math">Thị giá ≤ Base IV × (1 − MOS)</code>
            </div>
            <p className="step-desc">Biên an toàn tự động co giãn theo đòn bẩy tài chính, tính chu kỳ, thâm dụng vốn và chất lượng quản trị.</p>
          </div>
        </div>

        <div className="valuation-quote-callout">
          <span className="quote-icon">❝</span>
          <div className="quote-content">
            <p><strong>Nguyên tắc cốt lõi Buffett–Munger:</strong> <em>"Chúng tôi không dự đoán thị trường ngày mai. Chúng tôi mua cổ phần của doanh nghiệp tuyệt vời khi thị giá thấp hơn đáng kể so với Giá trị Thực (Intrinsic Value) và đồng hành dài hạn."</em></p>
          </div>
        </div>
      </div>
    </details>
  );
}


function ValuationStatusPill({ status, marginOfSafety }) {
  const map = {
    HIGH_CONVICTION_VALUE: { label: 'Đầu tư Giá trị Tuyệt vời', cls: 'status-pill-deep-value' },
    ATTRACTIVE: { label: 'Vùng giá Hấp dẫn', cls: 'status-pill-undervalued' },
    FAIRLY_VALUED: { label: 'Định giá Hợp lý', cls: 'status-pill-fair' },
    FAIR_VALUE: { label: 'Định giá Hợp lý', cls: 'status-pill-fair' },
    WATCH: { label: 'Cần Theo dõi thêm', cls: 'status-pill-fair' },
    AVOID_QUALITY: { label: 'Thận trọng Chất lượng', cls: 'status-pill-distressed' },
    UNVALUABLE: { label: 'Ngoài Vòng Năng lực', cls: 'status-pill-distressed' },
    DEEP_VALUE: { label: 'Định giá Rất Rẻ', cls: 'status-pill-deep-value' },
    UNDERVALUED: { label: 'Dưới Giá trị Thực', cls: 'status-pill-undervalued' },
    OVERVALUED: { label: 'Định giá Cao hơn Giá trị', cls: 'status-pill-overvalued' },
    GROWTH_PRICED_IN: { label: 'Đã phản ánh Tăng trưởng', cls: 'status-pill-overvalued' },
  };
  const conf = map[status] || { label: 'Đang theo dõi', cls: 'status-pill-fair' };
  return <span className={`valuation-pill ${conf.cls}`}>{conf.label}</span>;
}

function ValuationCard({ symbol, report, error, locale }) {
  if (error) return <article className="valuation-card valuation-card-error">
    <div className="valuation-card-header">
      <div><h2>{symbol}</h2><span className="valuation-badge-error">Lỗi dữ liệu</span></div>
    </div>
    <div className="valuation-error-body">
      <p role="alert">{error.message}</p>
      <code>{error.code}</code>
    </div>
  </article>;

  if (!report) return null;
  const multiples = report.valuation_multiples || {};
  const pv = publicValuation(report);
  const base = { intrinsic_value_per_share: pv.base };
  const bear = { intrinsic_value_per_share: pv.bear };
  const bull = { intrinsic_value_per_share: pv.bull };
  const bridge = report.owner_earnings_bridge || {};
  const assessment = report.assessment || {};
  const quality = report.quality_scorecard || {};
  const arch = report.archetype_profile || {};
  const mosAnalysis = report.margin_of_safety_analysis || {};
  const scenarios = ['BEAR', 'BASE', 'BULL'];
  const freshness = report.data_freshness || {};
  const mos = pv.mos;

  return <article className="valuation-card">
    <div className="valuation-card-header">
      <div className="valuation-title-group">
        <div className="valuation-symbol-row">
          <h2>{symbol}</h2>
          <span className="valuation-sector-tag">{multiples.sector || 'Doanh nghiệp niêm yết'}</span>
          {quality.total_score != null && (
            <span className="valuation-sector-tag" style={{ background: 'var(--surface-soft, #f4ecd9)', borderColor: 'var(--retro-border, #9c927f)', color: 'var(--retro-text, #2a251d)' }}>
              Điểm Chất lượng: {quality.total_score}/100 ({quality.tier === 'EXCEPTIONAL' ? 'Xuất sắc' : quality.tier === 'HIGH_QUALITY' ? 'Chất lượng cao' : quality.tier === 'INVESTABLE' ? 'Đạt chuẩn đầu tư' : quality.tier === 'WATCH' ? 'Theo dõi' : 'Thấp'})
            </span>
          )}
        </div>
        <p className="valuation-period-subtitle">Kỳ Báo cáo Tài chính: <strong>{report.fiscal_period_latest || 'Năm 2025'}</strong></p>
      </div>
      <ValuationStatusPill status={assessment.valuation_status} marginOfSafety={mos} />
    </div>

    {/* Primary Price & Valuation Row */}
    <div className="valuation-price-hero">
      <div className="price-box">
        <span className="price-label">Thị giá hiện tại</span>
        <span className="price-value">{money(report.current_market_price, locale)}</span>
      </div>
      <div className="price-box price-box-intrinsic">
        <span className="price-label">Giá trị Thực cơ sở</span>
        <span className="price-value highlight">{money(base.intrinsic_value_per_share, locale)}</span>
      </div>
      <div className="price-box price-box-mos">
        <span className="price-label">Biên An Toàn Thực tế</span>
        <span className={`price-value ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
          {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
        </span>
        {mosAnalysis.required_mos_pct != null && (
          <small style={{ fontSize: '0.72rem', color: 'var(--retro-muted, #736b5e)', marginTop: '2px', display: 'block' }}>
            Yêu cầu tối thiểu: {mosAnalysis.required_mos_pct}%
          </small>
        )}
      </div>
    </div>

    {/* Multiples ribbon */}
    <div className="valuation-multiples-ribbon">
      <div className="metric-chip" title="P/E: Giá trên Lợi nhuận mỗi cổ phần">
        <span className="chip-label">P/E (Giá/LNST)</span>
        <span className="chip-value">{displayNumber(multiples.pe, ' lần')}</span>
      </div>
      <div className="metric-chip" title="P/B: Giá trên Giá trị sổ sách mỗi cổ phần">
        <span className="chip-label">P/B (Giá/Sổ sách)</span>
        <span className="chip-value">{displayNumber(multiples.pb, ' lần', 2)}</span>
      </div>
      <div className="metric-chip" title="EPS: Lợi nhuận sau thuế tạo ra trên mỗi cổ phần">
        <span className="chip-label">Lợi nhuận/CP (EPS)</span>
        <span className="chip-value">{multiples.eps == null ? '—' : `${formatMoney(multiples.eps, false, locale)} ₫`}</span>
      </div>
      <div className="metric-chip" title="ROE: Tỷ suất sinh lời trên Vốn chủ sở hữu">
        <span className="chip-label">Sinh lời Vốn (ROE)</span>
        <span className="chip-value">{displayNumber(multiples.roe, '%')}</span>
      </div>
    </div>

    {/* Expert Financial Analysis Narrative (Laws of UX: chunking, Von Restorff, Peak-End) */}
    <div className="valuation-analyst-opinion">
      <div className="opinion-header">
        <span className="opinion-badge">Nhận định Chuyên sâu · Buffett–Munger</span>
        <span className={`opinion-verdict-pill ${verdictPillClass(assessment.valuation_status)}`}>
          {verdictLabel(assessment.valuation_status)}
        </span>
      </div>

      <div className="opinion-chips">
        <div className="opinion-chip">
          <span className="opinion-chip-label">Ngành nghề kinh doanh</span>
          <span className="opinion-chip-value">
            {archetypeLabel(arch.archetype)}
            {arch.recommended_model && (
              <small className="opinion-chip-note">{valuationModelLabel(arch.recommended_model)}</small>
            )}
          </span>
        </div>
        <div className="opinion-chip">
          <span className="opinion-chip-label">Điểm Chất lượng Doanh nghiệp</span>
          <span className="opinion-chip-value">
            {quality.total_score != null ? `${quality.total_score}/100` : '—'}
            {quality.tier && (
              <small className="opinion-chip-note">{qualityTierLabel(quality.tier)}</small>
            )}
          </span>
        </div>
        <div className="opinion-chip opinion-chip-mos">
          <span className="opinion-chip-label">Biên An Toàn Thực tế</span>
          <span className={`opinion-chip-value ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
            {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
            {mosAnalysis.required_mos_pct != null && (
              <small className="opinion-chip-note">
                Yêu cầu ≥ {mosAnalysis.required_mos_pct}% {mos >= mosAnalysis.required_mos_pct ? '· Đạt' : '· Chưa đạt'}
              </small>
            )}
          </span>
        </div>
      </div>

      <div className="opinion-intrinsic">
        <div className="opinion-intrinsic-main">
          <span className="opinion-intrinsic-label">Giá trị nội tại · Kịch bản Cơ sở</span>
          <span className="opinion-intrinsic-value">{money(base.intrinsic_value_per_share, locale)}</span>
        </div>
        <div className="opinion-intrinsic-range">
          <span className="opinion-range-item"><i>Thận trọng</i><b>{money(bear.intrinsic_value_per_share, locale)}</b></span>
          <span className="opinion-range-sep">→</span>
          <span className="opinion-range-item"><i>Lạc quan</i><b>{money(bull.intrinsic_value_per_share, locale)}</b></span>
        </div>
      </div>

      {assessment.financial_resilience_diagnosis && (
        <div className="opinion-finhealth">
          <span className="opinion-finhealth-title">Cấu trúc vốn & Sức khỏe tài chính</span>
          <p className="opinion-finhealth-text">{assessment.financial_resilience_diagnosis}</p>
        </div>
      )}

      {report.sector_conflict_warning && (
        <div className="opinion-sector-warning">
          <span className="opinion-sector-warning-title">⚠️ Phân loại Ngành Chuyên biệt</span>
          <p className="opinion-sector-warning-text">{report.sector_conflict_warning}</p>
        </div>
      )}
    </div>

    {/* Value Investor Health Pillars (Miller's Law - 3 Focused Cards) */}
    {report.value_investor_pillars && (
      <div className="valuation-pillars-grid">
        <div className={`pillar-card pillar-${report.value_investor_pillars.earnings_quality?.status?.toLowerCase() || 'watch'}`}>
          <div className="pillar-header">
            <span className="pillar-title">1. Chất lượng Tiền mặt</span>
            <span className="pillar-badge">
              {report.value_investor_pillars.earnings_quality?.status === 'EXCEPTIONAL' ? 'Xuất sắc' : report.value_investor_pillars.earnings_quality?.status === 'GOOD' ? 'Tốt' : 'Cần chú ý'}
            </span>
          </div>
          <div className="pillar-metric">
            <span className="pillar-val">
              {report.value_investor_pillars.earnings_quality?.avg_cash_conversion_5y != null
                ? `${report.value_investor_pillars.earnings_quality.avg_cash_conversion_5y}%`
                : report.value_investor_pillars.earnings_quality?.avg_roe_5y != null
                  ? `${report.value_investor_pillars.earnings_quality.avg_roe_5y}%`
                  : '—'}
            </span>
            <span className="pillar-sub">
              {report.value_investor_pillars.earnings_quality?.avg_cash_conversion_5y != null
                ? 'Tỷ lệ đổi LNST ra Tiền mặt (5 năm)'
                : 'Sinh lời trên Vốn 5 năm (Ngân hàng)'}
            </span>
          </div>
          <p className="pillar-desc">{report.value_investor_pillars.earnings_quality?.diagnosis}</p>
        </div>

        <div className={`pillar-card pillar-${report.value_investor_pillars.financial_fortress?.status?.toLowerCase() || 'strong'}`}>
          <div className="pillar-header">
            <span className="pillar-title">2. Pháo đài Tài chính</span>
            <span className="pillar-badge">
              {report.value_investor_pillars.financial_fortress?.status === 'STRONG' ? 'Rất Vững' : report.value_investor_pillars.financial_fortress?.status === 'HEALTHY' ? 'Lành mạnh' : 'Cần chú ý'}
            </span>
          </div>
          <div className="pillar-metric">
            <span className="pillar-val">{report.value_investor_pillars.financial_fortress?.debt_payback_years === 0 ? '0 năm (Tiền mặt ròng)' : `${report.value_investor_pillars.financial_fortress?.debt_payback_years} năm`}</span>
            <span className="pillar-sub">Thời gian trả hết Nợ bằng Dòng tiền</span>
          </div>
          <p className="pillar-desc">{report.value_investor_pillars.financial_fortress?.diagnosis}</p>
        </div>

        <div className={`pillar-card pillar-${report.value_investor_pillars.capital_allocation?.status?.toLowerCase() || 'good'}`}>
          <div className="pillar-header">
            <span className="pillar-title">3. Hiệu quả Phân bổ Vốn</span>
            <span className="pillar-badge">
              {report.value_investor_pillars.capital_allocation?.status === 'EXCELLENT' ? 'Xuất sắc' : report.value_investor_pillars.capital_allocation?.status === 'GOOD' ? 'Tốt' : 'Cần chú ý'}
            </span>
          </div>
          <div className="pillar-metric">
            <span className="pillar-val">{report.value_investor_pillars.capital_allocation?.avg_roe_5y != null ? `${report.value_investor_pillars.capital_allocation.avg_roe_5y}%` : '—'}</span>
            <span className="pillar-sub">Sinh lời ROE 5 năm · Pha loãng thực: {report.value_investor_pillars.capital_allocation?.share_dilution_5y_pct != null ? `${report.value_investor_pillars.capital_allocation.share_dilution_5y_pct}%` : '0%'}</span>
          </div>
          <p className="pillar-desc">{report.value_investor_pillars.capital_allocation?.diagnosis}</p>
        </div>
      </div>
    )}

    {/* Collapsed Technical Details (for advanced inspection) */}
    <details className="valuation-technical-details">
      <summary className="technical-summary">
        <span>Chi tiết Tính toán & Bảng Ma trận Độ nhạy Định giá</span>
      </summary>
      <div className="technical-content">
        {/* SOTP Sensitivity Analysis Matrix (Multiple vs Holding Discount) */}
        {report.sotp_sensitivity_matrix?.grid_values_per_share && (
          <div className="tech-section">
            <h4>Bảng Độ nhạy Định giá SOTP theo {report.sotp_sensitivity_matrix.row_label || 'Hệ số Cấu phần'} và {report.sotp_sensitivity_matrix.col_label || 'Chiết khấu Holding'}</h4>
            <div className="sensitivity-matrix-container">
              <table className="sensitivity-matrix-table">
                <thead>
                  <tr>
                    <th>{report.sotp_sensitivity_matrix.row_label} \ {report.sotp_sensitivity_matrix.col_label}</th>
                    {report.sotp_sensitivity_matrix.discount_rates.map(r => (
                      <th key={r} className={Number(r) === 0.15 ? 'th-base-rate' : ''}>{Number(r) * 100}%</th>
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
                          <td key={colIdx} className={isBase ? 'cell-base-case' : ''}>
                            {cellVal > 0 ? `${Math.round(cellVal).toLocaleString('vi-VN')} ₫` : '—'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <small className="matrix-note">
              * Độ nhạy SOTP: Kiểm tra giá trị nội tại khi thay đổi hệ số định giá các mảng liên doanh/cấu phần và tỷ lệ chiết khấu Tập đoàn/Holding.
            </small>
          </div>
        )}

        {/* Sensitivity Analysis Matrix 2D (r vs gT / ROE vs CoE for banks) */}
        {report.sensitivity_matrix?.grid_values_per_share && (
          <div className="tech-section">
            <h4>Bảng Độ nhạy Định giá theo {report.sensitivity_matrix.row_label || 'Tăng trưởng Dài hạn (g)'} và {report.sensitivity_matrix.col_label || 'Tỷ lệ Chiết khấu (r)'}</h4>
            <div className="sensitivity-matrix-container">
              <table className="sensitivity-matrix-table">
                <thead>
                  <tr>
                    <th>{report.sensitivity_matrix.row_label || 'Tăng trưởng (g)'} \ {report.sensitivity_matrix.col_label || 'Chiết khấu (r)'}</th>
                    {report.sensitivity_matrix.discount_rates.map(r => (
                      <th key={r} className={Number(r) === 0.11 ? 'th-base-rate' : ''}>{Number(r) * 100}%</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.sensitivity_matrix.terminal_growth_rates.map((g, rowIdx) => (
                    <tr key={g}>
                      <td><strong>{Number(g) * 100}%</strong></td>
                      {report.sensitivity_matrix.grid_values_per_share[rowIdx].map((cellVal, colIdx) => {
                        const isBase = Number(report.sensitivity_matrix.discount_rates[colIdx]) === 0.11 && Number(g) === 0.035;
                        return (
                          <td key={colIdx} className={isBase ? 'cell-base-case' : ''}>
                            {cellVal > 0 ? `${Math.round(cellVal).toLocaleString('vi-VN')} ₫` : '—'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <small className="matrix-note">
              {report.sensitivity_matrix.sensitivity_type === 'RIM_ROE_COE'
                ? '* Ngân hàng: giá trị theo Mô hình Thu nhập Thặng dư (RIM) với Normalized ROE và Chi phí vốn cổ phần.'
                : '* Ô viền vàng nổi bật là Kịch bản Cơ sở (Chiết khấu 11%, Tăng trưởng dài hạn 3.5%).'}
            </small>
          </div>
        )}

        {/* SOTP Breakdown Table (when available for conglomerates / plantations) */}
        {report.sotp_breakdown?.components?.length > 0 && (
          <div className="tech-section">
            <h4>Bóc tách Từng phần Định giá SOTP (Sum-of-the-Parts Breakdown)</h4>
            <div className="sensitivity-matrix-container">
              <table className="sensitivity-matrix-table" style={{ fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'var(--surface-soft, #f4ecd9)' }}>
                    <th style={{ textAlign: 'left' }}>Cấu phần / Mảng Kinh doanh</th>
                    <th style={{ textAlign: 'center' }}>Phương pháp</th>
                    <th style={{ textAlign: 'right' }}>Giá trị Gộp</th>
                    <th style={{ textAlign: 'center' }}>Sở hữu</th>
                    <th style={{ textAlign: 'right' }}>Giá trị Ròng</th>
                  </tr>
                </thead>
                <tbody>
                  {report.sotp_breakdown.components.map((comp, idx) => (
                    <tr key={idx}>
                      <td style={{ textAlign: 'left', fontWeight: '600' }}>
                        {comp.component_name}
                        {comp.rationale && <div style={{ fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-secondary, #696257)' }}>{comp.rationale}</div>}
                        {comp.formula_trace && <div style={{ fontSize: '0.72rem', color: 'var(--retro-green, #2f6b4d)', marginTop: '2px', fontFamily: 'var(--font-mono-num, monospace)' }}>📐 {comp.formula_trace}</div>}
                      </td>
                      <td style={{ textAlign: 'center', fontSize: '0.8rem' }}><code>{comp.valuation_method}</code></td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono-num, monospace)' }}>{money(comp.gross_value, locale)}</td>
                      <td style={{ textAlign: 'center' }}>{comp.ownership_pct}%</td>
                      <td style={{ textAlign: 'right', fontWeight: '700', fontFamily: 'var(--font-mono-num, monospace)' }}>{money(comp.net_value, locale)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ borderTop: '2px solid var(--retro-border, #9c927f)', fontWeight: '700' }}>
                    <td colSpan={4} style={{ textAlign: 'right' }}>Tổng Giá trị Cấu phần Tài sản:</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono-num, monospace)' }}>{money(report.sotp_breakdown.gross_asset_value, locale)}</td>
                  </tr>
                  <tr style={{ fontWeight: '600', color: 'var(--retro-hanko, #a63f30)' }}>
                    <td colSpan={4} style={{ textAlign: 'right' }}>Khấu trừ Nợ vay ròng (Net Debt):</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono-num, monospace)' }}>−{money(report.sotp_breakdown.total_net_debt, locale)}</td>
                  </tr>
                  <tr style={{ borderTop: '2px solid var(--retro-border, #9c927f)', fontWeight: '700', fontSize: '0.92rem', background: 'var(--surface-soft, #f4ecd9)' }}>
                    <td colSpan={4} style={{ textAlign: 'right' }}>Giá trị Vốn chủ sở hữu (Equity Value):</td>
                    <td style={{ textAlign: 'right', color: 'var(--retro-green, #2f6b4d)', fontFamily: 'var(--font-mono-num, monospace)' }}>{money(report.sotp_breakdown.equity_value, locale)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
            <small className="matrix-note" style={{ display: 'block', marginTop: '6px' }}>
              * Công thức SOTP nghiêm ngặt: Giá trị Cổ đông = Tổng (Cấu phần × Tỷ lệ sở hữu) − Chiết khấu Tập đoàn − Nợ vay ròng.
            </small>
          </div>
        )}

        {/* Holding Cash Quality Card */}
        {report.holding_cash_quality && (
          <div className="tech-section" style={{ background: 'color-mix(in srgb, var(--retro-green, #2f6b4d) 8%, var(--surface-soft, #f4ecd9))', padding: '12px 16px', borderRadius: '4px', borderLeft: '4px solid var(--retro-green, #2f6b4d)' }}>
            <h4 style={{ margin: '0 0 6px 0', color: 'var(--retro-green, #2f6b4d)' }}>💎 {report.holding_cash_quality.assessment}: {report.holding_cash_quality.cash_conversion_rate_pct}% Tỷ lệ Tiền mặt Thực nhận</h4>
            <p style={{ margin: 0, fontSize: '0.86rem', lineHeight: '1.5' }}>{report.holding_cash_quality.note}</p>
          </div>
        )}

        {bridge && bridge.owner_earnings != null && (
          <div className="tech-section">
            <h4>Bóc tách Lợi nhuận Thực của Chủ Doanh nghiệp ({bridge.normalization_method === 'MID_CYCLE_MEDIAN' ? `Chuẩn hóa ${bridge.normalization_years} năm chu kỳ` : 'Năm gần nhất LATEST_FY'})</h4>
            <dl className="valuation-calculation-grid">
              <div><dt>Lợi nhuận sau thuế</dt><dd>{money(bridge.net_income, locale)}</dd></div>
              <div><dt>Khấu hao tài sản</dt><dd>{money(bridge.depreciation_amortization, locale)}</dd></div>
              <div><dt>Đầu tư duy trì nhà xưởng ({bridge.maintenance_capex_confidence === 'LOW' ? 'Proxy Khấu hao' : 'Ước tính Thực'})</dt><dd>{money(bridge.maintenance_capex, locale)}</dd></div>
              {bridge.current_owner_earnings != null && bridge.normalization_method === 'MID_CYCLE_MEDIAN' && (
                <div><dt>Lợi nhuận Thực năm gần nhất (LATEST_FY)</dt><dd>{money(bridge.current_owner_earnings, locale)}</dd></div>
              )}
              <div><dt>{bridge.normalization_method === 'MID_CYCLE_MEDIAN' ? 'Lợi nhuận Thực Chuẩn hóa (Mid-Cycle)' : 'Lợi nhuận Thực tạo ra'}</dt><dd style={{ fontWeight: '700', color: 'var(--retro-green, #2f6b4d)' }}>{money(bridge.owner_earnings, locale)}</dd></div>
            </dl>
            {bridge.formula_description && (
              <small className="matrix-note" style={{ display: 'block', marginTop: '6px' }}>{bridge.formula_description}</small>
            )}
          </div>
        )}

        <div className="tech-section">
          <h4>Dải Kịch bản Giá trị Nội tại (Bear / Base / Bull IV)</h4>
          {pv.verified ? (
          <div className="valuation-scenarios">
            {scenarios.map(name => {
              const scenario = report.scenarios?.[name] || {};
              const labelVn = name === 'BEAR' ? 'Kịch bản Thận trọng (Bear IV)' : name === 'BASE' ? 'Kịch bản Cơ sở (Base IV)' : 'Kịch bản Khả quan (Bull IV)';
              return <div key={name} className={`scenario-card scenario-${name.toLowerCase()}`}>
                <div className="scenario-head">
                  <b>{labelVn}</b>
                  <span>{money(scenario.intrinsic_value_per_share, locale)}</span>
                </div>
                <small>Tăng trưởng dự phóng: {displayNumber(Number(scenario.growth_stage1_rate) * 100, '%')} · Chiết khấu: {displayNumber(Number(scenario.discount_rate) * 100, '%')}</small>
                {scenario.terminal_value_contribution_pct != null && (
                  <small style={{ display: 'block', color: Number(scenario.terminal_value_contribution_pct) > 75 ? 'var(--retro-hanko, #a63f30)' : 'inherit', marginTop: '2px' }}>
                    Tỷ trọng Giá trị cuối kỳ (TV): {displayNumber(scenario.terminal_value_contribution_pct, '%')}
                  </small>
                )}
                {scenario.scenario_warnings?.map((w, idx) => (
                  <small key={idx} style={{ display: 'block', color: 'var(--retro-hanko, #a63f30)', marginTop: '2px' }}>
                    ⚠️ {w}
                  </small>
                ))}
              </div>;
            })}
          </div>
          ) : (
            <p className="matrix-note" role="note">
              Kết quả IV dưới mô hình tham chiếu chỉ phục vụ kiểm toán (AUDIT_ONLY), không dùng để kết luận định giá công khai khi mô hình chưa verified.
            </p>
          )}
        </div>

        {pv.verified && (report.cagr_5y_net_profit != null || report.epv_result?.epv_per_share != null || report.reverse_dcf_result?.verdict) && (
          <div className="tech-section tech-cross-check">
            <h4>Đối chiếu & Kiểm tra Chéo Năng lực Sinh lời</h4>
            {report.cagr_5y_net_profit != null && (
              <p>• <strong>Tốc độ tăng trưởng Lợi nhuận ròng 5 năm qua:</strong> <span className="highlight-pill">+{displayNumber(report.cagr_5y_net_profit, '%')}/năm</span></p>
            )}
            {report.epv_result?.epv_per_share != null && (
              <p>• <strong>Định giá theo Sức kiếm tiền hiện tại (không giả định tăng trưởng):</strong> {money(report.epv_result?.epv_per_share, locale)}/cổ phần.</p>
            )}
            {report.reverse_dcf_result?.verdict && (
              <p>• <strong>Kỳ vọng tăng trưởng ngầm định từ Thị giá:</strong> {report.reverse_dcf_result?.verdict}</p>
            )}
          </div>
        )}

        {Array.isArray(report.financial_history_10y) && report.financial_history_10y.length > 0 && (
          <div className="tech-section">
            <h4>Chuỗi Lịch sử Kết quả Kinh doanh 10 năm ({report.financial_history_10y[0]?.fiscal_year} – {report.financial_history_10y[report.financial_history_10y.length - 1]?.fiscal_year})</h4>
            <div className="history-10y-table-container">
              <table className="history-10y-table">
                <thead>
                  <tr>
                    <th>Năm</th>
                    <th>Lợi nhuận ròng (tỷ đ)</th>
                    <th>Vốn chủ sở hữu (tỷ đ)</th>
                    <th>Sinh lời ROE (%)</th>
                    <th>Tiền từ Kinh doanh (tỷ đ)</th>
                  </tr>
                </thead>
                <tbody>
                  {report.financial_history_10y.slice().reverse().map(row => (
                    <tr key={row.fiscal_year}>
                      <td><strong>{row.fiscal_year}</strong></td>
                      <td>{row.net_profit != null ? Math.round(row.net_profit / 1e9).toLocaleString('vi-VN') : '—'}</td>
                      <td>{row.equity != null ? Math.round(row.equity / 1e9).toLocaleString('vi-VN') : '—'}</td>
                      <td>{row.roe != null ? `${row.roe}%` : '—'}</td>
                      <td>{row.operating_cash_flow != null ? Math.round(row.operating_cash_flow / 1e9).toLocaleString('vi-VN') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </details>

    <footer className="valuation-card-footer">
      <span>Nguồn dữ liệu: Báo cáo Tài chính Kiểm toán ({freshness.provider || multiples.source || 'Sàn chứng khoán'}) · Kỳ BCTC {report.fiscal_period_latest || 'Năm 2025'}</span>
      <span>Thời điểm đồng bộ: {freshness.fetched_at ? new Date(freshness.fetched_at).toLocaleDateString('vi-VN') : 'Mới nhất'}</span>
    </footer>
  </article>;
}

function ValuationSkeletonCard({ symbol }) {
  return <article className="valuation-card valuation-skeleton-card" aria-busy="true">
    <div className="valuation-card-header">
      <div className="valuation-title-group">
        <div className="valuation-symbol-row">
          <h2>{symbol}</h2>
          <span className="skeleton-pill skeleton-anim"></span>
        </div>
        <div className="skeleton-line skeleton-anim" style={{ width: '120px', height: '14px', marginTop: '6px' }}></div>
      </div>
      <span className="skeleton-pill skeleton-anim" style={{ width: '100px', height: '24px' }}></span>
    </div>
    <div className="valuation-price-hero">
      <div className="price-box"><div className="skeleton-line skeleton-anim" style={{ width: '80px', height: '12px' }}></div><div className="skeleton-line skeleton-anim" style={{ width: '110px', height: '28px', marginTop: '8px' }}></div></div>
      <div className="price-box price-box-intrinsic"><div className="skeleton-line skeleton-anim" style={{ width: '80px', height: '12px' }}></div><div className="skeleton-line skeleton-anim" style={{ width: '110px', height: '28px', marginTop: '8px' }}></div></div>
      <div className="price-box price-box-mos"><div className="skeleton-line skeleton-anim" style={{ width: '80px', height: '12px' }}></div><div className="skeleton-line skeleton-anim" style={{ width: '90px', height: '28px', marginTop: '8px' }}></div></div>
    </div>
    <div className="valuation-multiples-ribbon" style={{ opacity: 0.6 }}>
      <div className="metric-chip"><div className="skeleton-line skeleton-anim" style={{ width: '40px', height: '18px' }}></div></div>
      <div className="metric-chip"><div className="skeleton-line skeleton-anim" style={{ width: '40px', height: '18px' }}></div></div>
      <div className="metric-chip"><div className="skeleton-line skeleton-anim" style={{ width: '50px', height: '18px' }}></div></div>
      <div className="metric-chip"><div className="skeleton-line skeleton-anim" style={{ width: '40px', height: '18px' }}></div></div>
    </div>
    <div className="valuation-analyst-opinion" style={{ opacity: 0.5 }}>
      <div className="skeleton-line skeleton-anim" style={{ width: '100%', height: '16px' }}></div>
      <div className="skeleton-line skeleton-anim" style={{ width: '85%', height: '16px', marginTop: '6px' }}></div>
    </div>
  </article>;
}

function ValuationOverviewTable({ reports = {}, symbols = [], selectedSymbol, onSelectSymbol, locale = 'vi' }) {
  const validRows = symbols
    .map(sym => ({ sym, rep: reports[sym] }))
    .filter(item => item.rep);

  if (validRows.length <= 1) return null;

  return (
    <div className="valuation-overview-table-wrapper">
      <div className="valuation-overview-header-row">
        <h3 className="valuation-overview-title">Bảng Tổng quan Định giá Toàn bộ Danh mục ({validRows.length} mã)</h3>
        <span className="valuation-overview-hint">👉 Vuốt ngang xem Giá trị thực (IV) & MOS · Nhấp dòng để soi sâu</span>
      </div>
      <div className="valuation-overview-scroll">

        <table className="valuation-overview-table">
          <thead>
            <tr>
              <th className="th-symbol">Mã CP</th>
              <th>Bản chất Kinh tế</th>
              <th>Mô hình Định giá</th>
              <th style={{ textAlign: 'center' }}>Trạng thái Mô hình</th>
              <th style={{ textAlign: 'right' }}>Thị giá</th>
              <th style={{ textAlign: 'right' }}>Giá trị Thực (Base IV)</th>
              <th style={{ textAlign: 'right' }}>Biên An Toàn (MOS)</th>
              <th style={{ textAlign: 'center' }}>Kết luận</th>
            </tr>
          </thead>
          <tbody>
            {validRows.map(({ sym, rep }) => {
              const pv = publicValuation(rep);
              const base = { intrinsic_value_per_share: pv.base };
              const mos = pv.mos;
              const archName = archetypeLabel(rep.archetype_profile?.archetype);
              const modelName = valuationModelLabel(rep.valuation_model || rep.archetype_profile?.recommended_model);
              const mStatus = modelStatusLabel(rep.model_status);
              const isSelected = sym === selectedSymbol;
              return (
                <tr
                  key={sym}
                  className={`row-interactive ${isSelected ? 'row-selected' : ''}`}
                  onClick={() => onSelectSymbol?.(sym)}
                  title={`Nhấp để xem chi tiết ${sym}`}
                >
                  <td className="td-symbol">
                    <span className="symbol-cell-content">
                      <strong>{sym}</strong>
                      {isSelected && <span className="selected-indicator-dot" title="Đang xem mã này">●</span>}
                    </span>
                  </td>
                  <td className="td-arch">{archName}</td>
                  <td className="td-model">{modelName}</td>
                  <td className="td-status" style={{ textAlign: 'center' }}>
                    <span className={`model-status-badge ${rep.model_status === 'MODEL_VERIFIED' ? 'status-verified' : 'status-incomplete'}`}>
                      {mStatus}
                    </span>
                  </td>
                  <td className="td-num" style={{ textAlign: 'right' }}>{money(rep.current_market_price, locale)}</td>
                  <td className="td-num td-iv" style={{ textAlign: 'right' }}>{money(base.intrinsic_value_per_share, locale)}</td>
                  <td className="td-num" style={{ textAlign: 'right', fontWeight: '700', color: mos > 0 ? 'var(--retro-green, #2f6b4d)' : mos < 0 ? 'var(--retro-hanko, #a63f30)' : 'inherit' }}>
                    {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <ValuationStatusPill status={rep.assessment?.valuation_status} marginOfSafety={mos} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ValuationTickerDock({ symbols = [], reports = {}, selectedSymbol, onSelectSymbol, viewMode, onToggleViewMode }) {
  if (!symbols.length) return null;

  return (
    <div className="valuation-ticker-dock">
      <div className="ticker-dock-left">
        <span className="ticker-dock-label">Chọn mã soi sâu:</span>
        <div className="ticker-pills-list">
          {symbols.map(sym => {
            const rep = reports[sym];
            const mos = publicValuation(rep).mos;
            const isSelected = sym === selectedSymbol && viewMode === 'focus';
            const mosClass = mos > 0 ? 'pos' : mos < 0 ? 'neg' : '';
            return (
              <button
                key={sym}
                type="button"
                className={`ticker-pill-btn ${isSelected ? 'active' : ''}`}
                onClick={() => onSelectSymbol(sym)}
                title={`Xem chi tiết định giá ${sym}`}
              >
                <span className="ticker-pill-sym">{sym}</span>
                {mos != null && Number.isFinite(Number(mos)) && (
                  <span className={`ticker-pill-mos ${mosClass}`}>
                    {mos > 0 ? '+' : ''}{Number(mos).toFixed(0)}%
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="view-mode-toggle-group">
        <button
          type="button"
          className={`view-mode-btn ${viewMode === 'focus' ? 'active' : ''}`}
          onClick={() => onToggleViewMode('focus')}
          title="Chỉ hiển thị thẻ phân tích chi tiết của 1 mã được chọn (Gọn gàng, không phải cuộn nhiều)"
        >
          🎯 Soi 1 mã (Gọn)
        </button>
        <button
          type="button"
          className={`view-mode-btn ${viewMode === 'all' ? 'active' : ''}`}
          onClick={() => onToggleViewMode('all')}
          title="Hiển thị thẻ phân tích của toàn bộ danh mục nối tiếp nhau"
        >
          📑 Xem tất cả ({symbols.length})
        </button>
      </div>
    </div>
  );
}

function MobileValuationView({
  symbols = [],
  reports = {},
  errors = {},
  selectedSymbol,
  onSelectSymbol,
  loading,
  locale = 'vi',
  onExportAI,
  onRefresh,
  exporting,
  exportMsg
}) {
  const [mobileTab, setMobileTab] = useState('list'); // 'list' | 'detail' | 'methodology'

  const currentIdx = symbols.indexOf(selectedSymbol);
  const prevSymbol = currentIdx > 0 ? symbols[currentIdx - 1] : null;
  const nextSymbol = currentIdx >= 0 && currentIdx < symbols.length - 1 ? symbols[currentIdx + 1] : null;

  const handleCardClick = (sym) => {
    onSelectSymbol(sym);
    setMobileTab('detail');
  };

  return (
    <div className="mobile-valuation-shell">
      {/* Mobile Top Header */}
      <div className="mobile-valuation-topbar">
        <div className="mobile-valuation-title-wrap">
          <span className="mobile-eyebrow">Định giá Giá trị Thực</span>
          <h2>Định giá Cổ phiếu</h2>
        </div>
        <div className="mobile-topbar-actions">
          <button
            type="button"
            className="mobile-btn-action"
            onClick={onExportAI}
            disabled={exporting || loading || !symbols.length}
            title="Xuất báo cáo AI"
          >
            {exporting ? '⏳' : '📥 AI'}
          </button>
          <button
            type="button"
            className="mobile-btn-action"
            onClick={onRefresh}
            disabled={loading || !symbols.length}
            title="Làm mới dữ liệu"
          >
            {loading ? '⏳' : '↻'}
          </button>
        </div>
      </div>

      {exportMsg && (
        <div className="mobile-export-toast">
          {exportMsg}
        </div>
      )}

      {/* Mobile Segmented Navigation Tab Bar */}
      <div className="mobile-segmented-tabbar">
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'list' ? 'active' : ''}`}
          onClick={() => setMobileTab('list')}
        >
          <span className="tab-icon">📋</span> Danh mục ({symbols.length})
        </button>
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'detail' ? 'active' : ''}`}
          onClick={() => setMobileTab('detail')}
        >
          <span className="tab-icon">🎯</span> Soi {selectedSymbol || 'Chi tiết'}
        </button>
        <button
          type="button"
          className={`mobile-tab-btn ${mobileTab === 'methodology' ? 'active' : ''}`}
          onClick={() => setMobileTab('methodology')}
        >
          <span className="tab-icon">📖</span> Nguyên lý
        </button>
      </div>

      {/* Tab Content 1: Mobile Stock Cards Screener */}
      {mobileTab === 'list' && (
        <div className="mobile-cards-list-view">
          <div className="mobile-list-summary-bar">
            <span>Chạm vào mã để mở phân tích chi tiết:</span>
          </div>

          <div className="mobile-stock-cards-container">
            {symbols.map(sym => {
              const rep = reports[sym];
              const err = errors[sym];
              const pv = publicValuation(rep || {});
              const base = { intrinsic_value_per_share: pv.base };
              const mos = pv.mos;
              const quality = rep?.quality_scorecard || {};
              const multiples = rep?.valuation_multiples || {};
              const isSelected = sym === selectedSymbol;

              if (err) {
                return (
                  <div key={sym} className="mobile-stock-card card-error" onClick={() => handleCardClick(sym)}>
                    <div className="mobile-card-head">
                      <span className="mobile-sym">{sym}</span>
                      <span className="valuation-badge-error">Lỗi dữ liệu</span>
                    </div>
                    <p className="mobile-card-err-msg">{err.message}</p>
                  </div>
                );
              }

              if (loading && !rep) {
                return (
                  <div key={sym} className="mobile-stock-card skeleton-card">
                    <div className="skeleton-line" style={{ width: '80px', height: '20px' }}></div>
                    <div className="skeleton-line" style={{ width: '100%', height: '36px', marginTop: '8px' }}></div>
                  </div>
                );
              }

              return (
                <div
                  key={sym}
                  className={`mobile-stock-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleCardClick(sym)}
                >
                  <div className="mobile-card-head">
                    <div className="mobile-card-title-col">
                      <span className="mobile-sym">{sym}</span>
                      <span className="mobile-sector">{multiples.sector || archetypeLabel(rep?.archetype_profile?.archetype)}</span>
                    </div>
                    <ValuationStatusPill status={rep?.assessment?.valuation_status} marginOfSafety={mos} />
                  </div>

                  <div className="mobile-card-price-grid">
                    <div className="mobile-price-item">
                      <span className="label">Thị giá</span>
                      <span className="value">{money(rep?.current_market_price, locale)}</span>
                    </div>
                    <div className="mobile-price-item item-intrinsic">
                      <span className="label">Giá trị Thực (IV)</span>
                      <span className="value highlight">{money(base.intrinsic_value_per_share, locale)}</span>
                    </div>
                    <div className="mobile-price-item item-mos">
                      <span className="label">Biên an toàn</span>
                      <span className={`value ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
                        {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
                      </span>
                    </div>
                  </div>

                  <div className="mobile-card-footer">
                    <div className="mobile-card-badges">
                      {quality.total_score != null && (
                        <span className="mobile-quality-badge">
                          Chất lượng: <strong>{quality.total_score}/100</strong>
                        </span>
                      )}
                      <span className="mobile-model-badge">
                        {valuationModelLabel(rep?.valuation_model || rep?.archetype_profile?.recommended_model)}
                      </span>
                    </div>
                    <span className="mobile-tap-chevron">Chi tiết ›</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab Content 2: Mobile Deep-Dive Detail View */}
      {mobileTab === 'detail' && (
        <div className="mobile-detail-view">
          <div className="mobile-detail-nav-dock">
            <div className="mobile-ticker-pills-row">
              {symbols.map(sym => {
                const rep = reports[sym];
                const mos = publicValuation(rep || {}).mos;
                const isSelected = sym === selectedSymbol;
                const mosClass = mos > 0 ? 'pos' : mos < 0 ? 'neg' : '';
                return (
                  <button
                    key={sym}
                    type="button"
                    className={`mobile-ticker-pill ${isSelected ? 'active' : ''}`}
                    onClick={() => onSelectSymbol(sym)}
                  >
                    <span className="pill-sym">{sym}</span>
                    {mos != null && Number.isFinite(Number(mos)) && (
                      <span className={`pill-mos ${mosClass}`}>
                        {mos > 0 ? '+' : ''}{Number(mos).toFixed(0)}%
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            <div className="mobile-nav-step-row">
              <button
                type="button"
                className="mobile-step-btn"
                disabled={!prevSymbol}
                onClick={() => onSelectSymbol(prevSymbol)}
              >
                ◀ {prevSymbol || 'Đầu'}
              </button>
              <span className="mobile-step-indicator">{currentIdx + 1}/{symbols.length}</span>
              <button
                type="button"
                className="mobile-step-btn"
                disabled={!nextSymbol}
                onClick={() => onSelectSymbol(nextSymbol)}
              >
                {nextSymbol || 'Cuối'} ▶
              </button>
            </div>
          </div>

          {selectedSymbol && (
            loading && !reports[selectedSymbol] && !errors[selectedSymbol] ? (
              <ValuationSkeletonCard symbol={selectedSymbol} />
            ) : (
              <ValuationCard
                key={selectedSymbol}
                symbol={selectedSymbol}
                report={reports[selectedSymbol]}
                error={errors[selectedSymbol]}
                locale={locale}
              />
            )
          )}
        </div>
      )}

      {/* Tab Content 3: Mobile Methodology */}
      {mobileTab === 'methodology' && (
        <div className="mobile-methodology-view">
          <MethodologyGuide />
        </div>
      )}
    </div>
  );
}

export default function ValuationPage({ symbols = [], locale = 'vi' }) {
  const normalized = useMemo(() => [...new Set(symbols.map(value => String(value || '').toUpperCase()).filter(Boolean))], [symbols]);
  const symbolKey = normalized.join(',');
  const [reports, setReports] = useState({});
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [viewMode, setViewMode] = useState('focus'); // 'focus' (master-detail) | 'all'

  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState('');

  // Synchronize selectedSymbol when symbols list changes
  useEffect(() => {
    if (normalized.length > 0) {
      if (!selectedSymbol || !normalized.includes(selectedSymbol)) {
        setSelectedSymbol(normalized[0]);
      }
    } else {
      setSelectedSymbol(null);
    }
  }, [normalized, selectedSymbol]);

  const activeSelectedSymbol = (selectedSymbol && normalized.includes(selectedSymbol)) ? selectedSymbol : (normalized[0] || null);

  const handleSelectSymbol = (sym) => {
    setSelectedSymbol(sym);
    setViewMode('focus');
  };

  async function exportForAI() {
    setExporting(true);
    setExportMsg('');
    try {
      const filename = await downloadAIExport();
      setExportMsg(`Đã tạo ${filename}. Báo cáo chứa đầy đủ BCTC 10 năm, định giá DCF/EPV, chỉ số chất lượng & ma trận độ nhạy.`);
      setTimeout(() => setExportMsg(''), 6000);
    } catch (error) {
      setExportMsg(`Không thể xuất báo cáo: ${error.message}`);
    } finally {
      setExporting(false);
    }
  }

  async function load() {
    if (!normalized.length) return;
    setLoading(true);
    try {
      const result = await getValuationReports(normalized);
      setReports(result.reports);
      setErrors(result.errors);
    } catch (error) {
      setErrors(Object.fromEntries(normalized.map(symbol => [
        symbol,
        { code: error?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: error?.message || 'Không thể tải dữ liệu định giá.' },
      ])));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    if (!normalized.length) return undefined;
    setLoading(true);
    getValuationReports(normalized)
      .then(result => {
        if (!active) return;
        setReports(result.reports);
        setErrors(result.errors);
      })
      .catch(error => {
        if (!active) return;
        setErrors(Object.fromEntries(normalized.map(symbol => [
          symbol,
          { code: error?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: error?.message || 'Không thể tải dữ liệu định giá.' },
        ])));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [symbolKey]);

  const currentIdx = normalized.indexOf(activeSelectedSymbol);
  const prevSymbol = currentIdx > 0 ? normalized[currentIdx - 1] : null;
  const nextSymbol = currentIdx >= 0 && currentIdx < normalized.length - 1 ? normalized[currentIdx + 1] : null;

  return (
    <div className="page valuation-page-shell">
      <AppNav active="valuation" locale={locale} />
      <main className="valuation-page">
        {/* Dedicated Mobile View (<720px) */}
        <div className="valuation-mobile-container">
          <MobileValuationView
            symbols={normalized}
            reports={reports}
            errors={errors}
            selectedSymbol={activeSelectedSymbol}
            onSelectSymbol={handleSelectSymbol}
            loading={loading}
            locale={locale}
            onExportAI={exportForAI}
            onRefresh={load}
            exporting={exporting}
            exportMsg={exportMsg}
          />
        </div>

        {/* Dedicated Desktop View (>=720px) */}
        <div className="valuation-desktop-container">
          <header className="valuation-header">
            <div>
              <span className="eyebrow">BCTC mới nhất theo từng mã</span>
              <h1>Định giá cổ phiếu</h1>
              <p>Mô hình chiết khấu dòng tiền kết hợp lợi nhuận thực của chủ doanh nghiệp. Phân tích khách quan theo nguyên lý Giá trị cốt lõi.</p>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button type="button" className="btn-primary" onClick={exportForAI} disabled={exporting || loading || !normalized.length}>
                {exporting ? 'Đang xuất…' : '📥 Xuất báo cáo cho AI'}
              </button>
              <button type="button" className="btn-secondary" onClick={load} disabled={loading || !normalized.length}>
                {loading ? 'Đang tải…' : '↻ Làm mới dữ liệu'}
              </button>
            </div>
          </header>

          {exportMsg && (
            <div style={{
              padding: '10px 14px',
              marginBottom: '16px',
              background: 'var(--surface-soft, #f4ecd9)',
              border: '1px solid var(--retro-border, #9c927f)',
              borderRadius: '2px',
              fontSize: '0.84rem',
              color: 'var(--retro-green, #2f6b4d)',
              fontWeight: '600',
            }}>
              {exportMsg}
            </div>
          )}

          <MethodologyGuide />

          {!normalized.length ? (
            <div className="empty-state">Danh mục chưa có cổ phiếu để định giá.</div>
          ) : (
            <>
              <ValuationOverviewTable
                reports={reports}
                symbols={normalized}
                selectedSymbol={activeSelectedSymbol}
                onSelectSymbol={handleSelectSymbol}
                locale={locale}
              />

              <ValuationTickerDock
                symbols={normalized}
                reports={reports}
                selectedSymbol={activeSelectedSymbol}
                onSelectSymbol={handleSelectSymbol}
                viewMode={viewMode}
                onToggleViewMode={setViewMode}
              />

              {viewMode === 'focus' && activeSelectedSymbol ? (
                <div className="master-detail-stage">
                  <div className="master-detail-stage-header">
                    <div className="stage-title">
                      <span>🎯 Phân tích Chi tiết: <strong>{activeSelectedSymbol}</strong></span>
                      <span className="stage-index-badge">Mã {currentIdx + 1}/{normalized.length}</span>
                    </div>
                    <div className="stage-nav-btns">
                      <button
                        type="button"
                        className="btn-nav-step"
                        disabled={!prevSymbol}
                        onClick={() => setSelectedSymbol(prevSymbol)}
                        title={prevSymbol ? `Chuyển sang ${prevSymbol}` : ''}
                      >
                        ◀ {prevSymbol || 'Đầu danh sách'}
                      </button>
                      <button
                        type="button"
                        className="btn-nav-step"
                        disabled={!nextSymbol}
                        onClick={() => setSelectedSymbol(nextSymbol)}
                        title={nextSymbol ? `Chuyển sang ${nextSymbol}` : ''}
                      >
                        {nextSymbol || 'Cuối danh sách'} ▶
                      </button>
                    </div>
                  </div>

                  {loading && !reports[activeSelectedSymbol] && !errors[activeSelectedSymbol] ? (
                    <ValuationSkeletonCard symbol={activeSelectedSymbol} />
                  ) : (
                    <ValuationCard
                      key={activeSelectedSymbol}
                      symbol={activeSelectedSymbol}
                      report={reports[activeSelectedSymbol]}
                      error={errors[activeSelectedSymbol]}
                      locale={locale}
                    />
                  )}
                </div>
              ) : (
                <div className="valuation-grid">
                  {normalized.map(symbol => {
                    if (loading && !reports[symbol] && !errors[symbol]) {
                      return <ValuationSkeletonCard key={symbol} symbol={symbol} />;
                    }
                    return <ValuationCard key={symbol} symbol={symbol} report={reports[symbol]} error={errors[symbol]} locale={locale} />;
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

