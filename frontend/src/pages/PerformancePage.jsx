import React from 'react';
import AppNav from '../components/AppNav.jsx';
import EquityChart from '../components/EquityChart.jsx';
import { formatMoney } from '../lib/format.js';

function money(v) { return v == null ? '-' : `${formatMoney(v)} VND`; }
function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function PerformancePage({ performance = {} }) {
  const returns = performance.returns || {};
  const latest = performance.latest || {};
  const series = (performance.series || []).map((x) => ({ date: x.date, nav: Number(x.nav || 0) }));
  return (
    <div className="page">
      <AppNav active="Performance" />
      <header className="page-head">
        <h1>Performance</h1>
        <p className="muted">TWR neutralizes external contributions. XIRR reflects the investor's actual dated cash flows.</p>
      </header>

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">Daily</div><div className="metric-value">{pct(returns.daily)}</div></div>
        <div className="metric-card"><div className="metric-label">MTD</div><div className="metric-value">{pct(returns.mtd)}</div></div>
        <div className="metric-card"><div className="metric-label">YTD</div><div className="metric-value">{pct(returns.ytd)}</div></div>
        <div className="metric-card"><div className="metric-label">TWR since inception</div><div className="metric-value">{pct(returns.since_inception)}</div></div>
        <div className="metric-card"><div className="metric-label">XIRR</div><div className="metric-value">{pct(performance.xirr)}</div></div>
        <div className="metric-card"><div className="metric-label">Latest NAV</div><div className="metric-value">{money(latest.nav)}</div></div>
      </div>

      <div className="card">
        <h3>Official NAV history</h3>
        <div className="chart"><EquityChart data={series} /></div>
      </div>

      <div className="expand-grid">
        <div className="card">
          <h3>P/L accounting</h3>
          <div className="diag-row"><span>Realized P/L</span><b>{money(performance.realized_pnl)}</b></div>
          <div className="diag-row"><span>Dividend income</span><b>{money(performance.dividend_income)}</b></div>
          <div className="diag-row"><span>Fees &amp; taxes</span><b>{money(performance.fees_and_taxes)}</b></div>
          <div className="diag-row"><span>Net external contributions</span><b>{money(performance.net_external_contributions)}</b></div>
        </div>
        <div className="card">
          <h3>Measurement policy</h3>
          <p><b>TWR</b> measures portfolio performance without treating deposits as returns.</p>
          <p><b>XIRR</b> measures the investor experience from dated deposits/imports, withdrawals and current NAV.</p>
          <p className="muted">Only official, fully fresh daily snapshots enter the displayed performance series.</p>
        </div>
      </div>
    </div>
  );
}
