import React from 'react';
import { useI18n } from '../i18n.js';

const LINKS = [
  ['/', 'portfolio', 'nav.portfolio'],
  ['/transactions', 'transactions', 'nav.transactions'],
  ['/performance', 'performance', 'nav.performance'],
  ['/risk', 'risk', 'nav.risk'],
  ['/snapshots', 'snapshots', 'nav.snapshots'],
  ['/operations', 'operations', null, 'Operations', 'Vận hành'],
  ['/logs', 'logs', null, 'Logs', 'Nhật ký'],
  ['/settings', 'settings', 'nav.settings'],
  ['/guide', 'guide', 'nav.guide'],
];

export default function AppNav({ active = 'portfolio', locale = 'en' }) {
  const { t, setLanguage } = useI18n(locale);
  return (
    <nav className="app-nav" aria-label={t('nav.primary')}>
      <a className="brand" href="/">QPort</a>
      <div className="app-nav-links">
        {LINKS.map(([href, key, labelKey, en, vi]) => (
          <a key={href} href={href} className={active === key ? 'active' : ''}>{labelKey ? t(labelKey) : (locale === 'vi' ? vi : en)}</a>
        ))}
      </div>
      <div className="language-switch" aria-label={`${t('lang.english')} / ${t('lang.vietnamese')}`}>
        <button type="button" className={locale === 'en' ? 'active' : ''} onClick={() => setLanguage('en')} title={t('lang.english')}>EN</button>
        <button type="button" className={locale === 'vi' ? 'active' : ''} onClick={() => setLanguage('vi')} title={t('lang.vietnamese')}>VI</button>
      </div>
      <span className="nav-mode">{t('nav.mode')}</span>
    </nav>
  );
}
