import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction, deletePortfolioTransaction, updatePortfolioTransaction } from '../lib/api.js';
import { BROKERS } from '../lib/brokers.js';
import { validateTransactionForm } from '../lib/validation.js';
import { useI18n } from '../i18n.js';

const TYPE_VALUES = ['POSITION_IMPORT','CASH_DEPOSIT','BUY','SELL','CASH_WITHDRAW','CASH_DIVIDEND','STOCK_DIVIDEND','SPLIT','FEE'];
const EMPTY_FORM = (today = '') => ({
  event_date: today, symbol: '', quantity: '', price: '', amount: '', ratio: '', fee: '', tax: '', note: '',
  settlement_date: '', broker_code: 'UNASSIGNED', account_id: 'PRIMARY',
});

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export default function TransactionsPage({ transactions: initialTransactions = [], today, locale = 'en' }) {
  const { t, eventType } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => v == null ? '-' : `${formatMoney(v, false, locale)} VND`;
  const shares = (v) => formatShares(v, locale);
  const [transactions] = useState(initialTransactions);
  const [type, setType] = useState('POSITION_IMPORT');
  const [form, setForm] = useState(EMPTY_FORM(today || ''));
  const [editingId, setEditingId] = useState(null);
  const [correctionReason, setCorrectionReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [deleteRowId, setDeleteRowId] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');

  const requirements = useMemo(() => ({
    symbol: ['POSITION_IMPORT','BUY','SELL','STOCK_DIVIDEND','SPLIT','CASH_DIVIDEND'].includes(type),
    quantity: ['POSITION_IMPORT','BUY','SELL','STOCK_DIVIDEND'].includes(type),
    price: ['POSITION_IMPORT','BUY','SELL'].includes(type),
    amount: ['CASH_DEPOSIT','CASH_WITHDRAW','CASH_DIVIDEND','FEE'].includes(type),
    ratio: type === 'SPLIT',
    trade: ['BUY','SELL'].includes(type),
  }), [type]);

  function set(key, value) {
    setForm(x => ({ ...x, [key]: value }));
    setFieldErrors(x => ({ ...x, [key]: undefined }));
  }

  function changeType(value) {
    setType(value);
    setMessage('');
    setFieldErrors({});
    setForm(x => ({ ...x, symbol:'', quantity:'', price:'', amount:'', ratio:'', fee:'', tax:'', settlement_date:'' }));
  }

  function resetForm() {
    setEditingId(null);
    setCorrectionReason('');
    setType('POSITION_IMPORT');
    setForm(EMPTY_FORM(today || ''));
    setFieldErrors({});
  }

  function startEdit(row) {
    setEditingId(row.id);
    setType(row.event_type);
    setCorrectionReason('');
    setMessage('');
    setFieldErrors({});
    setForm({
      event_date: row.event_date || today || '',
      symbol: row.symbol || '',
      quantity: row.quantity ? String(row.quantity) : '',
      price: row.price ? String(row.price) : '',
      amount: row.amount ? String(row.amount) : '',
      ratio: row.ratio ? String(row.ratio) : '',
      fee: row.fee ? String(row.fee) : '',
      tax: row.tax ? String(row.tax) : '',
      note: row.note || '',
      settlement_date: row.metadata?.settlement_date || '',
      broker_code: row.metadata?.broker_code || 'UNASSIGNED',
      account_id: row.metadata?.account_id || 'PRIMARY',
    });
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function submit(e) {
    e.preventDefault();
    setMessage('');
    setFieldErrors({});
    let payload;
    try {
      payload = validateTransactionForm(type, form, today, locale);
      if (editingId && !correctionReason.trim()) {
        throw Object.assign(new Error(text('Enter why this transaction is being corrected.', 'Nhập lý do sửa giao dịch này.')), { field: 'correction_reason' });
      }
    } catch (err) {
      setFieldErrors(err.field ? { [err.field]: err.message } : {});
      setMessage(err.message);
      return;
    }

    setSaving(true);
    try {
      if (editingId) await updatePortfolioTransaction(editingId, { ...payload, correction_reason: correctionReason.trim() });
      else await createPortfolioTransaction(payload);
      window.location.reload();
    } catch (err) {
      if (err.field) setFieldErrors({ [err.field]: err.message });
      setMessage(err.message);
      setSaving(false);
    }
  }

  async function confirmDelete(row) {
    if (!deleteReason.trim()) {
      setMessage(text('Deletion reason is required.', 'Bắt buộc nhập lý do xóa.'));
      return;
    }
    setMessage('');
    try {
      await deletePortfolioTransaction(row.id, deleteReason.trim());
      window.location.reload();
    } catch (err) {
      setMessage(err.message);
    }
  }

  return <div className="page">
    <AppNav active="transactions" locale={locale} />
    <header className="page-head">
      <div>
        <h1>{t('transactions.title')}</h1>
        <p className="muted">{text('Record what actually happened in your portfolio. Advanced broker and settlement fields are optional.', 'Ghi lại những gì thực sự xảy ra trong danh mục. Broker và settlement là thông tin nâng cao, không bắt buộc.')}</p>
      </div>
    </header>

    <form className={`card ${editingId ? 'correction-form' : ''}`} onSubmit={submit} noValidate>
      <div className="section-head">
        <div>
          <h3>{editingId ? text(`Edit transaction #${editingId}`, `Sửa giao dịch #${editingId}`) : t('transactions.record_event')}</h3>
          <p className="muted">{text('Choose the event and enter only the fields that apply.', 'Chọn loại sự kiện và chỉ nhập các trường liên quan.')}</p>
        </div>
        {editingId && <button className="btn-variant" type="button" onClick={resetForm}>{text('Cancel edit','Hủy sửa')}</button>}
      </div>

      <label>{t('transactions.event_type')}
        <select value={type} onChange={e => changeType(e.target.value)} disabled={saving}>
          {TYPE_VALUES.map(v => <option key={v} value={v}>{eventType(v)}</option>)}
        </select>
      </label>

      <div className="form-grid">
        <label>{requirements.trade ? text('Trade date','Ngày giao dịch') : t('transactions.date')}
          <input type="date" max={today || undefined} value={form.event_date} onChange={e => set('event_date', e.target.value)} aria-invalid={!!fieldErrors.event_date}/>
          <FieldError error={fieldErrors.event_date}/>
        </label>
        {requirements.symbol && <label>{t('transactions.symbol')}
          <input value={form.symbol} maxLength={10} onChange={e => set('symbol', e.target.value.replace(/[^a-zA-Z0-9]/g,'').toUpperCase())} placeholder="FPT" aria-invalid={!!fieldErrors.symbol}/>
          <FieldError error={fieldErrors.symbol}/>
        </label>}
        {requirements.quantity && <label>{t('transactions.shares')}
          <input type="number" step="0.0001" min="0.0001" value={form.quantity} onChange={e => set('quantity', e.target.value)} aria-invalid={!!fieldErrors.quantity}/>
          <FieldError error={fieldErrors.quantity}/>
        </label>}
        {requirements.price && <label>{t('transactions.price_share')}
          <input type="number" step="1" min="1000" value={form.price} onChange={e => set('price', e.target.value)} placeholder="72000" aria-invalid={!!fieldErrors.price}/>
          <FieldError error={fieldErrors.price}/>
        </label>}
        {requirements.amount && <label>{t('transactions.amount')}
          <input value={form.amount} onChange={e => set('amount', e.target.value)} aria-invalid={!!fieldErrors.amount}/>
          <FieldError error={fieldErrors.amount}/>
        </label>}
        {requirements.ratio && <label>{t('transactions.share_ratio')}
          <input type="number" step="0.0001" min="0.0001" value={form.ratio} onChange={e => set('ratio', e.target.value)}/>
        </label>}
      </div>

      <details className="disclosure-card transaction-advanced">
        <summary><b>{text('Advanced details', 'Thông tin nâng cao')}</b><span className="muted">{text('Broker, account, settlement, fee and tax', 'Broker, tài khoản, settlement, phí và thuế')}</span></summary>
        <div className="form-grid">
          <label>{text('Broker','Công ty CK')}
            <select value={form.broker_code} onChange={e => set('broker_code', e.target.value)}>
              {BROKERS.map(b => <option key={b.code} value={b.code}>{b.name}</option>)}
            </select>
            <FieldError error={fieldErrors.broker_code}/>
          </label>
          <label>{text('Account','Tài khoản')}
            <input value={form.account_id} maxLength={32} onChange={e => set('account_id', e.target.value.toUpperCase().replace(/[^A-Z0-9_.-]/g,''))} placeholder="PRIMARY" aria-invalid={!!fieldErrors.account_id}/>
            <FieldError error={fieldErrors.account_id}/>
          </label>
          {requirements.trade && <label>{text('Settlement date', 'Ngày thanh toán')}
            <input type="date" min={form.event_date || undefined} value={form.settlement_date} onChange={e => set('settlement_date', e.target.value)} aria-invalid={!!fieldErrors.settlement_date}/>
            <FieldError error={fieldErrors.settlement_date}/>
          </label>}
          {requirements.trade && <label>{t('transactions.fee')}
            <input type="number" min="0" step="1" value={form.fee} onChange={e => set('fee', e.target.value)}/>
          </label>}
          {requirements.trade && <label>{t('transactions.tax')}
            <input type="number" min="0" step="1" value={form.tax} onChange={e => set('tax', e.target.value)}/>
          </label>}
        </div>
      </details>

      <label>{t('transactions.note')}
        <textarea maxLength={500} value={form.note} onChange={e => set('note', e.target.value)}/>
      </label>

      {editingId && <label>{text('Reason for correction','Lý do sửa dữ liệu')}
        <textarea maxLength={500} value={correctionReason} onChange={e => setCorrectionReason(e.target.value)} aria-invalid={!!fieldErrors.correction_reason}/>
        <FieldError error={fieldErrors.correction_reason}/>
      </label>}

      <div className="button-row">
        <button className="btn-export" type="submit" disabled={saving}>{saving ? '…' : editingId ? text('Save changes','Lưu thay đổi') : t('transactions.record')}</button>
        {editingId && <button className="btn-variant" type="button" onClick={resetForm}>{text('Cancel','Hủy')}</button>}
      </div>
      {message && <div className="run-message">{message}</div>}
    </form>

    <div className="card">
      <div className="section-head">
        <div><h3>{text('Transaction history','Lịch sử giao dịch')}</h3><div className="muted">{transactions.length} {text('events','sự kiện')}</div></div>
      </div>
      {transactions.length === 0 ? <div className="empty-state">{t('transactions.no_events')}</div> : <div className="table-scroll">
        <table className="ranking transaction-table">
          <thead><tr>
            <th>{text('Date','Ngày')}</th>
            <th>{text('Type','Loại')}</th>
            <th>{text('Ticker','Mã')}</th>
            <th>Broker</th>
            <th>{text('Account','Tài khoản')}</th>
            <th>{text('Qty','SL')}</th>
            <th>{text('Price / Amount','Giá / Tiền')}</th>
            <th>{text('Note','Ghi chú')}</th>
            <th>{text('Actions','Thao tác')}</th>
          </tr></thead>
          <tbody>{transactions.map(row => {
            const deleting = deleteRowId === row.id;
            const securityEvent = Boolean(row.symbol);
            const broker = row.metadata?.broker_code || 'UNASSIGNED';
            const account = row.metadata?.account_id || 'PRIMARY';
            return <tr key={row.id}>
              <td>{row.event_date}</td>
              <td><b>{eventType(row.event_type)}</b>{row.correction && <div className="muted">{text('Corrected','Đã sửa')}</div>}{row.metadata?.auto_generated && <div className="muted">AUTO</div>}</td>
              <td>{row.symbol || '-'}</td>
              <td>{securityEvent ? broker : '-'}</td>
              <td>{securityEvent ? account : '-'}</td>
              <td>{row.quantity ? shares(row.quantity) : '-'}</td>
              <td>{row.price ? money(row.price) : row.amount ? money(row.amount) : '-'}</td>
              <td>{row.note || '-'}</td>
              <td>{deleting ? <div className="inline-delete">
                <input value={deleteReason} onChange={e => setDeleteReason(e.target.value)} placeholder={text('Reason for delete','Lý do xóa')}/>
                <div className="row-actions">
                  <button className="btn-danger btn-small" type="button" onClick={() => confirmDelete(row)}>{text('Confirm','Xác nhận')}</button>
                  <button className="btn-small" type="button" onClick={() => { setDeleteRowId(null); setDeleteReason(''); }}>{text('Cancel','Hủy')}</button>
                </div>
              </div> : <div className="row-actions">
                <button className="btn-small" type="button" onClick={() => startEdit(row)}>{text('Edit','Sửa')}</button>
                <button className="btn-danger btn-small" type="button" onClick={() => { setDeleteRowId(row.id); setDeleteReason(''); }}>{text('Delete','Xóa')}</button>
              </div>}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>}
    </div>
  </div>;
}
