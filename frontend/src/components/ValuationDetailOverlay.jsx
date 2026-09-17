import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { getValuationReport, crawlValuationHistory, getCrawlStatus } from '../lib/api.js';
import { downloadReportAIExport } from '../lib/aiExport.js';
import TcbsTokenPrompt from './TcbsTokenPrompt.jsx';
import { displayNumber, formatMoney, money } from '../lib/format.js';
import {
  archetypeLabel,
  modelStatusLabel,
  qualityTierLabel,
  valuationModelLabel,
  verdictLabel,
  verdictPillClass,
} from '../lib/valuationLabels.js';
import {
  formatCompounderClassification,
  formatDecision,
} from '../utils/vietnameseSemantics.js';



function formatGridMoney(val, locale = 'vi') {
  if (val == null || !Number.isFinite(Number(val))) return '—';
  const n = Number(val);
  if (Math.abs(n) >= 1e12) {
    const t = n / 1e12;
    return `${t >= 100 ? t.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) : t.toLocaleString('vi-VN', { maximumFractionDigits: 1 })} nghìn tỷ ₫`;
  }
  if (Math.abs(n) >= 1e9) {
    const b = n / 1e9;
    return `${b >= 100 ? b.toLocaleString('vi-VN', { maximumFractionDigits: 0 }) : b.toLocaleString('vi-VN', { maximumFractionDigits: 0 })} tỷ ₫`;
  }
  return money(val, locale);
}

export function ValuationStatusPill({ status, marginOfSafety }) {
  const map = {
    BUY: { label: 'Có thể mua', cls: 'v-pill-deep-value', icon: '✓' },
    CONDITIONAL_BUY: { label: 'Có thể mua có ĐK', cls: 'v-pill-watch', icon: '◷' },
    WAIT_FOR_MOS: { label: 'Chờ biên an toàn', cls: 'v-pill-fair', icon: '◷' },
    DO_NOT_BUY: { label: 'Không đạt chuẩn mua', cls: 'v-pill-distressed', icon: '✕' },
    INSUFFICIENT_DATA: { label: 'Chưa đủ Dữ liệu BCTC', cls: 'v-pill-watch', icon: '—' },
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

const METRIC_LABELS_VI = {
  revenue: 'Doanh thu',
  net_profit: 'LNST',
  operating_cash_flow: 'CFO',
  cfo: 'CFO',
  fcf: 'FCF',
  equity: 'Vốn CSH',
  total_debt: 'Nợ vay',
  debt: 'Nợ vay',
  total_assets: 'Tổng TS',
  assets: 'Tổng TS',
  shares_outstanding: 'Số CP',
  shares: 'Số CP',
  gross_margin: 'Biên gộp',
  operating_margin: 'Biên EBIT',
  net_margin: 'Biên ròng',
  roe: 'ROE',
  roa: 'ROA',
};

function formatCompactFinancial(metricName, value, locale = 'vi') {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  const n = Number(value);
  const key = String(metricName || '').toLowerCase();
  const isShares = key.includes('shares') || key.includes('cp');
  const isPercent = key.includes('margin') || key.includes('roe') || key.includes('roa');

  if (isPercent) {
    const p = Math.abs(n) <= 1 ? n * 100 : n;
    return `${p.toFixed(1)}%`;
  }
  if (isShares) {
    if (Math.abs(n) >= 1e6) return `${(n / 1e6).toLocaleString('vi-VN', { maximumFractionDigits: 1 })}M CP`;
    if (Math.abs(n) >= 1e3) return `${(n / 1e3).toLocaleString('vi-VN', { maximumFractionDigits: 0 })}K CP`;
    return `${n.toLocaleString('vi-VN')} CP`;
  }
  if (Math.abs(n) >= 1e9) {
    const b = n / 1e9;
    const decimals = Math.abs(b) >= 100 ? 0 : 1;
    return `${b.toLocaleString('vi-VN', { minimumFractionDigits: 0, maximumFractionDigits: decimals })} tỷ`;
  }
  if (Math.abs(n) >= 1e6) {
    return `${(n / 1e6).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} tr`;
  }
  return `${n.toLocaleString('vi-VN')} ₫`;
}

const HISTORICAL_CLASSIFICATION_VI = {
  STRUCTURAL_REGIME_BREAK: { label: 'Thay đổi quy mô / Regime', cls: 'structural' },
  CYCLICAL_EXTREME: { label: 'Biến động chu kỳ', cls: 'cycle' },
  SHARE_STRUCTURE_CHANGE: { label: 'Thay đổi cơ cấu cổ phiếu', cls: 'share' },
  CASHFLOW_TIMING_CANDIDATE: { label: 'Lệch timing dòng tiền', cls: 'timing' },
  EARNINGS_ONE_OFF_CANDIDATE: { label: 'Lợi nhuận một lần (one-off)', cls: 'oneoff' },
  SUSPICIOUS_ISOLATED: { label: 'Biến động đơn lẻ theo dõi', cls: 'watch' },
  UNIT_MAPPING_ERROR_CANDIDATE: { label: 'Lỗi đơn vị / mapping', cls: 'blocking' },
  UNRESOLVED_MATERIAL: { label: 'Dữ liệu chưa phân loại', cls: 'blocking' },
};

const DATA_STATUS_VI = {
  VALID: 'Hợp lệ',
  VALID_WITH_CLASSIFIED_EVENTS: 'Đã phân loại',
  SUSPICIOUS: 'Nghi vấn',
  CONFLICTED: 'Mâu thuẫn',
  INSUFFICIENT: 'Thiếu dữ liệu',
};

function dataStatusLabel(status) {
  return DATA_STATUS_VI[status] || status || '-';
}

// feedback.txt §UI: banner "BIẾN ĐỘNG LỊCH SỬ ĐÃ PHÂN LOẠI" thay cho banner đỏ
// "BẤT THƯỜNG LỊCH SỬ — CẦN ĐỐI SOÁT NGUỒN". Chỉ đỏ khi UNRESOLVED_MATERIAL.
// Thiết kế tinh giản dạng Bảng Nhật ký Dữ liệu (Financial Ledger).
export function HistoricalResolutionsBlock({ report, locale = 'vi' }) {
  const anomalies = Array.isArray(report?.data_anomalies) ? report.data_anomalies : [];
  const window = report?.normalization_window;
  const regimes = Array.isArray(report?.regime_analysis) ? report.regime_analysis : [];
  if (!anomalies.length && !window && !regimes.length) return null;
  const hasBlocking = anomalies.some(
    a => ['UNRESOLVED_MATERIAL', 'UNIT_MAPPING_ERROR_CANDIDATE'].includes(a.resolution?.classification),
  );

  return (
    <details
      className={`v-anomaly-box v-anomaly-collapse ${hasBlocking ? 'v-anomaly-box-blocking' : ''} ${anomalies.length ? '' : 'v-anomaly-box-info'}`}
      open={hasBlocking}
      role={hasBlocking ? 'alert' : 'group'}
    >
      <summary className="v-anomaly-collapse-summary">
        <div className="v-anomaly-header-row">
          <div className="v-anomaly-title">
            <span className="v-anomaly-icon">{hasBlocking ? '⛔' : '🧭'}</span>
            <h3>{hasBlocking ? 'Dữ liệu chưa phân loại — Cản trở định giá' : 'Biến động lịch sử đã phân loại (Regime Engine)'}</h3>
            <span className="v-collapse-hint">{anomalies.length} sự kiện · nhấp để mở/đóng</span>
          </div>
          {(report?.data_status || report?.regime_status) && (
            <div className="v-anomaly-status-pills">
              <span className="v-pill-chip">{dataStatusLabel(report?.data_status)}</span>
              {report?.regime_status === 'SPLIT_REGIME' && <span className="v-pill-chip highlight">Tách Regime</span>}
              {report?.validation_confidence != null && (
                <span className="v-pill-chip">UFVS {report.validation_confidence}/100</span>
              )}
            </div>
          )}
        </div>
        <span className="v-collapse-chevron" aria-hidden="true">▾</span>
      </summary>

      <div className="v-anomaly-body">
        {!hasBlocking && (
          <p className="v-anomaly-desc">
            Các biến động lịch sử được phân loại tự động qua coherence đa chỉ tiêu, persistence và materiality. Dữ liệu đã phân loại an toàn cho chuẩn hóa chu kỳ.
          </p>
        )}

        {anomalies.length > 0 && (
          <div className="v-anomaly-table-wrap">
            <table className="v-anomaly-table">
              <thead>
                <tr>
                  <th className="th-year">Năm</th>
                  <th className="th-type">Phân loại</th>
                  <th className="th-metrics">Biến động chỉ tiêu tài chính</th>
                  <th className="th-meta">Độ tin cậy</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => {
                  const cls = HISTORICAL_CLASSIFICATION_VI[a.resolution?.classification] || {
                    label: a.resolution?.classification || 'Theo dõi',
                    cls: 'watch',
                  };
                  const mat = a.materiality?.grade;
                  return (
                    <tr key={i} className={`v-anomaly-tr v-row-${cls.cls}`}>
                      <td className="td-year">
                        <span className="v-year-tag">{a.fiscal_year}</span>
                      </td>
                      <td className="td-type">
                        <div className="v-type-group">
                          <span className={`v-anomaly-tag ${cls.cls}`}>{cls.label}</span>
                          {mat && mat !== 'IMMATERIAL' && mat !== 'UNKNOWN' && (
                            <span className="v-anomaly-tag material">{`Tác động ${a.materiality.impact_pct ?? '-'}%`}</span>
                          )}
                        </div>
                      </td>
                      <td className="td-metrics">
                        <div className="v-metrics-inline">
                          {(a.metrics || []).map((m, j) => {
                            const chg = Number(m.change_pct || 0);
                            const sign = chg > 0 ? '+' : '';
                            const label = METRIC_LABELS_VI[m.metric] || m.metric;
                            return (
                              <span key={j} className="v-metric-badge">
                                <span className="m-name">{label}:</span>{' '}
                                <span className="m-val">{formatCompactFinancial(m.metric, m.previous, locale)} → {formatCompactFinancial(m.metric, m.current, locale)}</span>{' '}
                                <span className={`m-chg ${chg >= 0 ? 'pos' : 'neg'}`}>({sign}{Math.abs(chg) >= 100 ? chg.toFixed(0) : chg.toFixed(1)}%)</span>
                              </span>
                            );
                          })}
                        </div>
                      </td>
                      <td className="td-meta">
                        <div className="v-meta-info">
                          <span className="v-meta-line">Tin cậy: <strong>{a.resolution?.confidence || '-'}</strong></span>
                          <span className="v-meta-line muted">Coh: <strong>{a.resolution?.internal_coherence ?? '-'}</strong> · {a.resolution?.persistent ? 'Duy trì' : 'Tạm thời'}</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {(window || regimes.length > 0) && (
          <div className="v-regime-footer">
            {window && (
              <div className="v-regime-bar">
                <span className="v-regime-bar-title">🧭 Window chuẩn hóa (latest comparable regime):</span>
                <span className="v-regime-bar-val">
                  <strong>{window.start_year}–{window.end_year}</strong> ({window.used_years} năm dữ liệu)
                </span>
              </div>
            )}
            {regimes.length > 0 && (
              <div className="v-regime-bar">
                <span className="v-regime-bar-title">✂️ Phân tích Regime:</span>
                <div className="v-regime-chips">
                  {regimes.map((rg, i) => (
                    <span key={i} className="v-regime-chip">
                      {rg.label}: {rg.start_year}–{rg.end_year}
                      {rg.structural_break_year ? ` (break @${rg.structural_break_year})` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </details>
  );
}

// Section "Vì sao Giá trị Thực cơ sở như vậy" (expand/collapse) — dùng chung
// cho trang Định giá và overlay trên trang Screener.
export function ValuationRationale({ report, locale = 'vi' }) {
  if (!report) return null;
  const bridge = report.owner_earnings_bridge || {};
  const growth = report.growth_derivation || {};
  const base = report.scenarios?.BASE || {};
  const win = report.normalization_window;

  const isBank = (
    report.archetype_profile?.archetype === 'FINANCIAL_BANK' ||
    report.valuation_model === 'RESIDUAL_INCOME_MODEL' ||
    report.valuation_model === 'BANK_EQUITY_MODEL'
  );

  const normMethod = bridge.normalization_method === 'MID_CYCLE_MEDIAN'
    ? 'Mid-Cycle Median (biên LNST trung vị × doanh thu trung vị)'
    : bridge.normalization_method === 'LATEST_FY'
      ? 'Năm tài chính mới nhất (LATEST_FY)'
      : (bridge.normalization_method || '—');

  const iv = base.intrinsic_value_per_share;

  // Fact-checked financial metrics & balance sheet facts
  const hist = report.financial_history_10y || [];
  const latestHist = hist.length > 0 ? hist[hist.length - 1] : {};
  const fortress = report.value_investor_pillars?.financial_fortress || {};

  const cashVal = fortress.total_cash_vnd != null
    ? fortress.total_cash_vnd
    : (latestHist.cash_and_equivalents != null ? latestHist.cash_and_equivalents : (base.cash_and_equivalents || 0));

  const debtVal = fortress.total_debt_vnd != null
    ? fortress.total_debt_vnd
    : (latestHist.total_debt != null ? latestHist.total_debt : (base.total_debt || 0));

  const netCashVal = cashVal - debtVal;
  const sharesVal = report.shares_outstanding || latestHist.shares_outstanding || (base.equity_value && iv ? Math.round(base.equity_value / iv) : 1);
  const totalEquity = base.equity_value || base.enterprise_value || (base.present_value || 0);
  const pvTerminalPct = base.terminal_value_contribution_pct != null ? Number(base.terminal_value_contribution_pct) / 100 : 0.732;
  const pvTerminal = base.pv_terminal != null ? base.pv_terminal : totalEquity * pvTerminalPct;
  const pvStage1 = base.pv_stage1 != null ? base.pv_stage1 : totalEquity * (1 - pvTerminalPct);
  const normOe = bridge.normalized_owner_earnings || bridge.current_owner_earnings || bridge.net_profit || 0;

  const bvpsVal = report.valuation_multiples?.bvps != null
    ? report.valuation_multiples.bvps
    : (report.fundamentals?.bvps != null
      ? report.fundamentals.bvps
      : (latestHist.equity && sharesVal ? latestHist.equity / sharesVal : 0));
  const targetPb = bvpsVal > 0 && iv ? (iv / bvpsVal).toFixed(2) : '—';

  return (
    <details className="valuation-rationale valuation-rationale-collapse" open={false}>
      <summary className="valuation-rationale-summary">
        <span className="rationale-summary-title">🧭 Vì sao Giá trị Thực cơ sở = {iv != null ? money(iv, locale) : '—'}?</span>
        <span className="v-collapse-chevron" aria-hidden="true">▾</span>
      </summary>
      <div className="valuation-rationale-body">
        <p className="valuation-rationale-lead">
          Giá trị Thực cơ sở được tính bằng mô hình{' '}
          <strong>{valuationModelLabel(report.valuation_model || report.archetype_profile?.recommended_model)}</strong>{' '}
          từ lợi nhuận đã chuẩn hóa, tăng trưởng dự phóng và chi phí vốn. Dưới đây là từng bước dẫn tới con số này.
        </p>

        <div className="rationale-grid">
          {/* 1. Normalization */}
          <div className="rationale-step">
            <span className="rationale-num">01</span>
            <div>
              <b>Chuẩn hóa lợi nhuận — {normMethod}</b>
              <p>
                {win
                  ? `Window chuẩn hóa (latest comparable regime): ${win.comparable_regime_start}–${win.comparable_regime_end} (dùng ${win.normalization_years ?? bridge.normalization_years ?? 0} năm). `
                  : ''}
                {bridge.formula_description || 'Lợi nhuận chu kỳ được chuẩn hóa để loại bỏ nhiễu đỉnh/đáy.'}
              </p>
              {(bridge.mid_cycle_margin != null || bridge.mid_cycle_revenue != null || bridge.normalized_owner_earnings != null) && (
                <dl className="valuation-calculation-grid">
                  {bridge.mid_cycle_margin != null && (
                    <div><dt>Biên LNST chu kỳ trung vị</dt><dd>{displayNumber(Number(bridge.mid_cycle_margin) * 100, '%')}</dd></div>
                  )}
                  {bridge.mid_cycle_revenue != null && (
                    <div><dt>Doanh thu trung vị</dt><dd>{formatGridMoney(bridge.mid_cycle_revenue, locale)}</dd></div>
                  )}
                  {bridge.normalized_owner_earnings != null && (
                    <div><dt>Lợi nhuận Thực chuẩn hóa</dt><dd>{formatGridMoney(bridge.normalized_owner_earnings, locale)}</dd></div>
                  )}
                  {bridge.current_owner_earnings != null && (
                    <div><dt>Lợi nhuận Thực năm gần nhất</dt><dd>{formatGridMoney(bridge.current_owner_earnings, locale)}</dd></div>
                  )}
                </dl>
              )}
            </div>
          </div>

          {/* 2. Growth & cost of capital */}
          <div className="rationale-step">
            <span className="rationale-num">02</span>
            <div>
              <b>Giả định tăng trưởng & chi phí vốn</b>
              <p>
                Tăng trưởng bền vững dự phóng <strong>{growth.base_growth != null ? displayNumber(growth.base_growth, '%') : '—'}</strong>
                {growth.historical_cagr_5y_pct != null ? ` (CAGR lợi nhuận 5 năm: ${growth.historical_cagr_5y_pct}%)` : ''}
                {growth.incremental_roe_pct != null ? ` · iROE: ${growth.incremental_roe_pct}%` : ''}
                {growth.retention_rate != null ? ` · Tỷ lệ giữ lại: ${displayNumber(growth.retention_rate * 100, '%')}` : ''}.{' '}
                Chiết khấu (chi phí vốn cổ phần) <strong>{displayNumber(Number(base.discount_rate || 0) * 100, '%')}</strong>,{' '}
                tăng trưởng dài hạn <strong>{displayNumber(Number(base.terminal_growth_rate || 0) * 100, '%')}</strong>.
              </p>
            </div>
          </div>

          {/* 3. Base scenario → IV/share */}
          <div className="rationale-step">
            <span className="rationale-num">03</span>
            <div>
              <b>Kịch bản Cơ sở (Base) → Giá trị Thực mỗi cổ phần</b>
              <p>
                {report.valuation_model === 'CONCESSION_DCF'
                  ? 'Đặc thù tài sản nhượng quyền hạ tầng Cảng biển có thời hạn tô nhượng hữu hạn: Toàn bộ dòng tiền được chiết khấu trong suốt vòng đời dự án, không giả định tồn tại vĩnh viễn (Terminal Value = 0).'
                  : 'Dòng tiền 5 năm dự phóng theo tăng trưởng cơ sở được chiết khấu, cộng Giá trị cuối (Terminal Value), trừ nợ ròng để ra Giá trị Doanh nghiệp → Giá trị Vốn chủ sở hữu → chia cho số cổ phần lưu hành.'}
              </p>
              {(base.enterprise_value != null || base.terminal_value != null || base.terminal_value_contribution_pct != null || iv != null) && (
                <dl className="valuation-calculation-grid">
                  {base.terminal_value != null && (
                    <div>
                      <dt>Giá trị cuối (Terminal)</dt>
                      <dd>
                        {report.valuation_model === 'CONCESSION_DCF' || base.terminal_value === 0
                          ? '0 ₫ (Hạ tầng nhượng quyền hữu hạn)'
                          : formatGridMoney(base.terminal_value, locale)}
                      </dd>
                    </div>
                  )}
                  {base.terminal_value_contribution_pct != null && (
                    <div>
                      <dt>Đóng góp Terminal</dt>
                      <dd>
                        {report.valuation_model === 'CONCESSION_DCF' || base.terminal_value_contribution_pct === 0
                          ? '0.0% (Không tính sau tô nhượng)'
                          : displayNumber(base.terminal_value_contribution_pct, '%')}
                      </dd>
                    </div>
                  )}
                  {base.enterprise_value != null && (
                    <div><dt>Giá trị Doanh nghiệp (EV)</dt><dd>{formatGridMoney(base.enterprise_value, locale)}</dd></div>
                  )}
                  {iv != null && (
                    <div><dt>Giá trị Thực cơ sở / CP</dt><dd className="highlight">{money(iv, locale)}</dd></div>
                  )}
                </dl>
              )}
            </div>
          </div>

          {/* 4. Formulas & Quantitative Breakdown */}
          <div className="rationale-step rationale-step-formula">
            <span className="rationale-num">04</span>
            <div style={{ width: '100%' }}>
              <b>Mô hình Toán học & Chứng minh Số liệu Định lượng</b>
              <p>
                Toàn bộ biến số đầu vào từ BCTC kiểm toán và các bước thế số giải tích xác định Giá trị Thực nội tại:
              </p>

              {!isBank ? (
                <div className="math-model-wrapper">
                  {/* LaTeX-style Main Mathematical Equation Box */}
                  <div className="math-latex-card">
                    <div className="math-latex-title">CÔNG THỨC ĐỊNH GIÁ CHIẾT KHẤU LỢI NHUẬN THỰC (TWO-STAGE OWNER EARNINGS DCF)</div>
                    <div className="math-latex-formula">
                      <div className="math-fraction">
                        <div className="math-num">
                          <span>PV(Dòng tiền 5 năm)</span>
                          <span className="math-sym">+</span>
                          <span>PV(Giá trị cuối Terminal)</span>
                        </div>
                        <div className="math-denom">Số lượng Cổ phần lưu hành (Shares)</div>
                      </div>
                      <span className="math-sym">=</span>
                      <span className="math-result-tag">Giá trị Thực / Cổ phần (IV)</span>
                    </div>
                  </div>

                  {/* Input Parameters Ledger */}
                  <div className="math-params-ledger">
                    <div className="param-item">
                      <span className="param-label">Lợi nhuận cơ sở (OE₀)</span>
                      <span className="param-val">{formatGridMoney(normOe, locale)}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Tăng trưởng 5 năm (g)</span>
                      <span className="param-val">{growth.base_growth != null ? displayNumber(growth.base_growth, '%') : '—'}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Chi phí vốn (r)</span>
                      <span className="param-val">{displayNumber(Number(base.discount_rate || 0) * 100, '%')}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Tăng trưởng vĩnh viễn (g_term)</span>
                      <span className="param-val">{displayNumber(Number(base.terminal_growth_rate || 0) * 100, '%')}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Tiền mặt & Đầu tư ngắn hạn</span>
                      <span className="param-val">{formatGridMoney(cashVal, locale)}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Tổng nợ vay tài chính</span>
                      <span className="param-val">{formatGridMoney(debtVal, locale)}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Số CP lưu hành (S)</span>
                      <span className="param-val">{sharesVal ? `${(sharesVal / 1e6).toFixed(1)}M CP` : '—'}</span>
                    </div>
                  </div>

                  {/* Step-by-Step Mathematical Proof */}
                  <div className="math-proof-ledger">
                    <div className="proof-row">
                      <div className="proof-badge">Bước 1 · Hiện giá Dòng tiền (PV)</div>
                      <div className="proof-calc">
                        <span className="p-chunk">PV(5 năm) = <strong>{formatGridMoney(pvStage1, locale)}</strong></span>
                        <span className="p-op">+</span>
                        <span className="p-chunk">PV(Terminal) = <strong>{formatGridMoney(pvTerminal, locale)}</strong></span>
                        <span className="p-op">⟹</span>
                        <span className="p-chunk highlight-accent">Tổng Hiện giá Vốn chủ = <strong>{formatGridMoney(totalEquity, locale)}</strong></span>
                      </div>
                    </div>

                    <div className="proof-row">
                      <div className="proof-badge">Bước 2 · Cấu trúc Vốn & Sức mạnh Pháo đài</div>
                      <div className="proof-calc">
                        <span className="p-chunk">Tiền mặt: <strong>{formatGridMoney(cashVal, locale)}</strong></span>
                        <span className="p-op">-</span>
                        <span className="p-chunk">Tổng nợ: <strong>{formatGridMoney(debtVal, locale)}</strong></span>
                        <span className="p-op">⟹</span>
                        <span className="p-chunk">Tiền mặt ròng = <strong>{formatGridMoney(netCashVal, locale)}</strong></span>
                        {netCashVal >= 0 ? (
                          <span className="p-chunk fortress-tag-safe">🛡️ Pháo đài tiền mặt ròng (0 rủi ro nợ)</span>
                        ) : (normOe > 0 && Math.abs(netCashVal) / normOe <= 2.0) ? (
                          <span className="p-chunk fortress-tag-safe">✓ Nợ thấp: Trả hết sau {(Math.abs(netCashVal) / normOe).toFixed(1)} năm LN (Chuẩn Buffett &lt; 3 năm)</span>
                        ) : (normOe > 0 && Math.abs(netCashVal) / normOe <= 4.0) ? (
                          <span className="p-chunk fortress-tag-moderate">⚖️ Đòn bẩy vừa: Cần {(Math.abs(netCashVal) / normOe).toFixed(1)} năm hoàn nợ (Đã cộng MoS +3%)</span>
                        ) : (
                          <span className="p-chunk fortress-tag-warning">⚠️ Cảnh báo đòn bẩy cao: Cần {normOe > 0 ? (Math.abs(netCashVal) / normOe).toFixed(1) : '> 5'} năm hoàn nợ</span>
                        )}
                      </div>
                      <p className="proof-note">
                        💡 <em>Lưu ý chuẩn định giá Buffett–FCFE:</em> Lợi nhuận Thực (OE) bắt nguồn từ LNST (đã khấu trừ toàn bộ chi phí lãi vay cho chủ nợ). Do đó, dòng tiền chiết khấu theo Chi phí vốn Cổ phần (Cost of Equity) chính là <strong>Giá trị Vốn chủ sở hữu (Equity Value)</strong> trực tiếp của cổ đông. Không trừ lại nợ lần 2 để tránh phạt trùng nợ (double counting).
                      </p>
                    </div>

                    <div className="proof-row is-final-proof">
                      <div className="proof-badge is-final-badge">Bước 3 · Giá trị Thực mỗi Cổ phần (IV)</div>
                      <div className="proof-calc">
                        <span className="p-chunk">Vốn chủ sở hữu: <strong>{formatGridMoney(totalEquity, locale)}</strong></span>
                        <span className="p-op">÷</span>
                        <span className="p-chunk"><strong>{sharesVal ? `${(sharesVal / 1e6).toFixed(1)} triệu CP` : '—'}</strong></span>
                        <span className="p-op">=</span>
                        <span className={`p-chunk is-final-result ${iv != null && iv <= 0 ? 'is-negative-iv' : ''}`}>
                          Giá trị Thực: <strong>{money(iv, locale)}</strong>{iv != null && iv <= 0 ? ' (Rủi ro Nợ vay / Solvency)' : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="math-model-wrapper">
                  <div className="math-latex-card">
                    <div className="math-latex-title">CÔNG THỨC ĐỊNH GIÁ NGÂN HÀNG (RESIDUAL INCOME MODEL - RIM)</div>
                    <div className="math-latex-formula">
                      <span>Giá trị Thực / CP (IV) = BVPS × [1 + (ROE - r) ÷ (r - g)]</span>
                    </div>
                  </div>

                  <div className="math-params-ledger">
                    <div className="param-item">
                      <span className="param-label">Giá trị sổ sách (BVPS)</span>
                      <span className="param-val">{money(bvpsVal, locale)}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">ROE Trung vị</span>
                      <span className="param-val">{report.valuation_multiples?.roe != null ? displayNumber(report.valuation_multiples.roe, '%') : (latestHist.roe != null ? displayNumber(latestHist.roe, '%') : '—')}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Chi phí vốn (r)</span>
                      <span className="param-val">{displayNumber(Number(base.discount_rate || 0) * 100, '%')}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Tăng trưởng dài hạn (g)</span>
                      <span className="param-val">{displayNumber(Number(base.terminal_growth_rate || 0) * 100, '%')}</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Hệ số P/B Hợp lý (Target P/B)</span>
                      <span className="param-val">{targetPb}x</span>
                    </div>
                    <div className="param-item">
                      <span className="param-label">Số CP lưu hành (S)</span>
                      <span className="param-val">{sharesVal ? `${(sharesVal / 1e6).toFixed(1)}M CP` : '—'}</span>
                    </div>
                  </div>

                  <div className="math-proof-ledger">
                    <div className="proof-row is-final-proof">
                      <div className="proof-badge is-final-badge">Thay số tính toán</div>
                      <div className="proof-calc">
                        <span className="p-chunk">BVPS: <strong>{money(bvpsVal, locale)}</strong></span>
                        <span className="p-op">×</span>
                        <span className="p-chunk">Target P/B: <strong>{targetPb}x</strong></span>
                        <span className="p-op">=</span>
                        <span className="p-chunk is-final-result">
                          Giá trị Thực: <strong>{money(iv, locale)}</strong>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </details>
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

export function ValuationReportBody({ symbol, report, locale = 'vi', onCrawl, crawling, crawlMessage, crawlEnabled }) {
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
  // Feedback 31/08: chỉ dùng IV/MOS đã được xác thực & đạt chuẩn Buffett (public
  // gated). Cổ phiếu bị chặn (hard reject / điểm quá thấp) trả N/A kèm cảnh báo.
  const publicBaseIV = report.public_base_iv ?? report.base_iv ?? null;
  const publicMos = report.public_mos ?? report.margin_of_safety_pct ?? null;
  const hasValuationWarning = Boolean(report.valuation_warning);

  const hasMultiples = multiples.pe != null || multiples.pb != null || multiples.eps != null || multiples.roe != null;
  const hasScenarios = publicBaseIV != null && bear.intrinsic_value_per_share != null && bull.intrinsic_value_per_share != null && base.intrinsic_value_per_share != null;
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

  // Feedback 31/08: chỉ hiển thị phần chi tiết định giá khi cổ phiếu ĐẠT chuẩn
  // Buffett (model verified + không bị chặn chất lượng + có public IV hợp lệ).
  // Mọi trường hợp khác (chất lượng quá thấp, hard reject, model chưa xác thực)
  // -> KHÔNG hiển thị chi tiết, chỉ đưa ra cảnh báo + nguyên nhân.
  const isQualified = isVerifiedModel
    && !hasValuationWarning
    && publicBaseIV != null
    && Number(publicBaseIV) > 0;
  if (!isQualified) {
    const hardRejects = quality.hard_rejects || [];
    const reportQuality = report.quality_scorecard || {};
    const reason = report.valuation_warning || (
      isVerifiedModel
        ? 'Điểm chất lượng hoặc dữ liệu chưa đạt chuẩn Buffett/Munger; Giá trị Thực (IV) và Biên An Toàn (MOS) không được công bố.'
        : `Mô hình định giá chưa được xác thực (${report.model_status || 'chưa verified'}): thiếu dữ liệu mô hình đặc thù nên chưa thể công bố định giá chi tiết.`
    );
    return (
      <div className="v-report-content">
        <div className="v-meta-grid">
          <div className="v-meta-item">
            <span className="v-meta-label">BẢN CHẤT DOANH NGHIỆP</span>
            <span className="v-meta-value">{arch.archetype ? archetypeLabel(arch.archetype) : 'Doanh nghiệp niêm yết'}</span>
            <span className="v-meta-sub">{valuationModelLabel(report.valuation_model || arch.recommended_model)}</span>
          </div>
          <div className="v-meta-item">
            <span className="v-meta-label">CHẤT LƯỢNG DOANH NGHIỆP</span>
            <span className="v-meta-value">{reportQuality.total_score != null ? `${reportQuality.total_score}/100` : '—'}</span>
            <span className="v-meta-sub">{qualityTierLabel(reportQuality.tier)}</span>
          </div>
          <div className="v-meta-item">
            <span className="v-meta-label">TRẠNG THÁI MÔ HÌNH</span>
            <span className="v-meta-value">{report.model_status ? modelStatusLabel(report.model_status) : '—'}</span>
            {report.confidence_level ? (
              <span className={`v-meta-sub v-confidence conf-${String(report.confidence_level).toLowerCase()}`}>
                Độ tin cậy: {report.confidence_level}
              </span>
            ) : null}
          </div>
        </div>

        <div className="v-warning-banner" role="alert">
          <span className="v-warning-icon">⚠️</span>
          <div className="v-warning-text">
            <b>KHÔNG CÔNG BỐ GIÁ TRỊ THỰC (IV) & BIÊN AN TOÀN (MOS)</b>
            <p>{reason}</p>
          </div>
        </div>

        {/* Dữ liệu cần thiết để hoàn thiện mô hình (khi block do thiếu dữ liệu) */}
        {!hasValuationWarning && Array.isArray(report.missing_data) && report.missing_data.length > 0 && (
          <div className="v-missing-data">
            <div className="v-missing-header">
              <span className="v-missing-icon">📋</span>
              <div className="v-missing-title-wrap">
                <b>DỮ LIỆU CẦN THIẾT ĐỂ ĐỊNH GIÁ {symbol}</b>
                <span className="v-missing-sub">
                  Cần bổ sung các dữ liệu sau để hoàn thiện mô hình {valuationModelLabel(report.valuation_model || arch.recommended_model)}
                </span>
              </div>
            </div>
            <ul className="v-missing-list">
              {report.missing_data.map(item => (
                <li key={item}>
                  <span className="v-missing-bullet">▸</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            {Array.isArray(report.confidence_reasons) && report.confidence_reasons.length > 0 && (
              <details className="v-missing-reasons">
                <summary>Chi tiết nguyên nhân từ engine</summary>
                <ul>
                  {report.confidence_reasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </details>
            )}
          </div>
        )}

        <HistoricalResolutionsBlock report={report} locale={locale} />

        {/* Vẫn hiển thị hệ số định giá cơ bản (P/E, P/B, EPS, ROE) cho mã chất lượng thấp */}
        {(multiples.pe != null || multiples.pb != null || multiples.eps != null || multiples.roe != null) && (
          <div className="v-multiples-grid">
            <div className="v-metric-card" title="P/E: Giá trên Lợi nhuận mỗi cổ phần">
              <span className="v-metric-label">P/E (GIÁ/LNST)</span>
              <span className="v-metric-value">{multiples.pe != null ? displayNumber(multiples.pe, ' lần') : '—'}</span>
            </div>
            <div className="v-metric-card" title="P/B: Giá trên Giá trị sổ sách mỗi cổ phần">
              <span className="v-metric-label">P/B (GIÁ/SỔ SÁCH)</span>
              <span className="v-metric-value">{multiples.pb != null ? displayNumber(multiples.pb, ' lần', 2) : '—'}</span>
            </div>
            <div className="v-metric-card" title="EPS: Lợi nhuận sau thuế tạo ra trên mỗi cổ phần">
              <span className="v-metric-label">LỢI NHUẬN/CP (EPS)</span>
              <span className="v-metric-value">{multiples.eps != null ? `${formatMoney(multiples.eps, false, locale)} ₫` : '—'}</span>
            </div>
            <div className="v-metric-card" title="ROE: Tỷ suất sinh lời trên Vốn chủ sở hữu">
              <span className="v-metric-label">SINH LỜI VỐN (ROE)</span>
              <span className="v-metric-value highlight-roe">{multiples.roe != null ? displayNumber(multiples.roe, '%') : '—'}</span>
            </div>
          </div>
        )}

        {hardRejects.length > 0 && (
          <div className="v-hard-rejects">
            <b>Lý do chặn định giá:</b>
            <ul>
              {hardRejects.map(reasonItem => <li key={reasonItem}>{reasonItem}</li>)}
            </ul>
          </div>
        )}

        <div className="v-blocked-note">
          QPort chỉ công bố phần định giá chi tiết (Giá trị Thực, Biên An Toàn, kịch bản Bear/Base/Bull,
          Mô hình định giá, Ma trận độ nhạy) cho doanh nghiệp đạt chuẩn chất lượng Buffett/Munger.
          Doanh nghiệp này chưa đạt chuẩn nên phần định giá chi tiết không được hiển thị.
        </div>

        {crawlEnabled && onCrawl && (
          <div className="v-crawl-panel">
            <button className="v-crawl-btn v-crawl-btn-lg" type="button" onClick={onCrawl} disabled={crawling}>
              {crawling ? '⏳ Đang cập nhật dữ liệu TCBS…' : '⬇ Cập nhật dữ liệu TCBS (7–10 năm lịch sử)'}
            </button>
            <p className="v-crawl-hint">
              Crawl lịch sử BCTC từ TCBS để hoàn thiện mô hình định giá (full-cycle). Cần Bearer token TCBS trên local.
            </p>
            {crawlMessage && (
              <div className={`v-crawl-message ${crawlMessage.ok ? 'ok' : 'err'}`} role="status">{crawlMessage.text}</div>
            )}
          </div>
        )}
      </div>
    );
  }

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

      {/* Cảnh báo định giá (feedback 31/08): không đạt chuẩn Buffett/Munger */}
      {hasValuationWarning && (
        <div className="v-warning-banner" role="alert">
          <span className="v-warning-icon">⚠️</span>
          <div className="v-warning-text">
            <b>KHÔNG CÔNG BỐ GIÁ TRỊ THỰC (IV) & BIÊN AN TOÀN (MOS)</b>
            <p>{report.valuation_warning}</p>
          </div>
        </div>
      )}

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
      {(() => {
        const munger = report.munger_analysis || {};
        const decision = munger.long_term_decision || {};
        const normPower = munger.normalized_earning_power || {};
        const durability = munger.earnings_durability || {};

        return (
          <div className="v-narrative-card">
            <div className="v-narrative-header">
              <div className="v-narrative-title-wrap">
                <span className="v-narrative-badge-icon">✦</span>
                <h3 className="v-narrative-title">NHẬN ĐỊNH CHUYÊN SÂU · BUFFETT–MUNGER</h3>
              </div>
              {(decision.state || assessment.valuation_status) && (
                <span className={`v-verdict-pill ${verdictPillClass(decision.state || assessment.valuation_status)}`}>
                  {decision.state_vietnamese || verdictLabel(assessment.valuation_status)}
                </span>
              )}
            </div>

            <div className="v-narrative-meta-grid">
              <div className="v-meta-item">
                <span className="v-meta-label">NGÀNH NGHỀ KINH DOANH</span>
                <span className="v-meta-value">{archetypeLabel(arch.archetype)}</span>
                <span className="v-meta-sub">
                  {formatCompounderClassification(munger.compounder_classification) || (arch.recommended_model ? valuationModelLabel(arch.recommended_model) : '')}
                </span>
              </div>
              {quality.total_score != null && (
                <div className="v-meta-item">
                  <span className="v-meta-label">ĐIỂM CHẤT LƯỢNG & ĐỘ BỀN</span>
                  <span className="v-meta-value">{quality.total_score}/100</span>
                  <span className="v-meta-sub">
                    {durability.profitable_years != null ? (
                      `Bền bỉ: ${durability.profitable_years}/${durability.total_years} năm · CV ${durability.pat_volatility != null ? (durability.pat_volatility * 100).toFixed(1) : 0}%`
                    ) : (
                      quality.tier ? qualityTierLabel(quality.tier) : ''
                    )}
                  </span>
                </div>
              )}
              {publicMos != null && Number.isFinite(Number(publicMos)) && (
                <div className="v-meta-item">
                  <span className="v-meta-label">BIÊN AN TOÀN THỰC TẾ</span>
                  <span className={`v-meta-value ${publicMos > 0 ? 'pos' : publicMos < 0 ? 'neg' : ''}`}>
                    {publicMos > 0 ? '+' : ''}{Number(publicMos).toFixed(1)}%
                  </span>
                  {mosAnalysis.required_mos_pct != null && (
                    <span className="v-meta-sub">
                      Yêu cầu ≥ {mosAnalysis.required_mos_pct}% · {publicMos >= mosAnalysis.required_mos_pct ? 'Đạt chuẩn' : 'Chưa đạt'}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* 3-Scenario Range Track - Only if scenarios exist */}
            {hasScenarios && (
              <div className="v-scenarios-panel">
                <div className="v-scenario-header-row">
                  <span className="v-scenario-title">GIÁ TRỊ NỘI TẠI · 3 KỊCH BẢN</span>
                  <span className="v-scenario-base-num" style={{ whiteSpace: 'nowrap' }}>{money(base.intrinsic_value_per_share, locale)}</span>
                </div>
                <div className="v-scenario-track">
                  <div className="v-scenario-node node-bear">
                    <span className="node-tag">THẬN TRỌNG</span>
                    <span className="node-price">{money(bear.intrinsic_value_per_share, locale)}</span>
                  </div>
                  <div className="v-scenario-arrow">⟶</div>
                  <div className="v-scenario-node node-base is-active">
                    <span className="node-tag">CƠ SỞ (BASE)</span>
                    <span className="node-price">{money(base.intrinsic_value_per_share, locale)}</span>
                  </div>
                  <div className="v-scenario-arrow">⟶</div>
                  <div className="v-scenario-node node-bull">
                    <span className="node-tag">LẠC QUAN</span>
                    <span className="node-price">{money(bull.intrinsic_value_per_share, locale)}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Primary Decision Narrative */}
            {decision.primary_reason ? (
              <div className="v-narrative-box" style={{ borderLeft: `4px solid ${decision.state === 'BUY' ? '#16a34a' : (decision.state === 'WAIT_FOR_MOS' ? '#0284c7' : '#d97706')}` }}>
                <h4 className="v-box-title">LUẬN ĐIỂM QUYẾT ĐỊNH ĐẦU TƯ DÀI HẠN</h4>
                <p className="v-box-text">{decision.primary_reason}</p>
              </div>
            ) : assessment.financial_resilience_diagnosis && (
              <div className="v-narrative-box">
                <h4 className="v-box-title">CẤU TRÚC VỐN & SỨC KHỎE TÀI CHÍNH</h4>
                <p className="v-box-text">{assessment.financial_resilience_diagnosis}</p>
              </div>
            )}

            {/* Explicit Decision Conditions (if CONDITIONAL_BUY) */}
            {decision.conditions && decision.conditions.length > 0 && (
              <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', padding: '10px 14px', margin: '12px 0', fontSize: '0.88rem' }}>
                <strong style={{ color: '#92400e', display: 'block', marginBottom: '4px' }}>Điều kiện phân bổ / theo dõi cụ thể:</strong>
                <ul style={{ margin: 0, paddingLeft: '18px', color: '#78350f' }}>
                  {decision.conditions.map((cond, cIdx) => (
                    <li key={cIdx} style={{ marginBottom: '2px' }}>
                      <strong>{cond.metric}:</strong> {cond.reason} (Thực tế: {typeof cond.actual === 'number' ? cond.actual.toLocaleString('vi-VN') : cond.actual} vs Ngưỡng: {typeof cond.threshold === 'number' ? cond.threshold.toLocaleString('vi-VN') : cond.threshold})
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Monitoring Signals / Watch Points (Non-blocking) */}
            {decision.monitoring_reasons && decision.monitoring_reasons.length > 0 && (
              <div style={{ background: 'var(--surface-soft, #f9fafb)', border: '1px solid var(--border, #e5e7eb)', borderRadius: '6px', padding: '10px 14px', margin: '12px 0', fontSize: '0.86rem' }}>
                <strong style={{ color: '#4b5563', display: 'block', marginBottom: '4px' }}>Chỉ tiêu giám sát định kỳ (Monitoring Signals — Không phải lỗi chặn mua):</strong>
                <ul style={{ margin: 0, paddingLeft: '18px', color: '#4b5563' }}>
                  {decision.monitoring_reasons.map((mr, mIdx) => (
                    <li key={mIdx} style={{ marginBottom: '2px' }}>{mr}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Hard Blockers (if any) */}
            {decision.blocking_reasons && decision.blocking_reasons.length > 0 && (
              <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '6px', padding: '10px 14px', margin: '12px 0', fontSize: '0.86rem' }}>
                <strong style={{ color: '#991b1b', display: 'block', marginBottom: '4px' }}>Rào cản chất lượng chặn mua (Hard Blockers):</strong>
                <ul style={{ margin: 0, paddingLeft: '18px', color: '#991b1b' }}>
                  {decision.blocking_reasons.map((br, bIdx) => (
                    <li key={bIdx} style={{ marginBottom: '2px' }}>{br}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Normalized Earning Power Insight */}
            {normPower && normPower.normalized_5y != null && (
              <div className="v-narrative-box" style={{ marginTop: '12px' }}>
                <h4 className="v-box-title">SỨC KIẾM TIỀN CHUẨN HÓA LỊCH SỬ</h4>
                <p className="v-box-text">{normPower.explanation || `Lợi nhuận chuẩn hóa 5 năm: ${normPower.normalized_5y?.toLocaleString('vi-VN')} đ (so với gần nhất: ${normPower.reported_latest?.toLocaleString('vi-VN')} đ).`}</p>
              </div>
            )}

            {report.sector_conflict_warning && (
              <div className="v-narrative-box v-warning-box">
                <h4 className="v-box-title">⚠️ PHÂN LOẠI NGÀNH CHUYÊN BIỆT</h4>
                <p className="v-box-text">{report.sector_conflict_warning}</p>
              </div>
            )}

            <HistoricalResolutionsBlock report={report} locale={locale} />
          </div>
        );
      })()}

      {/* Major Section: "Vì sao Giá trị Thực cơ sở = ... ₫?" with minor sections 01, 02, 03, 04 */}
      <ValuationRationale report={report} locale={locale} />

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

              {pillars.financial_fortress && (() => {
                const fort = pillars.financial_fortress;
                const isBank = fort.is_bank || arch.archetype === 'BANK';
                const isSec = fort.is_financial && !isBank;

                const name = isBank
                  ? '2. Pháo đài Tài chính · Đòn bẩy TS'
                  : (isSec ? '2. Pháo đài Tài chính · Đòn bẩy TS' : '2. Pháo đài Tài chính · Nợ / VCSH');

                const mainVal = isBank || isSec
                  ? (fort.bank_leverage != null ? `${fort.bank_leverage}x` : (fort.solvency_display || 'An toàn'))
                  : (fort.debt_payback_years === 0 ? '0 năm' : (fort.debt_payback_years != null ? `${fort.debt_payback_years} năm` : (fort.solvency_display || '0x')));

                const subLabel = isBank
                  ? `Đòn bẩy Tài sản${fort.equity_to_assets_pct != null ? ` · Đệm vốn ${fort.equity_to_assets_pct}%` : ''}`
                  : (isSec
                    ? 'Đòn bẩy Tài sản (TS/VCSH)'
                    : (fort.debt_payback_years === 0 ? 'Tiền mặt ròng (Không áp lực nợ)' : 'Thời gian trả hết Nợ bằng Dòng tiền'));

                return (
                  <div className="v-pillar-card">
                    <div className="v-pillar-head">
                      <span className="v-pillar-name">{name}</span>
                      {fort.status && (
                        <span className="v-pillar-tag">
                          {fort.status === 'STRONG' || fort.status === 'FORTRESS' ? 'Rất Vững' : fort.status === 'HEALTHY' ? 'Lành mạnh' : 'Cần chú ý'}
                        </span>
                      )}
                    </div>
                    <div className="v-pillar-metric">
                      <span className="v-pillar-val">{mainVal}</span>
                      <span className="v-pillar-sub">{subLabel}</span>
                    </div>
                    {fort.diagnosis && (
                      <p className="v-pillar-desc">{fort.diagnosis}</p>
                    )}
                  </div>
                );
              })()}

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

export default function ValuationDetailOverlay({ symbol, report: initialReport, error: initialError, locale = 'vi', onClose, crawlEnabled }) {
  const [report, setReport] = useState(initialReport || null);
  const [error, setError] = useState(initialError || null);
  const [loading, setLoading] = useState(!initialReport && !initialError);
  const [crawling, setCrawling] = useState(false);
  const [crawlMessage, setCrawlMessage] = useState(null);
  const [showTokenPrompt, setShowTokenPrompt] = useState(false);
  const [crawlErrorDetail, setCrawlErrorDetail] = useState(null);
  const [exporting, setExporting] = useState(false);
  // Mặc định hiện nút crawl; chỉ ẩn khi backend trả rõ crawl_enabled=false (Vercel).
  const [crawlEnabledState, setCrawlEnabledState] = useState(crawlEnabled !== false);

  const handleExport = async () => {
    if (!symbol || !report || exporting) return;
    setExporting(true);
    try {
      await downloadReportAIExport(symbol, report);
    } catch (err) {
      console.error('Symbol AI export failed:', symbol, err?.message || err);
    } finally {
      setExporting(false);
    }
  };

  const handleCrawl = async () => {
    if (!symbol || crawling) return;
    setCrawling(true);
    setCrawlMessage(null);
    setCrawlErrorDetail(null);
    try {
      const res = await crawlValuationHistory(symbol);
      if (res?.crawl_enabled !== undefined) setCrawlEnabledState(res.crawl_enabled);
      if (res?.ok === false) {
        setCrawlMessage({ ok: false, text: res?.error || 'Không thể crawl dữ liệu TCBS.' });
      } else {
        const successCount = res?.success_count != null ? Number(res.success_count) : (res?.imported_documents ?? res?.documents_processed ?? null);
        const summary = res?.message || null;
        if (successCount != null && successCount === 0) {
          setCrawlMessage({ ok: false, text: summary || 'Crawl xong nhưng không nhập được kỳ nào — kiểm tra token TCBS / nguồn dữ liệu.' });
        } else {
          setCrawlMessage({ ok: true, text: summary || `Đã cập nhật ${successCount ?? ''} kỳ dữ liệu TCBS vào DB. Đang tải lại định giá…` });
        }
        const repRes = await getValuationReport(symbol);
        const rep = repRes?.report || repRes;
        if (repRes?.crawl_enabled !== undefined) setCrawlEnabledState(repRes.crawl_enabled);
        if (repRes?.ok === false || !rep) {
          setError({ code: repRes?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: repRes?.error || 'Không thể tải dữ liệu định giá.' });
        } else {
          setReport(rep);
          setError(null);
        }
      }
    } catch (err) {
      if (err?.code === 'TCBS_AUTH_REQUIRED') {
        setCrawlErrorDetail(err?.message || 'Yêu cầu Bearer token TCBS.');
        setShowTokenPrompt(true);
      } else if (err?.code === 'CRAWL_DISABLED_ON_VERCEL') {
        setCrawlEnabledState(false);
        setCrawlMessage({ ok: false, text: 'Crawl dữ liệu TCBS chỉ khả dụng trên local/worker (Vercel là database-read-only).' });
      }
      setCrawlMessage({ ok: false, text: err?.message || 'Crawl TCBS thất bại.' });
    } finally {
      setCrawling(false);
    }
  };

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
      // Still learn crawl availability (local vs Vercel) even with an initial report.
      getCrawlStatus().then(res => {
        if (res?.crawl_enabled !== undefined) setCrawlEnabledState(res.crawl_enabled);
      }).catch(() => {});
      return undefined;
    }
    let active = true;
    setLoading(true);
    setError(null);
    getValuationReport(symbol)
      .then(res => {
        if (!active) return;
        if (res?.crawl_enabled !== undefined) setCrawlEnabledState(res.crawl_enabled);
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
  const mos = report?.public_mos ?? report?.margin_of_safety_pct ?? null;

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

        .v-crawl-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          border-radius: 6px;
          background: var(--retro-indigo, #2b4c7e);
          border: 1.5px solid var(--retro-indigo, #2b4c7e);
          color: #ffffff;
          font-size: 0.78rem;
          font-weight: 700;
          cursor: pointer;
          white-space: nowrap;
          transition: all 0.15s ease;
        }
        .v-crawl-btn:hover:not(:disabled) {
          filter: brightness(1.1);
          box-shadow: 0 2px 6px rgba(43, 76, 126, 0.3);
        }
        .v-crawl-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .v-ai-export-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          border-radius: 6px;
          background: var(--retro-green, #2f6b4d);
          border: 1.5px solid var(--retro-green, #2f6b4d);
          color: #ffffff;
          font-size: 0.78rem;
          font-weight: 700;
          cursor: pointer;
          white-space: nowrap;
          transition: all 0.15s ease;
        }
        .v-ai-export-btn:hover:not(:disabled) {
          filter: brightness(1.1);
          box-shadow: 0 2px 6px rgba(47, 107, 77, 0.3);
        }
        .v-ai-export-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .v-crawl-message {
          font-size: 0.74rem;
          line-height: 1.4;
          max-width: 260px;
        }
        .v-crawl-message.ok { color: #1e7e46; }
        .v-crawl-message.err { color: #b03a2e; }

        .v-crawl-panel {
          margin-top: 14px;
          padding: 14px 16px;
          border-radius: 8px;
          background: linear-gradient(180deg, #f0f4fb, #e8eef8);
          border: 1.5px solid var(--retro-indigo, #2b4c7e);
        }
        .v-crawl-btn-lg {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 12px 18px;
          font-size: 0.9rem;
          font-weight: 800;
          border-radius: 8px;
          background: var(--retro-indigo, #2b4c7e);
          border: 1.5px solid var(--retro-indigo, #2b4c7e);
          color: #ffffff;
          cursor: pointer;
          width: 100%;
          justify-content: center;
        }
        .v-crawl-btn-lg:hover:not(:disabled) {
          filter: brightness(1.1);
          box-shadow: 0 3px 8px rgba(43, 76, 126, 0.3);
        }
        .v-crawl-btn-lg:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }
        .v-crawl-hint {
          margin: 8px 0 0 0;
          font-size: 0.78rem;
          line-height: 1.5;
          color: var(--retro-indigo, #2b4c7e);
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
        .v-meta-grid {
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
          font-size: 0.78rem;
          font-weight: 800;
          letter-spacing: 0.06em;
          color: var(--retro-indigo, #2b4c7e);
          text-transform: uppercase;
        }
        .v-meta-value {
          font-size: 1.28rem;
          font-weight: 800;
          color: var(--retro-ink, #201d18);
          line-height: 1.25;
          text-align: left !important;
        }
        .v-meta-value.pos { color: #1e7e46 !important; text-align: left !important; }
        .v-meta-value.neg { color: #b03a2e !important; text-align: left !important; }
        .v-meta-sub {
          font-size: 0.88rem;
          font-weight: 600;
          color: var(--retro-muted, #736b5e);
          line-height: 1.4;
          text-align: left !important;
        }
        .v-confidence {
          display: inline-flex;
          align-items: center;
          margin-top: 4px;
          padding: 3px 10px;
          border-radius: 999px;
          font-size: 0.8rem;
          font-weight: 800;
          letter-spacing: 0.03em;
        }
        .v-confidence.conf-high {
          color: #1e7e46;
          background: rgba(30, 126, 70, 0.12);
          border: 1px solid rgba(30, 126, 70, 0.4);
        }
        .v-confidence.conf-medium {
          color: #b7791f;
          background: rgba(183, 121, 31, 0.12);
          border: 1px solid rgba(183, 121, 31, 0.4);
        }
        .v-confidence.conf-low {
          color: #b03a2e;
          background: rgba(176, 58, 46, 0.12);
          border: 1px solid rgba(176, 58, 46, 0.45);
          animation: vPulse 1.6s ease-in-out infinite;
        }
        @keyframes vPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(176, 58, 46, 0.3); }
          50% { box-shadow: 0 0 0 5px rgba(176, 58, 46, 0); }
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

        .v-warning-banner {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          margin: 10px 0 12px 0;
          padding: 12px 14px;
          border-radius: 8px;
          background: #fdecea;
          border: 1.5px solid #d9534f;
          color: #a63f30;
        }
        .v-warning-icon {
          font-size: 1.1rem;
          line-height: 1.3;
        }
        .v-warning-text b {
          font-size: 0.78rem;
          letter-spacing: 0.04em;
        }
        .v-warning-text p {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.5;
        }

        .v-missing-data {
          margin: 0 0 12px 0;
          padding: 14px 16px;
          border-radius: 8px;
          background: linear-gradient(180deg, #fdf8ee, #f7efdd);
          border: 1.5px solid var(--retro-border, #9c927f);
        }
        .v-missing-header {
          display: flex;
          align-items: flex-start;
          gap: 10px;
        }
        .v-missing-icon {
          font-size: 1.2rem;
          line-height: 1.3;
        }
        .v-missing-title-wrap {
          display: flex;
          flex-direction: column;
          gap: 3px;
        }
        .v-missing-title-wrap b {
          font-size: 0.82rem;
          letter-spacing: 0.03em;
          color: var(--retro-indigo, #2b4c7e);
        }
        .v-missing-sub {
          font-size: 0.76rem;
          color: var(--retro-muted, #736b5e);
        }
        .v-missing-list {
          margin: 10px 0 0 0;
          padding: 0;
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 7px;
        }
        .v-missing-list li {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          font-size: 0.85rem;
          line-height: 1.45;
          color: var(--retro-ink, #201d18);
          background: #fff;
          border: 1px solid var(--retro-border, #d8d0bd);
          border-radius: 6px;
          padding: 8px 10px;
        }
        .v-missing-bullet {
          color: var(--retro-indigo, #2b4c7e);
          font-weight: 800;
          line-height: 1.2;
        }
        .v-missing-reasons {
          margin-top: 10px;
          font-size: 0.78rem;
          color: var(--retro-muted, #736b5e);
        }
        .v-missing-reasons summary {
          cursor: pointer;
          font-weight: 600;
        }
        .v-missing-reasons ul {
          margin: 6px 0 0 0;
          padding-left: 18px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          color: var(--retro-ink, #201d18);
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

        /* Responsive Mobile Sheet (< 720px) - Full-Height Ergonomic Experience
           Laws of UX: Jakob (standard full-screen sheet), Fitts (44px close target),
           Hick (decluttered header), Proximity (verdict grouped), Postel (wrap, never clip). */
        @media (max-width: 719px) {
          /* Nút Xuất AI từng mã chỉ hiển thị trên desktop (>= 720px) */
          .v-ai-export-btn {
            display: none;
          }
          .v-overlay-backdrop {
            position: fixed;
            inset: 0;
            z-index: 99999;
            padding: 0;
            align-items: stretch;
            justify-content: stretch;
            background: rgba(0, 0, 0, 0.75);
            overscroll-behavior: contain;
          }
          .v-overlay-modal {
            position: fixed;
            inset: 0;
            width: 100vw;
            max-width: 100vw;
            height: 100vh;
            max-height: 100vh;
            height: 100dvh;
            max-height: 100dvh;
            min-height: 0;
            border-radius: 0;
            border: none;
            box-shadow: none;
            display: flex;
            flex-direction: column;
            background: var(--surface-bg, #fbf7ee);
          }
          .v-modal-grabber {
            display: none;
          }
          /* Decluttered header: title block wraps, verdict gets its own row, close is pinned (Fitts) */
          .v-overlay-header {
            position: relative;
            display: flex;
            flex-wrap: wrap;
            align-items: flex-start;
            justify-content: flex-start;
            gap: 8px;
            padding: calc(10px + env(safe-area-inset-top, 0px)) 62px 10px 14px;
            border-bottom: 1.5px solid var(--retro-border, #9c927f);
            background: var(--surface-soft, #f4ecd9);
            flex-shrink: 0;
          }
          .v-header-left {
            flex: 1 1 100%;
            min-width: 0;
            gap: 3px;
          }
          .v-header-title-row {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
          }
          .v-header-ticker {
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.1;
            flex-shrink: 0;
          }
          .v-tag {
            font-size: 0.7rem;
            padding: 2px 6px;
            white-space: nowrap;
          }
          .v-header-sub-row {
            font-size: 0.74rem;
            white-space: normal;
          }
          .v-header-actions {
            order: 2;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 8px;
          }
          .v-status-badge {
            padding: 5px 10px;
            font-size: 0.78rem;
            white-space: normal;
          }
          .v-close-btn {
            position: absolute;
            top: calc(10px + env(safe-area-inset-top, 0px));
            right: 12px;
            width: 44px;
            min-width: 44px;
            height: 44px;
            min-height: 44px;
            font-size: 1.25rem;
            border-radius: 10px;
          }
          .v-overlay-body {
            flex: 1;
            min-height: 0;
            overflow-y: auto;
            padding: 14px 14px calc(36px + env(safe-area-inset-bottom, 0px));
            -webkit-overflow-scrolling: touch;
            overscroll-behavior: contain;
          }
          /* Hero / cards: shrink-proof children, long VND values wrap instead of clipping (Postel) */
          .v-hero-grid {
            grid-template-columns: 1fr;
            gap: 8px;
            margin-bottom: 12px;
          }
          .v-hero-card,
          .v-metric-card,
          .v-meta-item,
          .v-pillar-card,
          .v-bridge-item {
            min-width: 0;
          }
          .v-hero-card {
            padding: 12px 14px;
          }
          .v-hero-value {
            font-size: clamp(1.15rem, 6.5vw, 1.4rem);
            white-space: normal;
            overflow-wrap: anywhere;
          }
          .v-multiples-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            margin-bottom: 12px;
          }
          .v-metric-card {
            padding: 8px 10px;
          }
          .v-metric-value {
            font-size: clamp(0.95rem, 5vw, 1.15rem);
            white-space: normal;
            overflow-wrap: anywhere;
          }
          .v-narrative-card {
            padding: 14px 12px;
            margin-bottom: 12px;
            gap: 12px;
          }
          .v-narrative-meta-grid,
          .v-meta-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 12px 14px;
          }
          .v-meta-item {
            display: flex;
            flex-direction: column;
            gap: 3px;
            text-align: left;
          }
          .v-meta-label {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            color: var(--retro-indigo, #2b4c7e);
            text-align: left;
          }
          .v-meta-value {
            white-space: normal;
            overflow-wrap: anywhere;
            font-size: clamp(1.1rem, 5.5vw, 1.28rem);
            text-align: left !important;
          }
          .v-meta-value.pos {
            color: #1e7e46 !important;
            text-align: left !important;
          }
          .v-meta-value.neg {
            color: #b03a2e !important;
            text-align: left !important;
          }
          .v-meta-sub {
            font-size: 0.82rem;
            color: var(--retro-muted, #736b5e);
            line-height: 1.35;
            text-align: left !important;
          }
          .v-scenario-header-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 6px;
            margin-bottom: 8px;
          }
          .v-scenario-title {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.03em;
            white-space: nowrap;
          }
          .v-scenario-base-num {
            font-size: 1.15rem;
            font-weight: 800;
            white-space: nowrap;
            text-align: right;
            color: var(--retro-indigo, #2b4c7e);
          }
          .v-scenario-track {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 6px;
            align-items: stretch;
          }
          .v-scenario-node {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            gap: 3px;
            padding: 8px 2px;
            min-width: 0;
            border-radius: 6px;
            border: 1px solid var(--retro-border, #9c927f);
            background: var(--surface-soft, #f4ecd9);
          }
          .v-scenario-node.is-active {
            border-color: var(--retro-indigo, #2b4c7e);
            background: color-mix(in srgb, var(--retro-indigo, #2b4c7e) 10%, var(--panel, #fffaf0));
            box-shadow: 0 0 0 1px var(--retro-indigo, #2b4c7e);
          }
          .v-scenario-node .node-tag {
            font-size: 0.60rem;
            font-weight: 700;
            color: var(--retro-muted, #696257);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
            letter-spacing: 0.01em;
          }
          .v-scenario-node .node-price {
            margin-top: 0;
            font-size: clamp(0.78rem, 3.8vw, 0.88rem);
            font-weight: 800;
            font-family: var(--font-mono-num, monospace);
            color: var(--text, #201d18);
            white-space: nowrap;
          }
          .v-scenario-node.is-active .node-price {
            color: var(--retro-indigo, #2b4c7e);
          }
          .v-scenario-arrow {
            display: none;
          }
          .v-pillars-grid {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          .v-pillar-card {
            padding: 12px;
          }
          .v-bridge-grid {
            grid-template-columns: 1fr;
            gap: 6px;
          }
        }
      `}</style>

      <div className="v-overlay-modal" onClick={e => e.stopPropagation()}>
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
              Kỳ BCTC: <strong>{report?.fiscal_period_latest || 'Năm 2025'}</strong>
            </div>
          </div>

          <div className="v-header-actions">
            {assessment.valuation_status && (
              <ValuationStatusPill status={assessment.valuation_status} marginOfSafety={mos} />
            )}
            <button
              className="v-ai-export-btn"
              type="button"
              onClick={handleExport}
              disabled={exporting || !report}
              title="Xuất báo cáo AI (định giá chi tiết + 10 năm tài chính) cho cổ phiếu này"
            >
              {exporting ? '⏳ Đang xuất…' : '🤖 Xuất AI'}
            </button>
            {(report && crawlEnabledState !== false && (report.valuation_warning || (Array.isArray(report.missing_data) && report.missing_data.length > 0) || report.model_status !== 'MODEL_VERIFIED')) && (
              <>
                <button
                  className="v-crawl-btn"
                  type="button"
                  onClick={handleCrawl}
                  disabled={crawling}
                  title="Crawl lịch sử BCTC (7–10 năm) từ TCBS để hoàn thiện mô hình định giá (cần TCBS_BEARER_TOKEN trên server)"
                >
                  {crawling ? '⏳ Đang cập nhật…' : '⬇ Cập nhật dữ liệu TCBS'}
                </button>
                {crawlMessage && (
                  <span className={`v-crawl-message ${crawlMessage.ok ? 'ok' : 'err'}`} role="status">
                    {crawlMessage.text}
                  </span>
                )}
              </>
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
            <ValuationReportBody
              symbol={symbol}
              report={report}
              locale={locale}
              onCrawl={handleCrawl}
              crawling={crawling}
              crawlMessage={crawlMessage}
              crawlEnabled={crawlEnabledState !== false}
            />
          )}
        </main>
      </div>
    </div>
  );

  if (typeof document !== 'undefined' && document.body) {
    return (
      <>
        {createPortal(overlayElement, document.body)}
        {showTokenPrompt && (
          <TcbsTokenPrompt
            symbol={symbol}
            errorDetail={crawlErrorDetail}
            onClose={() => setShowTokenPrompt(false)}
            onSuccess={() => {
              setShowTokenPrompt(false);
              setCrawlMessage({ ok: true, text: 'Token đã lưu. Đang tải lại định giá…' });
              getValuationReport(symbol)
                .then(res => {
                  const rep = res?.report || res;
                  if (res?.ok === false || !rep) {
                    setError({ code: res?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: res?.error || 'Không thể tải dữ liệu định giá.' });
                  } else { setReport(rep); setError(null); }
                })
                .catch(err => setError({ code: err?.code, message: err?.message }));
            }}
          />
        )}
      </>
    );
  }
  return overlayElement;
}
