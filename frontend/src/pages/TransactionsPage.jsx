import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction, deletePortfolioTransaction, updatePortfolioTransaction } from '../lib/api.js';
import { BROKERS } from '../lib/brokers.js';
import { validateTransactionForm } from '../lib/validation.js';

const TYPE_VALUES = ['POSITION_IMPORT', 'CASH_DEPOSIT', 'BUY', 'SELL', 'CASH_WITHDRAW', 'SPLIT', 'FEE'];
const DIVIDEND_TYPES = new Set(['CASH_DIVIDEND', 'STOCK_DIVIDEND']);
const TYPE_LABELS = {
  POSITION_IMPORT: 'Nhập danh mục ban đầu',
  CASH_DEPOSIT: 'Nạp tiền',
  BUY: 'Mua cổ phiếu',
  SELL: 'Bán cổ phiếu',
  CASH_WITHDRAW: 'Rút tiền',
  SPLIT: 'Tách / gộp cổ phiếu',
  FEE: 'Ghi nhận phí',
  CASH_DIVIDEND: 'Cổ tức tiền mặt',
  STOCK_DIVIDEND: 'Cổ tức cổ phiếu',
};

const EMPTY_FORM = (today = '') => ({
  event_date: today,
  symbol: '',
  quantity: '',
  price: '',
  amount: '',
  ratio: '',
  fee: '',
  tax: '',
  note: '',
  settlement_date: '',
  broker_code: 'UNASSIGNED',
  account_id: 'PRIMARY',
});

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export default function TransactionsPage({ transactions: initialTransactions = [], today, locale = 'vi' }) {
  const money = value => value == null ? '-' : `${formatMoney(value, false, locale)} ₫`;
  const shares = value => formatShares(value, locale);
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
    symbol: ['POSITION_IMPORT', 'BUY', 'SELL', 'SPLIT'].includes(type),
    quantity: ['POSITION_IMPORT', 'BUY', 'SELL'].includes(type),
    price: ['POSITION_IMPORT', 'BUY', 'SELL'].includes(type),
    amount: ['CASH_DEPOSIT', 'CASH_WITHDRAW', 'FEE'].includes(type),
    ratio: type === 'SPLIT',
    trade: ['BUY', 'SELL'].includes(type),
  }), [type]);

  function set(key, value) {
    setForm(current => ({ ...current, [key]: value }));
    setFieldErrors(current => ({ ...current, [key]: undefined }));
  }

  function changeType(value) {
    setType(value);
    setMessage('');
    setFieldErrors({});
    setForm(current => ({ ...current, symbol: '', quantity: '', price: '', amount: '', ratio: '', fee: '', tax: '', settlement_date: '' }));
  }

  function resetForm() {
    setEditingId(null);
    setCorrectionReason('');
    setType('POSITION_IMPORT');
    setForm(EMPTY_FORM(today || ''));
    setFieldErrors({});
  }

  function startEdit(row) {
    if (DIVIDEND_TYPES.has(row.event_type)) return;
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

  async function submit(event) {
    event.preventDefault();
    setMessage('');
    setFieldErrors({});
    let payload;
    try {
      payload = validateTransactionForm(type, form, today, 'vi');
      if (editingId && !correctionReason.trim()) {
        throw Object.assign(new Error('Hãy nhập lý do sửa giao dịch để lịch sử thay đổi có thể được kiểm tra lại sau này.'), { field: 'correction_reason' });
      }
    } catch (error) {
      setFieldErrors(error.field ? { [error.field]: error.message } : {});
      setMessage(error.message);
      return;
    }

    setSaving(true);
    try {
      if (editingId) await updatePortfolioTransaction(editingId, { ...payload, correction_reason: correctionReason.trim() });
      else await createPortfolioTransaction(payload);
      window.location.reload();
    } catch (error) {
      if (error.field) setFieldErrors({ [error.field]: error.message });
      setMessage(error.message);
      setSaving(false);
    }
  }

  async function confirmDelete(row) {
    if (DIVIDEND_TYPES.has(row.event_type)) return;
    if (!deleteReason.trim()) {
      setMessage('Hãy nhập lý do xóa giao dịch.');
      return;
    }
    try {
      await deletePortfolioTransaction(row.id, deleteReason.trim());
      window.location.reload();
    } catch (error) {
      setMessage(error.message);
    }
  }

  function rowActions(row) {
    const deleting = deleteRowId === row.id;
    const dividendEvent = DIVIDEND_TYPES.has(row.event_type);
    if (dividendEvent) return <span className="status-pill">Chỉ đọc</span>;
    if (deleting) return <div className="inline-delete">
      <input value={deleteReason} onChange={event => setDeleteReason(event.target.value)} placeholder="Lý do xóa" />
      <div className="row-actions">
        <button className="btn-danger btn-small" type="button" onClick={() => confirmDelete(row)}>Xác nhận</button>
        <button className="btn-small" type="button" onClick={() => { setDeleteRowId(null); setDeleteReason(''); }}>Hủy</button>
      </div>
    </div>;
    return <div className="row-actions">
      <button className="btn-small" type="button" onClick={() => startEdit(row)}>Sửa</button>
      <button className="btn-danger btn-small" type="button" onClick={() => { setDeleteRowId(row.id); setDeleteReason(''); }}>Xóa</button>
    </div>;
  }

  return <div className="page investor-transactions-page">
    <AppNav active="transactions" locale={locale} />

    <header className="page-head">
      <div>
        <div className="eyebrow">Sổ giao dịch</div>
        <h1>Giao dịch</h1>
        <p className="muted">Ghi đúng những gì đã thực sự xảy ra trong tài khoản chứng khoán. Danh mục, giá vốn và lãi/lỗ sẽ được tính lại từ lịch sử này.</p>
      </div>
    </header>

    <form className={`card ${editingId ? 'correction-form' : ''}`} onSubmit={submit} noValidate>
      <div className="section-head">
        <div>
          <h2>{editingId ? `Sửa giao dịch #${editingId}` : 'Thêm giao dịch'}</h2>
          <p className="muted">Chọn đúng loại giao dịch. Chỉ các trường cần thiết cho loại đó mới được yêu cầu.</p>
        </div>
        {editingId && <button className="btn-variant" type="button" onClick={resetForm}>Hủy sửa</button>}
      </div>

      <label>Loại giao dịch
        <select value={type} onChange={event => changeType(event.target.value)} disabled={saving}>
          {TYPE_VALUES.map(value => <option key={value} value={value}>{TYPE_LABELS[value]}</option>)}
        </select>
      </label>

      {type === 'POSITION_IMPORT' && <div className="info-callout">Dùng mục này khi bạn đã sở hữu cổ phiếu trước khi bắt đầu dùng QPort. Nhập đúng số lượng và giá vốn hiện tại, không cần tạo giao dịch mua giả trong quá khứ.</div>}
      {type === 'BUY' && <div className="info-callout transaction-buy-note">Dùng cho lệnh mua thông thường hoặc mua cổ phiếu phát hành thêm/quyền mua có trả tiền. Nhập số cổ phiếu thực nhận và giá thực trả.</div>}

      <div className="form-grid">
        <label>{requirements.trade ? 'Ngày giao dịch' : 'Ngày'}
          <input type="date" max={today || undefined} value={form.event_date} onChange={event => set('event_date', event.target.value)} aria-invalid={!!fieldErrors.event_date} />
          <FieldError error={fieldErrors.event_date} />
        </label>
        {requirements.symbol && <label>Mã cổ phiếu
          <input value={form.symbol} maxLength={10} onChange={event => set('symbol', event.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase())} placeholder="FPT" aria-invalid={!!fieldErrors.symbol} />
          <FieldError error={fieldErrors.symbol} />
        </label>}
        {requirements.quantity && <label>Số lượng cổ phiếu
          <input type="number" step="0.0001" min="0.0001" value={form.quantity} onChange={event => set('quantity', event.target.value)} aria-invalid={!!fieldErrors.quantity} />
          <FieldError error={fieldErrors.quantity} />
        </label>}
        {requirements.price && <label>{type === 'SELL' ? 'Giá bán (VND/CP)' : 'Giá mua / giá vốn (VND/CP)'}
          <input type="number" step="1" min="1000" value={form.price} onChange={event => set('price', event.target.value)} placeholder="72000" aria-invalid={!!fieldErrors.price} />
          <FieldError error={fieldErrors.price} />
        </label>}
        {requirements.amount && <label>Số tiền (VND)
          <input value={form.amount} onChange={event => set('amount', event.target.value)} aria-invalid={!!fieldErrors.amount} />
          <FieldError error={fieldErrors.amount} />
        </label>}
        {requirements.ratio && <label>Tỷ lệ sau tách/gộp
          <input type="number" step="0.0001" min="0.0001" value={form.ratio} onChange={event => set('ratio', event.target.value)} />
        </label>}
      </div>

      <details className="disclosure-card transaction-advanced">
        <summary><b>Thông tin bổ sung</b><span className="muted">Công ty chứng khoán, tài khoản, phí, thuế và ngày thanh toán</span></summary>
        <div className="form-grid">
          <label>Công ty chứng khoán
            <select value={form.broker_code} onChange={event => set('broker_code', event.target.value)}>
              {BROKERS.map(broker => <option key={broker.code} value={broker.code}>{broker.name}</option>)}
            </select>
            <FieldError error={fieldErrors.broker_code} />
          </label>
          <label>Tài khoản
            <input value={form.account_id} maxLength={32} onChange={event => set('account_id', event.target.value.toUpperCase().replace(/[^A-Z0-9_.-]/g, ''))} placeholder="PRIMARY" aria-invalid={!!fieldErrors.account_id} />
            <FieldError error={fieldErrors.account_id} />
          </label>
          {requirements.trade && <label>Ngày thanh toán
            <input type="date" min={form.event_date || undefined} value={form.settlement_date} onChange={event => set('settlement_date', event.target.value)} aria-invalid={!!fieldErrors.settlement_date} />
            <FieldError error={fieldErrors.settlement_date} />
          </label>}
          {requirements.trade && <label>Phí giao dịch (VND)<input type="number" min="0" step="1" value={form.fee} onChange={event => set('fee', event.target.value)} /></label>}
          {requirements.trade && <label>Thuế (VND)<input type="number" min="0" step="1" value={form.tax} onChange={event => set('tax', event.target.value)} /></label>}
        </div>
      </details>

      <label>Ghi chú<textarea maxLength={500} value={form.note} onChange={event => set('note', event.target.value)} placeholder="Thông tin cần nhớ về giao dịch này" /></label>

      {editingId && <label>Lý do sửa dữ liệu
        <textarea maxLength={500} value={correctionReason} onChange={event => setCorrectionReason(event.target.value)} aria-invalid={!!fieldErrors.correction_reason} />
        <FieldError error={fieldErrors.correction_reason} />
      </label>}

      <div className="button-row">
        <button className="btn-primary" type="submit" disabled={saving}>{saving ? 'Đang lưu…' : editingId ? 'Lưu thay đổi' : 'Lưu giao dịch'}</button>
        {editingId && <button className="btn-variant" type="button" onClick={resetForm}>Hủy</button>}
      </div>
      {message && <div className="run-message">{message}</div>}
    </form>

    <section className="card investor-transaction-history">
      <div className="section-head"><div><h2>Lịch sử giao dịch</h2><div className="muted">{transactions.length} giao dịch / sự kiện đã ghi nhận</div></div></div>
      {transactions.length === 0 ? <div className="empty-state">Chưa có giao dịch nào.</div> : <>
        <div className="holding-mobile-list transaction-mobile-list">
          {transactions.map(row => {
            const hasSymbol = Boolean(row.symbol);
            const symbol = row.symbol ? String(row.symbol).toUpperCase() : '';
            const mainValue = row.amount ? money(row.amount) : row.price ? `${money(row.price)}/CP` : row.quantity ? `${shares(row.quantity)} CP` : '-';
            return <article className="holding-mobile-card transaction-mobile-card" key={`mobile-${row.id}`}>
              <div className="holding-mobile-head">
                <div className="holding-mobile-symbol">
                  <strong>{symbol || TYPE_LABELS[row.event_type] || row.event_type}</strong>
                  <span>{row.event_date} · {TYPE_LABELS[row.event_type] || row.event_type}</span>
                </div>
                <div className="holding-mobile-value">
                  <strong>{mainValue}</strong>
                  {row.correction && <span>Đã chỉnh sửa</span>}
                  {row.metadata?.auto_generated && <span>Tự động ghi nhận</span>}
                </div>
              </div>
              <div className="holding-mobile-facts">
                <div><span>Số lượng</span><b>{row.quantity ? `${shares(row.quantity)} CP` : '-'}</b></div>
                <div><span>CTCK / Tài khoản</span><b>{hasSymbol ? `${row.metadata?.broker_code || '-'} · ${row.metadata?.account_id || '-'}` : '-'}</b></div>
                <div><span>Phí</span><b>{Number(row.fee || 0) ? money(Number(row.fee || 0)) : '-'}</b></div>
                <div><span>Thuế</span><b>{Number(row.tax || 0) ? money(Number(row.tax || 0)) : '-'}</b></div>
              </div>
              {row.note && <p className="transaction-mobile-note">{row.note}</p>}
              <div className="transaction-mobile-actions">{rowActions(row)}</div>
            </article>;
          })}
        </div>

        <div className="table-scroll portfolio-table-desktop">
          <table className="ranking transaction-table">
            <thead><tr>
              <th>Ngày</th><th>Loại</th><th>Mã</th><th>CTCK</th><th>Tài khoản</th><th>SL</th><th>Giá / Số tiền</th><th>Phí / Thuế</th><th>Ghi chú</th><th>Thao tác</th>
            </tr></thead>
            <tbody>{transactions.map(row => {
              const hasSymbol = Boolean(row.symbol);
              return <tr key={row.id}>
                <td>{row.event_date}</td>
                <td><b>{TYPE_LABELS[row.event_type] || row.event_type}</b>{row.correction && <div className="muted">Đã chỉnh sửa</div>}{row.metadata?.auto_generated && <div className="muted">Tự động</div>}</td>
                <td>{row.symbol ? String(row.symbol).toUpperCase() : '-'}</td>
                <td>{hasSymbol ? (row.metadata?.broker_code || '-') : '-'}</td>
                <td>{hasSymbol ? (row.metadata?.account_id || '-') : '-'}</td>
                <td>{row.quantity ? shares(row.quantity) : '-'}</td>
                <td>{row.price ? money(row.price) : row.amount ? money(row.amount) : '-'}</td>
                <td>{Number(row.fee || 0) || Number(row.tax || 0) ? `${money(Number(row.fee || 0))} / ${money(Number(row.tax || 0))}` : '-'}</td>
                <td>{row.note || '-'}</td>
                <td>{rowActions(row)}</td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      </>}
    </section>
  </div>;
}
