import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { getValuationReports } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';

function displayNumber(value, suffix = '', digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(digits)}${suffix}`;
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
  return <article className="valuation-card">
    <div className="valuation-card-title">
      <div><h2>{symbol}</h2><p>{multiples.sector || 'Chưa xác định nhóm ngành'}</p></div>
      <span>{report.fiscal_period_latest || 'BCTC mới nhất'}</span>
    </div>
    <div className="valuation-price-row">
      <div><small>Thị giá</small><strong>{report.current_market_price == null ? '—' : `${formatMoney(report.current_market_price, false, locale)} ₫`}</strong></div>
      <div><small>Giá trị cơ sở</small><strong>{base.intrinsic_value_per_share == null ? '—' : `${formatMoney(base.intrinsic_value_per_share, false, locale)} ₫`}</strong></div>
      <div><small>Biên an toàn</small><strong>{displayNumber(base.margin_of_safety_pct, '%')}</strong></div>
    </div>
    <dl className="valuation-metrics">
      <div><dt>P/E</dt><dd>{displayNumber(multiples.pe, 'x')}</dd></div>
      <div><dt>P/B</dt><dd>{displayNumber(multiples.pb, 'x')}</dd></div>
      <div><dt>EPS</dt><dd>{multiples.eps == null ? '—' : `${formatMoney(multiples.eps, false, locale)} ₫`}</dd></div>
      <div><dt>ROE</dt><dd>{displayNumber(multiples.roe, '%')}</dd></div>
    </dl>
    <p className="valuation-source">Nguồn: {report.source || report.provider || 'Vnstock'} · Cập nhật: {report.fetched_at ? new Date(report.fetched_at).toLocaleString('vi-VN') : 'không rõ'}</p>
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
      {!normalized.length ? <div className="empty-state">Danh mục chưa có cổ phiếu để định giá.</div> : <div className="valuation-grid">
        {normalized.map(symbol => <ValuationCard key={symbol} symbol={symbol} report={reports[symbol]} error={errors[symbol]} locale={locale} />)}
      </div>}
      {loading && Object.keys(reports).length === 0 && Object.keys(errors).length === 0 && <div className="empty-state" role="status">Đang tải BCTC mới nhất từ Vnstock…</div>}
    </main>
  </div>;
}
