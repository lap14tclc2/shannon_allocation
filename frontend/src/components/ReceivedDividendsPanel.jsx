import React, { useEffect, useMemo, useState } from 'react';
import { listPortfolioTransactions } from '../lib/api.js';
import { formatMoney, formatShares } from '../lib/format.js';

export default function ReceivedDividendsPanel({ locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = value => value == null ? '-' : `${formatMoney(value, false, locale)} VND`;
  const shares = value => value == null ? '-' : formatShares(value, locale);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    listPortfolioTransactions()
      .then(items => {
        if (!active) return;
        setRows((items || []).filter(item => ['CASH_DIVIDEND', 'STOCK_DIVIDEND'].includes(item.event_type)));
      })
      .catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const cashNet = row => {
    if (row.event_type !== 'CASH_DIVIDEND') return 0;
    const meta = row.metadata || {};
    if (meta.cash_dividend_net_amount != null) return Number(meta.cash_dividend_net_amount || 0);
    return Math.max(0, Number(row.amount || 0) - Number(row.tax || 0));
  };

  const cashTax = row => row.event_type === 'CASH_DIVIDEND'
    ? Number((row.metadata || {}).cash_dividend_withholding_tax ?? row.tax ?? 0)
    : 0;

  const groups = useMemo(() => {
    const map = new Map();
    for (const row of rows) {
      const symbol = String(row.symbol || 'UNKNOWN').toUpperCase();
      const current = map.get(symbol) || { symbol, rows: [], cashGross: 0, cashNet: 0, cashTax: 0, stock: 0, latest: '' };
      current.rows.push(row);
      if (row.event_type === 'CASH_DIVIDEND') {
        current.cashGross += Number(row.amount || 0);
        current.cashNet += cashNet(row);
        current.cashTax += cashTax(row);
      }
      if (row.event_type === 'STOCK_DIVIDEND') current.stock += Number(row.quantity || 0);
      if (!current.latest || String(row.event_date || '') > current.latest) current.latest = String(row.event_date || '');
      map.set(symbol, current);
    }
    return [...map.values()].sort((a, b) => b.latest.localeCompare(a.latest) || a.symbol.localeCompare(b.symbol));
  }, [rows]);

  const totalCashGross = rows.reduce((sum, row) => sum + (row.event_type === 'CASH_DIVIDEND' ? Number(row.amount || 0) : 0), 0);
  const totalCashNet = rows.reduce((sum, row) => sum + cashNet(row), 0);
  const totalCashTax = rows.reduce((sum, row) => sum + cashTax(row), 0);
  const totalStock = rows.filter(row => row.event_type === 'STOCK_DIVIDEND').reduce((sum, row) => sum + Number(row.quantity || 0), 0);

  return <section className="card received-dividends-card">
    <div className="section-head">
      <div>
        <div className="eyebrow">{text('Ledger income', 'Thu nhập đã ghi sổ')}</div>
        <h2>{text('Dividends received', 'Cổ tức đã nhận')}</h2>
        <p className="muted">{text(
          'Only dividend transactions already posted to the ledger appear here. Cash dividends show gross entitlement, 5% withholding and actual net cash received.',
          'Chỉ cổ tức đã post vào ledger mới xuất hiện ở đây. Cổ tức tiền mặt hiển thị quyền gross, thuế khấu trừ 5% và tiền net thực nhận.'
        )}</p>
      </div>
      <div className="received-dividend-totals">
        <span>{text('Gross cash', 'Tiền gross')}: <b>{money(totalCashGross)}</b></span>
        <span>{text('Withholding tax', 'Thuế khấu trừ')}: <b>{money(totalCashTax)}</b></span>
        <span>{text('Net cash', 'Tiền net')}: <b>{money(totalCashNet)}</b></span>
        <span>{text('Stock shares', 'CP nhận')}: <b>{shares(totalStock)}</b></span>
      </div>
    </div>

    {loading ? <div className="loading-line"><span className="spinner" />{text('Loading received dividends…', 'Đang tải cổ tức đã nhận…')}</div> :
      error ? <div className="run-message">{error}</div> :
      groups.length === 0 ? <div className="empty-state">{text('No received dividend has been posted yet.', 'Chưa có cổ tức đã nhận nào được post vào ledger.')}</div> :
      <div className="received-dividend-list">
        {groups.map(group => <details className="received-dividend-node" key={group.symbol}>
          <summary>
            <div><b>{group.symbol}</b><span className="muted">{group.rows.length} {text('receipts', 'lần nhận')}</span></div>
            <div><span>{text('Latest', 'Mới nhất')}</span><b>{group.latest || '-'}</b></div>
            <div><span>{text('Net cash received', 'Tiền net đã nhận')}</span><b>{money(group.cashNet)}</b></div>
            <div><span>{text('Stock received', 'CP đã nhận')}</span><b>{shares(group.stock)}</b></div>
          </summary>
          <div className="table-scroll received-dividend-table-wrap">
            <table className="ranking received-dividend-table">
              <thead><tr>
                <th>{text('Date', 'Ngày')}</th>
                <th>{text('Type', 'Loại')}</th>
                <th className="num">{text('Gross cash', 'Tiền gross')}</th>
                <th className="num">{text('Tax', 'Thuế')}</th>
                <th className="num">{text('Net cash', 'Tiền net')}</th>
                <th className="num">{text('Shares', 'CP')}</th>
                <th>Broker</th>
                <th>{text('Account', 'Tài khoản')}</th>
                <th>{text('Source', 'Nguồn')}</th>
                <th>ID</th>
              </tr></thead>
              <tbody>{group.rows.sort((a,b) => String(b.event_date || '').localeCompare(String(a.event_date || '')) || Number(b.id || 0) - Number(a.id || 0)).map(row => {
                const meta = row.metadata || {};
                const automatic = Boolean(meta.auto_generated);
                const isCash = row.event_type === 'CASH_DIVIDEND';
                return <tr key={row.id}>
                  <td>{row.event_date || '-'}</td>
                  <td><b>{isCash ? text('Cash', 'Tiền mặt') : text('Stock', 'Cổ phiếu')}</b></td>
                  <td className="num">{isCash ? money(row.amount) : '-'}</td>
                  <td className="num">{isCash ? money(cashTax(row)) : '-'}</td>
                  <td className="num">{isCash ? money(cashNet(row)) : '-'}</td>
                  <td className="num">{row.event_type === 'STOCK_DIVIDEND' ? shares(row.quantity) : '-'}</td>
                  <td>{automatic && (meta.broker_code || 'UNASSIGNED') === 'UNASSIGNED' ? text('ALL · pro-rata', 'TẤT CẢ · pro-rata') : (meta.broker_code || 'UNASSIGNED')}</td>
                  <td>{automatic && (meta.broker_code || 'UNASSIGNED') === 'UNASSIGNED' ? text('existing lots', 'lot hiện có') : (meta.account_id || 'PRIMARY')}</td>
                  <td>{automatic ? text('AUTO corporate action', 'AUTO quyền DN') : text('Manual ledger', 'Ledger thủ công')}</td>
                  <td>#{row.id}</td>
                </tr>;
              })}</tbody>
            </table>
          </div>
        </details>)}
      </div>}
  </section>;
}
