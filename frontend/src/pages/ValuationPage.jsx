import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getValuationReports } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { formatMoney } from '../lib/format.js';

function displayNumber(value, suffix = '', digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(digits)}${suffix}`;
}

function money(value, locale) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${formatMoney(value, false, locale)} ₫`;
}

function MethodologyGuide() {
  return <section className="valuation-methodology">
    <div className="valuation-methodology-head">
      <span className="eyebrow">Nguyên lý Đầu tư Giá trị Buffett–Munger</span>
      <h2>QPort xác định Giá trị Thực của doanh nghiệp như thế nào?</h2>
    </div>
    <div className="valuation-method-grid">
      <article>
        <b>01 · Chuẩn hóa Báo cáo Tài chính</b>
        <p>Lấy dữ liệu kiểm toán 10 năm: Lợi nhuận sau thuế, khấu hao, chi phí đầu tư tài sản, nợ vay, lượng tiền mặt và số cổ phần lưu hành. Bóc tách cổ tức cổ phiếu để không gây nhầm lẫn pha loãng.</p>
      </article>
      <article>
        <b>02 · Lợi nhuận Thực của Chủ Doanh nghiệp</b>
        <p><code>Lợi nhuận Thực = Lợi nhuận ròng + Khấu hao − Chi phí đầu tư duy trì ± Biến động vốn lưu động</code>. Phản ánh đúng lượng tiền mặt thực tế người chủ có thể rút ra hàng năm.</p>
      </article>
      <article>
        <b>03 · Dải Định giá 3 Kịch bản</b>
        <p>Xây dựng 3 kịch bản: Thận trọng (Bear) / Cơ sở (Base) / Lạc quan (Bull). Với Ngân hàng, dùng Mô hình Thu nhập Thặng dư (RIM); với Doanh nghiệp sản xuất, dùng Chiết khấu dòng tiền thực bình quân chu kỳ.</p>
      </article>
      <article>
        <b>04 · Thước đo Biên An Toàn Động</b>
        <p>Biên an toàn được tính toán động (20% – 50%) dựa trên rủi ro ngành, mức độ thâm dụng vốn và chất lượng quản trị, giúp bảo vệ vốn trước mọi biến động bất ngờ của thị trường.</p>
      </article>
    </div>
    <p className="valuation-method-warning">Dữ liệu tài chính được chuẩn hóa từ nguồn chính thức của sàn chứng khoán. Hệ thống phục vụ mục đích thông tin và theo dõi danh mục dài hạn (Buy & Hold).</p>
  </section>;
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
  const base = report.scenarios?.BASE || {};
  const bear = report.scenarios?.BEAR || {};
  const bull = report.scenarios?.BULL || {};
  const bridge = report.owner_earnings_bridge || {};
  const assessment = report.assessment || {};
  const quality = report.quality_scorecard || {};
  const arch = report.archetype_profile || {};
  const mosAnalysis = report.margin_of_safety_analysis || {};
  const scenarios = ['BEAR', 'BASE', 'BULL'];
  const freshness = report.data_freshness || {};
  const mos = base.margin_of_safety_pct;

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

    {/* Expert Financial Analysis Narrative */}
    <div className="valuation-analyst-opinion">
      <div className="opinion-header">
        <span className="opinion-badge">Nhận định Chuyên sâu theo Chuẩn Buffett–Munger</span>
      </div>
      <p className="opinion-verdict">{assessment.valuation_verdict}</p>
      {assessment.financial_resilience_diagnosis && (
        <div className="opinion-subtext">
          <small><strong>Cấu trúc vốn & Sức khỏe tài chính:</strong> {assessment.financial_resilience_diagnosis}</small>
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
            <span className="pillar-val">{report.value_investor_pillars.earnings_quality?.avg_cash_conversion_5y != null ? `${report.value_investor_pillars.earnings_quality.avg_cash_conversion_5y}%` : '—'}</span>
            <span className="pillar-sub">Tỷ lệ đổi LNST ra Tiền mặt (5 năm)</span>
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
        {/* Sensitivity Analysis Matrix 2D (r vs gT) */}
        {report.sensitivity_matrix?.grid_values_per_share && (
          <div className="tech-section">
            <h4>Bảng Độ nhạy Định giá theo Tỷ lệ Chiết khấu (r) và Tăng trưởng Dài hạn (g)</h4>
            <div className="sensitivity-matrix-container">
              <table className="sensitivity-matrix-table">
                <thead>
                  <tr>
                    <th>Tăng trưởng (g) \ Chiết khấu (r)</th>
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
            <small className="matrix-note">* Ô viền vàng nổi bật là Kịch bản Cơ sở (Chiết khấu 11%, Tăng trưởng dài hạn 3.5%).</small>
          </div>
        )}

        <div className="tech-section">
          <h4>Bóc tách Lợi nhuận Thực của Chủ Doanh nghiệp (Owner Earnings)</h4>
          <dl className="valuation-calculation-grid">
            <div><dt>Lợi nhuận sau thuế</dt><dd>{money(bridge.net_income, locale)}</dd></div>
            <div><dt>Khấu hao tài sản</dt><dd>{money(bridge.depreciation_amortization, locale)}</dd></div>
            <div><dt>Đầu tư duy trì nhà xưởng</dt><dd>{money(bridge.maintenance_capex, locale)}</dd></div>
            <div><dt>Lợi nhuận Thực tạo ra</dt><dd>{money(bridge.owner_earnings, locale)}</dd></div>
          </dl>
        </div>

        <div className="tech-section">
          <h4>Ba Kịch bản Định giá Chi tiết</h4>
          <div className="valuation-scenarios">
            {scenarios.map(name => {
              const scenario = report.scenarios?.[name] || {};
              const labelVn = name === 'BEAR' ? 'Thận trọng (Bear)' : name === 'BASE' ? 'Cơ sở (Base)' : 'Lạc quan (Bull)';
              return <div key={name} className={`scenario-card scenario-${name.toLowerCase()}`}>
                <div className="scenario-head">
                  <b>{labelVn}</b>
                  <span>{money(scenario.intrinsic_value_per_share, locale)}</span>
                </div>
                <small>Tăng trưởng dự phóng: {displayNumber(Number(scenario.growth_stage1_rate) * 100, '%')} · Tỷ lệ chiết khấu: {displayNumber(Number(scenario.discount_rate) * 100, '%')}</small>
              </div>;
            })}
          </div>
        </div>

        <div className="tech-section tech-cross-check">
          <h4>Đối chiếu & Kiểm tra Chéo Năng lực Sinh lời</h4>
          {report.cagr_5y_net_profit != null && (
            <p>• <strong>Tốc độ tăng trưởng Lợi nhuận ròng 5 năm qua:</strong> <span className="highlight-pill">+{displayNumber(report.cagr_5y_net_profit, '%')}/năm</span></p>
          )}
          <p>• <strong>Định giá theo Sức kiếm tiền hiện tại (Không giả định tăng trưởng - EPV):</strong> {money(report.epv_result?.epv_per_share, locale)}/cổ phần.</p>
          <p>• <strong>Kỳ vọng ngầm định từ Thị giá (Reverse DCF):</strong> {report.reverse_dcf_result?.verdict || 'Đang tổng hợp dữ liệu.'}</p>
        </div>

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

export default function ValuationPage({ symbols = [], locale = 'vi' }) {
  const normalized = useMemo(() => [...new Set(symbols.map(value => String(value || '').toUpperCase()).filter(Boolean))], [symbols]);
  const symbolKey = normalized.join(',');
  const [reports, setReports] = useState({});
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState('');

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

  return <div className="app-shell">
    <AppNav active="valuation" locale={locale} />
    <main className="valuation-page">
      <header className="valuation-header">
        <div>
          <span className="eyebrow">BCTC mới nhất theo từng mã</span>
          <h1>Định giá cổ phiếu</h1>
          <p>Mô hình chiết khấu dòng tiền kết hợp lợi nhuận chủ sở hữu (Owner Earnings). Phân tích khách quan theo nguyên lý Giá trị cốt lõi.</p>
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
        <div className="valuation-grid">
          {normalized.map(symbol => {
            if (loading && !reports[symbol] && !errors[symbol]) {
              return <ValuationSkeletonCard key={symbol} symbol={symbol} />;
            }
            return <ValuationCard key={symbol} symbol={symbol} report={reports[symbol]} error={errors[symbol]} locale={locale} />;
          })}
        </div>
      )}
    </main>
  </div>;
}
