import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction } from '../lib/api.js';

const TYPES = [
  ['POSITION_IMPORT', 'Opening position import'],
  ['CASH_DEPOSIT', 'Cash deposit'],
  ['BUY', 'Buy execution'],
  ['SELL', 'Sell execution'],
  ['CASH_WITHDRAW', 'Cash withdrawal'],
  ['CASH_DIVIDEND', 'Cash dividend'],
  ['STOCK_DIVIDEND', 'Stock dividend'],
  ['SPLIT', 'Stock split / share ratio'],
  ['FEE', 'Standalone fee'],
];

function money(v) { return v == null ? '-' : `${formatMoney(v)} VND`; }

export default function TransactionsPage({ transactions: initialTransactions = [], today }) {
  const [transactions, setTransactions] = useState(initialTransactions);
  const [type, setType] = useState('POSITION_IMPORT');
  const [form, setForm] = useState({ event_date: today || '', symbol: '', quantity: '', price: '', amount: '', ratio: '', fee: '', tax: '', note: '' });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const requirements = useMemo(() => ({
    symbol: ['POSITION_IMPORT', 'BUY', 'SELL', 'STOCK_DIVIDEND', 'SPLIT', 'CASH_DIVIDEND'].includes(type),
    quantity: ['POSITION_IMPORT', 'BUY', 'SELL', 'STOCK_DIVIDEND'].includes(type),
    price: ['POSITION_IMPORT', 'BUY', 'SELL'].includes(type),
    amount: ['CASH_DEPOSIT', 'CASH_WITHDRAW', 'CASH_DIVIDEND', 'FEE'].includes(type),
    ratio: type === 'SPLIT',
    costs: ['BUY', 'SELL'].includes(type),
  }), [type]);

  function set(key, value) { setForm((x) => ({ ...x, [key]: value })); }

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const payload = {
        event_type: type,
        event_date: form.event_date,
        symbol: form.symbol || undefined,
        quantity: Number(form.quantity || 0),
        price: Number(form.price || 0),
        amount: Number(form.amount || 0),
        ratio: Number(form.ratio || 0),
        fee: Number(form.fee || 0),
        tax: Number(form.tax || 0),
        note: form.note,
      };
      const result = await createPortfolioTransaction(payload);
      setMessage(`Recorded immutable ledger event #${result.event_id}.`);
      window.location.reload();
    } catch (err) {
      setMessage(`Could not record event: ${err.message}`);
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <AppNav active="Transactions" />
      <header className="page-head">
        <h1>Transactions</h1>
        <p className="muted">The ledger is the source of truth. Existing events are not edited or deleted by the application.</p>
      </header>

      <div className="expand-grid ledger-layout">
        <form className="card" onSubmit={submit}>
          <h3>Record portfolio event</h3>
          <label>Event type
            <select value={type} onChange={(e) => setType(e.target.value)} disabled={saving}>
              {TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <div className="form-grid">
            <label>Date<input type="date" value={form.event_date} onChange={(e) => set('event_date', e.target.value)} required /></label>
            {requirements.symbol && <label>Symbol<input value={form.symbol} onChange={(e) => set('symbol', e.target.value.toUpperCase())} placeholder="FPT" required /></label>}
            {requirements.quantity && <label>Shares<input type="number" step="0.0001" min="0" value={form.quantity} onChange={(e) => set('quantity', e.target.value)} required /></label>}
            {requirements.price && <label>Price / share (VND)<input type="number" step="1" min="0" value={form.price} onChange={(e) => set('price', e.target.value)} required /></label>}
            {requirements.amount && <label>Amount (VND)<input type="number" step="1" min="0" value={form.amount} onChange={(e) => set('amount', e.target.value)} required /></label>}
            {requirements.ratio && <label>Share ratio<input type="number" step="0.0001" min="0" value={form.ratio} onChange={(e) => set('ratio', e.target.value)} placeholder="2 for 2:1 split" required /></label>}
            {requirements.costs && <label>Fee (VND)<input type="number" step="1" min="0" value={form.fee} onChange={(e) => set('fee', e.target.value)} /></label>}
            {requirements.costs && <label>Tax (VND)<input type="number" step="1" min="0" value={form.tax} onChange={(e) => set('tax', e.target.value)} /></label>}
          </div>
          <label>Note<textarea value={form.note} onChange={(e) => set('note', e.target.value)} placeholder="Optional source / broker note" /></label>
          <button className="btn-export" type="submit" disabled={saving}>{saving ? 'Recording…' : 'Record event'}</button>
          {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
          <p className="muted" style={{ marginBottom: 0 }}>For migration, use <b>Opening position import</b>. It creates shares/cost basis without pretending a historical cash trade occurred.</p>
        </form>

        <div className="card">
          <h3>Ledger rules</h3>
          <div className="rule-list">
            <div>✓ Price movement does not change shares.</div>
            <div>✓ Risk/model output does not change shares.</div>
            <div>✓ BUY requires cash already recorded in the ledger.</div>
            <div>✓ SELL cannot exceed owned shares.</div>
            <div>✓ Corporate actions are explicit events.</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Immutable event history ({transactions.length})</h3>
        {transactions.length === 0 ? <div className="muted">No events yet.</div> : (
          <div className="table-scroll"><table className="ranking">
            <thead><tr><th>ID</th><th>Date</th><th>Type</th><th>Symbol</th><th>Quantity</th><th>Price</th><th>Amount</th><th>Costs</th><th>Created by</th><th>Note</th></tr></thead>
            <tbody>{transactions.map((t) => (
              <tr key={t.id || `${t.event_date}-${t.event_type}-${t.symbol}`}>
                <td>{t.id ?? '-'}</td><td>{t.event_date}</td><td><b>{t.event_type}</b></td><td>{t.symbol || '-'}</td>
                <td>{t.quantity ? formatShares(t.quantity) : '-'}</td><td>{t.price ? money(t.price) : '-'}</td><td>{t.amount ? money(t.amount) : '-'}</td>
                <td>{money(Number(t.fee || 0) + Number(t.tax || 0))}</td><td>{t.created_by || '-'}</td><td>{t.note || '-'}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
