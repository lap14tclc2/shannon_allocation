import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction } from '../lib/api.js';
import { validateTransactionForm } from '../lib/validation.js';
import { useI18n } from '../i18n.js';

const TYPE_VALUES = [
  'POSITION_IMPORT', 'CASH_DEPOSIT', 'BUY', 'SELL', 'CASH_WITHDRAW',
  'CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'FEE',
];

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export default function TransactionsPage({ transactions: initialTransactions = [], today, locale = 'en' }) {
  const { t, eventType } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  const shares = (v) => formatShares(v, locale);
  const [transactions] = useState(initialTransactions);
  const [type, setType] = useState('POSITION_IMPORT');
  const [form, setForm] = useState({ event_date: today || '', symbol: '', quantity: '', price: '', amount: '', ratio: '', fee: '', tax: '', note: '' });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const requirements = useMemo(() => ({
    symbol: ['POSITION_IMPORT', 'BUY', 'SELL', 'STOCK_DIVIDEND', 'SPLIT', 'CASH_DIVIDEND'].includes(type),
    quantity: ['POSITION_IMPORT', 'BUY', 'SELL', 'STOCK_DIVIDEND'].includes(type),
    price: ['POSITION_IMPORT', 'BUY', 'SELL'].includes(type),
    amount: ['CASH_DEPOSIT', 'CASH_WITHDRAW', 'CASH_DIVIDEND', 'FEE'].includes(type),
    ratio: type === 'SPLIT',
    costs: ['BUY', 'SELL'].includes(type),
  }), [type]);

  function set(key, value) {
    setForm((x) => ({ ...x, [key]: value }));
    setFieldErrors((x) => ({ ...x, [key]: undefined }));
  }

  function changeType(value) {
    setType(value);
    setMessage('');
    setFieldErrors({});
    setForm((x) => ({ ...x, symbol: '', quantity: '', price: '', amount: '', ratio: '', fee: '', tax: '' }));
  }

  async function submit(e) {
    e.preventDefault();
    setMessage('');
    setFieldErrors({});
    let payload;
    try {
      payload = validateTransactionForm(type, form, today, locale);
    } catch (err) {
      setFieldErrors(err.field ? { [err.field]: err.message } : {});
      setMessage(err.message);
      return;
    }

    setSaving(true);
    try {
      const result = await createPortfolioTransaction(payload);
      setMessage(t('transactions.recorded', { id: result.event_id }));
      window.location.reload();
    } catch (err) {
      if (err.field) setFieldErrors({ [err.field]: err.message });
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
        <form className="card" onSubmit={submit} noValidate>
          <h3>{t('transactions.record_event')}</h3>
          <p className="muted">{text('Inputs are validated twice: here for immediate feedback and again by the backend before the immutable ledger is written.', 'Dữ liệu được kiểm tra hai lần: tại form để báo lỗi ngay và tại backend trước khi ghi vào sổ cái bất biến.')}</p>
          <label>{t('transactions.event_type')}
            <select value={type} onChange={(e) => changeType(e.target.value)} disabled={saving}>
              {TYPE_VALUES.map((value) => <option key={value} value={value}>{eventType(value)}</option>)}
            </select>
          </label>
          <div className="form-grid">
            <label>{t('transactions.date')}<input type="date" max={today || undefined} value={form.event_date} onChange={(e) => set('event_date', e.target.value)} aria-invalid={!!fieldErrors.event_date} /><FieldError error={fieldErrors.event_date} /></label>
            {requirements.symbol && <label>{t('transactions.symbol')}<input value={form.symbol} maxLength={10} onChange={(e) => set('symbol', e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase())} placeholder="FPT" aria-invalid={!!fieldErrors.symbol} /><FieldError error={fieldErrors.symbol} /></label>}
            {requirements.quantity && <label>{t('transactions.shares')}<input type="number" step="0.0001" min="0.0001" max="1000000000" value={form.quantity} onChange={(e) => set('quantity', e.target.value)} aria-invalid={!!fieldErrors.quantity} /><FieldError error={fieldErrors.quantity} /></label>}
            {requirements.price && <label>{t('transactions.price_share')}<input type="number" step="1" min="1000" max="10000000" value={form.price} onChange={(e) => set('price', e.target.value)} placeholder="72000" aria-invalid={!!fieldErrors.price} /><span className="muted">{text('Full VND/share, e.g. 72,000 — not 72.', 'VND đầy đủ/cổ phiếu, ví dụ 72.000 — không phải 72.')}</span><FieldError error={fieldErrors.price} /></label>}
            {requirements.amount && <label>{t('transactions.amount')}<input type="number" step="1" min="1" value={form.amount} onChange={(e) => set('amount', e.target.value)} aria-invalid={!!fieldErrors.amount} /><FieldError error={fieldErrors.amount} /></label>}
            {requirements.ratio && <label>{t('transactions.share_ratio')}<input type="number" step="0.0001" min="0.0001" max="100" value={form.ratio} onChange={(e) => set('ratio', e.target.value)} placeholder={t('transactions.ratio_placeholder')} aria-invalid={!!fieldErrors.ratio} /><FieldError error={fieldErrors.ratio} /></label>}
            {requirements.costs && <label>{t('transactions.fee')}<input type="number" step="1" min="0" value={form.fee} onChange={(e) => set('fee', e.target.value)} aria-invalid={!!fieldErrors.fee} /><FieldError error={fieldErrors.fee} /></label>}
            {requirements.costs && <label>{t('transactions.tax')}<input type="number" step="1" min="0" value={form.tax} onChange={(e) => set('tax', e.target.value)} aria-invalid={!!fieldErrors.tax} /><FieldError error={fieldErrors.tax} /></label>}
          </div>
          <label>{t('transactions.note')}<textarea maxLength={500} value={form.note} onChange={(e) => set('note', e.target.value)} placeholder={t('transactions.note_placeholder')} aria-invalid={!!fieldErrors.note} /><span className="muted">{form.note.length}/500</span><FieldError error={fieldErrors.note} /></label>
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
            <div>✓ {text('Future-dated events and suspicious sub-1,000 VND trade prices are rejected.', 'Sự kiện ở ngày tương lai và giá giao dịch đáng ngờ dưới 1.000 VND sẽ bị từ chối.')}</div>
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
