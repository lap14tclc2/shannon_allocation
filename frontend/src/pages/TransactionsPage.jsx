import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction, deletePortfolioTransaction, updatePortfolioTransaction } from '../lib/api.js';
import { validateTransactionForm } from '../lib/validation.js';
import { useI18n } from '../i18n.js';

const TYPE_VALUES = ['POSITION_IMPORT','CASH_DEPOSIT','BUY','SELL','CASH_WITHDRAW','CASH_DIVIDEND','STOCK_DIVIDEND','SPLIT','FEE'];
const EMPTY_FORM = (today = '') => ({
  event_date: today, symbol: '', quantity: '', price: '', amount: '', ratio: '', fee: '', tax: '', note: '',
  settlement_date: '', account_id: 'PRIMARY',
});
function FieldError({ error }) { return error ? <span className="field-error">{error}</span> : null; }

export default function TransactionsPage({ transactions: initialTransactions = [], corrections = [], today, locale = 'en' }) {
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
  const [deletingId, setDeletingId] = useState(null);
  const [message, setMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  const requirements = useMemo(() => ({
    symbol: ['POSITION_IMPORT','BUY','SELL','STOCK_DIVIDEND','SPLIT','CASH_DIVIDEND'].includes(type),
    quantity: ['POSITION_IMPORT','BUY','SELL','STOCK_DIVIDEND'].includes(type),
    price: ['POSITION_IMPORT','BUY','SELL'].includes(type),
    amount: ['CASH_DEPOSIT','CASH_WITHDRAW','CASH_DIVIDEND','FEE'].includes(type),
    ratio: type === 'SPLIT',
    trade: ['BUY','SELL'].includes(type),
  }), [type]);

  function set(key, value) { setForm(x => ({ ...x, [key]: value })); setFieldErrors(x => ({ ...x, [key]: undefined })); }
  function changeType(value) {
    setType(value); setMessage(''); setFieldErrors({});
    setForm(x => ({ ...x, symbol:'', quantity:'', price:'', amount:'', ratio:'', fee:'', tax:'', settlement_date:'', account_id:'PRIMARY' }));
  }
  function resetForm() { setEditingId(null); setCorrectionReason(''); setType('POSITION_IMPORT'); setForm(EMPTY_FORM(today || '')); setFieldErrors({}); }
  function startEdit(row) {
    setEditingId(row.id); setType(row.event_type); setCorrectionReason(''); setMessage(''); setFieldErrors({});
    setForm({
      event_date: row.event_date || today || '', symbol: row.symbol || '', quantity: row.quantity ? String(row.quantity) : '',
      price: row.price ? String(row.price) : '', amount: row.amount ? String(row.amount) : '', ratio: row.ratio ? String(row.ratio) : '',
      fee: row.fee ? String(row.fee) : '', tax: row.tax ? String(row.tax) : '', note: row.note || '',
      settlement_date: row.metadata?.settlement_date || '', account_id: row.metadata?.account_id || 'PRIMARY',
    });
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function submit(e) {
    e.preventDefault(); setMessage(''); setFieldErrors({});
    let payload;
    try {
      payload = validateTransactionForm(type, form, today, locale);
      if (editingId && !correctionReason.trim()) throw Object.assign(new Error(text('Enter why this transaction is being corrected.', 'Nhập lý do sửa giao dịch này.')), { field: 'correction_reason' });
    } catch (err) { setFieldErrors(err.field ? { [err.field]: err.message } : {}); setMessage(err.message); return; }
    setSaving(true);
    try {
      if (editingId) await updatePortfolioTransaction(editingId, { ...payload, correction_reason: correctionReason.trim() });
      else await createPortfolioTransaction(payload);
      window.location.reload();
    } catch (err) { if (err.field) setFieldErrors({ [err.field]: err.message }); setMessage(err.message); setSaving(false); }
  }

  async function remove(row) {
    const reason = window.prompt(text(`Why should transaction #${row.id} be removed from the effective ledger?`, `Vì sao cần xóa giao dịch #${row.id} khỏi sổ cái hiệu lực?`));
    if (reason == null) return;
    if (!reason.trim()) { setMessage(text('Deletion reason is required.', 'Bắt buộc nhập lý do xóa.')); return; }
    if (!window.confirm(text(`Delete transaction #${row.id} from the effective portfolio? The source row remains in the audit log.`, `Xóa giao dịch #${row.id} khỏi danh mục hiệu lực? Dòng gốc vẫn nằm trong audit log.`))) return;
    setDeletingId(row.id);
    try { await deletePortfolioTransaction(row.id, reason.trim()); window.location.reload(); }
    catch (err) { setMessage(err.message); setDeletingId(null); }
  }

  return <div className="page">
    <AppNav active="transactions" locale={locale} />
    <header className="page-head"><div><h1>{t('transactions.title')}</h1><p className="muted">{text('Trade-date event journal with append-only corrections. Settlement is a separate operational control.', 'Sổ sự kiện theo ngày giao dịch với correction append-only. Settlement là một kiểm soát vận hành riêng.')}</p></div></header>

    <div className="expand-grid ledger-layout">
      <form className={`card ${editingId ? 'correction-form' : ''}`} onSubmit={submit} noValidate>
        <div className="section-head"><div><h3>{editingId ? text(`Correct transaction #${editingId}`, `Sửa giao dịch #${editingId}`) : t('transactions.record_event')}</h3><p className="muted">{text('Inputs are validated by UI and backend; the complete chronological ledger is then replayed before acceptance.', 'Input được validate ở UI và backend; sau đó toàn bộ ledger theo thứ tự thời gian được replay trước khi chấp nhận.')}</p></div>{editingId && <button className="btn-variant" type="button" onClick={resetForm}>{text('Cancel edit','Hủy sửa')}</button>}</div>
        <label>{t('transactions.event_type')}<select value={type} onChange={e => changeType(e.target.value)} disabled={saving}>{TYPE_VALUES.map(v => <option key={v} value={v}>{eventType(v)}</option>)}</select></label>
        <div className="form-grid">
          <label>{requirements.trade ? text('Trade date','Ngày giao dịch') : t('transactions.date')}<input type="date" max={today || undefined} value={form.event_date} onChange={e => set('event_date', e.target.value)} aria-invalid={!!fieldErrors.event_date}/><FieldError error={fieldErrors.event_date}/></label>
          {requirements.symbol && <label>{t('transactions.symbol')}<input value={form.symbol} maxLength={10} onChange={e => set('symbol', e.target.value.replace(/[^a-zA-Z0-9]/g,'').toUpperCase())} placeholder="FPT" aria-invalid={!!fieldErrors.symbol}/><FieldError error={fieldErrors.symbol}/></label>}
          {requirements.quantity && <label>{t('transactions.shares')}<input type="number" step="0.0001" min="0.0001" value={form.quantity} onChange={e => set('quantity', e.target.value)} aria-invalid={!!fieldErrors.quantity}/><FieldError error={fieldErrors.quantity}/></label>}
          {requirements.price && <label>{t('transactions.price_share')}<input type="number" step="1" min="1000" value={form.price} onChange={e => set('price', e.target.value)} placeholder="72000" aria-invalid={!!fieldErrors.price}/><span className="muted">{text('Full VND/share.', 'VND đầy đủ/cổ phiếu.')}</span><FieldError error={fieldErrors.price}/></label>}
          {requirements.amount && <label>{t('transactions.amount')}<input value={form.amount} onChange={e => set('amount', e.target.value)} aria-invalid={!!fieldErrors.amount}/><FieldError error={fieldErrors.amount}/></label>}
          {requirements.ratio && <label>{t('transactions.share_ratio')}<input type="number" step="0.0001" min="0.0001" value={form.ratio} onChange={e => set('ratio', e.target.value)}/></label>}
          {requirements.trade && <label>{text('Settlement date (optional)', 'Ngày thanh toán (không bắt buộc)')}<input type="date" min={form.event_date || undefined} value={form.settlement_date} onChange={e => set('settlement_date', e.target.value)} aria-invalid={!!fieldErrors.settlement_date}/><span className="muted">{text('Blank = estimated T+2 weekdays; confirm actual settlement in Operations.', 'Để trống = ước tính T+2 ngày làm việc; xác nhận settlement thực tế ở Vận hành.')}</span><FieldError error={fieldErrors.settlement_date}/></label>}
          {requirements.trade && <label>{text('Account', 'Tài khoản')}<input value={form.account_id} maxLength={32} onChange={e => set('account_id', e.target.value.toUpperCase().replace(/[^A-Z0-9_.-]/g,''))} placeholder="PRIMARY" aria-invalid={!!fieldErrors.account_id}/><FieldError error={fieldErrors.account_id}/></label>}
          {requirements.trade && <label>{t('transactions.fee')}<input type="number" min="0" step="1" value={form.fee} onChange={e => set('fee', e.target.value)}/></label>}
          {requirements.trade && <label>{t('transactions.tax')}<input type="number" min="0" step="1" value={form.tax} onChange={e => set('tax', e.target.value)}/></label>}
        </div>
        <label>{t('transactions.note')}<textarea maxLength={500} value={form.note} onChange={e => set('note', e.target.value)}/><span className="muted">{form.note.length}/500</span></label>
        {editingId && <label>{text('Correction reason','Lý do sửa dữ liệu')}<textarea maxLength={500} value={correctionReason} onChange={e => setCorrectionReason(e.target.value)} aria-invalid={!!fieldErrors.correction_reason}/><FieldError error={fieldErrors.correction_reason}/></label>}
        <div className="button-row"><button className="btn-export" type="submit" disabled={saving}>{saving ? '…' : editingId ? text('Save correction','Lưu correction') : t('transactions.record')}</button>{editingId && <button className="btn-variant" type="button" onClick={resetForm}>{text('Cancel','Hủy')}</button>}</div>
        {message && <div className="run-message">{message}</div>}
      </form>

      <div className="card"><h3>{text('Institutional ledger rules','Quy tắc ledger institutional-lite')}</h3><div className="rule-list">
        <div>✓ {text('BUY/SELL positions are recognized on trade date.', 'BUY/SELL được ghi nhận vị thế theo ngày giao dịch.')}</div>
        <div>✓ {text('Settlement changes settlement status, not source trade history.', 'Settlement thay đổi trạng thái thanh toán, không sửa lịch sử trade gốc.')}</div>
        <div>✓ {text('Open lots are retained; SELL uses FIFO lot disposal.', 'Các lot được giữ riêng; SELL dùng FIFO để xuất lot.')}</div>
        <div>✓ {text('Edit/Delete preserves original rows and can create NAV restatement controls.', 'Sửa/Xóa giữ dòng gốc và có thể tạo kiểm soát restatement NAV.')}</div>
      </div></div>
    </div>

    <div className="card"><div className="section-head"><div><h3>{text('Effective event history','Lịch sử sự kiện hiệu lực')}</h3><div className="muted">{transactions.length} events</div></div></div>
      {transactions.length === 0 ? <div className="empty-state">{t('transactions.no_events')}</div> : <div className="table-scroll"><table className="ranking transaction-table"><thead><tr><th>ID</th><th>{text('Date','Ngày')}</th><th>{text('Type','Loại')}</th><th>{text('Ticker','Mã')}</th><th>{text('Qty','SL')}</th><th>{text('Price','Giá')}</th><th>{text('Settlement','Thanh toán')}</th><th>{text('Account','Tài khoản')}</th><th>Audit</th><th>{text('Actions','Thao tác')}</th></tr></thead><tbody>{transactions.map(row => <tr key={row.id}><td>{row.id}</td><td>{row.event_date}</td><td><b>{eventType(row.event_type)}</b></td><td>{row.symbol || '-'}</td><td>{row.quantity ? shares(row.quantity) : '-'}</td><td>{row.price ? money(row.price) : row.amount ? money(row.amount) : '-'}</td><td>{row.metadata?.settlement_date || (['BUY','SELL'].includes(row.event_type) ? text('Estimated in Operations','Ước tính ở Vận hành') : '-')}</td><td>{row.metadata?.account_id || '-'}</td><td>{row.correction ? <span className="status-pill status-stale">{text('CORRECTED','ĐÃ SỬA')}</span> : text('Original','Gốc')}</td><td><div className="row-actions"><button className="btn-small" onClick={() => startEdit(row)}>{text('Edit','Sửa')}</button><button className="btn-danger btn-small" disabled={deletingId === row.id} onClick={() => remove(row)}>{text('Delete','Xóa')}</button></div></td></tr>)}</tbody></table></div>}
    </div>

    <div className="card correction-audit-card"><h3>{text('Correction audit log','Nhật ký correction')}</h3>{corrections.length === 0 ? <p className="muted">{text('No corrections yet.','Chưa có correction.')}</p> : <div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>Event</th><th>Action</th><th>{text('Reason','Lý do')}</th><th>{text('When','Thời điểm')}</th><th>{text('Original','Gốc')}</th></tr></thead><tbody>{corrections.map(c => <tr key={c.id}><td>{c.id}</td><td>#{c.event_id}</td><td>{c.action}</td><td>{c.reason}</td><td>{c.created_at}</td><td>{c.original ? `${c.original.event_type} ${c.original.symbol || ''}` : '-'}</td></tr>)}</tbody></table></div>}</div>
  </div>;
}
