import React, { useState } from 'react';
import { useI18n } from '../i18n.js';

const LINKS = [
  ['/', 'portfolio', 'nav.portfolio', '◫'],
  ['/transactions', 'transactions', 'nav.transactions', '↕'],
  ['/performance', 'performance', 'nav.performance', '⌁'],
  ['/guide', 'guide', 'nav.guide', '?'],
];

export default function AppNav({ active = 'portfolio', locale = 'en' }) {
  const { t, setLanguage } = useI18n(locale);
  const [open, setOpen] = useState(false);
  const text = (en, vi) => locale === 'vi' ? vi : en;

  return (
    <nav className={`app-nav ${open ? 'nav-open' : ''}`} aria-label={t('nav.primary')}>
      <div className="app-nav-head">
        <a className="brand" href="/" aria-label="QPort portfolio home">
          <span className="brand-mark">Q</span>
          <span className="brand-copy">
            <strong>QPort</strong>
            <small>{text('Buy & hold portfolio', 'Danh mục buy & hold')}</small>
          </span>
        </a>
        <button
          type="button"
          className="nav-toggle"
          aria-expanded={open}
          aria-label={text('Toggle navigation', 'Mở/đóng điều hướng')}
          onClick={() => setOpen(value => !value)}
        >
          <span />
          <span />
          <span />
        </button>
      </div>

      <div className="app-nav-links">
        <div className="nav-group">
          {LINKS.map(([href, key, labelKey, icon]) => (
            <a
              key={href}
              href={href}
              className={active === key ? 'active' : ''}
              aria-current={active === key ? 'page' : undefined}
            >
              <span className="nav-icon" aria-hidden="true">{icon}</span>
              <span>{t(labelKey)}</span>
            </a>
          ))}
        </div>
      </div>

      <div className="app-nav-footer">
        <div className="language-switch" aria-label={`${t('lang.english')} / ${t('lang.vietnamese')}`}>
          <button type="button" className={locale === 'en' ? 'active' : ''} onClick={() => setLanguage('en')} title={t('lang.english')}>EN</button>
          <button type="button" className={locale === 'vi' ? 'active' : ''} onClick={() => setLanguage('vi')} title={t('lang.vietnamese')}>VI</button>
        </div>
        <span className="nav-mode"><span className="status-dot" />{t('nav.mode')}</span>
      </div>
    </nav>
  );
}
