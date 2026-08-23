import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function RiskPage({ risk = {}, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const contributions = risk.risk_contributions || {};
  const erc = risk.erc_reference_weights || {};
  const symbols = [...new Set([...Object.keys(contributions), ...Object.keys(erc)])].sort();
  const quality = risk.quality || {};

  return (
    <div className="page">
      <AppNav active="risk" locale={locale} />
      <header className="page-head">
        <h1>{t('risk.title')}</h1>
        <p className="muted">{t('risk.subtitle')}</p>
      </header>

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">{t('risk.status')}</div><div className="metric-value">{status(risk.status || 'UNAVAILABLE')}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.vol63')}</div><div className="metric-value">{pct(risk.volatility_63)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.vol252')}</div><div className="metric-value">{pct(risk.volatility_252)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.largest')}</div><div className="metric-value">{pct(risk.max_position_weight)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.hhi')}</div><div className="metric-value">{risk.hhi == null ? '-' : Number(risk.hhi).toFixed(3)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('risk.coverage')}</div><div className="metric-value">{pct(quality.coverage_weight)}</div></div>
      </div>

      <div className="card">
        <h3>{t('risk.contrib_erc')}</h3>
        <p className="muted">{t('risk.erc_note')}</p>
        {symbols.length === 0 ? <div className="muted">{t('risk.not_enough')}</div> : (
          <div className="table-scroll"><table className="ranking">
            <thead><tr><th>{t('risk.ticker')}</th><th>{t('risk.current_contrib')}</th><th>{t('risk.equal_reference')}</th><th>{t('risk.interpretation')}</th></tr></thead>
            <tbody>{symbols.map((s) => {
              const rc = contributions[s];
              const ew = erc[s];
              const interpretation = rc == null ? status('NO_DATA') : Number(rc) > 0.35 ? status('HIGH_RISK_CONTRIBUTION') : status('NORMAL');
              return <tr key={s}><td><b>{s}</b></td><td>{pct(rc)}</td><td>{pct(ew)}</td><td>{interpretation}</td></tr>;
            })}</tbody>
          </table></div>
        )}
      </div>

      <div className="card">
        <h3>{t('risk.data_quality')}</h3>
        <div className="diag-row"><span>{t('common.as_of')}</span><b>{risk.as_of || '-'}</b></div>
        <div className="diag-row"><span>{t('risk.requested_symbols')}</span><b>{quality.requested_symbols ?? '-'}</b></div>
        <div className="diag-row"><span>{t('risk.eligible_symbols')}</span><b>{quality.eligible_symbols ?? '-'}</b></div>
        <div className="diag-row"><span>{t('risk.missing_covariance')}</span><b>{quality.missing_covariance_cells ?? '-'}</b></div>
        {(quality.missing_symbols || []).length > 0 && <div className="run-message">{t('risk.missing_history', { symbols: quality.missing_symbols.join(', ') })}</div>}
      </div>
    </div>
  );
}
