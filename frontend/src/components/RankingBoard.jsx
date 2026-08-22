import React, { useMemo, useState } from 'react';
import { formatMoney, formatPercent } from '../lib/format.js';

const COLS = [
  { key: 'rank', label: '#', width: 30 },
  { key: 'symbols', label: 'Symbols' },
  { key: 'n_symbols', label: 'N', width: 34 },
  { key: 'n_allocations', label: 'Alloc', width: 46 },
  { key: 'score', label: 'Score', width: 56, num: true },
  { key: 'twr_annualized_pct', label: 'TWR ann %', width: 70, pct: true },
  { key: 'xirr_pct', label: 'XIRR %', width: 66, pct: true },
  { key: 'sharpe', label: 'Sharpe', width: 60, num: true },
  { key: 'sortino', label: 'Sortino', width: 62, num: true },
  { key: 'max_drawdown_pct', label: 'MDD %', width: 64, pct: true },
  { key: 'final_nav', label: 'Final NAV', width: 88, money: true },
];

export default function RankingBoard({ rows, selected, onSelect, hrefFor }) {
  const [sortKey, setSortKey] = useState('score');
  const [sortDesc, setSortDesc] = useState(true);

  const sorted = useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'string') return sortDesc ? bv.localeCompare(av) : av.localeCompare(bv);
      return sortDesc ? bv - av : av - bv;
    });
    return arr;
  }, [rows, sortKey, sortDesc]);

  function toggleSort(key) {
    if (key === sortKey) setSortDesc((d) => !d);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  function handleRowClick(slug) {
    if (hrefFor) {
      window.location.assign(hrefFor(slug));
    } else if (onSelect) {
      onSelect(slug);
    }
  }

  return (
    <div className="board">
      <table className="ranking">
        <thead>
          <tr>
            {COLS.map((c) => (
              <th
                key={c.key}
                style={{ width: c.width }}
                onClick={() => toggleSort(c.key)}
                className={sortKey === c.key ? 'sorted' : ''}
              >
                {c.label}
                {sortKey === c.key ? (sortDesc ? ' ▼' : ' ▲') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.slug}
              className={selected === r.slug ? 'row-selected' : ''}
              onClick={() => handleRowClick(r.slug)}
            >
              <td>{r.rank}</td>
              <td className="symbols-cell">
                {hrefFor ? <a href={hrefFor(r.slug)}>{r.symbols}</a> : r.symbols}
              </td>
              <td>{r.n_symbols}</td>
              <td>{r.n_allocations}</td>
              <td className="num score-cell">{r.score?.toFixed(1)}</td>
              <td className={Number(r.twr_annualized_pct) >= 0 ? 'pos' : 'neg'}>{formatPercent(r.twr_annualized_pct)}</td>
              <td className={Number(r.xirr_pct) >= 0 ? 'pos' : 'neg'}>{formatPercent(r.xirr_pct)}</td>
              <td className="num">{r.sharpe?.toFixed(2)}</td>
              <td className="num">{r.sortino?.toFixed(2)}</td>
              <td className="neg">{formatPercent(r.max_drawdown_pct)}</td>
              <td className="num">{formatMoney(r.final_nav, true)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <div className="muted">No combinations in this run.</div>}
    </div>
  );
}