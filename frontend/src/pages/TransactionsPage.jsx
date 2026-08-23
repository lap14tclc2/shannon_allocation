import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import {
  createPortfolioTransaction,
  deletePortfolioTransaction,
  updatePortfolioTransaction,
} from '../lib/api.js';
import { validateTransactionForm } from '../lib/validation.js';
import { useI18n } from '../i18n.js';

const TYPE_VALUES = [
  'POSITION_IMPORT', 'CASH_DEPOSIT', 'BUY', 'SELL', 'CASH_WITHDRAW',
  'CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'FEE',
];

const EMPTY_FORM = (today = '') => ({
  event_date: today, symbol: '', quantity: '', price: '', amount: '', ratio: '',
  fee: '', tax: '', note: '',
});

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export default function TransactionsPage({ transactions: initialTransactions = [], corrections = [], today, locale = 'en' }) {
  const { t, eventType } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
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
      if (editingId) {
        const result = await updatePortfolioTransaction(editingId, { ...payload, correction_reason: correctionReason.trim() });
        setMessage(text(`Transaction #${result.event_id} corrected.`, `Đã sửa giao dịch #${result.event_id}.`));
      } else {
        const result = await createPortfolioTransaction(payload);
        setMessage(t('transactions.recorded', { id: result.event_id }));
      }
      window.location.reload();
    } catch (err) {
      if (err.field) setFieldErrors({ [err.field]: err.message });
      setMessage(editingId
        ? text(`Correction failed: ${err.message}`, `Sửa dữ liệu thất bại: ${err.message}`)
        : t('transactions.failed', { error: err.message }));
      setSaving(false);
    }
  }

  async function remove(row) {
    const reason = window.prompt(text(
      `Why should transaction #${row.id} be removed from the effective ledger?`,
      `Vì sao cần xóa giao dịch #${row.id} khỏi sổ cái hiệu lực?`,
    ));
    if (reason == null) return;
    if (!reason.trim()) {
      setMessage(text('Deletion reason is required.', 'Bắt buộc nhập lý do xóa.'));
      return;
    }
    const ok = window.confirm(text(
      `Delete transaction #${row.id} from the effective portfolio? The source row will remain in the audit log.`,
      `Xóa giao dịch #${row.id} khỏi danh mục hiệu lực? Dòng gốc vẫn được giữ trong audit log.`,
    ));
    if (!ok) return;
    setDeletingId(row.id);
    setMessage('');
    try {
      await deletePortfolioTransaction(row.id, reason.trim());
      window.location.reload();
    } catch (err) {
      setMessage(text(`Delete failed: ${err.message}`, `Xóa thất bại: ${err.message}`));
      setDeletingId(null);
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
        <form className={`card ${editingId ? 'correction-form' : ''}`} onSubmit={submit} noValidate>
          <div className="section-head">
            <div>
              <h3>{editingId ? text(`Correct transaction #${editingId}`, `Sửa giao dịch #${editingId}`) : t('transactions.record_event')}</h3>
              <p className="muted">{editingId
                ? text('The original ledger row is preserved. Saving creates an audited correction and recalculates the effective portfolio.', 'Dòng sổ cái gốc được giữ nguyên. Khi lưu, QPort tạo correction có audit và tính lại danh mục hiệu lực.')
                : text('Inputs are validated twice: here for immediate feedback and again by the backend before the source ledger is written.', 'Dữ liệu được kiểm tra hai lần: tại form để báo lỗi ngay và tại backend trước khi ghi vào sổ cái nguồn.')}</p>
            </div>
            {editingId && <button className="btn-variant" type="button" onClick={resetForm} disabled={saving}>{text('Cancel edit', 'Hủy sửa')}</button>}
          </div>
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
          {editingId && <label>{text('Correction reason', 'Lý do sửa dữ liệu')}<textarea maxLength={500} value={correctionReason} onChange={(e) => { setCorrectionReason(e.target.value); setFieldErrors((x) => ({ ...x, correction_reason: undefined })); }} placeholder={text('Example: wrong broker price entered during initial import', 'Ví dụ: nhập sai giá broker khi import ban đầu')} aria-invalid={!!fieldErrors.correction_reason} /><span className="muted">{correctionReason.length}/500</span><FieldError error={fieldErrors.correction_reason} /></label>}
          <div className="button-row">
            <button className="btn-export" type="submit" disabled={saving}>{saving ? t('transactions.recording') : editingId ? text('Save correction', 'Lưu correction') : t('transactions.record')}</button>
            {editingId && <button className="btn-variant" type="button" onClick={resetForm} disabled={saving}>{text('Cancel', 'Hủy')}</button>}
          </div>
          {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
          <p className="muted" style={{ marginBottom: 0 }}>{editingId
            ? text('Edit/Delete never physically mutates the original source row.', 'Sửa/Xóa không bao giờ thay đổi vật lý dòng dữ liệu gốc.')
            : t('transactions.migration_note')}</p>
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
            <div>✓ {text('Corrections are append-only and the full effective ledger is revalidated after every edit/delete.', 'Correction chỉ được ghi nối tiếp và toàn bộ sổ cái hiệu lực được kiểm tra lại sau mỗi lần sửa/xóa.')}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="section-head"><div><h3>{t('transactions.history', { count: transactions.length })}</h3><div className="muted">{text('This table shows the effective ledger after corrections.', 'Bảng này hiển thị sổ cái hiệu lực sau các correction.')}</div></div></div>
        {transactions.length === 0 ? <div className="muted">{t('transactions.no_events')}</div> : (
          <div className="table-scroll"><table className="ranking transaction-table">
            <thead><tr><th>{t('transactions.id')}</th><th>{t('transactions.date')}</th><th>{t('transactions.type')}</th><th>{t('transactions.symbol')}</th><th>{t('transactions.quantity')}</th><th>{t('transactions.price')}</th><th>{t('transactions.amount')}</th><th>{t('transactions.costs')}</th><th>{text('Audit', 'Audit')}</th><th>{t('transactions.note')}</th><th>{text('Actions', 'Thao tác')}</th></tr></thead>
            <tbody>{transactions.map((row) => (
              <tr key={row.id || `${row.event_date}-${row.event_type}-${row.symbol}`}>
                <td>{row.id ?? '-'}</td><td>{row.event_date}</td><td><b>{eventType(row.event_type)}</b></td><td>{row.symbol || '-'}</td>
                <td>{row.quantity ? shares(row.quantity) : '-'}</td><td>{row.price ? money(row.price) : '-'}</td><td>{row.amount ? money(row.amount) : '-'}</td>
                <td>{money(Number(row.fee || 0) + Number(row.tax || 0))}</td>
                <td>{row.correction ? <span className="status-pill status-stale" title={row.correction.reason}>{text('CORRECTED', 'ĐÃ SỬA')}</span> : <span className="muted">{text('Original', 'Gốc')}</span>}</td>
                <td>{row.note || '-'}</td>
                <td><div className="row-actions"><button className="btn-variant btn-small" type="button" onClick={() => startEdit(row)}>{text('Edit', 'Sửa')}</button><button className="btn-danger btn-small" type="button" disabled={deletingId === row.id} onClick={() => remove(row)}>{deletingId === row.id ? '…' : text('Delete', 'Xóa')}</button></div></td>
              </tr>
            ))}</tbody>
          </table></div>
        )}
      </div>

      <div className="card correction-audit-card">
        <div className="section-head"><div><h3>{text('Correction audit log', 'Nhật ký correction')}</h3><div className="muted">{text('Original transaction rows are retained here even when removed from the effective portfolio.', 'Dòng giao dịch gốc vẫn được giữ tại đây kể cả khi đã xóa khỏi danh mục hiệu lực.')}</div></div><span className="status-pill">{corrections.length}</span></div>
        {corrections.length === 0 ? <p className="muted">{text('No corrections yet.', 'Chưa có correction.')}</p> : <div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>{text('Event', 'Giao dịch')}</th><th>{text('Action', 'Thao tác')}</th><th>{text('Reason', 'Lý do')}</th><th>{text('When', 'Thời điểm')}</th><th>{text('Original', 'Dữ liệu gốc')}</th></tr></thead><tbody>{corrections.map((c) => <tr key={c.id}><td>{c.id}</td><td>#{c.event_id}</td><td><b>{c.action}</b></td><td>{c.reason}</td><td>{c.created_at}</td><td>{c.original ? `${c.original.event_type} ${c.original.symbol || ''} ${c.original.quantity || c.original.amount || ''}` : '-'}</td></tr>)}</tbody></table></div>}
      </div>
    </div>
  );
}
