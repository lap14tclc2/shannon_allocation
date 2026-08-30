import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import ValuationDetailOverlay, {
  ValuationReportBody,
  ValuationSkeletonCard,
  ValuationStatusPill,
} from '../components/ValuationDetailOverlay.jsx';
import { getValuationReports } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { formatMoney } from '../lib/format.js';
import {
  archetypeLabel,
  modelStatusLabel,
  qualityTierLabel,
  valuationModelLabel,
} from '../lib/valuationLabels.js';

function displayNumber(value, suffix = '', digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(digits)}${suffix}`;
}

function money(value, locale) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${formatMoney(value, false, locale)} ₫`;
}

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

function ValuationCard({ symbol, report, error, locale, onOpenDetail }) {
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
  const arch = report.archetype_profile || {};
  const mosAnalysis = report.margin_of_safety_analysis || {};
  const scenarios = ['BEAR', 'BASE', 'BULL'];
  const freshness = report.data_freshness || {};
  const mos = base.margin_of_safety_pct;

  return <article id={`valuation-${symbol}`} className="valuation-card">
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <ValuationStatusPill status={assessment.valuation_status} marginOfSafety={mos} />
        {onOpenDetail && (
          <button type="button" className="btn-small btn-view-detail" onClick={() => onOpenDetail(symbol)} title={`Mở cửa sổ chi tiết ${symbol}`}>
            Chi tiết ↗
          </button>
        )}
      </div>
    </div>

    {/* Primary Price & Valuation Row */}
    <div className="valuation-price-hero">
      <div className="price-box">
        <span className="price-label">Thị giá hiện tại (VNDirect)</span>
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
          <small style={{ fontSize: '0.72rem', color: 'var(--retro-muted, #696257)', marginTop: '2px', display: 'block' }}>
            Yêu cầu tối thiểu: ≥ {mosAnalysis.required_mos_pct}%
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
            <span className="pillar-sub">Sinh lời ROE 5 năm · Pha loãng: {report.value_investor_pillars.capital_allocation?.share_dilution_5y_pct != null ? `${report.value_investor_pillars.capital_allocation.share_dilution_5y_pct}%` : '0%'}</span>
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
                  <span>{money(scenario.intrinsic_value_per_share, locale)}</span>
                </div>
                <small>Tăng trưởng dự phóng: {displayNumber(Number(scenario.growth_stage1_rate || 0) * 100, '%')} · Tỷ lệ chiết khấu: {displayNumber(Number(scenario.discount_rate || 0) * 100, '%')}</small>
              </div>;
            })}
          </div>
        </div>
      </div>
    </details>

    <footer className="valuation-card-footer">
      <span>Nguồn dữ liệu: Báo cáo Tài chính Kiểm toán ({freshness.provider || multiples.source || 'Sàn chứng khoán'}) · Kỳ BCTC {report.fiscal_period_latest || 'Năm 2025'}</span>
      <span>Thời điểm đồng bộ: {freshness.fetched_at ? new Date(freshness.fetched_at).toLocaleDateString('vi-VN') : 'Mới nhất'}</span>
    </footer>
  </article>;
}

function SymbolTabStrip({ symbols = [], activeSymbol = null, onSelectSymbol }) {
  return (
    <nav className="valuation-symbol-tabs" aria-label="Chuyển nhanh tới mã cổ phiếu">
      {symbols.map(symbol => (
        <button
          key={symbol}
          type="button"
          className={`valuation-symbol-tab ${activeSymbol === symbol ? 'is-active' : ''}`}
          onClick={() => onSelectSymbol?.(symbol)}
        >
          {symbol}
        </button>
      ))}
    </nav>
  );
}

function ValuationOverviewTable({ reports = {}, symbols = [], locale = 'vi', onSelectSymbol }) {
  const validRows = symbols
    .map(sym => ({ sym, rep: reports[sym] }))
    .filter(item => item.rep);

  if (validRows.length <= 1) return null;

  return (
    <div className="valuation-overview-table-wrapper">
      <div className="valuation-overview-header-row">
        <h3 className="valuation-overview-title">Bảng Tổng quan Định giá Toàn bộ Danh mục ({validRows.length} mã)</h3>
        <span className="valuation-overview-hint">💡 Nhấp vào bất kỳ dòng nào để mở cửa sổ chi tiết định giá đầy đủ</span>
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
              <th style={{ textAlign: 'right' }}>Bear IV</th>
              <th style={{ textAlign: 'right' }}>Base IV</th>
              <th style={{ textAlign: 'right' }}>Bull IV</th>
              <th style={{ textAlign: 'right' }}>MOS</th>
              <th style={{ textAlign: 'right' }}>Req MOS</th>
              <th style={{ textAlign: 'center' }}>Kết luận</th>
              <th style={{ textAlign: 'center' }}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {validRows.map(({ sym, rep }) => {
              const base = rep.scenarios?.BASE || {};
              const bear = rep.scenarios?.BEAR || {};
              const bull = rep.scenarios?.BULL || {};
              const mos = base.margin_of_safety_pct;
              const archName = archetypeLabel(rep.archetype_profile?.archetype);
              const modelName = valuationModelLabel(rep.valuation_model || rep.archetype_profile?.recommended_model);
              const mStatus = modelStatusLabel(rep.model_status);
              const isVerified = rep.model_status === 'MODEL_VERIFIED';
              const iv = isVerified ? base.intrinsic_value_per_share : null;
              const pubMos = isVerified ? mos : null;
              const reqMos = rep.margin_of_safety_analysis?.required_mos_pct;
              return (
                <tr key={sym} className="valuation-overview-row clickable" onClick={() => onSelectSymbol?.(sym)} title={`Xem chi tiết định giá ${sym}`}>
                  <td className="td-symbol"><strong>{sym}</strong></td>
                  <td className="td-arch">{archName}</td>
                  <td className="td-model">{modelName}</td>
                  <td className="td-status" style={{ textAlign: 'center' }}>
                    <span className={`model-status-badge ${rep.model_status === 'MODEL_VERIFIED' ? 'status-verified' : 'status-incomplete'}`}>
                      {mStatus}
                    </span>
                  </td>
                  <td className="td-num" style={{ textAlign: 'right' }}>{money(rep.current_market_price, locale)}</td>
                  <td className="td-num td-iv" style={{ textAlign: 'right' }}>
                    {isVerified && bear.intrinsic_value_per_share != null ? money(bear.intrinsic_value_per_share, locale) : 'N/A'}
                  </td>
                  <td className="td-num td-iv" style={{ textAlign: 'right' }}>
                    {iv != null && Number.isFinite(Number(iv)) ? money(iv, locale) : 'N/A'}
                  </td>
                  <td className="td-num td-iv" style={{ textAlign: 'right' }}>
                    {isVerified && bull.intrinsic_value_per_share != null ? money(bull.intrinsic_value_per_share, locale) : 'N/A'}
                  </td>
                  <td className="td-num" style={{ textAlign: 'right', fontWeight: '700', color: pubMos > 0 ? 'var(--retro-green, #2f6b4d)' : pubMos < 0 ? 'var(--retro-hanko, #a63f30)' : 'inherit' }}>
                    {pubMos != null && Number.isFinite(Number(pubMos)) ? `${pubMos > 0 ? '+' : ''}${Number(pubMos).toFixed(1)}%` : 'N/A'}
                  </td>
                  <td className="td-num" style={{ textAlign: 'right' }}>
                    {reqMos != null ? `${reqMos}%` : '—'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <ValuationStatusPill status={rep.assessment?.valuation_status} marginOfSafety={pubMos} />
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button type="button" className="btn-small btn-view-detail" onClick={(e) => { e.stopPropagation(); onSelectSymbol?.(sym); }}>
                      Chi tiết ↗
                    </button>
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

export default function ValuationPage({ symbols = [], locale = 'vi' }) {
  const normalized = useMemo(() => [...new Set(symbols.map(value => String(value || '').toUpperCase()).filter(Boolean))], [symbols]);
  const symbolKey = normalized.join(',');
  const [reports, setReports] = useState({});
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(null);

  const [exporting, setExporting] = useState(false);
  const [exportMsg, setExportMsg] = useState('');

  // Handle URL deep link query e.g. /valuation?symbol=XYZ or #XYZ
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const urlParams = new URLSearchParams(window.location.search);
    const symParam = urlParams.get('symbol') || urlParams.get('ticker') || window.location.hash.replace('#', '');
    if (symParam && normalized.includes(symParam.toUpperCase())) {
      setSelectedSymbol(symParam.toUpperCase());
    }
  }, [symbolKey, normalized]);

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
      {normalized.length > 1 && (
        <SymbolTabStrip
          symbols={normalized}
          activeSymbol={selectedSymbol}
          onSelectSymbol={setSelectedSymbol}
        />
      )}
      <MethodologyGuide />
      {!normalized.length ? (
        <div className="empty-state">Danh mục chưa có cổ phiếu để định giá.</div>
      ) : (
        <>
          <ValuationOverviewTable
            reports={reports}
            symbols={normalized}
            locale={locale}
            onSelectSymbol={setSelectedSymbol}
          />
          <div className="valuation-grid">
            {normalized.map(symbol => {
              if (loading && !reports[symbol] && !errors[symbol]) {
                return <ValuationSkeletonCard key={symbol} symbol={symbol} />;
              }
              return (
                <ValuationCard
                  key={symbol}
                  symbol={symbol}
                  report={reports[symbol]}
                  error={errors[symbol]}
                  locale={locale}
                  onOpenDetail={setSelectedSymbol}
                />
              );
            })}
          </div>
        </>
      )}

      {selectedSymbol && (
        <ValuationDetailOverlay
          symbol={selectedSymbol}
          report={reports[selectedSymbol]}
          error={errors[selectedSymbol]}
          locale={locale}
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </main>
  </div>;
}

