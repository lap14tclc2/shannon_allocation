import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction } from '../lib/api.js';
import { useI18n } from '../i18n.js';

const TYPE_VALUES = [
  'POSITION_IMPORT',
  'CASH_DEPOSIT',
  'BUY',
  'SELL',
  'CASH_WITHDRAW',
  'CASH_DIVIDEND',
  'STOCK_DIVIDEND',
  'SPLIT',
  'FEE',
];

export default function TransactionsPage({ transactions: initialTransactions = [], today, locale = 'en' }) {
  const { t, eventType } = useI18n(locale);
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  const shares = (v) => formatShares(v, locale);
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
      setMessage(t('transactions.recorded', { id: result.event_id }));
      window.location.reload();
    } catch (err) {
      setMessage(t('transactions.failed', { error: err.message }));
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <AppNav active="transactions" locale={locale} />
      <header className="page-head">
        <h1>{t('transactions.title')}</h1>
        <p className="muted">{t('transactions.subtitle')}</p>
      </header>

      <div className="expand-grid ledger-layout">
        <form className="card" onSubmit={submit}>
          <h3>{t('transactions.record_event')}</h3>
          <label>{t('transactions.event_type')}
            <select value={type} onChange={(e) => setType(e.target.value)} disabled={saving}>
              {TYPE_VALUES.map((value) => <option key={value} value={value}>{eventType(value)}</option>)}
            </select>
          </label>
          <div className="form-grid">
            <label>{t('transactions.date')}<input type="date" value={form.event_date} onChange={(e) => set('event_date', e.target.value)} required /></label>
            {requirements.symbol && <label>{t('transactions.symbol')}<input value={form.symbol} onChange={(e) => set('symbol', e.target.value.toUpperCase())} placeholder="FPT" required /></label>}
            {requirements.quantity && <label>{t('transactions.shares')}<input type="number" step="0.0001" min="0" value={form.quantity} onChange={(e) => set('quantity', e.target.value)} required /></label>}
            {requirements.price && <label>{t('transactions.price_share')}<input type="number" step="1" min="0" value={form.price} onChange={(e) => set('price', e.target.value)} required /></label>}
            {requirements.amount && <label>{t('transactions.amount')}<input type="number" step="1" min="0" value={form.amount} onChange={(e) => set('amount', e.target.value)} required /></label>}
            {requirements.ratio && <label>{t('transactions.share_ratio')}<input type="number" step="0.0001" min="0" value={form.ratio} onChange={(e) => set('ratio', e.target.value)} placeholder={t('transactions.ratio_placeholder')} required /></label>}
            {requirements.costs && <label>{t('transactions.fee')}<input type="number" step="1" min="0" value={form.fee} onChange={(e) => set('fee', e.target.value)} /></label>}
            {requirements.costs && <label>{t('transactions.tax')}<input type="number" step="1" min="0" value={form.tax} onChange={(e) => set('tax', e.target.value)} /></label>}
          </div>
          <label>{t('transactions.note')}<textarea value={form.note} onChange={(e) => set('note', e.target.value)} placeholder={t('transactions.note_placeholder')} /></label>
          <button className="btn-export" type="submit" disabled={saving}>{saving ? t('transactions.recording') : t('transactions.record')}</button>
          {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
          <p className="muted" style={{ marginBottom: 0 }}>{t('transactions.migration_note')}</p>
        </form>

        <div className="card">
          <h3>{t('transactions.ledger_rules')}</h3>
          <div className="rule-list">
            <div>✓ {t('transactions.rule_price')}</div>
            <div>✓ {t('transactions.rule_risk')}</div>
            <div>✓ {t('transactions.rule_buy_cash')}</div>
            <div>✓ {t('transactions.rule_sell')}</div>
            <div>✓ {t('transactions.rule_corp')}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>{t('transactions.history', { count: transactions.length })}</h3>
        {transactions.length === 0 ? <div className="muted">{t('transactions.no_events')}</div> : (
          <div className="table-scroll"><table className="ranking">
            <thead><tr><th>{t('transactions.id')}</th><th>{t('transactions.date')}</th><th>{t('transactions.type')}</th><th>{t('transactions.symbol')}</th><th>{t('transactions.quantity')}</th><th>{t('transactions.price')}</th><th>{t('transactions.amount')}</th><th>{t('transactions.costs')}</th><th>{t('transactions.created_by')}</th><th>{t('transactions.note')}</th></tr></thead>
            <tbody>{transactions.map((row) => (
              <tr key={row.id || `${row.event_date}-${row.event_type}-${row.symbol}`}>
                <td>{row.id ?? '-'}</td><td>{row.event_date}</td><td><b>{eventType(row.event_type)}</b></td><td>{row.symbol || '-'}</td>
                <td>{row.quantity ? shares(row.quantity) : '-'}</td><td>{row.price ? money(row.price) : '-'}</td><td>{row.amount ? money(row.amount) : '-'}</td>
                <td>{money(Number(row.fee || 0) + Number(row.tax || 0))}</td><td>{row.created_by || '-'}</td><td>{row.note || '-'}</td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
    </div>
  );
}
