import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import {
  ValuationSkeletonCard,
  ValuationStatusPill,
  HistoricalResolutionsBlock,
  ValuationRationale,
} from '../components/ValuationDetailOverlay.jsx';
import { getValuationReports } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { displayNumber, formatMoney, money } from '../lib/format.js';
import {
  archetypeLabel,
  valuationModelLabel,
} from '../lib/valuationLabels.js';



function MethodologyGuide() {
  return <details className="valuation-methodology" open={false}>
    <summary className="valuation-methodology-summary">
      <span className="eyebrow">Nguyên lý Đầu tư Giá trị Buffett–Munger</span>
      <b>QPort xác định Giá trị Thực của doanh nghiệp như thế nào?</b>
    </summary>
    <div className="valuation-method-grid">
      <article>
        <b>01 · Phân loại Bản chất Kinh tế & Chuẩn hóa 10 năm</b>
        <p>Phân loại doanh nghiệp vào 40 mô hình kinh tế đặc thù (Ngân hàng, BĐS KCN, Hàng hóa chu kỳ, Tiện ích hữu hạn, Tiêu dùng thiết yếu...). Dữ liệu BCTC 10 năm được chuẩn hóa trung vị chu kỳ (Mid-Cycle Median) để loại bỏ nhiễu đỉnh/đáy.</p>
      </article>
      <article>
        <b>02 · Bóc tách Dòng tiền & Bản chất Sinh lợi Thực</b>
        <p>Bóc tách dòng tiền thực tế theo đặc thù ngành: Lợi nhuận Thực của Chủ Doanh nghiệp (Dòng tiền Thực tế), Dòng tiền Hợp đồng Thuê đất & Doanh thu chưa thực hiện (BĐS KCN), Dòng tiền Khai thác Hữu hạn (Concession) hoặc Thu nhập Thặng dư (RIM Ngân hàng).</p>
      </article>
      <article>
        <b>03 · Định tuyến Mô hình Chuyên biệt & Dải 3 Kịch bản</b>
        <p>Định tuyến tự động sang mô hình chuẩn: RIM cho Ngân hàng; Lease DCF/RNAV cho BĐS KCN (IDC, BCM); Concession DCF (TV = 0) cho Hạ tầng & Tiện ích (GAS, POW); Chiết khấu dòng tiền DCF chu kỳ cho Sản xuất. Thiết lập 3 Kịch bản: Thận trọng (Bear IV) / Cơ sở (Base IV) / Khả quan (Bull IV).</p>
      </article>
      <article>
        <b>04 · Thước đo Biên An Toàn Động & 16 Lớp Rủi ro</b>
        <p>Biên an toàn được tính toán động (20% – 50%) kết hợp 16 lớp phủ kinh tế (tính chu kỳ, thâm dụng vốn, chi phối nhà nước, nhạy cảm hàng hóa, đòn bẩy...), đảm bảo nguyên tắc bảo vệ vốn và Margin of Safety nghiêm ngặt.</p>
      </article>
    </div>
    <p className="valuation-method-warning">Dữ liệu tài chính được chuẩn hóa từ nguồn chính thức của sàn chứng khoán. Hệ thống phục vụ mục đích thông tin và theo dõi danh mục dài hạn (Buy & Hold).</p>
  </details>;
}

function ValuationCard({ symbol, report, error, locale }) {
  if (error) return <article id={`valuation-${symbol}`} className="valuation-card valuation-card-error">
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
  const base = report.scenarios?.BASE || {};
  const bear = report.scenarios?.BEAR || {};
  const bull = report.scenarios?.BULL || {};
  const bridge = report.owner_earnings_bridge || {};
  const assessment = report.assessment || {};
  const quality = report.quality_scorecard || {};
  const mosAnalysis = report.margin_of_safety_analysis || {};
  const scenarios = ['BEAR', 'BASE', 'BULL'];
  const freshness = report.data_freshness || {};
  const mos = base.margin_of_safety_pct;

  // Feedback 31/08: doanh nghiệp không đạt chuẩn Buffett (chất lượng quá thấp,
  // hard reject, hoặc mô hình chưa xác thực) -> KHÔNG hiển thị section chi tiết
  // định giá, chỉ đưa ra cảnh báo + nguyên nhân.
  const isQualified = report.model_status === 'MODEL_VERIFIED'
    && !report.valuation_warning
    && report.public_base_iv != null
    && Number(report.public_base_iv) > 0;
  if (!isQualified) {
    const hardRejects = quality.hard_rejects || [];
    const reason = report.valuation_warning || (
      report.model_status === 'MODEL_VERIFIED'
        ? 'Điểm chất lượng hoặc dữ liệu chưa đạt chuẩn Buffett/Munger; Giá trị Thực (IV) và Biên An Toàn (MOS) không được công bố.'
        : `Mô hình định giá chưa được xác thực (${report.model_status || 'chưa verified'}): thiếu dữ liệu mô hình đặc thù nên chưa thể công bố định giá chi tiết.`
    );
    return <article id={`valuation-${symbol}`} className="valuation-card valuation-card-blocked">
      <div className="valuation-card-header">
        <div className="valuation-title-group">
          <div className="valuation-symbol-row">
            <h2>{symbol}</h2>
            <span className="valuation-sector-tag">{multiples.sector || 'Doanh nghiệp niêm yết'}</span>
            {quality.total_score != null && (
              <span className="valuation-sector-tag" style={{ background: 'var(--surface-soft, var(--panel-2))', borderColor: 'var(--border)', color: 'var(--text)' }}>
                Điểm Chất lượng: {quality.total_score}/100 ({quality.tier === 'EXCEPTIONAL' ? 'Xuất sắc' : quality.tier === 'HIGH_QUALITY' ? 'Chất lượng cao' : quality.tier === 'INVESTABLE' ? 'Đạt chuẩn đầu tư' : quality.tier === 'WATCH' ? 'Theo dõi' : 'Thấp'})
              </span>
            )}
          </div>
          <p className="valuation-period-subtitle">Kỳ Báo cáo Tài chính: <strong>{report.fiscal_period_latest || 'Năm 2025'}</strong></p>
        </div>
        <div>
          <ValuationStatusPill status={assessment.valuation_status} />
        </div>
      </div>

      <div className="valuation-warning-banner" role="alert">
        <span className="valuation-warning-icon">⚠️</span>
        <div className="valuation-warning-text">
          <b>KHÔNG CÔNG BỐ GIÁ TRỊ THỰC (IV) & BIÊN AN TOÀN (MOS)</b>
          <p>{reason}</p>
        </div>
      </div>

      {/* Vẫn hiển thị hệ số định giá cơ bản (P/E, P/B, EPS, ROE) cho mã chất lượng thấp */}
      {(multiples.pe != null || multiples.pb != null || multiples.eps != null || multiples.roe != null) && (
        <div className="valuation-multiples-ribbon">
          <div className="metric-chip" title="P/E: Giá trên Lợi nhuận mỗi cổ phần">
            <span className="chip-label">P/E (Giá/LNST)</span>
            <span className="chip-value">{multiples.pe != null ? displayNumber(multiples.pe, ' lần') : '—'}</span>
          </div>
          <div className="metric-chip" title="P/B: Giá trên Giá trị sổ sách mỗi cổ phần">
            <span className="chip-label">P/B (Giá/Sổ sách)</span>
            <span className="chip-value">{multiples.pb != null ? displayNumber(multiples.pb, ' lần', 2) : '—'}</span>
          </div>
          <div className="metric-chip" title="EPS: Lợi nhuận sau thuế tạo ra trên mỗi cổ phần">
            <span className="chip-label">Lợi nhuận/CP (EPS)</span>
            <span className="chip-value">{multiples.eps == null ? '—' : `${formatMoney(multiples.eps, false, locale)} ₫`}</span>
          </div>
          <div className="metric-chip" title="ROE: Tỷ suất sinh lời trên Vốn chủ sở hữu">
            <span className="chip-label">Sinh lời Vốn (ROE)</span>
            <span className="chip-value">{multiples.roe != null ? displayNumber(multiples.roe, '%') : '—'}</span>
          </div>
        </div>
      )}

      {hardRejects.length > 0 && (
        <div className="valuation-hard-rejects">
          <b>Lý do chặn định giá:</b>
          <ul>
            {hardRejects.map(reasonItem => <li key={reasonItem}>{reasonItem}</li>)}
          </ul>
        </div>
      )}

      {/* Dữ liệu cần thiết để hoàn thiện mô hình (khi block do thiếu dữ liệu) */}
      {!report.valuation_warning && Array.isArray(report.missing_data) && report.missing_data.length > 0 && (
        <div className="valuation-missing-data">
          <div className="valuation-missing-header">
            <span className="valuation-missing-icon" aria-hidden="true">📋</span>
            <div>
              <b>DỮ LIỆU CẦN THIẾT ĐỂ ĐỊNH GIÁ {symbol}</b>
              <span className="valuation-missing-sub">
                Cần bổ sung để hoàn thiện mô hình {valuationModelLabel(report.valuation_model || report.archetype_profile?.recommended_model)}
              </span>
            </div>
          </div>
          <ul className="valuation-missing-list">
            {report.missing_data.map(item => (
              <li key={item}>
                <span className="valuation-missing-bullet">▸</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="valuation-blocked-note">
        QPort chỉ công bố phần định giá chi tiết (Giá trị Thực, Biên An Toàn, các kịch bản Bear/Base/Bull,
        Mô hình Định giá, Ma trận độ nhạy) cho doanh nghiệp đạt chuẩn chất lượng Buffett/Munger.
        Doanh nghiệp này chưa đạt chuẩn nên phần định giá chi tiết không được hiển thị.
      </div>

      {/* feedback.txt — Regime Engine: phân loại lịch sử + window chuẩn hóa */}
      <HistoricalResolutionsBlock report={report} locale={locale} />
    </article>;
  }

  return <article id={`valuation-${symbol}`} className="valuation-card">
    <div className="valuation-card-header">
      <div className="valuation-title-group">
        <div className="valuation-symbol-row">
          <h2>{symbol}</h2>
          <span className="valuation-sector-tag">{multiples.sector || 'Doanh nghiệp niêm yết'}</span>
          {quality.total_score != null && (
            <span className="valuation-sector-tag" style={{ background: 'var(--surface-soft, var(--panel-2))', borderColor: 'var(--border)', color: 'var(--text)' }}>
              Điểm Chất lượng: {quality.total_score}/100 ({quality.tier === 'EXCEPTIONAL' ? 'Xuất sắc' : quality.tier === 'HIGH_QUALITY' ? 'Chất lượng cao' : quality.tier === 'INVESTABLE' ? 'Đạt chuẩn đầu tư' : quality.tier === 'WATCH' ? 'Theo dõi' : 'Thấp'})
            </span>
          )}
        </div>
        <p className="valuation-period-subtitle">Kỳ Báo cáo Tài chính: <strong>{report.fiscal_period_latest || 'Năm 2025'}</strong></p>
      </div>
      <div>
        <ValuationStatusPill status={assessment.valuation_status} marginOfSafety={mos} />
      </div>
    </div>

    {/* Primary Price & Valuation Row */}
    <div className="valuation-price-hero">
      <div className="price-box">
        <div className="price-box-head">
          <span className="price-label">Thị giá hiện tại</span>
          <span className="price-source-tag">VNDirect</span>
        </div>
        <span className="price-value">{money(report.current_market_price, locale)}</span>
        <span className="price-footnote">Giá thị trường khớp lệnh</span>
      </div>

      <div className="price-box price-box-intrinsic">
        <div className="price-box-head">
          <span className="price-label">Giá trị Thực cơ sở</span>
          <span className="price-highlight-tag">Định giá cốt lõi</span>
        </div>
        <span className="price-value highlight">{money(base.intrinsic_value_per_share, locale)}</span>
        <span className="price-footnote">Mô hình {valuationModelLabel(report.valuation_model || report.archetype_profile?.recommended_model)}</span>
      </div>

      <div className="price-box price-box-mos">
        <div className="price-box-head">
          <span className="price-label">Biên An Toàn Thực tế</span>
          {mosAnalysis.required_mos_pct != null && (
            <span className="price-req-tag">Yêu cầu: ≥{mosAnalysis.required_mos_pct}%</span>
          )}
        </div>
        <span className={`price-value ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
          {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
        </span>
        <span className="price-footnote">
          {mos != null && mos >= (mosAnalysis.required_mos_pct || 25) ? '✓ Đạt biên độ an toàn bảo vệ vốn' : 'Biên an toàn hiện tại'}
        </span>
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

    {/* Expert Financial Analysis Executive Dashboard */}
    <div className="valuation-analyst-opinion">
      <div className="opinion-header">
        <div className="opinion-badge-wrap">
          <span className="opinion-seal">📜</span>
          <span className="opinion-badge">Nhận định Chuyên sâu theo Chuẩn Buffett–Munger</span>
        </div>
        <span className={`opinion-status-pill ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
          {assessment.valuation_status === 'DEEP_VALUE' ? 'Biên an toàn rất cao'
            : assessment.valuation_status === 'UNDERVALUED' ? 'Định giá Hấp dẫn'
            : assessment.valuation_status === 'FAIR_VALUE' ? 'Định giá Hợp lý'
            : assessment.valuation_status === 'OVERVALUED' ? 'Định giá Cao'
            : 'Cần theo dõi'}
        </span>
      </div>

      {/* 4-Stat Executive Summary Strip */}
      <div className="opinion-executive-grid">
        <div className="opinion-stat-item">
          <span className="opinion-stat-label">Bản chất Doanh nghiệp</span>
          <span className="opinion-stat-val">
            {archetypeLabel(report.archetype_profile?.archetype)}
          </span>
          <span className="opinion-stat-sub">
            Mô hình: {valuationModelLabel(report.valuation_model || report.archetype_profile?.recommended_model)}
          </span>
        </div>

        <div className="opinion-stat-item">
          <span className="opinion-stat-label">Dải Định giá (Bear – Bull)</span>
          <span className="opinion-stat-val highlight">
            {bear.intrinsic_value_per_share != null ? money(bear.intrinsic_value_per_share, locale) : '—'} – {bull.intrinsic_value_per_share != null ? money(bull.intrinsic_value_per_share, locale) : '—'}
          </span>
          <span className="opinion-stat-sub">
            Cơ sở: <strong>{money(base.intrinsic_value_per_share, locale)}</strong>
          </span>
        </div>

        <div className="opinion-stat-item">
          <span className="opinion-stat-label">Biên An toàn Thực tế</span>
          <span className={`opinion-stat-val ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
            {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
          </span>
          <span className="opinion-stat-sub">
            Yêu cầu tối thiểu: ≥ {mosAnalysis.required_mos_pct || 25}%
          </span>
        </div>

        <div className="opinion-stat-item">
          <span className="opinion-stat-label">Chất lượng Doanh nghiệp</span>
          <span className="opinion-stat-val">
            {quality.total_score != null ? `${quality.total_score}/100` : '—'}
          </span>
          <span className="opinion-stat-sub">
            Hạng: <strong>{quality.tier === 'EXCEPTIONAL' ? 'Xuất sắc' : quality.tier === 'HIGH_QUALITY' ? 'Chất lượng cao' : quality.tier === 'INVESTABLE' ? 'Đạt chuẩn' : 'Cần theo dõi'}</strong>
          </span>
        </div>
      </div>

      {/* Strategic / Structural Financial Insight */}
      {assessment.financial_resilience_diagnosis && (
        <div className="opinion-subtext">
          <span className="opinion-subtext-icon">💡</span>
          <div className="opinion-subtext-body">
            <strong>Cấu trúc Vốn & Đặc thù Kinh tế:</strong> {assessment.financial_resilience_diagnosis}
          </div>
        </div>
      )}
    </div>

    {/* Value Investor Health Pillars (Miller's Law - 3 Focused Cards) */}
    {report.value_investor_pillars && (
      <div className="valuation-pillars-grid">
        <div className={`pillar-card pillar-${report.value_investor_pillars.earnings_quality?.status?.toLowerCase() || 'watch'}`}>
          <div className="pillar-header">
            <span className="pillar-num">01</span>
            <span className="pillar-title">Chất lượng Tiền mặt</span>
            <span className="pillar-badge">
              {report.value_investor_pillars.earnings_quality?.status === 'EXCEPTIONAL' ? 'Xuất sắc' : report.value_investor_pillars.earnings_quality?.status === 'GOOD' ? 'Tốt' : 'Cần chú ý'}
            </span>
          </div>
          <div className="pillar-metric">
            <span className="pillar-val">{report.value_investor_pillars.earnings_quality?.avg_cash_conversion_5y != null ? `${report.value_investor_pillars.earnings_quality.avg_cash_conversion_5y}%` : (report.value_investor_pillars.earnings_quality?.avg_roe_5y != null ? `${report.value_investor_pillars.earnings_quality.avg_roe_5y}%` : '—')}</span>
            <span className="pillar-sub">{report.value_investor_pillars.earnings_quality?.avg_cash_conversion_5y != null ? 'LNST → Tiền mặt (bình quân 5 năm)' : 'ROE chu kỳ 5 năm (tổ chức tài chính)'}</span>
          </div>
          <div className="pillar-metric-list">
            {report.value_investor_pillars.earnings_quality?.latest_cash_conversion != null && (
              <div className="pillar-metric-item">
                <span className="pm-label">Chuyển hóa LNST→Tiền mặt (Năm gần nhất)</span>
                <span className="pm-val">{report.value_investor_pillars.earnings_quality.latest_cash_conversion}%</span>
              </div>
            )}
            {report.value_investor_pillars.earnings_quality?.avg_cash_conversion_5y != null && (
              <div className="pillar-metric-item">
                <span className="pm-label">≥90% chuẩn Xuất sắc · ≥70% Tốt</span>
                <span className="pm-val">{report.value_investor_pillars.earnings_quality.avg_cash_conversion_5y >= 90 ? '✓ Xuất sắc' : report.value_investor_pillars.earnings_quality.avg_cash_conversion_5y >= 70 ? '✓ Tốt' : '⚠ Dưới chuẩn'}</span>
              </div>
            )}
          </div>
          <p className="pillar-desc">{report.value_investor_pillars.earnings_quality?.diagnosis}</p>
        </div>

        {(() => {
          const fortress = report.value_investor_pillars.financial_fortress || {};
          const isBank = fortress.is_bank || report.archetype_profile?.archetype === 'BANK';
          const isSec = fortress.is_financial && !isBank;

          const title = isBank
            ? 'Pháo đài Tài chính · Đòn bẩy TS'
            : (isSec ? 'Pháo đài Tài chính · Đòn bẩy TS' : 'Pháo đài Tài chính · Nợ / VCSH');

          const mainVal = isBank || isSec
            ? (fortress.bank_leverage != null ? `${fortress.bank_leverage}x` : (fortress.solvency_display || 'An toàn'))
            : (fortress.debt_to_equity_ratio != null ? `${fortress.debt_to_equity_ratio}x` : (fortress.net_debt_vnd === 0 ? '0x' : '—'));

          const subLabel = isBank
            ? `Đòn bẩy Tài sản${fortress.equity_to_assets_pct != null ? ` · Đệm vốn ${fortress.equity_to_assets_pct}%` : ''}`
            : (isSec ? 'Đòn bẩy Tài sản (TS/VCSH)' : 'Nợ / Vốn chủ sở hữu (D/E)');

          return (
            <div className={`pillar-card pillar-${fortress.status?.toLowerCase() || 'strong'}`}>
              <div className="pillar-header">
                <span className="pillar-num">02</span>
                <span className="pillar-title">{title}</span>
                <span className="pillar-badge">
                  {fortress.status === 'STRONG' || fortress.status === 'FORTRESS' ? 'Rất Vững' : fortress.status === 'HEALTHY' ? 'Lành mạnh' : 'Cần chú ý'}
                </span>
              </div>
              <div className="pillar-metric">
                <span className="pillar-val">{mainVal}</span>
                <span className="pillar-sub">{subLabel}</span>
              </div>
              <div className="pillar-metric-list">
                {isBank ? (
                  <>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Tổng tài sản</span>
                      <span className="pm-val">{fortress.total_assets_vnd != null ? money(fortress.total_assets_vnd, locale) : '—'}</span>
                    </div>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Vốn chủ sở hữu</span>
                      <span className="pm-val">{fortress.total_equity_vnd != null ? money(fortress.total_equity_vnd, locale) : '—'}</span>
                    </div>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Tỷ lệ Đệm vốn (VCSH/TS)</span>
                      <span className="pm-val">{fortress.equity_to_assets_pct != null ? `${fortress.equity_to_assets_pct}%` : '—'}</span>
                    </div>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Đòn bẩy Tài sản (TS/VCSH)</span>
                      <span className="pm-val">{fortress.bank_leverage != null ? `${fortress.bank_leverage}x` : '—'}</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Tổng nợ vay</span>
                      <span className="pm-val">{fortress.total_debt_vnd != null ? money(fortress.total_debt_vnd, locale) : '—'}</span>
                    </div>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Tiền mặt & tương đương</span>
                      <span className="pm-val">{fortress.total_cash_vnd != null ? money(fortress.total_cash_vnd, locale) : '—'}</span>
                    </div>
                    <div className="pillar-metric-item">
                      <span className="pm-label">Nợ ròng (Nợ − Tiền)</span>
                      <span className="pm-val">{fortress.net_debt_vnd != null ? money(fortress.net_debt_vnd, locale) : '—'}</span>
                    </div>
                    <div className="pillar-metric-item">
                      <span className="pm-label">{fortress.debt_payback_years === 0 ? 'Trả hết nợ bằng dòng tiền' : 'Nợ ròng / EBITDA'}</span>
                      <span className="pm-val">{fortress.net_debt_to_ebitda != null ? `${fortress.net_debt_to_ebitda}x` : (fortress.debt_payback_years === 0 ? '0 năm' : '—')}</span>
                    </div>
                  </>
                )}
              </div>
              <p className="pillar-desc">{fortress.diagnosis}</p>
            </div>
          );
        })()}

        <div className={`pillar-card pillar-${report.value_investor_pillars.capital_allocation?.status?.toLowerCase() || 'good'}`}>
          <div className="pillar-header">
            <span className="pillar-num">03</span>
            <span className="pillar-title">Hiệu quả Phân bổ Vốn</span>
            <span className="pillar-badge">
              {report.value_investor_pillars.capital_allocation?.status === 'EXCELLENT' ? 'Xuất sắc' : report.value_investor_pillars.capital_allocation?.status === 'GOOD' ? 'Tốt' : 'Cần chú ý'}
            </span>
          </div>
          <div className="pillar-metric">
            <span className="pillar-val">{report.value_investor_pillars.capital_allocation?.avg_roe_5y != null ? `${report.value_investor_pillars.capital_allocation.avg_roe_5y}%` : '—'}</span>
            <span className="pillar-sub">ROE bình quân 5 năm</span>
          </div>
          <div className="pillar-metric-list">
            <div className="pillar-metric-item">
              <span className="pm-label">iROIC lũy kế 3 năm (ΔLNST/ΔVCSH)</span>
              <span className="pm-val">{report.quality_scorecard?.capital_allocation_evidence?.cumulative_3y_iroic_pct != null ? `${report.quality_scorecard.capital_allocation_evidence.cumulative_3y_iroic_pct}%` : '—'}</span>
            </div>
            <div className="pillar-metric-item">
              <span className="pm-label">Pha loãng đã xác nhận (5Y)</span>
              <span className="pm-val">{report.value_investor_pillars.capital_allocation?.confirmed_economic_dilution_5y_pct != null ? `+${report.value_investor_pillars.capital_allocation.confirmed_economic_dilution_5y_pct}%` : (report.value_investor_pillars.capital_allocation?.dilution_classification === 'UNEXPLAINED_SHARE_CHANGE' ? 'Chưa rõ' : '0%')}</span>
            </div>
            <div className="pillar-metric-item">
              <span className="pm-label">Tăng CP chưa giải thích (5Y)</span>
              <span className="pm-val">{report.value_investor_pillars.capital_allocation?.unexplained_share_change_5y_pct != null ? `${report.value_investor_pillars.capital_allocation.unexplained_share_change_5y_pct}%` : '—'}</span>
            </div>
          </div>
          <p className="pillar-desc">{report.value_investor_pillars.capital_allocation?.diagnosis}</p>
        </div>
      </div>
    )}

    {/* feedback.txt — Numeric Validation & Regime Engine: biến động lịch sử đã
        phân loại + Window chuẩn hóa (latest comparable regime / structural break) */}
    <HistoricalResolutionsBlock report={report} locale={locale} />

    {/* Collapsed Technical Details (for advanced inspection) */}
    <details className="valuation-technical-details">
      <summary className="technical-summary">
        <span>Chi tiết Tính toán & Bảng Ma trận Độ nhạy Định giá</span>
      </summary>
      <div className="technical-content">
        {report.sotp_sensitivity_matrix?.grid_values_per_share?.length > 0 && (
          <div className="tech-section">
            <h4>Bảng Độ nhạy Định giá theo Tỷ lệ Chiết khấu (r) và Tăng trưởng Dài hạn (g)</h4>
            <div className="sensitivity-matrix-container">
              <table className="sensitivity-matrix-table">
                <thead>
                  <tr>
                    <th>Tăng trưởng (g) \ Chiết khấu (r)</th>
                    {report.sotp_sensitivity_matrix.discount_rates.map(r => (
                      <th key={r}>{Number(r) * 100}%</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.sotp_sensitivity_matrix.terminal_growth_rates.map((g, rowIdx) => (
                    <tr key={g}>
                      <td><strong>{Number(g) * 100}%</strong></td>
                      {report.sotp_sensitivity_matrix.grid_values_per_share[rowIdx]?.map((cellVal, colIdx) => (
                        <td key={colIdx}>
                          {cellVal > 0 ? `${Math.round(cellVal).toLocaleString('vi-VN')} ₫` : '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {bridge && bridge.net_profit != null && (
          <div className="tech-section">
            <h4>Bóc tách Lợi nhuận Thực của Chủ Doanh nghiệp</h4>
            <dl className="valuation-calculation-grid">
              <div><dt>Lợi nhuận sau thuế</dt><dd>{money(bridge.net_profit, locale)}</dd></div>
              <div><dt>Khấu hao tài sản</dt><dd>{money(bridge.depreciation_amortization, locale)}</dd></div>
              <div><dt>Đầu tư duy trì nhà xưởng</dt><dd>{money(bridge.maintenance_capex, locale)}</dd></div>
              <div><dt>Lợi nhuận Thực tạo ra</dt><dd>{money(bridge.owner_earnings, locale)}</dd></div>
            </dl>
          </div>
        )}

        <div className="tech-section">
          <h4>Ba Kịch bản Định giá Chi tiết</h4>
          <div className="valuation-scenarios">
            {scenarios.map(name => {
              const scenario = report.scenarios?.[name] || {};
              const labelVn = name === 'BEAR' ? 'Thận trọng (Bear)' : name === 'BASE' ? 'Cơ sở (Base)' : 'Lạc quan (Bull)';
              return <div key={name} className={`scenario-card scenario-${name.toLowerCase()}`}>
                <div className="scenario-head">
                  <b>{labelVn}</b>
                  <span className="scenario-val">{money(scenario.intrinsic_value_per_share, locale)}</span>
                </div>
                <div className="scenario-meta">
                  <span>Tăng trưởng dự phóng: <strong>{displayNumber(Number(scenario.growth_stage1_rate || 0) * 100, '%')}</strong></span>
                  <span>Tỷ lệ chiết khấu: <strong>{displayNumber(Number(scenario.discount_rate || 0) * 100, '%')}</strong></span>
                </div>
              </div>;
            })}
          </div>
        </div>
      </div>
    </details>

    {/* Vì sao Giá trị Thực cơ sở như vậy — dưới section chi tiết tính toán */}
    <ValuationRationale report={report} locale={locale} />

    <footer className="valuation-card-footer">
      <span>Nguồn dữ liệu: Báo cáo Tài chính Kiểm toán ({freshness.provider || multiples.source || 'Sàn chứng khoán'}) · Kỳ BCTC {report.fiscal_period_latest || 'Năm 2025'}</span>
      <span>Thời điểm đồng bộ: {freshness.fetched_at ? new Date(freshness.fetched_at).toLocaleDateString('vi-VN') : 'Mới nhất'}</span>
    </footer>
  </article>;
}

function getPageNumbers(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  if (currentPage <= 4) {
    return [1, 2, 3, 4, 5, '...', totalPages];
  }
  if (currentPage >= totalPages - 3) {
    return [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
}

function ValuationOverviewTable({ reports = {}, symbols = [], selectedSymbol, locale = 'vi', onSelectSymbol }) {
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  const validRows = symbols
    .map(sym => ({ sym, rep: reports[sym] }))
    .filter(item => item.rep);

  if (validRows.length <= 1) return null;

  const totalPages = Math.ceil(validRows.length / pageSize);
  const safePage = Math.min(Math.max(1, currentPage), totalPages);
  const paginatedRows = validRows.slice((safePage - 1) * pageSize, safePage * pageSize);

  return (
    <div className="valuation-overview-table-wrapper">
      <div className="valuation-overview-header-row">
        <h3 className="valuation-overview-title">Bảng Tổng quan Định giá Danh mục ({validRows.length} mã)</h3>
        <span className="valuation-overview-hint">💡 Nhấp vào mã hoặc dòng để cuộn xem chi tiết bên dưới</span>
      </div>
      {/* Desktop Table View (>= 720px) */}
      <div className="valuation-overview-desktop valuation-overview-scroll">
        <table className="valuation-overview-table">
          <thead>
            <tr>
              <th className="th-symbol">Mã CP</th>
              <th>Bản chất Kinh tế</th>
              <th style={{ textAlign: 'right' }}>Thị giá</th>
              <th style={{ textAlign: 'right' }}>Giá trị Thực (Base)</th>
              <th style={{ textAlign: 'right' }}>MOS</th>
              <th style={{ textAlign: 'center' }}>Kết luận</th>
              <th style={{ textAlign: 'center' }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {paginatedRows.map(({ sym, rep }) => {
              const base = rep.scenarios?.BASE || {};
              const mos = base.margin_of_safety_pct;
              const archName = archetypeLabel(rep.archetype_profile?.archetype);
              const iv = rep.public_base_iv ?? rep.base_iv ?? null;
              const pubMos = rep.public_mos ?? rep.margin_of_safety_pct ?? null;
              const hasWarning = Boolean(rep.valuation_warning);
              const isSelected = selectedSymbol === sym;
              return (
                <tr
                  key={sym}
                  className={`valuation-overview-row clickable ${isSelected ? 'row-selected' : ''}`}
                  onClick={() => onSelectSymbol?.(sym)}
                  title={hasWarning ? rep.valuation_warning : `Xem chi tiết định giá ${sym}`}
                  style={isSelected ? { backgroundColor: 'color-mix(in srgb, var(--accent, #a63f30) 10%, var(--surface-soft, #f4ecd9))' } : undefined}
                >
                  <td className="td-symbol">
                    <strong>{sym}</strong>
                    {hasWarning && <span style={{ marginLeft: '6px', fontSize: '0.8rem', color: 'var(--retro-hanko, #a63f30)' }} title={rep.valuation_warning}>⚠</span>}
                    {isSelected && <span style={{ marginLeft: '6px', fontSize: '0.72rem', color: 'var(--accent)', fontWeight: '700' }}>● Đang xem</span>}
                  </td>
                  <td className="td-arch">{archName}</td>
                  <td className="td-num" style={{ textAlign: 'right' }}>{money(rep.current_market_price, locale)}</td>
                  <td className="td-num td-iv" style={{ textAlign: 'right' }}>
                    {iv != null && Number.isFinite(Number(iv)) ? money(iv, locale) : (hasWarning ? '—' : 'N/A')}
                  </td>
                  <td className="td-num" style={{ textAlign: 'right', fontWeight: '700', color: pubMos > 0 ? 'var(--retro-green, #2f6b4d)' : pubMos < 0 ? 'var(--retro-hanko, #a63f30)' : 'inherit' }}>
                    {pubMos != null && Number.isFinite(Number(pubMos)) ? `${pubMos > 0 ? '+' : ''}${Number(pubMos).toFixed(1)}%` : (hasWarning ? '⚠ Không công bố' : 'N/A')}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <ValuationStatusPill status={rep.assessment?.valuation_status} marginOfSafety={pubMos} />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      type="button"
                      className={`btn-small btn-view-detail ${isSelected ? 'btn-active-detail' : ''}`}
                      onClick={(e) => { e.stopPropagation(); onSelectSymbol?.(sym); }}
                    >
                      {isSelected ? 'Đang xem ↓' : 'Xem chi tiết ↓'}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Overview Card List (< 720px) */}
      <div className="valuation-overview-mobile-list">
        {paginatedRows.map(({ sym, rep }) => {
          const base = rep.scenarios?.BASE || {};
          const mos = base.margin_of_safety_pct;
          const archName = archetypeLabel(rep.archetype_profile?.archetype);
          const isVerified = rep.model_status === 'MODEL_VERIFIED';
          const iv = rep.public_base_iv ?? rep.base_iv ?? null;
          const pubMos = rep.public_mos ?? rep.margin_of_safety_pct ?? null;
          const hasWarning = Boolean(rep.valuation_warning);
          const isSelected = selectedSymbol === sym;
          const quality = rep.quality_scorecard || {};

          return (
            <article
              key={sym}
              className={`valuation-mobile-card ${isSelected ? 'is-selected' : ''} ${hasWarning ? 'vm-card-warning' : ''}`}
              onClick={() => onSelectSymbol?.(sym)}
              title={hasWarning ? rep.valuation_warning : undefined}
            >
              <div className="vm-card-top">
                <div className="vm-title-wrap">
                  <span className="vm-symbol">{sym}{hasWarning && <span style={{ marginLeft: '6px', color: 'var(--retro-hanko, #a63f30)' }}>⚠</span>}</span>
                  <span className="vm-arch">{archName}</span>
                </div>
                <ValuationStatusPill status={rep.assessment?.valuation_status} marginOfSafety={pubMos} />
              </div>

              {hasWarning && (
                <div className="vm-warning-line" role="alert">⚠ {rep.valuation_warning}</div>
              )}

              <div className="vm-metrics-grid">
                <div className="vm-metric-box">
                  <span className="vm-label">Thị giá</span>
                  <span className="vm-val">{money(rep.current_market_price, locale)}</span>
                </div>
                <div className="vm-metric-box vm-box-iv">
                  <span className="vm-label">Giá trị Thực</span>
                  <span className="vm-val highlight">{iv != null && Number.isFinite(Number(iv)) ? money(iv, locale) : 'N/A'}</span>
                </div>
                <div className="vm-metric-box vm-box-mos">
                  <span className="vm-label">Biên An toàn</span>
                  <span className={`vm-val ${pubMos > 0 ? 'pos' : pubMos < 0 ? 'neg' : ''}`}>
                    {pubMos != null && Number.isFinite(Number(pubMos)) ? `${pubMos > 0 ? '+' : ''}${Number(pubMos).toFixed(1)}%` : (hasWarning ? '⚠ Không công bố' : 'N/A')}
                  </span>
                </div>
              </div>

              <div className="vm-card-bottom">
                <span className="vm-quality-badge">
                  {quality.total_score != null ? `Điểm: ${quality.total_score}/100` : ''}
                </span>
                <button
                  type="button"
                  className={`btn-small ${isSelected ? 'btn-active-detail' : 'btn-view-detail'}`}
                  onClick={(e) => { e.stopPropagation(); onSelectSymbol?.(sym); }}
                >
                  {isSelected ? '● Đang xem bên dưới ↓' : 'Xem chi tiết định giá ↓'}
                </button>
              </div>
            </article>
          );
        })}
      </div>

      {totalPages > 1 && (
        <div className="valuation-pagination">
          <span className="pagination-info">
            Hiển thị <strong>{(safePage - 1) * pageSize + 1}</strong> – <strong>{Math.min(safePage * pageSize, validRows.length)}</strong> trên <strong>{validRows.length}</strong> mã
          </span>

          <div className="pagination-controls">
            <button
              type="button"
              className="pagination-btn pagination-prev"
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={safePage <= 1}
              aria-label="Trang trước"
            >
              ← Trước
            </button>

            <div className="pagination-pages-desktop">
              {getPageNumbers(safePage, totalPages).map((p, idx) => {
                if (p === '...') {
                  return <span key={`ellipsis-${idx}`} className="pagination-ellipsis">…</span>;
                }
                const pageNum = Number(p);
                const isActive = safePage === pageNum;
                return (
                  <button
                    key={pageNum}
                    type="button"
                    className={`pagination-page-btn ${isActive ? 'is-active' : ''}`}
                    onClick={() => setCurrentPage(pageNum)}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <div className="pagination-pages-mobile">
              <span className="pagination-mobile-indicator">
                Trang <strong>{safePage}</strong> / {totalPages}
              </span>
            </div>

            <button
              type="button"
              className="pagination-btn pagination-next"
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={safePage >= totalPages}
              aria-label="Trang sau"
            >
              Sau →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ValuationPage({ symbols = [], locale = 'vi' }) {
  const querySymbol = typeof window !== 'undefined'
    ? (new URLSearchParams(window.location.search).get('symbol') || window.location.hash.replace('#valuation-', ''))?.trim().toUpperCase()
    : null;

  const allSymbols = useMemo(() => {
    const list = [...(symbols || [])];
    if (querySymbol && !list.map(s => String(s || '').toUpperCase()).includes(querySymbol)) {
      list.unshift(querySymbol);
    }
    return list;
  }, [symbols, querySymbol]);

  const normalized = useMemo(() => [...new Set(allSymbols.map(value => String(value || '').toUpperCase()).filter(Boolean))], [allSymbols]);
  const symbolKey = normalized.join(',');
  const [reports, setReports] = useState({});
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(querySymbol || null);

  const activeSymbol = selectedSymbol && normalized.includes(selectedSymbol) ? selectedSymbol : (normalized[0] || null);

  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState('');

  useEffect(() => {
    if (querySymbol && normalized.includes(querySymbol)) {
      setSelectedSymbol(querySymbol);
      setTimeout(() => {
        const el = document.getElementById(`valuation-${querySymbol}`) || document.getElementById('valuation-detail-section');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 150);
    }
  }, [querySymbol, normalized]);

  function handleSelectSymbol(sym) {
    setSelectedSymbol(sym);
    setTimeout(() => {
      const el = document.getElementById(`valuation-${sym}`) || document.getElementById('valuation-detail-section');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 50);
  }

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

  return <div className="page valuation-page-shell">
    <AppNav active="valuation" locale={locale} />
    <main className="valuation-page">
      <header className="valuation-header">
        <div>
          <span className="eyebrow">BCTC mới nhất theo từng mã</span>
          <h1>Định giá cổ phiếu</h1>
          <p>Mô hình chiết khấu dòng tiền kết hợp lợi nhuận thực của chủ doanh nghiệp. Phân tích khách quan theo nguyên lý Giá trị cốt lõi.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button type="button" className="btn-primary export-ai-btn" onClick={exportForAI} disabled={exporting || loading || !normalized.length}>
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
            selectedSymbol={activeSymbol}
            locale={locale}
            onSelectSymbol={handleSelectSymbol}
          />
          <div id="valuation-detail-section" className="valuation-detail-section" style={{ marginTop: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
              <h2 style={{ fontSize: '1.25rem', margin: 0, color: 'var(--text)' }}>
                Chi tiết Mô hình Định giá: <strong style={{ color: 'var(--accent)' }}>{activeSymbol}</strong>
              </h2>
              {normalized.length > 1 && (
                <span style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                  (Đang hiển thị mã <strong>{activeSymbol}</strong> · Chọn mã khác từ bảng tổng quan trên để chuyển đổi)
                </span>
              )}
            </div>

            {loading && !reports[activeSymbol] && !errors[activeSymbol] ? (
              <ValuationSkeletonCard symbol={activeSymbol} />
            ) : (
              <ValuationCard
                key={activeSymbol}
                symbol={activeSymbol}
                report={reports[activeSymbol]}
                error={errors[activeSymbol]}
                locale={locale}
              />
            )}
          </div>
        </>
      )}
    </main>
  </div>;
}
