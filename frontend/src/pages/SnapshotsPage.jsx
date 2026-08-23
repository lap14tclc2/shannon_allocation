import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney } from '../lib/format.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function SnapshotsPage({ snapshots = [], locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  return (
    <div className="page">
      <AppNav active="snapshots" locale={locale} />
      <header className="page-head">
        <h1>{t('snapshots.title')}</h1>
        <p className="muted">{t('snapshots.subtitle')}</p>
      </header>

      <div className="card">
        {snapshots.length === 0 ? <div className="muted">{t('snapshots.empty')}</div> : (
          <div className="table-scroll"><table className="ranking">
            <thead><tr><th>{t('snapshots.date')}</th><th>{t('snapshots.status')}</th><th>{t('snapshots.nav')}</th><th>{t('snapshots.cash')}</th><th>{t('snapshots.equity')}</th><th>{t('snapshots.daily_pl')}</th><th>{t('snapshots.daily_return')}</th><th>{t('snapshots.drawdown')}</th><th>{t('snapshots.vol252')}</th><th>{t('snapshots.positions')}</th></tr></thead>
            <tbody>{snapshots.map((s) => (
              <tr key={s.id || s.snapshot_date}>
                <td><b>{s.snapshot_date}</b></td>
                <td><span className={`status-pill status-${String(s.data_quality || 'missing').toLowerCase()}`}>{s.official ? t('common.official') : status(s.data_quality)}</span></td>
                <td>{money(s.nav)}</td><td>{money(s.cash)}</td><td>{money(s.equity_value)}</td>
                <td className={Number(s.daily_pnl || 0) >= 0 ? 'pos' : 'neg'}>{money(s.daily_pnl)}</td>
                <td>{pct(s.daily_return)}</td><td>{pct(s.current_drawdown)}</td><td>{pct(s.volatility_252)}</td>
                <td>{(s.positions || []).length}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
