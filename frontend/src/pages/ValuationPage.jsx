import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getValuationReports } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';

function displayNumber(value, suffix = '', digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(digits)}${suffix}`;
}

function money(value, locale) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${formatMoney(value, false, locale)} ₫`;
}

function MethodologyGuide() {
  return <section className="valuation-methodology">
    <div className="valuation-methodology-head"><span className="eyebrow">Phương pháp minh bạch</span><h2>QPort định giá như thế nào?</h2></div>
    <div className="valuation-method-grid">
      <article><b>01 · Chuẩn hóa BCTC</b><p>Lấy lợi nhuận sau thuế, khấu hao, CAPEX, nợ vay, tiền mặt và số cổ phiếu lưu hành của kỳ mới nhất. Không dùng giá trị hard-code.</p></article>
      <article><b>02 · Owner Earnings</b><p><code>Lợi nhuận chủ sở hữu = LNST + Khấu hao − CAPEX duy trì − Thay đổi vốn lưu động</code>. Trường thiếu được thể hiện trong cầu nối số liệu.</p></article>
      <article><b>03 · Ba kịch bản DCF</b><p>Bear/Base/Bull thay đổi tăng trưởng và tỷ lệ chiết khấu. Giá trị vốn chủ sở hữu bằng giá trị hiện tại của dòng tiền, cộng tiền và trừ nợ.</p></article>
      <article><b>04 · Kiểm tra chéo</b><p>EPV định giá sức kiếm tiền hiện tại; Reverse DCF suy ra tăng trưởng mà thị giá đang kỳ vọng; ma trận độ nhạy cho thấy kết quả đổi ra sao khi giả định thay đổi.</p></article>
    </div>
    <p className="valuation-method-warning">Finance Data là nguồn dữ liệu duy nhất cho định giá. QPort luôn hiển thị nguồn, kỳ báo cáo và thời điểm đồng bộ; nếu thiếu dữ liệu, hãy contact admin.</p>
  </section>;
}

function ValuationStatusPill({ status, marginOfSafety }) {
  const map = {
    DEEP_VALUE: { label: 'Định giá Rất Rẻ', cls: 'status-pill-deep-value' },
    UNDERVALUED: { label: 'Dưới giá trị (Rẻ)', cls: 'status-pill-undervalued' },
    FAIR_VALUE: { label: 'Vùng giá Hợp lý', cls: 'status-pill-fair' },
    OVERVALUED: { label: 'Định giá Cao', cls: 'status-pill-overvalued' },
    DISTRESSED: { label: 'Rủi ro Tài chính', cls: 'status-pill-distressed' },
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
  const bridge = report.owner_earnings_bridge || {};
  const assessment = report.assessment || {};
  const scenarios = ['BEAR', 'BASE', 'BULL'];
  const freshness = report.data_freshness || {};
  const mos = base.margin_of_safety_pct;

  return <article className="valuation-card">
    <div className="valuation-card-header">
      <div className="valuation-title-group">
        <div className="valuation-symbol-row">
          <h2>{symbol}</h2>
          <span className="valuation-sector-tag">{multiples.sector || 'Doanh nghiệp niêm yết'}</span>
        </div>
        <p className="valuation-period-subtitle">Kỳ BCTC: <strong>{report.fiscal_period_latest || 'FY2025'}</strong></p>
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
        <span className="price-label">Giá trị cơ sở (Base IV)</span>
        <span className="price-value highlight">{money(base.intrinsic_value_per_share, locale)}</span>
      </div>
      <div className="price-box price-box-mos">
        <span className="price-label">Biên an toàn (MoS)</span>
        <span className={`price-value ${mos > 0 ? 'pos' : mos < 0 ? 'neg' : ''}`}>
          {mos != null && Number.isFinite(Number(mos)) ? `${mos > 0 ? '+' : ''}${Number(mos).toFixed(1)}%` : '—'}
        </span>
      </div>
    </div>

    {/* Multiples ribbon */}
    <div className="valuation-multiples-ribbon">
      <div className="metric-chip">
        <span className="chip-label">P/E</span>
        <span className="chip-value">{displayNumber(multiples.pe, 'x')}</span>
      </div>
      <div className="metric-chip">
        <span className="chip-label">P/B</span>
        <span className="chip-value">{displayNumber(multiples.pb, 'x', 2)}</span>
      </div>
      <div className="metric-chip">
        <span className="chip-label">EPS</span>
        <span className="chip-value">{multiples.eps == null ? '—' : `${formatMoney(multiples.eps, false, locale)} ₫`}</span>
      </div>
      <div className="metric-chip">
        <span className="chip-label">ROE</span>
        <span className="chip-value">{displayNumber(multiples.roe, '%')}</span>
      </div>
    </div>

    {/* Expert Financial Analysis Narrative */}
    <div className="valuation-analyst-opinion">
      <div className="opinion-header">
        <span className="opinion-badge">Góc nhìn Chuyên gia Tài chính</span>
      </div>
      <p className="opinion-verdict">{assessment.valuation_verdict}</p>
      {assessment.financial_resilience_diagnosis && (
        <div className="opinion-subtext">
          <small><strong>Cấu trúc vốn & Hiệu quả sinh lời:</strong> {assessment.financial_resilience_diagnosis}</small>
        </div>
      )}
    </div>

    {/* Collapsed Technical Details (for advanced inspection) */}
    <details className="valuation-technical-details">
      <summary className="technical-summary">
        <span>Chi tiết định giá kỹ thuật & Cầu nối dòng tiền (Owner Earnings, DCF, EPV)</span>
      </summary>
      <div className="technical-content">
        <div className="tech-section">
          <h4>Cầu nối Owner Earnings</h4>
          <dl className="valuation-calculation-grid">
            <div><dt>Lợi nhuận sau thuế</dt><dd>{money(bridge.net_income, locale)}</dd></div>
            <div><dt>Khấu hao (D&A)</dt><dd>{money(bridge.depreciation_amortization, locale)}</dd></div>
            <div><dt>CAPEX duy trì</dt><dd>{money(bridge.maintenance_capex, locale)}</dd></div>
            <div><dt>Owner Earnings</dt><dd>{money(bridge.owner_earnings, locale)}</dd></div>
          </dl>
        </div>

        <div className="tech-section">
          <h4>Ba kịch bản DCF (5 năm + Gordon Growth)</h4>
          <div className="valuation-scenarios">
            {scenarios.map(name => {
              const scenario = report.scenarios?.[name] || {};
              return <div key={name} className={`scenario-card scenario-${name.toLowerCase()}`}>
                <div className="scenario-head">
                  <b>{name}</b>
                  <span>{money(scenario.intrinsic_value_per_share, locale)}</span>
                </div>
                <small>Tăng trưởng {displayNumber(Number(scenario.growth_stage1_rate) * 100, '%')} · Chiết khấu {displayNumber(Number(scenario.discount_rate) * 100, '%')}</small>
              </div>;
            })}
          </div>
        </div>

        <div className="tech-section tech-cross-check">
          <h4>Kiểm tra chéo (EPV & Reverse DCF)</h4>
          <p>• <strong>EPV (Sức mạnh kiếm tiền hiện tại không tăng trưởng):</strong> {money(report.epv_result?.epv_per_share, locale)}/cổ phiếu.</p>
          <p>• <strong>Reverse DCF (Tăng trưởng thị trường đang kỳ vọng):</strong> {report.reverse_dcf_result?.verdict || 'Chưa đủ dữ liệu Reverse DCF.'}</p>
        </div>
      </div>
    </details>

    <footer className="valuation-card-footer">
      <span>Nguồn: Finance Data ({freshness.provider || multiples.source || 'tcbs'}) · BCTC {report.fiscal_period_latest || 'FY2025'}</span>
      <span>Đồng bộ: {freshness.fetched_at ? new Date(freshness.fetched_at).toLocaleDateString('vi-VN') : 'Mới nhất'}</span>
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
        <button type="button" className="btn-secondary" onClick={load} disabled={loading || !normalized.length}>
          {loading ? 'Đang tải…' : '↻ Làm mới dữ liệu'}
        </button>
      </header>
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
