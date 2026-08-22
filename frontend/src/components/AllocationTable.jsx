import React, { useState } from 'react';
import { formatMoney, formatPercent, formatWeight, formatShares } from '../lib/format.js';

function TradesSummary({ recs }) {
  const trades = (recs || []).filter((r) => r.recommendation !== 'HOLD');
  if (trades.length === 0) return <span className="muted">no trades</span>;
  return (
    <span>
      {trades.map((r, i) => (
        <span key={i} className={`tag tag-${r.recommendation.toLowerCase()}`}>
          {r.symbol} {r.recommendation}
        </span>
      ))}
    </span>
  );
}

function HoldingsTable({ title, holdings }) {
  return (
    <div className="sub-card">
      <h4>{title}</h4>
      <table className="sub-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Shares</th>
            <th>Price</th>
            <th>Value</th>
            <th>Weight</th>
          </tr>
        </thead>
        <tbody>
          {(holdings || []).map((h) => (
            <tr key={h.symbol}>
              <td>{h.symbol}</td>
              <td>{formatShares(h.shares)}</td>
              <td>{formatMoney(h.price)}</td>
              <td>{formatMoney(h.value)}</td>
              <td>{formatWeight(h.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecommendationsTable({ recs }) {
  return (
    <div className="sub-card">
      <h4>Recommendations</h4>
      <table className="sub-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Current</th>
            <th>Target</th>
            <th>Band</th>
            <th>Drift</th>
            <th>Rec</th>
            <th>Target Trade</th>
            <th>Funded Trade</th>
            <th>Shares</th>
          </tr>
        </thead>
        <tbody>
          {(recs || []).map((r) => (
            <tr key={r.symbol}>
              <td>{r.symbol}</td>
              <td>{formatWeight(r.current_weight)}</td>
              <td>{formatWeight(r.target_weight)}</td>
              <td>
                <span className={`tag tag-${r.band.toLowerCase()}`}>{r.band}</span>
              </td>
              <td>{formatPercent(r.drift * 100, 2)}</td>
              <td>
                <span className={`tag tag-${r.recommendation.toLowerCase()}`}>{r.recommendation}</span>
              </td>
              <td>{formatMoney(r.target_trade_amount)}</td>
              <td>{formatMoney(r.funded_trade_amount)}</td>
              <td>{formatShares(r.shares_to_trade)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WeightsBar({ targets }) {
  const entries = Object.entries(targets || {});
  return (
    <div className="weights-bar">
      {entries.map(([sym, w]) => (
        <div
          key={sym}
          className="weight-seg"
          style={{ width: `${(Number(w) || 0) * 100}%` }}
          title={`${sym} ${formatWeight(w)}`}
        >
          {sym}
        </div>
      ))}
    </div>
  );
}

function AllocationExpanded({ a }) {
  return (
    <div className="expanded">
      <div className="erc-card">
        <h4>ERC Diagnostics</h4>
        <div className="diag-grid">
          <div><span>Observations</span><b>{a.erc?.observations}</b></div>
          <div><span>Window</span><b>{a.erc?.window_start} → {a.erc?.window_end}</b></div>
          <div><span>Portfolio risk</span><b>{formatPercent((a.erc?.portfolio_risk || 0) * 100)}</b></div>
          <div><span>ERC error</span><b>{a.erc?.erc_error}</b></div>
        </div>
        <h4>Target weights</h4>
        <WeightsBar targets={a.targets} />
        <div className="diag-grid">
          <div><span>Deposit</span><b>{formatMoney(a.deposit_amount)}</b></div>
          <div><span>Rebalances since last</span><b>{a.rebalances_since_last_allocation}</b></div>
        </div>
      </div>
      <div className="expand-grid">
        <HoldingsTable title="Holdings before" holdings={a.holdings_before} />
        <HoldingsTable title="Holdings after" holdings={a.holdings_after} />
      </div>
      <RecommendationsTable recs={a.recommendations} />
    </div>
  );
}

function AllocationRow({ a }) {
  const [open, setOpen] = useState(false);
  const trades = (a.recommendations || []).filter((r) => r.recommendation !== 'HOLD');
  return (
    <>
      <tr className="alloc-row" onClick={() => setOpen((o) => !o)}>
        <td className="alloc-toggle">{open ? '▼' : '▶'}</td>
        <td>{a.allocation_date}</td>
        <td>Q{a.quarter}</td>
        <td>{a.initial_allocation ? 'Initial' : ''}</td>
        <td className="num">{a.deposit_amount ? formatMoney(a.deposit_amount) : '—'}</td>
        <td className="num">{formatMoney(a.nav_after)}</td>
        <td className="num">{formatMoney(a.cash_after)}</td>
        <td className="num">{a.erc?.observations}</td>
        <td><TradesSummary recs={a.recommendations} /></td>
      </tr>
      {open && (
        <tr className="alloc-expanded-row">
          <td colSpan={9}>
            <AllocationExpanded a={a} />
          </td>
        </tr>
      )}
    </>
  );
}

export default function AllocationTable({ allocations }) {
  return (
    <div className="card">
      <h3>Quarterly allocations ({allocations.length})</h3>
      <table className="alloc-table">
        <thead>
          <tr>
            <th style={{ width: 24 }}></th>
            <th>Date</th>
            <th>Q</th>
            <th>Note</th>
            <th>Deposit</th>
            <th>NAV</th>
            <th>Cash after</th>
            <th>Obs</th>
            <th>Trades</th>
          </tr>
        </thead>
        <tbody>
          {(allocations || []).map((a, i) => (
            <AllocationRow key={i} a={a} />
          ))}
        </tbody>
      </table>
    </div>
  );
}