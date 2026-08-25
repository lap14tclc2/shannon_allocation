import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { deletePortfolio, setCashReserve, setReferenceWeights } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { formatMoney } from '../lib/format.js';
import { validateCashReserveInput, validateReferenceWeightInputs } from '../lib/validation.js';

const CASH_PRESETS = [
  [0, '0'],
  [10_000_000, '10 triệu'],
  [20_000_000, '20 triệu'],
  [50_000_000, '50 triệu'],
];

function FieldError({ error }) {
  return error ? <span className="field-error">{error}</span> : null;
}

function normalizedCurrentWeights(positions) {
  const source = positions.map(position => {
    const equityWeight = Number(position.equity_weight);
    if (Number.isFinite(equityWeight) && equityWeight > 0) return equityWeight;
    const weight = Number(position.weight);
    return Number.isFinite(weight) && weight > 0 ? weight : 0;
  });
  const sum = source.reduce((total, value) => total + value, 0);
  if (!sum) return Object.fromEntries(positions.map(position => [position.symbol, '']));
  return Object.fromEntries(positions.map((position, index) => [position.symbol, ((source[index] / sum) * 100).toFixed(2)]));
}

function equalWeights(positions) {
  if (!positions.length) return {};
  const base = Math.floor((100 / positions.length) * 100) / 100;
  let assigned = 0;
  return Object.fromEntries(positions.map((position, index) => {
    const value = index === positions.length - 1 ? Number((100 - assigned).toFixed(2)) : base;
    assigned += value;
    return [position.symbol, value.toFixed(2)];
  }));
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
  const [messageTone, setMessageTone] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [exporting, setExporting] = useState(false);
  const [exportMessage, setExportMessage] = useState('');
  const [deleting, setDeleting] = useState(false);

  const total = useMemo(() => Object.values(weights).reduce((sum, value) => sum + (value === '' ? 0 : Number(value || 0)), 0), [weights]);
  const reservePreview = useMemo(() => {
    if (String(cashReserve ?? '').trim() === '') return null;
    try { return validateCashReserveInput(cashReserve, 'vi'); } catch { return null; }
  }, [cashReserve]);

  function setWeight(symbol, value) {
    setWeights(currentWeights => ({ ...currentWeights, [symbol]: value }));
    setFieldErrors(currentErrors => ({ ...currentErrors, [symbol]: undefined, weights: undefined }));
  }

  function applyCashPreset(value) {
    setCashReserveValue(String(value));
    setFieldErrors(currentErrors => ({ ...currentErrors, cash_reserve: undefined }));
    setMessage('');
  }

  function applyWeightTemplate(template) {
    if (template === 'equal') setWeights(equalWeights(positions));
    if (template === 'current') setWeights(normalizedCurrentWeights(positions));
    if (template === 'clear') setWeights(Object.fromEntries(positions.map(position => [position.symbol, ''])));
    setFieldErrors({});
    setMessage('');
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setMessage('');
    setMessageTone('');
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
      setMessage(`Đã lưu. QPort sẽ giữ lại ${formatMoney(savedReserve, false, locale)} VND trước khi tính phần tiền có thể mua thêm.`);
      setMessageTone('success');
    } catch (error) {
      if (error.field) setFieldErrors({ [error.field]: error.message });
      setMessage(error.message);
      setMessageTone('error');
    } finally {
      setSaving(false);
    }
  }

  async function exportForAI() {
    setExporting(true);
    setExportMessage('');
    try {
      const filename = await downloadAIExport();
      setExportMessage(`Đã tạo ${filename}. Bạn có thể gửi file này cho ChatGPT, Gemini hoặc Claude.`);
    } catch (error) {
      setExportMessage(`Không thể xuất báo cáo: ${error.message}`);
    } finally {
      setExporting(false);
    }
  }

  async function removePortfolio() {
    const confirmation = window.prompt(
      'Thao tác này xóa vĩnh viễn toàn bộ giao dịch, lịch sử, cổ tức, snapshot và dữ liệu danh mục nhưng giữ nguyên account.\n\nNhập chính xác: XOA DANH MUC',
      '',
    );
    if (confirmation !== 'XOA DANH MUC') return;
    setDeleting(true);
    try {
      await deletePortfolio(confirmation);
      window.alert('Đã xóa portfolio. Account của bạn vẫn được giữ nguyên.');
      window.location.replace('/');
    } catch (error) {
      window.alert(`Không thể xóa portfolio: ${error.message}`);
      setDeleting(false);
    }
  }

  return <div className="page settings-page">
    <AppNav active="settings" locale={locale} />

    <header className="page-head settings-head">
      <div>
        <div className="eyebrow">Tùy chọn cá nhân</div>
        <h1>Cài đặt</h1>
        <p className="muted">Điều chỉnh cách QPort hiểu phần tiền bạn muốn giữ lại, đặt định hướng mua thêm khi cần và sử dụng các công cụ hỗ trợ danh mục.</p>
      </div>
    </header>

    <main className="settings-stack">
      <form className="card settings-card settings-preferences-card" onSubmit={save} noValidate>
        <div className="settings-card-head">
          <div className="settings-card-icon" aria-hidden="true">₫</div>
          <div>
            <span className="settings-card-kicker">Tùy chọn danh mục</span>
            <h2>Tiền mặt muốn giữ lại</h2>
            <p>Số tiền này được coi là phần bạn muốn giữ lại. QPort sẽ không xem nó là tiền sẵn sàng để mua thêm cổ phiếu.</p>
          </div>
        </div>

        <div className="settings-reserve-panel">
          <label className="settings-money-field">Số tiền dự trữ
            <div className="settings-money-input-wrap">
              <input
                type="text"
                inputMode="decimal"
                value={cashReserve}
                onChange={event => { setCashReserveValue(event.target.value); setFieldErrors(currentErrors => ({ ...currentErrors, cash_reserve: undefined })); }}
                placeholder="20tr hoặc 20.000.000"
                aria-invalid={!!fieldErrors.cash_reserve}
                autoComplete="off"
              />
              <span>VND</span>
            </div>
            <FieldError error={fieldErrors.cash_reserve} />
          </label>

          <div className="settings-preset-row" aria-label="Chọn nhanh số tiền dự trữ">
            {CASH_PRESETS.map(([value, label]) => <button key={value} type="button" className={reservePreview === value ? 'settings-preset active' : 'settings-preset'} onClick={() => applyCashPreset(value)}>{label}</button>)}
          </div>

          <div className="settings-reserve-summary">
            <span>{reservePreview == null ? 'Nhập số tiền để xem trước.' : 'QPort sẽ giữ lại'}</span>
            <strong>{reservePreview == null ? '-' : `${formatMoney(reservePreview, false, locale)} VND`}</strong>
            <small>Nếu bạn chỉ dùng QPort để theo dõi danh mục, có thể đặt mức này bằng 0.</small>
          </div>
        </div>

        <details className="settings-advanced">
          <summary>
            <div>
              <span className="settings-card-kicker">Nâng cao</span>
              <b>Tỷ trọng tham chiếu</b>
              <small>Chỉ dùng nếu bạn muốn QPort định hướng tiền mua thêm theo một tỷ trọng dài hạn.</small>
            </div>
            <span className="settings-advanced-state">{enabled ? 'Đang bật' : 'Đang tắt'}</span>
          </summary>

          <div className="settings-advanced-body">
            <div className="settings-advanced-intro">
              <p>Đây không phải tái cân bằng tự động và QPort không tự bán cổ phiếu. Tỷ trọng này chỉ giúp diễn giải phần tiền mua thêm.</p>
              <label className="toggle-row"><input type="checkbox" checked={enabled} onChange={event => { setEnabled(event.target.checked); setMessage(''); setFieldErrors({}); }} /><span>{enabled ? 'Sử dụng tỷ trọng tham chiếu' : 'Không sử dụng'}</span></label>
            </div>

            {enabled && (positions.length === 0 ? <p className="muted">Chưa có cổ phiếu để đặt tỷ trọng.</p> : <>
              <div className="settings-weight-tools">
                <button type="button" className="btn-ghost" onClick={() => applyWeightTemplate('equal')}>Phân bổ đều</button>
                <button type="button" className="btn-ghost" onClick={() => applyWeightTemplate('current')}>Theo tỷ trọng hiện tại</button>
                <button type="button" className="btn-ghost" onClick={() => applyWeightTemplate('clear')}>Xóa tỷ trọng</button>
              </div>
              <div className="reference-grid settings-reference-grid">
                {positions.map(position => <label key={position.symbol}>
                  <span><b>{position.symbol}</b><small>Hiện tại {(Number(position.weight || 0) * 100).toFixed(1)}%</small></span>
                  <div className="reference-input"><input type="number" min="0.01" max="100" step="0.01" value={weights[position.symbol] ?? ''} onChange={event => setWeight(position.symbol, event.target.value)} aria-invalid={!!fieldErrors[position.symbol]} /><span>%</span></div>
                  <FieldError error={fieldErrors[position.symbol]} />
                </label>)}
              </div>
              <div className="settings-weight-total"><span>Tổng tỷ trọng mục tiêu</span><b className={Math.abs(total - 100) < .001 ? 'pos' : 'neg'}>{Number.isFinite(total) ? total.toFixed(2) : '-'}%</b></div>
              {Math.abs(total - 100) >= .001 && <p className="settings-inline-warning">Tổng tỷ trọng cần bằng 100% trước khi lưu.</p>}
              <FieldError error={fieldErrors.weights} />
            </>)}
          </div>
        </details>

        <div className="settings-save-row">
          <button className="btn-primary" type="submit" disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</button>
          <span className="muted">Các thay đổi chỉ ảnh hưởng đến tùy chọn cá nhân, không tạo giao dịch.</span>
        </div>
        {message && <div className={`settings-message ${messageTone}`} role={messageTone === 'error' ? 'alert' : 'status'}>{message}</div>}
      </form>

      <section className="card settings-card settings-tools-card">
        <div className="settings-card-head">
          <div className="settings-card-icon settings-ai-icon" aria-hidden="true">AI</div>
          <div>
            <span className="settings-card-kicker">Công cụ</span>
            <h2>Xuất báo cáo cho AI</h2>
            <p>Tạo một file Markdown đầy đủ để ChatGPT, Gemini hoặc Claude có thể đọc và phân tích danh mục dựa trên dữ liệu QPort.</p>
          </div>
        </div>

        <div className="settings-export-layout">
          <div className="settings-export-copy">
            <strong>Báo cáo chỉ đọc, không tạo giao dịch.</strong>
            <p>File export bao gồm dữ liệu đang có trong QPort và giữ nguyên thông tin CTCK/tài khoản để AI không nhầm nguồn cổ phiếu.</p>
            <div className="settings-export-tags">
              <span>Danh mục</span><span>Giao dịch</span><span>CTCK & tax lots</span><span>Hiệu quả</span><span>Rủi ro</span><span>Cổ tức</span><span>Snapshots</span><span>Audit trail</span>
            </div>
          </div>
          <div className="settings-export-action">
            <div className="settings-export-stat"><span>Mã đang nắm giữ</span><strong>{positions.length}</strong></div>
            <div className="settings-export-stat"><span>Định dạng</span><strong>Markdown</strong></div>
            <button type="button" className="btn-primary settings-export-button" onClick={exportForAI} disabled={exporting}>{exporting ? 'Đang tổng hợp dữ liệu…' : 'Xuất báo cáo cho AI'}</button>
          </div>
        </div>
        {exportMessage && <div className="settings-message" role="status">{exportMessage}</div>}
      </section>

      <section className="card settings-card settings-danger-card">
        <div className="settings-danger-copy">
          <span className="settings-card-kicker">Vùng nguy hiểm</span>
          <h2>Xóa portfolio</h2>
          <p>Xóa toàn bộ dữ liệu danh mục, giao dịch, snapshot và dữ liệu liên quan. Account đăng nhập của bạn vẫn được giữ lại.</p>
        </div>
        <button type="button" className="btn-danger" onClick={removePortfolio} disabled={deleting}>{deleting ? 'Đang xóa…' : 'Xóa portfolio'}</button>
      </section>
    </main>
  </div>;
}
