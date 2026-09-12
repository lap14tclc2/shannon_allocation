import React, { useEffect, useMemo, useState } from 'react';
import { useDispatch } from 'react-redux';
import SymbolSuggestInput from './SymbolSuggestInput.jsx';
import { createPortfolioTransaction, updatePortfolioTransaction } from '../lib/api.js';
import { BROKERS } from '../lib/brokers.js';
import { formatShares, money as moneyFn } from '../lib/format.js';
import { refreshDashboard } from '../lib/store.js';
import { parseVndMoneyInput, vndToVietnameseWords } from '../lib/validation.js';

function todayVn() {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date());
}

export default function PortfolioEditModal({
  isOpen = false,
  onClose,
  initialMode = 'ADD_POSITION',
  initialData = {},
  holdingSymbols = [],
  transactions = [],
  onSuccess,
  locale = 'vi',
}) {
  const dispatch = useDispatch();
  const [mode, setMode] = useState(initialMode);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Form Fields
  const [symbol, setSymbol] = useState(initialData.symbol || '');
  const [eventType, setEventType] = useState(initialData.event_type || 'POSITION_IMPORT');
  const [eventDate, setEventDate] = useState(initialData.event_date || todayVn());
  const [quantity, setQuantity] = useState(initialData.quantity ? String(initialData.quantity) : '');
  const [price, setPrice] = useState(initialData.price ? String(initialData.price) : '');
  const [fee, setFee] = useState(initialData.fee ? String(initialData.fee) : '0');
  const [brokerCode, setBrokerCode] = useState(initialData.broker_code || 'UNASSIGNED');
  const [accountId, setAccountId] = useState(initialData.account_id || 'PRIMARY');
  const [amount, setAmount] = useState(initialData.amount ? String(initialData.amount) : '');
  const [note, setNote] = useState(initialData.note || '');
  const [correctionReason, setCorrectionReason] = useState('');
  const [selectedEventId, setSelectedEventId] = useState(initialData.event_id || null);

  // Sync mode and initial data when modal opens or initialMode changes
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode);
      setError('');
      setCorrectionReason('');
      setSymbol(initialData.symbol || '');
      setEventType(initialData.event_type || 'POSITION_IMPORT');
      setEventDate(initialData.event_date || todayVn());
      setQuantity(initialData.quantity ? String(initialData.quantity) : '');
      setPrice(initialData.price ? String(initialData.price) : '');
      setFee(initialData.fee != null ? String(initialData.fee) : '0');
      setBrokerCode(initialData.broker_code || 'UNASSIGNED');
      setAccountId(initialData.account_id || 'PRIMARY');
      setAmount(initialData.amount ? String(initialData.amount) : '');
      setNote(initialData.note || '');
      setSelectedEventId(initialData.event_id || null);
    }
  }, [isOpen, initialMode, initialData]);

  // Available transactions for the selected symbol if in EDIT_POSITION mode
  const symbolTransactions = useMemo(() => {
    if (!symbol) return [];
    const sym = symbol.trim().toUpperCase();
    return (transactions || []).filter(tx => String(tx.symbol || '').toUpperCase() === sym && ['POSITION_IMPORT', 'BUY', 'SELL'].includes(tx.event_type));
  }, [symbol, transactions]);

  // When selected event changes in EDIT mode, load its fields
  useEffect(() => {
    if (mode === 'EDIT_POSITION' && selectedEventId) {
      const found = transactions.find(tx => Number(tx.id) === Number(selectedEventId));
      if (found) {
        setSymbol(found.symbol || '');
        setEventType(found.event_type || 'POSITION_IMPORT');
        setEventDate(found.event_date || todayVn());
        setQuantity(found.quantity ? String(found.quantity) : '');
        setPrice(found.price ? String(found.price) : '');
        setFee(found.fee != null ? String(found.fee) : '0');
        setBrokerCode(found.broker_code || 'UNASSIGNED');
        setAccountId(found.account_id || 'PRIMARY');
        setNote(found.note || '');
      }
    }
  }, [selectedEventId, mode, transactions]);

  if (!isOpen) return null;

  // Real-time formatting helpers
  const parsedShares = Number(quantity.replace(/[^0-9.]/g, ''));
  const sharesFormatted = Number.isFinite(parsedShares) && parsedShares > 0 ? formatShares(parsedShares, locale) : '';

  const parsedPriceNumber = Number(price.replace(/[^0-9.]/g, ''));
  const priceFormatted = Number.isFinite(parsedPriceNumber) && parsedPriceNumber > 0 ? moneyFn(parsedPriceNumber, locale) : '';

  let parsedAmountVnd = null;
  let amountWords = '';
  if (['ADD_CASH', 'WITHDRAW_CASH', 'ADJUST_CASH'].includes(mode) && amount.trim()) {
    try {
      parsedAmountVnd = parseVndMoneyInput(amount, 'amount', locale);
      amountWords = vndToVietnameseWords(parsedAmountVnd);
    } catch (e) {
      parsedAmountVnd = null;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      if (mode === 'ADD_POSITION') {
        const cleanSymbol = symbol.trim().toUpperCase();
        if (!cleanSymbol) throw new Error('Vui lòng chọn hoặc nhập mã cổ phiếu.');
        const qtyNum = Number(quantity.replace(/[^0-9.]/g, ''));
        if (!Number.isFinite(qtyNum) || qtyNum <= 0) throw new Error('Số lượng cổ phiếu phải lớn hơn 0.');
        const priceNum = Number(price.replace(/[^0-9.]/g, ''));
        if (!Number.isFinite(priceNum) || priceNum < 1000) throw new Error('Giá giao dịch phải là số tiền VND đầy đủ (tối thiểu 1.000đ/cp).');
        const feeNum = Number(fee.replace(/[^0-9.]/g, '')) || 0;

        const payload = {
          event_type: eventType === 'BUY' ? 'BUY' : 'POSITION_IMPORT',
          event_date: eventDate,
          symbol: cleanSymbol,
          quantity: qtyNum,
          price: priceNum,
          fee: feeNum,
          broker_code: brokerCode,
          account_id: accountId,
          note: note.trim(),
        };

        const res = await createPortfolioTransaction(payload);
        if (!res?.ok && res?.error) throw new Error(res.error);
      } else if (mode === 'EDIT_POSITION') {
        if (!selectedEventId) throw new Error('Vui lòng chọn giao dịch cần chỉnh sửa.');
        if (!correctionReason.trim()) throw new Error('Vui lòng nhập lý do chỉnh sửa vị thế.');

        const qtyNum = Number(quantity.replace(/[^0-9.]/g, ''));
        if (!Number.isFinite(qtyNum) || qtyNum <= 0) throw new Error('Số lượng cổ phiếu phải lớn hơn 0.');
        const priceNum = Number(price.replace(/[^0-9.]/g, ''));
        if (!Number.isFinite(priceNum) || priceNum < 1000) throw new Error('Giá giao dịch phải từ 1.000đ/cp trở lên.');
        const feeNum = Number(fee.replace(/[^0-9.]/g, '')) || 0;

        const payload = {
          quantity: qtyNum,
          price: priceNum,
          fee: feeNum,
          broker_code: brokerCode,
          account_id: accountId,
          note: note.trim(),
          correction_reason: correctionReason.trim(),
        };

        const res = await updatePortfolioTransaction(selectedEventId, payload);
        if (!res?.ok && res?.error) throw new Error(res.error);
      } else if (['ADD_CASH', 'WITHDRAW_CASH', 'ADJUST_CASH'].includes(mode)) {
        if (parsedAmountVnd == null || parsedAmountVnd <= 0) {
          throw new Error('Vui lòng nhập số tiền hợp lệ (ví dụ: 50.000.000đ hoặc 50tr).');
        }

        const cashEventType = mode === 'WITHDRAW_CASH' ? 'CASH_WITHDRAW' : 'CASH_DEPOSIT';
        const defaultNote = mode === 'WITHDRAW_CASH' ? 'Rút tiền mặt' : mode === 'ADJUST_CASH' ? 'Điều chỉnh số dư tiền mặt' : 'Nạp tiền mặt';

        const payload = {
          event_type: cashEventType,
          event_date: eventDate,
          amount: parsedAmountVnd,
          note: note.trim() || defaultNote,
        };

        const res = await createPortfolioTransaction(payload);
        if (!res?.ok && res?.error) throw new Error(res.error);
      }

      // Immediately refresh Redux dashboard store to reflect updated holdings & cash
      await dispatch(refreshDashboard()).unwrap();
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Giao dịch không thành công. Vui lòng kiểm tra lại.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="appearance-overlay" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div
        className="appearance-backdrop"
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.65)', backdropFilter: 'blur(4px)' }}
      />
      <div
        className="card portfolio-edit-modal-card"
        style={{
          position: 'relative',
          zIndex: 1001,
          maxWidth: '560px',
          width: '90%',
          maxHeight: '90vh',
          overflowY: 'auto',
          background: 'var(--card-bg, #161b22)',
          border: '1px solid var(--border-color, #30363d)',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <div className="eyebrow" style={{ textTransform: 'uppercase', fontSize: '11px', letterSpacing: '1px', color: '#8b949e' }}>
              Sổ Cái Giao Dịch Bất Biến
            </div>
            <h2 style={{ margin: '4px 0 0 0', fontSize: '20px', fontWeight: 600 }}>
              {mode === 'ADD_POSITION' && '+ Thêm vị thế cổ phiếu'}
              {mode === 'EDIT_POSITION' && `Chỉnh sửa vị thế ${symbol ? `(${symbol})` : ''}`}
              {mode === 'ADD_CASH' && '+ Nạp tiền vào danh mục'}
              {mode === 'WITHDRAW_CASH' && 'Rút tiền từ danh mục'}
              {mode === 'ADJUST_CASH' && 'Điều chỉnh số dư tiền mặt'}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#8b949e', fontSize: '24px', cursor: 'pointer', padding: '4px' }}
          >
            ✕
          </button>
        </div>

        {/* Mode Selector Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border-color, #30363d)', pb: '12px' }}>
          <button
            type="button"
            className={`btn-small ${mode === 'ADD_POSITION' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setMode('ADD_POSITION'); setError(''); }}
          >
            + Vị thế mới
          </button>
          <button
            type="button"
            className={`btn-small ${mode === 'EDIT_POSITION' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setMode('EDIT_POSITION'); setError(''); }}
          >
            Chỉnh sửa vị thế
          </button>
          <button
            type="button"
            className={`btn-small ${mode === 'ADD_CASH' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setMode('ADD_CASH'); setError(''); }}
          >
            + Nạp tiền
          </button>
          <button
            type="button"
            className={`btn-small ${mode === 'WITHDRAW_CASH' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => { setMode('WITHDRAW_CASH'); setError(''); }}
          >
            Rút tiền
          </button>
        </div>

        {error && (
          <div className="data-error-message" style={{ marginBottom: '16px', padding: '12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', borderRadius: '6px', color: '#f87171' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Stock Position Form */}
          {['ADD_POSITION', 'EDIT_POSITION'].includes(mode) && (
            <>
              {mode === 'ADD_POSITION' ? (
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Mã cổ phiếu / Công ty *</label>
                  <SymbolSuggestInput
                    value={symbol}
                    onChange={setSymbol}
                    onSelectSecurity={(sec) => setSymbol(sec.symbol)}
                    holdingSymbols={holdingSymbols}
                    placeholder="Nhập mã CP (ví dụ: FPT, DGC, ACB...)"
                  />
                </div>
              ) : (
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Mã cổ phiếu</label>
                  <input
                    className="input-text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    placeholder="Mã cổ phiếu (VD: FPT)"
                    style={{ width: '100%' }}
                  />
                  {symbolTransactions.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '12px', color: '#8b949e' }}>Chọn lô / giao dịch cần sửa:</label>
                      <select
                        className="select-input"
                        value={selectedEventId || ''}
                        onChange={(e) => setSelectedEventId(e.target.value ? Number(e.target.value) : null)}
                        style={{ width: '100%' }}
                      >
                        <option value="">-- Chọn giao dịch --</option>
                        {symbolTransactions.map(tx => (
                          <option key={tx.id} value={tx.id}>
                            #{tx.id} - {tx.event_date}: {tx.event_type} {formatShares(tx.quantity, locale)} CP @ {moneyFn(tx.price, locale)} ({tx.broker_code})
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}

              {mode === 'ADD_POSITION' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Loại giao dịch *</label>
                  <div style={{ display: 'flex', gap: '16px' }}>
                    <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="radio"
                        name="pos_type"
                        value="POSITION_IMPORT"
                        checked={eventType === 'POSITION_IMPORT'}
                        onChange={() => setEventType('POSITION_IMPORT')}
                      />
                      Nhập vị thế sẵn có
                    </label>
                    <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input
                        type="radio"
                        name="pos_type"
                        value="BUY"
                        checked={eventType === 'BUY'}
                        onChange={() => setEventType('BUY')}
                      />
                      Mua mới (trừ tiền mặt)
                    </label>
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Số lượng (Cổ phiếu) *</label>
                  <input
                    className="input-text"
                    type="text"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="Ví dụ: 1000"
                    style={{ width: '100%' }}
                  />
                  {sharesFormatted && <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>{sharesFormatted} cổ phiếu</div>}
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Giá giao dịch (VND/CP) *</label>
                  <input
                    className="input-text"
                    type="text"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="Ví dụ: 25500 hoặc 72000"
                    style={{ width: '100%' }}
                  />
                  {priceFormatted && <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>{priceFormatted}/cp</div>}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Ngày giao dịch</label>
                  <input
                    className="input-text"
                    type="date"
                    value={eventDate}
                    onChange={(e) => setEventDate(e.target.value)}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Phí giao dịch (VND)</label>
                  <input
                    className="input-text"
                    type="text"
                    value={fee}
                    onChange={(e) => setFee(e.target.value)}
                    placeholder="0"
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Nơi lưu ký (CTCK)</label>
                  <select
                    className="select-input"
                    value={brokerCode}
                    onChange={(e) => setBrokerCode(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    {BROKERS.map(b => (
                      <option key={b.code} value={b.code}>{b.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {mode === 'EDIT_POSITION' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600, color: '#f59e0b' }}>Lý do chỉnh sửa *</label>
                  <input
                    className="input-text"
                    type="text"
                    value={correctionReason}
                    onChange={(e) => setCorrectionReason(e.target.value)}
                    placeholder="Ví dụ: Đỉnh chính giá mua theo sao kê CTCK"
                    style={{ width: '100%', borderColor: '#f59e0b' }}
                  />
                </div>
              )}

              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Ghi chú (Tùy chọn)</label>
                <input
                  className="input-text"
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Ghi chú cá nhân..."
                  style={{ width: '100%' }}
                />
              </div>
            </>
          )}

          {/* Cash Form */}
          {['ADD_CASH', 'WITHDRAW_CASH', 'ADJUST_CASH'].includes(mode) && (
            <>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Số tiền VND *</label>
                <input
                  className="input-text"
                  type="text"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="Ví dụ: 50.000.000đ hoặc 50tr"
                  style={{ width: '100%', fontSize: '16px', padding: '10px' }}
                  autoFocus
                />
                {parsedAmountVnd != null && (
                  <div style={{ marginTop: '6px', fontSize: '13px', color: '#10b981' }}>
                    <strong>{moneyFn(parsedAmountVnd, locale)}</strong>
                    {amountWords && <span style={{ marginLeft: '8px', fontStyle: 'italic', color: '#a7f3d0' }}>({amountWords})</span>}
                  </div>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Ngày phát sinh</label>
                  <input
                    className="input-text"
                    type="date"
                    value={eventDate}
                    onChange={(e) => setEventDate(e.target.value)}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 600 }}>Ghi chú nội dung</label>
                  <input
                    className="input-text"
                    type="text"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder={mode === 'WITHDRAW_CASH' ? 'Rút tiền mặt trang trải nhu cầu' : 'Nạp vốn đầu tư hàng tháng'}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            </>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '12px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
              Hủy bỏ
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Đang lưu vào sổ cái…' : 'Xác nhận & Lưu sổ cái'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
