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
    <p className="valuation-method-warning">CafeF là fallback HTML công khai và có thể thay đổi cấu trúc. QPort luôn hiển thị nguồn, thời điểm tải và chặn kết quả nếu thiếu giá, lợi nhuận hoặc số cổ phiếu.</p>
  </section>;
}

function ValuationCard({ symbol, report, error, locale }) {
  if (error) return <article className="valuation-card valuation-card-error">
    <div className="valuation-card-title"><h2>{symbol}</h2><span>Không tải được</span></div>
    <p role="alert">{error.message}</p>
    <code>{error.code}</code>
  </article>;

  if (!report) return null;
  const multiples = report.valuation_multiples || {};
  const base = report.scenarios?.BASE || {};
  const bridge = report.owner_earnings_bridge || {};
  const scenarios = ['BEAR', 'BASE', 'BULL'];
  const freshness = report.data_freshness || {};
  return <article className="valuation-card">
    <div className="valuation-card-title">
      <div><h2>{symbol}</h2><p>{multiples.sector || 'Chưa xác định nhóm ngành'}</p></div>
      <span>{report.fiscal_period_latest || 'BCTC mới nhất'}</span>
    </div>
    <div className="valuation-price-row">
      <div><small>Thị giá</small><strong>{money(report.current_market_price, locale)}</strong></div>
      <div><small>Giá trị cơ sở</small><strong>{money(base.intrinsic_value_per_share, locale)}</strong></div>
      <div><small>Biên an toàn</small><strong>{displayNumber(base.margin_of_safety_pct, '%')}</strong></div>
    </div>
    <dl className="valuation-metrics">
      <div><dt>P/E</dt><dd>{displayNumber(multiples.pe, 'x')}</dd></div>
      <div><dt>P/B</dt><dd>{displayNumber(multiples.pb, 'x')}</dd></div>
      <div><dt>EPS</dt><dd>{multiples.eps == null ? '—' : `${formatMoney(multiples.eps, false, locale)} ₫`}</dd></div>
      <div><dt>ROE</dt><dd>{displayNumber(multiples.roe, '%')}</dd></div>
    </dl>
    <details className="valuation-details" open>
      <summary>Chi tiết phép tính</summary>
      <h3>Cầu nối Owner Earnings</h3>
      <dl className="valuation-calculation-grid">
        <div><dt>Lợi nhuận sau thuế</dt><dd>{money(bridge.net_income, locale)}</dd></div>
        <div><dt>Khấu hao</dt><dd>{money(bridge.depreciation_amortization, locale)}</dd></div>
        <div><dt>CAPEX duy trì</dt><dd>{money(bridge.maintenance_capex, locale)}</dd></div>
        <div><dt>Owner Earnings</dt><dd>{money(bridge.owner_earnings, locale)}</dd></div>
      </dl>
      <h3>Kịch bản DCF</h3>
      <div className="valuation-scenarios">{scenarios.map(name => {
        const scenario = report.scenarios?.[name] || {};
        return <div key={name}><b>{name}</b><span>{money(scenario.intrinsic_value_per_share, locale)}</span><small>Tăng trưởng {displayNumber(Number(scenario.growth_stage1_rate) * 100, '%')} · Chiết khấu {displayNumber(Number(scenario.discount_rate) * 100, '%')}</small></div>;
      })}</div>
      <h3>Kiểm tra chéo</h3>
      <p>EPV/cổ phiếu: <b>{money(report.epv_result?.epv_per_share, locale)}</b>. {report.reverse_dcf_result?.verdict || 'Chưa đủ dữ liệu Reverse DCF.'}</p>
      <p>{report.assessment?.valuation_verdict}</p>
    </details>
    <p className="valuation-source">Nguồn: {freshness.provider || multiples.source || 'Không rõ'}{freshness.fallback_from ? ` (fallback từ ${freshness.fallback_from})` : ''} · Kỳ dữ liệu: {report.fiscal_period_latest || 'không rõ'} · Tải lúc: {freshness.fetched_at ? new Date(freshness.fetched_at).toLocaleString('vi-VN') : 'không rõ'}</p>
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
    const result = await getValuationReports(normalized);
    setReports(result.reports);
    setErrors(result.errors);
    setLoading(false);
  }

  useEffect(() => {
    let active = true;
    if (!normalized.length) return undefined;
    setLoading(true);
    getValuationReports(normalized).then(result => {
      if (!active) return;
      setReports(result.reports);
      setErrors(result.errors);
      setLoading(false);
    });
    return () => { active = false; };
  }, [symbolKey]);

  return <div className="app-shell">
    <AppNav active="valuation" locale={locale} />
    <main className="valuation-page">
      <header className="valuation-header">
        <div><span className="eyebrow">BCTC mới nhất theo từng mã</span><h1>Định giá cổ phiếu</h1><p>Dữ liệu được tải mới trực tiếp cho từng mã; QPort không dùng hồ sơ định giá chung hoặc giá trị hard-code.</p></div>
        <button type="button" className="btn-secondary" onClick={load} disabled={loading || !normalized.length}>{loading ? 'Đang tải…' : 'Tải lại dữ liệu mới'}</button>
      </header>
      <MethodologyGuide />
      {!normalized.length ? <div className="empty-state">Danh mục chưa có cổ phiếu để định giá.</div> : <div className="valuation-grid">
        {normalized.map(symbol => <ValuationCard key={symbol} symbol={symbol} report={reports[symbol]} error={errors[symbol]} locale={locale} />)}
      </div>}
      {loading && Object.keys(reports).length === 0 && Object.keys(errors).length === 0 && <div className="empty-state" role="status">Đang tải BCTC mới nhất từ Vnstock…</div>}
    </main>
  </div>;
}
