import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { money as moneyFn, pct } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';
import { useI18n } from '../i18n.js';



export default function SnapshotsPage({ snapshots = [], locale = 'en' }) {
  const { t, status, text } = useI18n(locale);
  const money = (v) => moneyFn(v, locale, 'VND');
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const official = snapshots.filter((s) => s.official).length;
  const latest = snapshots[0];

  async function sync() {
    setSyncing(true); setMessage('');
    try { const result = await syncPortfolio(); setMessage(result.message || 'OK'); window.location.reload(); }
    catch (err) { setMessage(err.message); setSyncing(false); }
  }

  return (
    <div className="page">
      <AppNav active="snapshots" locale={locale} />
      <header className="page-head portfolio-head"><div><h1>{t('snapshots.title')}</h1><p className="muted">{text('Snapshots are automatic daily checkpoints. You do not enter them manually.', 'Snapshot là các mốc trạng thái hàng ngày được tạo tự động. Bạn không cần nhập thủ công.')}</p></div><button className="btn-export" type="button" onClick={sync} disabled={syncing}>{syncing ? text('Syncing…', 'Đang đồng bộ…') : text('↻ Sync & rebuild snapshots', '↻ Đồng bộ & dựng lại snapshot')}</button></header>
      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid compact-metrics"><div className="metric-card"><div className="metric-label">{text('Stored snapshots', 'Snapshot đã lưu')}</div><div className="metric-value">{snapshots.length}</div></div><div className="metric-card"><div className="metric-label">{text('Official', 'Chính thức')}</div><div className="metric-value">{official}</div></div><div className="metric-card"><div className="metric-label">{text('Latest date', 'Ngày mới nhất')}</div><div className="metric-value">{latest?.snapshot_date || '-'}</div></div></div>

      <div className="expand-grid">
        <div className="card"><h3>{text('What is a snapshot?', 'Snapshot là gì?')}</h3><p>{text('A snapshot freezes the portfolio state for one market date: holdings from the ledger + closing prices + cash + NAV + daily return + drawdown.', 'Snapshot chốt trạng thái danh mục tại một ngày thị trường: cổ phiếu từ sổ cái + giá đóng cửa + tiền mặt + NAV + lợi suất ngày + drawdown.')}</p><p className="muted">{text('It is derived data. The immutable transaction ledger remains the source of truth.', 'Đây là dữ liệu dẫn xuất. Sổ cái giao dịch bất biến vẫn là nguồn sự thật.')}</p></div>
        <div className="card"><h3>{text('Official vs stale', 'Chính thức và dữ liệu cũ')}</h3><p><b>{text('OFFICIAL', 'CHÍNH THỨC')}</b> — {text('all active holdings have a price for that same trading date. These rows are used for performance.', 'tất cả mã đang nắm giữ có giá cùng ngày giao dịch. Các dòng này được dùng để tính hiệu suất.')}</p><p><b>{text('STALE', 'CŨ')}</b> — {text('at least one holding only has a previous price. It remains visible for diagnosis but is excluded from official performance.', 'ít nhất một mã chỉ có giá cũ hơn. Snapshot vẫn hiển thị để chẩn đoán nhưng không được dùng làm bằng chứng hiệu suất chính thức.')}</p></div>
      </div>

      <div className="card">
        {snapshots.length === 0 ? <div className="empty-state"><h3>{text('No snapshots yet', 'Chưa có snapshot')}</h3><p>{text('Click Sync & rebuild snapshots. QPort will fetch D1 history and reconstruct daily portfolio checkpoints from the dates recorded in your ledger.', 'Bấm Đồng bộ & dựng lại snapshot. QPort sẽ lấy lịch sử D1 và dựng lại các mốc danh mục hàng ngày từ ngày đã ghi trong sổ cái.')}</p></div> : (
          <div className="table-scroll"><table className="ranking"><thead><tr><th>{t('snapshots.date')}</th><th>{t('snapshots.status')}</th><th>{t('snapshots.nav')}</th><th>{t('snapshots.cash')}</th><th>{t('snapshots.equity')}</th><th>{t('snapshots.daily_pl')}</th><th>{t('snapshots.daily_return')}</th><th>{t('snapshots.drawdown')}</th><th>{t('snapshots.vol252')}</th><th>{t('snapshots.positions')}</th></tr></thead><tbody>{snapshots.map((s) => <tr key={s.id || s.snapshot_date}><td><b>{s.snapshot_date}</b></td><td><span className={`status-pill status-${String(s.data_quality || 'missing').toLowerCase()}`}>{s.official ? t('common.official') : status(s.data_quality)}</span></td><td>{money(s.nav)}</td><td>{money(s.cash)}</td><td>{money(s.equity_value)}</td><td className={Number(s.daily_pnl || 0) >= 0 ? 'pos' : 'neg'}>{money(s.daily_pnl)}</td><td>{pct(s.daily_return)}</td><td>{pct(s.current_drawdown)}</td><td>{pct(s.volatility_252)}</td><td>{(s.positions || []).length}</td></tr>)}</tbody></table></div>
        )}
      </div>
    </div>
  );
}
