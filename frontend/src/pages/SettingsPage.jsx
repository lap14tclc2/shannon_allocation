import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { setReferenceWeights } from '../lib/api.js';
import { useI18n } from '../i18n.js';

export default function SettingsPage({ dashboard = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const positions = dashboard.portfolio?.positions || [];
  const current = dashboard.portfolio?.reference_weights || {};
  const [weights, setWeights] = useState(() => Object.fromEntries(
    positions.map((p) => [p.symbol, current[p.symbol] != null ? Number(current[p.symbol]) * 100 : ''])
  ));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const total = useMemo(
    () => Object.values(weights).reduce((sum, v) => sum + (v === '' ? 0 : Number(v || 0)), 0),
    [weights]
  );

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const nonEmpty = Object.entries(weights).filter(([, v]) => String(v).trim() !== '' && Number(v) > 0);
      if (nonEmpty.length && Math.abs(total - 100) > 0.001) {
        throw new Error(t('settings.total_error', { total: total.toFixed(2) }));
      }
      const payload = Object.fromEntries(nonEmpty.map(([s, v]) => [s, Number(v) / 100]));
      await setReferenceWeights(payload);
      setMessage(Object.keys(payload).length ? t('settings.saved') : t('settings.cleared'));
      setSaving(false);
    } catch (err) {
      setMessage(err.message);
      setSaving(false);
    }
  }

  function clear() {
    setWeights(Object.fromEntries(positions.map((p) => [p.symbol, ''])));
  }

  return (
    <div className="page">
      <AppNav active="settings" locale={locale} />
      <header className="page-head">
        <h1>{t('settings.title')}</h1>
        <p className="muted">{t('settings.subtitle')}</p>
      </header>

      <form className="card" onSubmit={save}>
        <h3>{t('settings.reference_weights')} <span className="muted">{t('common.optional')}</span></h3>
        <p className="muted">{t('settings.reference_note')}</p>
        {positions.length === 0 ? (
          <p className="muted">{t('settings.add_first')}</p>
        ) : (
          <div className="reference-grid">
            {positions.map((p) => (
              <label key={p.symbol}>
                <span><b>{p.symbol}</b> <span className="muted">{t('settings.current_weight', { value: `${(Number(p.weight || 0) * 100).toFixed(1)}%` })}</span></span>
                <div className="reference-input"><input type="number" min="0" max="100" step="0.01" value={weights[p.symbol] ?? ''} onChange={(e) => setWeights((x) => ({ ...x, [p.symbol]: e.target.value }))} /><span>%</span></div>
              </label>
            ))}
          </div>
        )}
        <div className="diag-row" style={{ marginTop: 12 }}><span>{t('settings.total_configured')}</span><b>{total.toFixed(2)}%</b></div>
        <div className="button-row">
          <button className="btn-export" type="submit" disabled={saving || positions.length === 0}>{saving ? t('settings.saving') : t('settings.save')}</button>
          <button className="btn-variant" type="button" onClick={clear} disabled={saving || positions.length === 0}>{t('settings.clear')}</button>
        </div>
        {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
      </form>

      <div className="card">
        <h3>{t('settings.market_policy')}</h3>
        <div className="diag-row"><span>{t('settings.provider_boundary')}</span><b>AUTO</b></div>
        <div className="diag-row"><span>{t('settings.optional_primary')}</span><b>Vnstock</b></div>
        <div className="diag-row"><span>{t('settings.fallback')}</span><b>VNDIRECT</b></div>
        <div className="diag-row"><span>{t('settings.eod_sync')}</span><b>15:30 Asia/Ho_Chi_Minh</b></div>
        <p className="muted">{t('settings.provider_failure')}</p>
      </div>
    </div>
  );
}
