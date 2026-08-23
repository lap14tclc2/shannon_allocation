import React from 'react';
import AppNav from '../components/AppNav.jsx';
import EquityChart from '../components/EquityChart.jsx';
import { formatMoney } from '../lib/format.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function PerformancePage({ performance = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  const returns = performance.returns || {};
  const latest = performance.latest || {};
  const series = (performance.series || []).map((x) => ({ date: x.date, nav: Number(x.nav || 0) }));
  return (
    <div className="page">
      <AppNav active="performance" locale={locale} />
      <header className="page-head">
        <h1>{t('performance.title')}</h1>
        <p className="muted">{t('performance.subtitle')}</p>
      </header>

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">{t('performance.daily')}</div><div className="metric-value">{pct(returns.daily)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.mtd')}</div><div className="metric-value">{pct(returns.mtd)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.ytd')}</div><div className="metric-value">{pct(returns.ytd)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.twr')}</div><div className="metric-value">{pct(returns.since_inception)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.xirr')}</div><div className="metric-value">{pct(performance.xirr)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.latest_nav')}</div><div className="metric-value">{money(latest.nav)}</div></div>
      </div>

      <div className="card">
        <h3>{t('performance.nav_history')}</h3>
        <div className="chart"><EquityChart data={series} /></div>
      </div>

      <div className="expand-grid">
        <div className="card">
          <h3>{t('performance.pl_accounting')}</h3>
          <div className="diag-row"><span>{t('performance.realized_pl')}</span><b>{money(performance.realized_pnl)}</b></div>
          <div className="diag-row"><span>{t('performance.dividend_income')}</span><b>{money(performance.dividend_income)}</b></div>
          <div className="diag-row"><span>{t('performance.fees_taxes')}</span><b>{money(performance.fees_and_taxes)}</b></div>
          <div className="diag-row"><span>{t('performance.net_contributions')}</span><b>{money(performance.net_external_contributions)}</b></div>
        </div>
        <div className="card">
          <h3>{t('performance.measurement_policy')}</h3>
          <p><b>TWR</b> {t('performance.twr_explain').replace(/^TWR\s*/i, '')}</p>
          <p><b>XIRR</b> {t('performance.xirr_explain').replace(/^XIRR\s*/i, '')}</p>
          <p className="muted">{t('performance.official_only')}</p>
        </div>
      </div>
    </div>
  );
}
