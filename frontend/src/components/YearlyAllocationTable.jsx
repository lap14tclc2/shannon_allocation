import React, { useMemo } from 'react';
import { formatMoney } from '../lib/format.js';

// Per-year money allocation rollup computed from the quarterly allocation records:
// deposits added, NAV start/end, buy/sell notional at allocation events, cash after.
export default function YearlyAllocationTable({ allocations }) {
  const rows = useMemo(() => {
    const byYear = {};
    for (const a of allocations || []) {
      const y = a.year;
      if (!byYear[y]) {
        byYear[y] = { year: y, deposit: 0, buys: 0, sells: 0, nav_start: null, nav_end: null, cash_after: null, count: 0 };
      }
      const row = byYear[y];
      row.deposit += a.deposit_amount || 0;
      row.count += 1;
      if (row.nav_start == null) row.nav_start = a.nav_before;
      row.nav_end = a.nav_after;
      row.cash_after = a.cash_after;
      for (const rec of a.recommendations || []) {
        if (rec.recommendation === 'BUY') row.buys += rec.funded_trade_amount || 0;
        else if (rec.recommendation === 'SELL') row.sells += rec.funded_trade_amount || 0;
      }
    }
    return Object.values(byYear).sort((x, y) => x.year - y.year);
  }, [allocations]);

  if (!rows.length) return null;

  return (
    <div className="card">
      <h3>Money allocation by year</h3>
      <table className="sub-table">
        <thead>
          <tr>
            <th>Year</th>
            <th>Deposits</th>
            <th>NAV start</th>
            <th>NAV end</th>
            <th>Buys (alloc)</th>
            <th>Sells (alloc)</th>
            <th>Cash after</th>
            <th>Allocations</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.year}>
              <td>{r.year}</td>
              <td>{formatMoney(r.deposit)}</td>
              <td>{formatMoney(r.nav_start)}</td>
              <td>{formatMoney(r.nav_end)}</td>
              <td>{formatMoney(r.buys)}</td>
              <td>{formatMoney(r.sells)}</td>
              <td>{formatMoney(r.cash_after)}</td>
              <td>{r.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="muted">Buys/Sells = allocation-event notional only (intra-period band rebalances not included).</div>
    </div>
  );
}