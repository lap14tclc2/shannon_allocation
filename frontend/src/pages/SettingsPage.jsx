import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { setCashReserve, setReferenceWeights } from '../lib/api.js';
import { formatMoney } from '../lib/format.js';
import { validateCashReserveInput, validateReferenceWeightInputs } from '../lib/validation.js';
import { useI18n } from '../i18n.js';

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

export default function SettingsPage({ dashboard = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const positions = dashboard.portfolio?.positions || [];
  const current = dashboard.portfolio?.reference_weights || {};
  const prefs = dashboard.preferences || {};
  const [enabled, setEnabled] = useState(Object.keys(current).length > 0);
  const [weights, setWeights] = useState(() => Object.fromEntries(positions.map((p) => [p.symbol, current[p.symbol] != null ? Number(current[p.symbol]) * 100 : ''])));
  const [cashReserve, setCashReserveValue] = useState(prefs.cash_reserve_configured ? String(Number(prefs.cash_reserve || 0)) : '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const total = useMemo(() => Object.values(weights).reduce((sum, v) => sum + (v === '' ? 0 : Number(v || 0)), 0), [weights]);

  const reservePreview = useMemo(() => {
    if (String(cashReserve ?? '').trim() === '') return null;
    try { return validateCashReserveInput(cashReserve, locale); } catch { return null; }
  }, [cashReserve, locale]);

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    setFieldErrors({});
    try {
      const reserve = validateCashReserveInput(cashReserve, locale);
      let normalizedWeights = {};
      if (enabled) {
        if (positions.length === 0) throw new Error(text('Add holdings before enabling target-weight guidance.', 'Hãy thêm cổ phiếu trước khi bật tham chiếu tỷ trọng.'));
        normalizedWeights = validateReferenceWeightInputs(weights, positions.map((p) => p.symbol), locale);
      }
      const reserveResult = await setCashReserve(reserve);
      await setReferenceWeights(normalizedWeights);
      const persistedReserve = Number(reserveResult?.cash_reserve);
      if (!Number.isFinite(persistedReserve) || persistedReserve !== reserve) {
        throw new Error(text(
          `Cash reserve verification failed. Expected ${reserve.toLocaleString('en-US')} VND but backend returned ${String(reserveResult?.cash_reserve)}.`,
          `Xác minh tiền dự trữ thất bại. Dự kiến ${reserve.toLocaleString('vi-VN')} VND nhưng backend trả về ${String(reserveResult?.cash_reserve)}.`,
        ));
      }
      setCashReserveValue(String(persistedReserve));
      setMessage(text(
        `Preferences saved. Strategic cash reserve confirmed at ${formatMoney(persistedReserve, false, locale)} VND. Cash is only considered deployable above this reserve and when explicit target weights are enabled.`,
        `Đã lưu tùy chọn. Tiền mặt dự trữ được xác nhận là ${formatMoney(persistedReserve, false, locale)} VND. Tiền mặt chỉ được coi là có thể phân bổ khi vượt mức này và đã bật tỷ trọng mục tiêu rõ ràng.`,
      ));
      setSaving(false);
    } catch (err) {
      if (err.field) setFieldErrors({ [err.field]: err.message });
      setMessage(err.message);
      setSaving(false);
    }
  }

  function setWeight(symbol, value) {
    setWeights((x) => ({ ...x, [symbol]: value }));
    setFieldErrors((x) => ({ ...x, [symbol]: undefined, weights: undefined }));
  }

  return (
    <div className="page">
      <AppNav active="settings" locale={locale} />
      <header className="page-head"><div><h1>{t('settings.title')}</h1><p className="muted">{text('QPort keeps settings intentionally small. Accounting and Buy & Hold rules are fixed; only explicit guidance preferences belong here.', 'QPort cố ý giữ cài đặt ở mức tối thiểu. Quy tắc hạch toán và Buy & Hold là cố định; chỉ các tùy chọn hướng dẫn rõ ràng nằm ở đây.')}</p></div></header>

      <div className="expand-grid">
        <div className="card"><h3>{text('System policy', 'Chính sách hệ thống')}</h3><div className="diag-row"><span>{text('Investment mode', 'Chế độ đầu tư')}</span><b>BUY &amp; HOLD</b></div><div className="diag-row"><span>{text('Automatic trading', 'Giao dịch tự động')}</span><b>{text('OFF', 'TẮT')}</b></div><div className="diag-row"><span>{text('Portfolio changes', 'Thay đổi danh mục')}</span><b>{text('Ledger events only', 'Chỉ từ sự kiện sổ cái')}</b></div><div className="diag-row"><span>{text('Daily tracking', 'Theo dõi hàng ngày')}</span><b>{text('ON', 'BẬT')}</b></div><p className="muted">{text('These are product invariants, not tunable parameters.', 'Đây là nguyên tắc bất biến của sản phẩm, không phải tham số để tối ưu.')}</p></div>
        <div className="card"><h3>{text('Market data', 'Dữ liệu thị trường')}</h3><div className="diag-row"><span>{text('Mode', 'Chế độ')}</span><b>AUTO</b></div><div className="diag-row"><span>{text('Primary when installed', 'Nguồn ưu tiên khi có')}</span><b>Vnstock</b></div><div className="diag-row"><span>{text('Fallback', 'Nguồn dự phòng')}</span><b>VNDIRECT</b></div><div className="diag-row"><span>{text('Scheduled EOD sync', 'Đồng bộ cuối ngày')}</span><b>15:30 Asia/Ho_Chi_Minh</b></div><p className="muted">{text('Provider failure becomes stale/missing information; it never changes holdings.', 'Lỗi nguồn dữ liệu chỉ trở thành thông tin CŨ/THIẾU; nó không bao giờ thay đổi danh mục.')}</p></div>
      </div>

      <form className="card" onSubmit={save} noValidate>
        <div className="section-head"><div><h3>{text('Cash policy', 'Chính sách tiền mặt')}</h3><p className="muted">{text('Available cash is not automatically deployable. Set the amount you intentionally want to keep untouched. Enter 0 only if you explicitly want no reserve.', 'Tiền mặt khả dụng không tự động đồng nghĩa có thể phân bổ. Hãy đặt số tiền bạn chủ động muốn giữ nguyên. Chỉ nhập 0 nếu bạn thực sự không muốn giữ dự trữ.')}</p></div></div>
        <label>{text('Strategic cash reserve (VND)', 'Tiền mặt dự trữ chiến lược (VND)')}
          <input
            type="text"
            inputMode="decimal"
            value={cashReserve}
            onChange={(e) => { setCashReserveValue(e.target.value); setFieldErrors((x) => ({ ...x, cash_reserve: undefined })); }}
            placeholder={text('20m or 20,000,000', '20tr hoặc 20.000.000')}
            aria-invalid={!!fieldErrors.cash_reserve}
            autoComplete="off"
          />
          <span className="muted">{text('Accepted: 20000000 · 20,000,000 · 20.000.000 · 20m · 20tr', 'Chấp nhận: 20000000 · 20,000,000 · 20.000.000 · 20m · 20tr')}</span>
          {reservePreview != null && <span className="money-preview"><b>{text('Will save', 'Sẽ lưu')}:</b> {formatMoney(reservePreview, false, locale)} VND</span>}
          <FieldError error={fieldErrors.cash_reserve} />
        </label>

        <hr className="soft-rule" />
        <div className="section-head"><div><h3>{text('Optional target-weight guidance', 'Tham chiếu tỷ trọng không bắt buộc')}</h3><p className="muted">{text('Enable only if these percentages represent your deliberate long-term portfolio policy. Without them QPort shows MONITOR and will not invent an equal-weight ADD recommendation.', 'Chỉ bật khi các tỷ lệ này thực sự là chính sách danh mục dài hạn của bạn. Nếu chưa cấu hình, QPort sẽ hiển thị THEO DÕI và không tự tạo gợi ý MUA THÊM theo equal-weight.')}</p></div><label className="toggle-row"><input type="checkbox" checked={enabled} onChange={(e) => { setEnabled(e.target.checked); setMessage(''); setFieldErrors({}); }} /><span>{enabled ? text('Enabled', 'Đang bật') : text('Disabled — pure Buy & Hold', 'Đang tắt — Buy & Hold thuần')}</span></label></div>

        {enabled && (positions.length === 0 ? <p className="muted">{t('settings.add_first')}</p> : <><div className="reference-grid">{positions.map((p) => <label key={p.symbol}><span><b>{p.symbol}</b> <span className="muted">{text('current NAV weight', 'tỷ trọng NAV hiện tại')} {(Number(p.weight || 0) * 100).toFixed(1)}%</span></span><div className="reference-input"><input type="number" min="0.01" max="100" step="0.01" value={weights[p.symbol] ?? ''} onChange={(e) => setWeight(p.symbol, e.target.value)} aria-invalid={!!fieldErrors[p.symbol]} /><span>%</span></div><FieldError error={fieldErrors[p.symbol]} /></label>)}</div><div className="diag-row"><span>{text('Target total', 'Tổng mục tiêu')}</span><b className={Math.abs(total - 100) < .001 ? 'pos' : 'neg'}>{Number.isFinite(total) ? total.toFixed(2) : '—'}%</b></div><FieldError error={fieldErrors.weights} /></>)}

        <div className="button-row"><button className="btn-export" type="submit" disabled={saving}>{saving ? t('settings.saving') : text('Save preferences', 'Lưu tùy chọn')}</button></div>
        {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
      </form>
    </div>
  );
}
