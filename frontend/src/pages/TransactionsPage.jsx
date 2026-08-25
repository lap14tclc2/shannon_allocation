import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares } from '../lib/format.js';
import { createPortfolioTransaction, discardPortfolioTransaction, updatePortfolioTransaction } from '../lib/api.js';
import { BROKERS } from '../lib/brokers.js';
import { deriveHoldingBooks, findHoldingBook, holdingBookKey } from '../lib/holdingBooks.js';
import { parseVndMoneyInput, validateTransactionForm } from '../lib/validation.js';

const TYPE_VALUES = ['POSITION_IMPORT', 'CASH_DEPOSIT', 'BUY', 'SELL', 'CASH_WITHDRAW', 'SPLIT', 'FEE'];
const DIVIDEND_TYPES = new Set(['CASH_DIVIDEND', 'STOCK_DIVIDEND']);
const EDITABLE_TYPES = new Set(['POSITION_IMPORT', 'BUY', 'SELL']);
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

function brokerName(code) {
  return BROKERS.find(item => item.code === code)?.name || code || 'Chưa gán';
}

function sellIntentFromLocation() {
  if (typeof window === 'undefined') return { active: false, locked: false };
  const params = new URLSearchParams(window.location.search || '');
  const active = params.get('action') === 'sell';
  const symbol = String(params.get('symbol') || '').toUpperCase();
  const broker_code = String(params.get('broker') || '').toUpperCase();
  const account_id = String(params.get('account') || '').toUpperCase();
  return {
    active,
    symbol,
    broker_code,
    account_id,
    locked: active && Boolean(symbol && broker_code && account_id),
  };
}

export default function TransactionsPage({ transactions: initialTransactions = [], today, locale = 'vi' }) {
  const money = value => value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
  const shares = value => formatShares(value, locale);
  const [transactions] = useState(initialTransactions);
  const holdingBooks = useMemo(() => deriveHoldingBooks(transactions), [transactions]);
  const intent = useMemo(() => sellIntentFromLocation(), []);
  const intentBook = useMemo(() => intent.locked
    ? findHoldingBook(holdingBooks, intent.symbol, intent.broker_code, intent.account_id)
    : null, [holdingBooks, intent]);

  const [type, setType] = useState(intent.active ? 'SELL' : 'POSITION_IMPORT');
  const [form, setForm] = useState(() => {
    const initial = EMPTY_FORM(today || '');
    if (!intent.locked) return initial;
    return {
      ...initial,
      symbol: intent.symbol,
      broker_code: intent.broker_code,
      account_id: intent.account_id,
    };
  });
  const [selectedSellKey, setSelectedSellKey] = useState(() => intent.locked
    ? `${intent.symbol}|${intent.broker_code}|${intent.account_id}`
    : '');
  const [editingId, setEditingId] = useState(null);
  const [correctionReason, setCorrectionReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [discardTarget, setDiscardTarget] = useState(null);
  const [discardReason, setDiscardReason] = useState('');
  const [discardError, setDiscardError] = useState('');
  const [discarding, setDiscarding] = useState(false);

  const activeTransactionCount = useMemo(
    () => transactions.filter(row => String(row?.status || 'ACTIVE').toUpperCase() !== 'SOFT_DELETED').length,
    [transactions],
  );

  const selectedSellBook = useMemo(() => {
    if (!selectedSellKey) return null;
    return holdingBooks.find(row => holdingBookKey(row) === selectedSellKey) || null;
  }, [holdingBooks, selectedSellKey]);

  const lockedSell = !editingId && type === 'SELL' && intent.locked;
  const sellBook = lockedSell ? intentBook : selectedSellBook;
  const isSellCreate = !editingId && type === 'SELL';
  const estimatedSellPrice = isSellCreate && Number(form.quantity) > 0 && String(form.amount || '').trim()
    ? (() => {
        try {
          return parseVndMoneyInput(form.amount, 'amount', 'vi') / Number(form.quantity);
        } catch {
          return null;
        }
      })()
    : null;

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

  function applySellBook(key) {
    setSelectedSellKey(key);
    const book = holdingBooks.find(row => holdingBookKey(row) === key);
    setForm(current => ({
      ...current,
      event_date: today || current.event_date,
      symbol: book?.symbol || '',
      broker_code: book?.broker_code || 'UNASSIGNED',
      account_id: book?.account_id || 'PRIMARY',
      quantity: '',
      amount: '',
      price: '',
      fee: '',
      tax: '',
      note: '',
      settlement_date: '',
    }));
    setFieldErrors({});
    setMessage('');
  }

  function changeType(value) {
    if (intent.locked && value !== 'SELL') return;
    setType(value);
    setEditingId(null);
    setCorrectionReason('');
    setMessage('');
    setFieldErrors({});
    setSelectedSellKey('');
    setForm(EMPTY_FORM(today || ''));
  }

  function resetForm() {
    setEditingId(null);
    setCorrectionReason('');
    setMessage('');
    setFieldErrors({});
    if (intent.active) {
      setType('SELL');
      setSelectedSellKey(intent.locked ? `${intent.symbol}|${intent.broker_code}|${intent.account_id}` : '');
      setForm({
        ...EMPTY_FORM(today || ''),
        symbol: intent.locked ? intent.symbol : '',
        broker_code: intent.locked ? intent.broker_code : 'UNASSIGNED',
        account_id: intent.locked ? intent.account_id : 'PRIMARY',
      });
    } else {
      setType('POSITION_IMPORT');
      setSelectedSellKey('');
      setForm(EMPTY_FORM(today || ''));
    }
  }

  function startEdit(row) {
    if (
      String(row?.status || 'ACTIVE').toUpperCase() === 'SOFT_DELETED'
      || DIVIDEND_TYPES.has(row.event_type)
      || !EDITABLE_TYPES.has(row.event_type)
    ) return;
    setEditingId(row.id);
    setType(row.event_type);
    setCorrectionReason('');
    setMessage('');
    setFieldErrors({});
    setSelectedSellKey('');
    setForm({
      event_date: row.event_date || today || '',
      symbol: row.symbol || '',
      quantity: row.quantity ? String(row.quantity) : '',
      price: row.price ? String(row.price) : '',
      amount: '',
      ratio: '',
      fee: row.fee ? String(row.fee) : '',
      tax: row.tax ? String(row.tax) : '',
      note: row.note || '',
      settlement_date: row.metadata?.settlement_date || '',
      broker_code: row.metadata?.broker_code || 'UNASSIGNED',
      account_id: row.metadata?.account_id || 'PRIMARY',
    });
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function validateSellSelection() {
    if (!sellBook) {
      const error = new Error(lockedSell
        ? 'Nguồn cổ phiếu đã chọn không còn tồn tại trong danh mục. Hãy quay lại Danh mục và chọn lại nơi bán.'
        : 'Hãy chọn mã cổ phiếu và CTCK bạn muốn bán.');
      error.field = 'sell_source';
      throw error;
    }
    const quantity = Number(form.quantity);
    if (Number.isFinite(quantity) && quantity > Number(sellBook.shares) + 1e-8) {
      const error = new Error(`Bạn chỉ có ${shares(sellBook.shares)} CP ${sellBook.symbol} tại ${brokerName(sellBook.broker_code)} · ${sellBook.account_id}.`);
      error.field = 'quantity';
      throw error;
    }
  }

  async function submit(event) {
    event.preventDefault();
    setMessage('');
    setFieldErrors({});
    let payload;
    try {
      let validationForm = form;
      if (isSellCreate) {
        validateSellSelection();
        const grossAmount = parseVndMoneyInput(form.amount, 'amount', 'vi');
        const quantity = Number(form.quantity);
        if (!Number.isFinite(quantity) || quantity <= 0) {
          const error = new Error('Số lượng bán phải lớn hơn 0.');
          error.field = 'quantity';
          throw error;
        }
        validationForm = {
          ...form,
          event_date: today || form.event_date,
          symbol: sellBook.symbol,
          broker_code: sellBook.broker_code,
          account_id: sellBook.account_id,
          price: String(grossAmount / quantity),
          fee: '',
          tax: '',
          note: '',
          settlement_date: '',
        };
      }

      payload = validateTransactionForm(type, validationForm, today, 'vi');
      if (editingId && !correctionReason.trim()) {
        const error = new Error('Hãy nhập lý do sửa giao dịch để lịch sử thay đổi có thể được kiểm tra lại sau này.');
        error.field = 'correction_reason';
        throw error;
      }
    } catch (error) {
      setFieldErrors(error.field ? { [error.field]: error.message } : {});
      setMessage(error.message);
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await updatePortfolioTransaction(editingId, {
          quantity: payload.quantity,
          price: payload.price,
          broker_code: payload.broker_code,
          correction_reason: correctionReason.trim(),
        });
      } else {
        await createPortfolioTransaction(payload);
      }
      window.location.replace('/transactions');
    } catch (error) {
      if (error.field) setFieldErrors({ [error.field]: error.message });
      setMessage(error.message);
      setSaving(false);
    }
  }

  function startDiscard(row) {
    if (
      String(row?.status || 'ACTIVE').toUpperCase() === 'SOFT_DELETED'
      || row?.metadata?.auto_generated
    ) return;
    setDiscardTarget(row);
    setDiscardReason('');
    setDiscardError('');
  }

  function cancelDiscard() {
    if (discarding) return;
    setDiscardTarget(null);
    setDiscardReason('');
    setDiscardError('');
  }

  async function confirmDiscard() {
    const reason = discardReason.trim();
    if (!reason) {
      setDiscardError('Hãy nhập lý do loại bỏ giao dịch.');
      return;
    }
    setDiscarding(true);
    setDiscardError('');
    try {
      await discardPortfolioTransaction(discardTarget.id, reason);
      window.location.replace('/transactions');
    } catch (error) {
      setDiscardError(error.message);
      setDiscarding(false);
    }
  }

  function rowActions(row) {
    const softDeleted = String(row?.status || 'ACTIVE').toUpperCase() === 'SOFT_DELETED';
    if (softDeleted) return <span className="status-pill status-soft-deleted">Đã loại bỏ</span>;

    const automatic = Boolean(row?.metadata?.auto_generated);
    const dividendEvent = DIVIDEND_TYPES.has(row.event_type);
    const editable = !automatic && !dividendEvent && EDITABLE_TYPES.has(row.event_type);
    const discardable = !automatic;

    if (!editable && !discardable) return <span className="status-pill">Chỉ đọc</span>;
    return <div className="transaction-row-actions">
      {editable && <button className="btn-small" type="button" onClick={() => startEdit(row)}>Sửa</button>}
      {discardable && <button className="btn-small btn-discard" type="button" onClick={() => startDiscard(row)}>Loại bỏ</button>}
    </div>;
  }

  return <div className="page investor-transactions-page">
    <AppNav active="transactions" locale={locale} />

    <header className="page-head">
      <div>
        <div className="eyebrow">Sổ giao dịch</div>
        <h1>Giao dịch</h1>
        <p className="muted">Giao dịch đã ghi không bị xóa vật lý. Bạn có thể sửa dữ liệu hoặc loại bỏ một giao dịch khỏi sổ hiệu lực; QPort luôn giữ bản ghi gốc để kiểm tra sau này.</p>
      </div>
    </header>

    <form className={`card ${editingId ? 'correction-form' : ''} ${isSellCreate ? 'transaction-sell-form' : ''}`} onSubmit={submit} noValidate>
      <div className="section-head">
        <div>
          <h2>{editingId ? `Sửa giao dịch #${editingId}` : isSellCreate ? 'Bán cổ phiếu' : 'Thêm giao dịch'}</h2>
          <p className="muted">{editingId
            ? 'Ngày, mã cổ phiếu, loại giao dịch và tài khoản được khóa. Chỉ số lượng, giá và CTCK có thể sửa.'
            : isSellCreate
              ? 'Chọn đúng nơi đang giữ cổ phiếu. Sau khi chọn, mã, CTCK, tài khoản và ngày giao dịch sẽ được khóa.'
              : 'Chọn đúng loại giao dịch. Chỉ các trường cần thiết cho loại đó mới được yêu cầu.'}</p>
        </div>
        {editingId && <button className="btn-variant" type="button" onClick={resetForm}>Hủy sửa</button>}
      </div>

      <label>Loại giao dịch
        <select value={type} onChange={event => changeType(event.target.value)} disabled={saving || editingId != null || intent.locked}>
          {TYPE_VALUES.map(value => <option key={value} value={value}>{TYPE_LABELS[value]}</option>)}
        </select>
      </label>

      {type === 'POSITION_IMPORT' && !editingId && <div className="info-callout">Dùng mục này khi bạn đã sở hữu cổ phiếu trước khi bắt đầu dùng QPort. Nhập đúng số lượng và giá vốn hiện tại.</div>}
      {type === 'BUY' && !editingId && <div className="info-callout transaction-buy-note">Ghi đúng CTCK và tài khoản nhận cổ phiếu. Thông tin này sẽ quyết định nguồn cổ phiếu có thể bán về sau.</div>}

      {isSellCreate ? <>
        <div className="sell-source-panel">
          <div className="sell-source-title"><b>Nguồn cổ phiếu cần bán</b><span>CTCK đang lưu ký</span></div>
          {lockedSell ? <div className="sell-source-locked">
            <strong>{intent.symbol}</strong>
            <span>{brokerName(intent.broker_code)} · {intent.account_id}</span>
            <span>{intentBook ? `${shares(intentBook.shares)} CP khả dụng` : 'Nguồn này hiện không còn cổ phiếu khả dụng'}</span>
          </div> : <label>Chọn mã / CTCK / tài khoản
            <select value={selectedSellKey} onChange={event => applySellBook(event.target.value)} aria-invalid={!!fieldErrors.sell_source}>
              <option value="">-- Chọn cổ phiếu cần bán --</option>
              {holdingBooks.map(book => <option key={holdingBookKey(book)} value={holdingBookKey(book)}>
                {book.symbol} · {brokerName(book.broker_code)} · {book.account_id} · {shares(book.shares)} CP
              </option>)}
            </select>
            <FieldError error={fieldErrors.sell_source} />
          </label>}
        </div>

        <div className="form-grid sell-readonly-grid">
          <label>Ngày giao dịch<input type="date" value={today || form.event_date} readOnly /></label>
          <label>Mã cổ phiếu<input value={sellBook?.symbol || intent.symbol || ''} readOnly /></label>
          <label>CTCK<input value={brokerName(sellBook?.broker_code || intent.broker_code)} readOnly /></label>
          <label>Tài khoản<input value={sellBook?.account_id || intent.account_id || ''} readOnly /></label>
        </div>

        <div className="form-grid sell-input-grid">
          <label>Số lượng bán
            <input type="number" step="0.0001" min="0.0001" max={sellBook?.shares || undefined} value={form.quantity} onChange={event => set('quantity', event.target.value)} aria-invalid={!!fieldErrors.quantity} />
            <FieldError error={fieldErrors.quantity} />
            {sellBook && <span className="field-hint">Tối đa {shares(sellBook.shares)} CP tại {brokerName(sellBook.broker_code)}</span>}
          </label>
          <label>Tổng tiền bán trước phí/thuế (VND)
            <input inputMode="numeric" value={form.amount} onChange={event => set('amount', event.target.value)} placeholder="Ví dụ 72.000.000" aria-invalid={!!fieldErrors.amount} />
            <FieldError error={fieldErrors.amount} />
            <span className="field-hint">Giá bán bình quân: {estimatedSellPrice == null ? '-' : `${money(estimatedSellPrice)}/CP`}</span>
          </label>
        </div>
        <div className="info-callout">QPort sẽ ghi SELL đúng tại <b>{sellBook ? `${brokerName(sellBook.broker_code)} · ${sellBook.account_id}` : 'CTCK/tài khoản đã chọn'}</b>. Cổ phiếu ở CTCK khác không được dùng để bù cho lệnh bán này.</div>
      </> : editingId ? <>
        <div className="form-grid">
          <label>Ngày giao dịch<input type="date" value={form.event_date} readOnly /></label>
          <label>Mã cổ phiếu<input value={form.symbol || '-'} readOnly /></label>
          <label>Tài khoản<input value={form.account_id || 'PRIMARY'} readOnly /></label>
          <label>Số lượng
            <input type="number" step="0.0001" min="0.0001" value={form.quantity} onChange={event => set('quantity', event.target.value)} aria-invalid={!!fieldErrors.quantity} />
            <FieldError error={fieldErrors.quantity} />
          </label>
          <label>Giá (VND/CP)
            <input type="number" step="1" min="1000" value={form.price} onChange={event => set('price', event.target.value)} aria-invalid={!!fieldErrors.price} />
            <FieldError error={fieldErrors.price} />
          </label>
          <label>CTCK
            <select value={form.broker_code} onChange={event => set('broker_code', event.target.value)} aria-invalid={!!fieldErrors.broker_code}>
              {BROKERS.map(broker => <option key={broker.code} value={broker.code}>{broker.name}</option>)}
            </select>
            <FieldError error={fieldErrors.broker_code} />
          </label>
        </div>
        <label>Lý do sửa dữ liệu
          <textarea maxLength={500} value={correctionReason} onChange={event => setCorrectionReason(event.target.value)} aria-invalid={!!fieldErrors.correction_reason} placeholder="Ví dụ: nhập nhầm giá khớp lệnh" />
          <FieldError error={fieldErrors.correction_reason} />
        </label>
      </> : <>
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
          {requirements.price && <label>Giá mua / giá vốn (VND/CP)
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
          <summary><b>Thông tin CTCK & chi phí</b><span className="muted">Nơi lưu ký cổ phiếu, tài khoản, phí và thuế</span></summary>
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
      </>}

      <div className="button-row">
        <button className="btn-primary" type="submit" disabled={saving || (lockedSell && !intentBook)}>{saving ? 'Đang lưu…' : editingId ? 'Lưu thay đổi' : isSellCreate ? 'Ghi nhận bán cổ phiếu' : 'Lưu giao dịch'}</button>
        {editingId && <button className="btn-variant" type="button" onClick={resetForm}>Hủy</button>}
      </div>
      {message && <div className="run-message">{message}</div>}
    </form>

    {discardTarget && <section className="card transaction-discard-confirmation" role="dialog" aria-labelledby="discard-transaction-title">
      <div className="section-head">
        <div>
          <div className="eyebrow">Loại khỏi sổ hiệu lực</div>
          <h2 id="discard-transaction-title">Loại bỏ giao dịch #{discardTarget.id}?</h2>
          <p className="muted">Bản ghi gốc vẫn được giữ với trạng thái Đã loại bỏ. QPort sẽ tính lại số cổ phiếu, tiền, giá vốn, lãi/lỗ và snapshot từ các giao dịch còn hiệu lực.</p>
        </div>
      </div>
      <div className="discard-transaction-summary">
        <b>{TYPE_LABELS[discardTarget.event_type] || discardTarget.event_type}</b>
        <span>{discardTarget.event_date}</span>
        <span>{discardTarget.symbol || 'Không có mã cổ phiếu'}</span>
      </div>
      <label>Lý do loại bỏ
        <textarea
          maxLength={500}
          value={discardReason}
          onChange={event => {
            setDiscardReason(event.target.value);
            setDiscardError('');
          }}
          aria-invalid={!!discardError}
          placeholder="Ví dụ: giao dịch bị nhập trùng"
          autoFocus
        />
        <FieldError error={discardError} />
      </label>
      <div className="button-row">
        <button className="btn-danger" type="button" onClick={confirmDiscard} disabled={discarding}>
          {discarding ? 'Đang tính lại danh mục…' : 'Xác nhận loại bỏ'}
        </button>
        <button className="btn-variant" type="button" onClick={cancelDiscard} disabled={discarding}>Hủy</button>
      </div>
    </section>}

    <section className="card investor-transaction-history">
      <div className="section-head"><div><h2>Lịch sử giao dịch</h2><div className="muted">{activeTransactionCount} đang hiệu lực · {transactions.length - activeTransactionCount} đã loại bỏ · Bản ghi gốc luôn được giữ</div></div></div>
      {transactions.length === 0 ? <div className="empty-state">Chưa có giao dịch nào.</div> : <>
        <div className="holding-mobile-list transaction-mobile-list">
          {transactions.map(row => {
            const hasSymbol = Boolean(row.symbol);
            const symbol = row.symbol ? String(row.symbol).toUpperCase() : '';
            const mainValue = row.amount ? money(row.amount) : row.price ? `${money(row.price)}/CP` : row.quantity ? `${shares(row.quantity)} CP` : '-';
            const softDeleted = String(row?.status || 'ACTIVE').toUpperCase() === 'SOFT_DELETED';
            return <article className={`holding-mobile-card transaction-mobile-card ${softDeleted ? 'transaction-soft-deleted' : ''}`} key={`mobile-${row.id}`}>
              <div className="holding-mobile-head">
                <div className="holding-mobile-symbol">
                  <strong>{symbol || TYPE_LABELS[row.event_type] || row.event_type}</strong>
                  <span>{row.event_date} · {TYPE_LABELS[row.event_type] || row.event_type}</span>
                </div>
                <div className="holding-mobile-value">
                  <strong>{mainValue}</strong>
                  {softDeleted
                    ? <span className="status-soft-deleted">Đã loại bỏ</span>
                    : row.correction && <span>Đã chỉnh sửa</span>}
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
              const softDeleted = String(row?.status || 'ACTIVE').toUpperCase() === 'SOFT_DELETED';
              return <tr className={softDeleted ? 'transaction-soft-deleted' : ''} key={row.id}>
                <td>{row.event_date}</td>
                <td><b>{TYPE_LABELS[row.event_type] || row.event_type}</b>{softDeleted
                  ? <div className="status-pill status-soft-deleted">Đã loại bỏ</div>
                  : row.correction && <div className="muted">Đã chỉnh sửa</div>}{row.metadata?.auto_generated && <div className="muted">Tự động</div>}</td>
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
