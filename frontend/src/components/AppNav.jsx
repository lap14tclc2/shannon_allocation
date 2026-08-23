import React from 'react';

const LINKS = [
  ['/', 'Portfolio'],
  ['/transactions', 'Transactions'],
  ['/performance', 'Performance'],
  ['/risk', 'Risk'],
  ['/snapshots', 'Snapshots'],
  ['/settings', 'Settings'],
  ['/research', 'Research'],
];

export default function AppNav({ active = 'Portfolio' }) {
  return (
    <nav className="app-nav" aria-label="Primary">
      <a className="brand" href="/">QPort</a>
      <div className="app-nav-links">
        {LINKS.map(([href, label]) => (
          <a key={href} href={href} className={active === label ? 'active' : ''}>{label}</a>
        ))}
      </div>
      <span className="nav-mode">BUY &amp; HOLD</span>
    </nav>
  );
}
