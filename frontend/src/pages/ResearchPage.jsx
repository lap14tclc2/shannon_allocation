import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

export default function ResearchPage({ experiments = [], runs = [], locale = 'en' }) {
  const { t } = useI18n(locale);
  return (
    <div className="page">
      <AppNav active="research" locale={locale} />
      <header className="page-head">
        <h1>{t('research.title')}</h1>
        <p className="muted">{t('research.subtitle')}</p>
      </header>

      <div className="card research-boundary">
        <h3>{t('research.boundary_title')}</h3>
        <div className="boundary-flow">
          <span>{t('research.backtest_optimizer')}</span><b>→</b><span>{t('research.proposal_only')}</span><b>→</b><span>{t('research.user_decision')}</span><b>→</b><span>{t('research.explicit_event')}</span>
        </div>
        <p className="muted">{t('research.no_auto_api')}</p>
      </div>

      <div className="expand-grid">
        <div className="card">
          <div className="section-head"><div><h3>{t('research.optimizer_experiments')}</h3><div className="muted">{t('research.legacy_note')}</div></div><a className="btn-export" href="/research/optimizer">{t('research.open_optimizer')}</a></div>
          {experiments.length === 0 ? <p className="muted">{t('research.no_experiments')}</p> : (
            <ul className="run-list">{experiments.slice(0, 10).map((e) => (
              <li key={e.experiment_id}><div className="run-link"><a href={`/research/optimizer/${e.experiment_id}`}>{e.experiment_id}</a><span className="muted">{e.generated_at || '-'} · {e.mode || 'research'}</span></div></li>
            ))}</ul>
          )}
        </div>

        <div className="card">
          <h3>{t('research.historical_runs')}</h3>
          {runs.length === 0 ? <p className="muted">{t('research.no_runs')}</p> : (
            <ul className="run-list">{runs.slice(0, 10).map((r) => (
              <li key={r.run_id}><div className="run-link"><a href={`/runs/${r.run_id}`}>{r.run_id}</a><span className="muted">{r.generated_at || '-'}</span></div></li>
            ))}</ul>
          )}
        </div>
      </div>

      <div className="card">
        <p className="muted" style={{ margin: 0 }}>{t('research.legacy_language_note')}</p>
      </div>
    </div>
  );
}
