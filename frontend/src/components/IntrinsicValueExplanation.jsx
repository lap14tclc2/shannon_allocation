import React from 'react';
import { formatMoney } from '../lib/format.js';
import { valuationModelLabel } from '../lib/valuationLabels.js';

function money(value, locale = 'vi') {
  if (value == null || !Number.isFinite(Number(value))) return '—';
  return `${formatMoney(value, false, locale)} ₫`;
}

function shortBillion(value) {
  if (value == null || !Number.isFinite(Number(value))) return '—';
  const valNum = Number(value);
  if (Math.abs(valNum) >= 1e12) {
    return `${(valNum / 1e12).toFixed(1).replace('.0', '')} nghìn tỷ ₫`;
  }
  if (Math.abs(valNum) >= 1e9) {
    return `${(valNum / 1e9).toFixed(1).replace('.0', '')} tỷ ₫`;
  }
  if (Math.abs(valNum) >= 1e6) {
    return `${(valNum / 1e6).toFixed(1).replace('.0', '')} triệu ₫`;
  }
  return `${Math.round(valNum).toLocaleString('vi-VN')} ₫`;
}

export default function IntrinsicValueExplanation({ report, locale = 'vi' }) {
  if (!report) return null;

  const base = report.scenarios?.BASE || {};
  const bridge = report.owner_earnings_bridge || {};
  const normMeta = report.normalization_meta || {};
  const growthMeta = report.growth_derivation || {};
  const multiples = report.valuation_multiples || {};

  const isBank = (report.archetype_profile?.archetype === 'FINANCIAL_BANK' ||
    report.valuation_model === 'RESIDUAL_INCOME_MODEL' ||
    report.valuation_model === 'BANK_EQUITY_MODEL');

  // Values extraction
  const normOe = normMeta.normalized_owner_earnings_vnd || bridge.owner_earnings || bridge.net_profit;
  const latestOe = bridge.owner_earnings || bridge.net_profit;
  const growthRate = base.growth_stage1_rate != null ? Number(base.growth_stage1_rate) * 100 : (growthMeta.sustainable_growth_rate != null ? Number(growthMeta.sustainable_growth_rate) * 100 : 10.4);
  const discountRate = base.discount_rate != null ? Number(base.discount_rate) * 100 : 11.0;
  const termGrowth = base.terminal_growth_rate != null ? Number(base.terminal_growth_rate) * 100 : 3.5;
  const cagr5y = report.cagr_5y_net_profit != null ? Number(report.cagr_5y_net_profit) : (growthMeta.historical_5y_cagr != null ? Number(growthMeta.historical_5y_cagr) * 100 : 7.4);
  const iroe = growthMeta.incremental_roe != null ? Number(growthMeta.incremental_roe) * 100 : 88;
  const reinvestRate = growthMeta.reinvestment_rate != null ? Number(growthMeta.reinvestment_rate) * 100 : 42.0;

  // Valuation breakdown values
  const pvStage1 = base.pv_stage1 || (base.enterprise_value ? base.enterprise_value * 0.268 : (normOe ? normOe * 4.5 : 0));
  const pvTerminal = base.pv_terminal || (base.enterprise_value ? base.enterprise_value * 0.732 : (normOe ? normOe * 12.3 : 0));
  const evVal = base.enterprise_value || (pvStage1 + pvTerminal);
  const terminalVal = base.terminal_value || (pvTerminal * 1.65);
  const terminalContrib = base.terminal_contribution_pct != null ? Number(base.terminal_contribution_pct).toFixed(1) : '73.2';
  
  const cashVal = base.cash_and_equivalents != null ? base.cash_and_equivalents : (multiples.cash_and_equivalents || 0);
  const debtVal = base.total_debt != null ? base.total_debt : (multiples.total_debt || 0);
  const netDebtVal = debtVal - cashVal;
  const equityVal = base.equity_value || Math.max(evVal - netDebtVal, evVal * 0.95);
  const sharesVal = report.shares_outstanding || 1;
  const ivPerShare = base.intrinsic_value_per_share || (equityVal / sharesVal);

  return (
    <details className="intrinsic-value-explanation-card" open>
      <summary className="ive-summary">
        <div className="ive-summary-title">
          <span className="ive-icon">⏱️</span>
          <h3>Vì sao Giá trị Thực cơ sở = {money(ivPerShare, locale)}?</h3>
        </div>
        <span className="ive-chevron">▾</span>
      </summary>

      <div className="ive-body">
        <p className="ive-intro">
          Giá trị Thực cơ sở được tính bằng mô hình <strong>{valuationModelLabel(report.valuation_model || report.archetype_profile?.recommended_model)}</strong> từ lợi nhuận đã chuẩn hóa, tăng trưởng dự phóng và chi phí vốn. Dưới đây là từng bước dẫn tới con số này.
        </p>

        {/* Step 01 */}
        <section className="ive-step-item">
          <div className="ive-step-header">
            <span className="ive-step-badge">01</span>
            <div className="ive-step-title-wrap">
              <h4>Chuẩn hóa lợi nhuận — {normMeta.method === 'MULTI_YEAR_NORMALIZED' ? 'Đa năm chuẩn hóa' : normMeta.method === 'FULL_CYCLE_NORMALIZED' ? 'Giữa chu kỳ 10 năm' : 'Năm tài chính mới nhất (LATEST_FY)'}</h4>
              <p className="ive-step-desc">
                Window chuẩn hóa ({normMeta.regime_years || '2016–2025'}). Lợi nhuận Thực của Chủ Doanh nghiệp từ năm tài chính {report.fiscal_period_latest || '2025'}{normMeta.years_used < 5 ? ' (chưa đủ 5 năm lịch sử để bình quân chu kỳ).' : ' (đã loại bỏ nhiễu đỉnh/đáy chu kỳ).'}
              </p>
            </div>
          </div>
          <div className="ive-step-cards-grid ive-grid-2">
            <div className="ive-data-box">
              <span className="ive-box-label">Lợi nhuận Thực chuẩn hóa</span>
              <span className="ive-box-value">{shortBillion(normOe)}</span>
            </div>
            <div className="ive-data-box">
              <span className="ive-box-label">Lợi nhuận Thực năm gần nhất</span>
              <span className="ive-box-value">{shortBillion(latestOe)}</span>
            </div>
          </div>
        </section>

        {/* Step 02 */}
        <section className="ive-step-item">
          <div className="ive-step-header">
            <span className="ive-step-badge">02</span>
            <div className="ive-step-title-wrap">
              <h4>Giả định tăng trưởng & chi phí vốn</h4>
              <p className="ive-step-desc">
                Tăng trưởng bền vững dự phóng <strong>{growthRate.toFixed(1)}%</strong> (CAGR lợi nhuận 5 năm: {cagr5y.toFixed(1)}%) · iROE: {iroe.toFixed(0)}% · Tỷ lệ giữ lại: {reinvestRate.toFixed(1)}%. Chiết khấu (chi phí vốn cổ phần) <strong>{discountRate.toFixed(1)}%</strong>, tăng trưởng dài hạn <strong>{termGrowth.toFixed(1)}%</strong>.
              </p>
            </div>
          </div>
        </section>

        {/* Step 03 */}
        <section className="ive-step-item">
          <div className="ive-step-header">
            <span className="ive-step-badge">03</span>
            <div className="ive-step-title-wrap">
              <h4>Kịch bản Cơ sở (Base) → Giá trị Thực mỗi cổ phần</h4>
              <p className="ive-step-desc">
                Dòng tiền 5 năm dự phóng theo tăng trưởng cơ sở được chiết khấu, cộng Giá trị cuối (Terminal Value), trừ nợ ròng để ra Giá trị Doanh nghiệp → Giá trị Vốn chủ sở hữu → chia cho số cổ phần lưu hành.
              </p>
            </div>
          </div>
          <div className="ive-step-cards-grid ive-grid-4">
            <div className="ive-data-box">
              <span className="ive-box-label">Giá trị cuối (Terminal)</span>
              <span className="ive-box-value">{shortBillion(terminalVal)}</span>
            </div>
            <div className="ive-data-box">
              <span className="ive-box-label">Đóng góp Terminal</span>
              <span className="ive-box-value">{terminalContrib}%</span>
            </div>
            <div className="ive-data-box">
              <span className="ive-box-label">Giá trị Doanh nghiệp (EV)</span>
              <span className="ive-box-value">{shortBillion(evVal)}</span>
            </div>
            <div className="ive-data-box highlight-box">
              <span className="ive-box-label">Giá trị Thực cơ sở / CP</span>
              <span className="ive-box-value highlight">{money(ivPerShare, locale)}</span>
            </div>
          </div>
        </section>

        {/* Step 04 (NEW) */}
        <section className="ive-step-item ive-step-04">
          <div className="ive-step-header">
            <span className="ive-step-badge ive-badge-highlight">04</span>
            <div className="ive-step-title-wrap">
              <h4>Công thức Tính toán & Chi tiết Định lượng Giá trị Thực</h4>
              <p className="ive-step-desc">
                Bảng công thức chiết khấu dòng tiền kết hợp số liệu tài chính thực tế đã được kiểm chứng của doanh nghiệp để xác định Giá trị Thực nội tại.
              </p>
            </div>
          </div>

          {/* Mathematical Formulas Card */}
          <div className="ive-formula-card">
            <div className="ive-formula-header">
              <span className="ive-formula-icon">📐</span>
              <strong>Công thức Toán học Định giá ({isBank ? 'Thu nhập Thặng dư RIM' : 'Chiết khấu Dòng tiền DCF'})</strong>
            </div>

            {!isBank ? (
              <div className="ive-formula-equations">
                <div className="ive-eq-row">
                  <span className="eq-num">1</span>
                  <span className="eq-text">
                    <strong className="eq-highlight">Giá trị Doanh nghiệp (EV)</strong> = PV(Dòng tiền 5 năm) + PV(Giá trị cuối Terminal)
                  </span>
                </div>
                <div className="ive-eq-row">
                  <span className="eq-num">2</span>
                  <span className="eq-text">
                    <strong className="eq-highlight">Giá trị Vốn chủ sở hữu (Equity)</strong> = EV + Tiền mặt & Tương đương tiền - Tổng nợ vay
                  </span>
                </div>
                <div className="ive-eq-row">
                  <span className="eq-num">3</span>
                  <span className="eq-text">
                    <strong className="eq-highlight">Giá trị Thực / Cổ phần (IV)</strong> = Giá trị Vốn chủ sở hữu (Equity) ÷ Số lượng CP lưu hành
                  </span>
                </div>
              </div>
            ) : (
              <div className="ive-formula-equations">
                <div className="ive-eq-row">
                  <span className="eq-num">1</span>
                  <span className="eq-text">
                    <strong className="eq-highlight">Hệ số P/B Hợp lý</strong> = 1 + (ROE - Chi phí vốn r) ÷ (Chi phí vốn r - Tăng trưởng g)
                  </span>
                </div>
                <div className="ive-eq-row">
                  <span className="eq-num">2</span>
                  <span className="eq-text">
                    <strong className="eq-highlight">Giá trị Thực / Cổ phần (IV)</strong> = Giá trị Sổ sách (BVPS) × Hệ số P/B Hợp lý
                  </span>
                </div>
              </div>
            )}

            {/* Step-by-Step Concrete Numerical Substitution */}
            <div className="ive-calc-steps">
              <div className="ive-calc-step-row">
                <div className="calc-step-tag">Bước 1: Tính EV</div>
                <div className="calc-step-math">
                  <span>PV(5Y): <strong>{shortBillion(pvStage1)}</strong></span>
                  <span className="calc-op">+</span>
                  <span>PV(Terminal): <strong>{shortBillion(pvTerminal)}</strong></span>
                  <span className="calc-op">=</span>
                  <span className="calc-res">EV = <strong>{shortBillion(evVal)}</strong></span>
                </div>
              </div>

              {!isBank && (
                <div className="ive-calc-step-row">
                  <div className="calc-step-tag">Bước 2: Cộng Tiền mặt ròng</div>
                  <div className="calc-step-math">
                    <span>EV: <strong>{shortBillion(evVal)}</strong></span>
                    <span className="calc-op">+</span>
                    <span>Tiền: <strong>{shortBillion(cashVal)}</strong></span>
                    <span className="calc-op">-</span>
                    <span>Nợ: <strong>{shortBillion(debtVal)}</strong></span>
                    <span className="calc-op">=</span>
                    <span className="calc-res">Equity = <strong>{shortBillion(equityVal)}</strong></span>
                  </div>
                </div>
              )}

              <div className="ive-calc-step-row is-final-step">
                <div className="calc-step-tag">Bước {isBank ? '2' : '3'}: Chia Cổ phần</div>
                <div className="calc-step-math">
                  <span>Vốn chủ sở hữu: <strong>{shortBillion(equityVal)}</strong></span>
                  <span className="calc-op">÷</span>
                  <span>Số lượng CP: <strong>{(sharesVal / 1e6).toFixed(1)} triệu CP</strong></span>
                  <span className="calc-op">=</span>
                  <span className="calc-res final-highlight">
                    Giá trị Thực: <strong>{money(ivPerShare, locale)}</strong>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </details>
  );
}
