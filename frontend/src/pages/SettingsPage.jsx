import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { setReferenceWeights } from '../lib/api.js';
import { useI18n } from '../i18n.js';

export default function SettingsPage({ dashboard = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const positions = dashboard.portfolio?.positions || [];
  const current = dashboard.portfolio?.reference_weights || {};
  const [enabled, setEnabled] = useState(Object.keys(current).length > 0);
  const [weights, setWeights] = useState(() => Object.fromEntries(positions.map((p) => [p.symbol, current[p.symbol] != null ? Number(current[p.symbol]) * 100 : ''])));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const total = useMemo(() => Object.values(weights).reduce((sum, v) => sum + (v === '' ? 0 : Number(v || 0)), 0), [weights]);

  async function save(e) {
    e.preventDefault(); setSaving(true); setMessage('');
    try {
      if (!enabled) {
        await setReferenceWeights({});
        setMessage(text('Target-weight guidance disabled. Pure Buy & Hold monitoring remains active.', 'Đã tắt tham chiếu tỷ trọng. Theo dõi Buy & Hold thuần vẫn hoạt động.'));
        return setSaving(false);
      }
      const nonEmpty = Object.entries(weights).filter(([, v]) => String(v).trim() !== '' && Number(v) > 0);
      if (nonEmpty.length !== positions.length) throw new Error(text('Enter a target for every holding, or disable target-weight guidance.', 'Nhập tỷ trọng mục tiêu cho mọi mã, hoặc tắt tham chiếu tỷ trọng.'));
      if (Math.abs(total - 100) > 0.001) throw new Error(t('settings.total_error', { total: total.toFixed(2) }));
      await setReferenceWeights(Object.fromEntries(nonEmpty.map(([s, v]) => [s, Number(v) / 100])));
      setMessage(t('settings.saved')); setSaving(false);
    } catch (err) { setMessage(err.message); setSaving(false); }
  }

  return (
    <div className="page">
      <AppNav active="settings" locale={locale} />
      <header className="page-head"><div><h1>{t('settings.title')}</h1><p className="muted">{text('QPort has very few settings by design. Portfolio accounting and Buy & Hold rules are fixed; only optional guidance preferences belong here.', 'QPort cố ý có rất ít cài đặt. Quy tắc hạch toán và Buy & Hold là cố định; trang này chỉ chứa tùy chọn hướng dẫn không bắt buộc.')}</p></div></header>

      <div className="expand-grid">
        <div className="card"><h3>{text('System policy', 'Chính sách hệ thống')}</h3><div className="diag-row"><span>{text('Investment mode', 'Chế độ đầu tư')}</span><b>BUY &amp; HOLD</b></div><div className="diag-row"><span>{text('Automatic trading', 'Giao dịch tự động')}</span><b>{text('OFF', 'TẮT')}</b></div><div className="diag-row"><span>{text('Portfolio changes', 'Thay đổi danh mục')}</span><b>{text('Ledger events only', 'Chỉ từ sự kiện sổ cái')}</b></div><div className="diag-row"><span>{text('Daily tracking', 'Theo dõi hàng ngày')}</span><b>{text('ON', 'BẬT')}</b></div><p className="muted">{text('These are product invariants, not user-tunable parameters.', 'Đây là nguyên tắc bất biến của sản phẩm, không phải tham số để tối ưu.')}</p></div>
        <div className="card"><h3>{text('Market data', 'Dữ liệu thị trường')}</h3><div className="diag-row"><span>{text('Mode', 'Chế độ')}</span><b>AUTO</b></div><div className="diag-row"><span>{text('Primary when installed', 'Nguồn ưu tiên khi có')}</span><b>Vnstock</b></div><div className="diag-row"><span>{text('Fallback', 'Nguồn dự phòng')}</span><b>VNDIRECT</b></div><div className="diag-row"><span>{text('Scheduled EOD sync', 'Đồng bộ cuối ngày')}</span><b>15:30 Asia/Ho_Chi_Minh</b></div><p className="muted">{text('If a provider fails, QPort shows stale/missing data. It never changes holdings because of a data failure.', 'Nếu nguồn dữ liệu lỗi, QPort hiển thị CŨ/THIẾU. Hệ thống không bao giờ thay đổi cổ phiếu vì lỗi dữ liệu.')}</p></div>
      </div>

      <form className="card" onSubmit={save}>
        <div className="section-head"><div><h3>{text('Optional target-weight guidance', 'Tham chiếu tỷ trọng không bắt buộc')}</h3><p className="muted">{text('Use this only if you want ADD / HOLD / REVIEW labels and cash-deployment suggestions. It does not rebalance or trade.', 'Chỉ bật nếu bạn muốn nhãn MUA THÊM / GIỮ / XEM XÉT và gợi ý dùng tiền mặt. Tính năng này không tái cân bằng hay đặt lệnh.')}</p></div><label className="toggle-row"><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /><span>{enabled ? text('Enabled', 'Đang bật') : text('Disabled — pure Buy & Hold', 'Đang tắt — Buy & Hold thuần')}</span></label></div>

        {enabled && (positions.length === 0 ? <p className="muted">{t('settings.add_first')}</p> : <><div className="reference-grid">{positions.map((p) => <label key={p.symbol}><span><b>{p.symbol}</b> <span className="muted">{text('current', 'hiện tại')} {(Number(p.weight || 0) * 100).toFixed(1)}%</span></span><div className="reference-input"><input type="number" min="0" max="100" step="0.01" value={weights[p.symbol] ?? ''} onChange={(e) => setWeights((x) => ({ ...x, [p.symbol]: e.target.value }))} /><span>%</span></div></label>)}</div><div className="diag-row"><span>{text('Target total', 'Tổng mục tiêu')}</span><b className={Math.abs(total - 100) < .001 ? 'pos' : 'neg'}>{total.toFixed(2)}%</b></div></>)}
        <div className="button-row"><button className="btn-export" type="submit" disabled={saving}>{saving ? t('settings.saving') : text('Save preference', 'Lưu tùy chọn')}</button></div>
        {message && <div className="run-message" style={{ marginTop: 10 }}>{message}</div>}
      </form>
    </div>
  );
}
