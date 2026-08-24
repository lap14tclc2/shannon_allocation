import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { setCashReserve, setReferenceWeights } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';
import { validateCashReserveInput, validateReferenceWeightInputs } from '../lib/validation.js';

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export default function SettingsPage({ dashboard = {}, locale = 'vi' }) {
  const positions = dashboard.portfolio?.positions || [];
  const current = dashboard.portfolio?.reference_weights || {};
  const prefs = dashboard.preferences || {};
  const [enabled, setEnabled] = useState(Object.keys(current).length > 0);
  const [weights, setWeights] = useState(() => Object.fromEntries(positions.map(position => [position.symbol, current[position.symbol] != null ? Number(current[position.symbol]) * 100 : ''])));
  const [cashReserve, setCashReserveValue] = useState(prefs.cash_reserve_configured ? String(Number(prefs.cash_reserve || 0)) : '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const total = useMemo(() => Object.values(weights).reduce((sum, value) => sum + (value === '' ? 0 : Number(value || 0)), 0), [weights]);

  const reservePreview = useMemo(() => {
    if (String(cashReserve ?? '').trim() === '') return null;
    try { return validateCashReserveInput(cashReserve, 'vi'); } catch { return null; }
  }, [cashReserve]);

  function setWeight(symbol, value) {
    setWeights(currentWeights => ({ ...currentWeights, [symbol]: value }));
    setFieldErrors(currentErrors => ({ ...currentErrors, [symbol]: undefined, weights: undefined }));
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setMessage('');
    setFieldErrors({});
    try {
      const reserve = validateCashReserveInput(cashReserve, 'vi');
      let normalizedWeights = {};
      if (enabled) {
        if (!positions.length) throw new Error('Hãy thêm cổ phiếu vào danh mục trước khi đặt tỷ trọng tham chiếu.');
        normalizedWeights = validateReferenceWeightInputs(weights, positions.map(position => position.symbol), 'vi');
      }
      const reserveResult = await setCashReserve(reserve);
      await setReferenceWeights(normalizedWeights);
      const savedReserve = Number(reserveResult?.cash_reserve);
      if (!Number.isFinite(savedReserve)) throw new Error('Không thể xác nhận số tiền dự trữ đã lưu.');
      setCashReserveValue(String(savedReserve));
      setMessage(`Đã lưu cài đặt. Tiền mặt muốn giữ lại: ${formatMoney(savedReserve, false, locale)} VND.`);
    } catch (error) {
      if (error.field) setFieldErrors({ [error.field]: error.message });
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  }

  return <div className="page">
    <AppNav active="settings" locale={locale} />

    <header className="page-head">
      <div>
        <div className="eyebrow">Tùy chọn cá nhân</div>
        <h1>Cài đặt</h1>
        <p className="muted">Chỉ hiển thị những gì bạn thực sự có thể thay đổi. Các quy tắc hạch toán và cập nhật dữ liệu do hệ thống tự quản lý.</p>
      </div>
    </header>

    <form className="card" onSubmit={save} noValidate>
      <div className="section-head">
        <div>
          <h2>Tiền mặt muốn giữ lại</h2>
          <p className="muted">Nếu bạn dùng tính năng tham chiếu tỷ trọng, QPort chỉ coi phần tiền mặt vượt mức này là có thể dùng để mua thêm. Nếu chỉ theo dõi danh mục, bạn có thể để 0.</p>
        </div>
      </div>

      <label>Số tiền dự trữ (VND)
        <input
          type="text"
          inputMode="decimal"
          value={cashReserve}
          onChange={event => { setCashReserveValue(event.target.value); setFieldErrors(current => ({ ...current, cash_reserve: undefined })); }}
          placeholder="20tr hoặc 20.000.000"
          aria-invalid={!!fieldErrors.cash_reserve}
          autoComplete="off"
        />
        <span className="muted">Có thể nhập: 20000000 · 20.000.000 · 20tr</span>
        {reservePreview != null && <span className="money-preview"><b>Sẽ lưu:</b> {formatMoney(reservePreview, false, locale)} VND</span>}
        <FieldError error={fieldErrors.cash_reserve} />
      </label>

      <details className="disclosure-card" open={enabled}>
        <summary>
          <div><b>Tỷ trọng tham chiếu</b><span className="muted">Tùy chọn nâng cao cho người muốn định hướng tiền mua thêm</span></div>
        </summary>
        <div className="section-head">
          <div>
            <p className="muted">Đây không phải cơ chế tái cân bằng tự động. Chỉ bật nếu bạn có chủ đích đặt tỷ trọng dài hạn cho từng mã.</p>
          </div>
          <label className="toggle-row"><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); setMessage(''); setFieldErrors({}); }} /><span>{enabled ? 'Đang bật' : 'Đang tắt'}</span></label>
        </div>

        {enabled && (positions.length === 0 ? <p className="muted">Chưa có cổ phiếu để đặt tỷ trọng.</p> : <>
          <div className="reference-grid">
            {positions.map(position => <label key={position.symbol}>
              <span><b>{position.symbol}</b> <span className="muted">hiện tại {(Number(position.weight || 0) * 100).toFixed(1)}%</span></span>
              <div className="reference-input"><input type="number" min="0.01" max="100" step="0.01" value={weights[position.symbol] ?? ''} onChange={event => setWeight(position.symbol, event.target.value)} aria-invalid={!!fieldErrors[position.symbol]} /><span>%</span></div>
              <FieldError error={fieldErrors[position.symbol]} />
            </label>)}
          </div>
          <div className="diag-row"><span>Tổng tỷ trọng</span><b className={Math.abs(total - 100) < .001 ? 'pos' : 'neg'}>{Number.isFinite(total) ? total.toFixed(2) : '—'}%</b></div>
          <FieldError error={fieldErrors.weights} />
        </>)}
      </details>

      <div className="button-row"><button className="btn-primary" type="submit" disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu cài đặt'}</button></div>
      {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
    </form>
  </div>;
}
