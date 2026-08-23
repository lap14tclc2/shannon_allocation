import React from 'react';
import AppNav from '../components/AppNav.jsx';
import { useI18n } from '../i18n.js';

const STEPS = [
  ['guide.step1', 'guide.step1_body'],
  ['guide.step2', 'guide.step2_body'],
  ['guide.step3', 'guide.step3_body'],
  ['guide.step4', 'guide.step4_body'],
  ['guide.step5', 'guide.step5_body'],
  ['guide.step6', 'guide.step6_body'],
  ['guide.step7', 'guide.step7_body'],
  ['guide.step8', 'guide.step8_body'],
  ['guide.step9', 'guide.step9_body'],
  ['guide.step10', 'guide.step10_body'],
];

const WARNINGS = ['guide.warning_1', 'guide.warning_2', 'guide.warning_3', 'guide.warning_4'];

export default function GuidePage({ locale = 'en' }) {
  const { t } = useI18n(locale);
  return (
    <div className="page">
      <AppNav active="guide" locale={locale} />
      <header className="page-head">
        <h1>{t('guide.title')}</h1>
        <p className="muted">{t('guide.subtitle')}</p>
      </header>

      <div className="card guide-principle">
        <h3>{t('guide.principle')}</h3>
        <p>{t('guide.principle_body')}</p>
      </div>

      <div className="card">
        <div className="section-head">
          <div>
            <h3>{t('guide.quick_start')}</h3>
            <div className="muted">QPort operational workflow</div>
          </div>
        </div>
        <pre className="guide-code"><code>{`cd frontend\nnpm ci\nnpm run build\nnpm run build:ssr\n\ncd ../python\npip install -r requirements.txt\npython serve.py`}</code></pre>
      </div>

      <div className="guide-steps">
        {STEPS.map(([titleKey, bodyKey]) => (
          <section className="card" key={titleKey}>
            <h3>{t(titleKey)}</h3>
            <p>{t(bodyKey)}</p>
          </section>
        ))}
      </div>

      <div className="card warning-card">
        <h3>{t('guide.warning_title')}</h3>
        <div className="rule-list">
          {WARNINGS.map((key) => <div key={key}>✓ {t(key)}</div>)}
        </div>
      </div>

      <div className="card">
        <h3>{t('guide.full_docs')}</h3>
        <div className="button-row">
          <a className="btn-export" href="https://github.com/lap14tclc2/shannon_allocation/blob/refactor-buy-hold/docs/USER_GUIDE_EN.md">{t('guide.english_doc')}</a>
          <a className="btn-variant" href="https://github.com/lap14tclc2/shannon_allocation/blob/refactor-buy-hold/docs/USER_GUIDE_VI.md">{t('guide.vietnamese_doc')}</a>
        </div>
      </div>
    </div>
  );
}
