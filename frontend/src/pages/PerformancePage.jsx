import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import EquityChart from '../components/EquityChart.jsx';
import { formatMoney } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function PerformancePage({ performance = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  const returns = performance.returns || {};
  const series = (performance.series || []).map((x) => ({ date: x.date, nav: Number(x.nav || 0) }));
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');

  async function sync() {
    setSyncing(true); setMessage('');
    try { const result = await syncPortfolio(); setMessage(result.message || 'OK'); window.location.reload(); }
    catch (err) { setMessage(err.message); setSyncing(false); }
  }

  return (
    <div className="page">
      <AppNav active="performance" locale={locale} />
      <header className="page-head portfolio-head"><div><h1>{t('performance.title')}</h1><p className="muted">{t('performance.subtitle')}</p></div><button className="btn-export" type="button" onClick={sync} disabled={syncing}>{syncing ? text('Syncing…', 'Đang đồng bộ…') : text('↻ Rebuild performance history', '↻ Dựng lại lịch sử hiệu suất')}</button></header>
      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">{t('performance.latest_nav')}</div><div className="metric-value">{money(performance.nav)}</div><div className="muted">{performance.latest_date || text('Live valuation', 'Định giá hiện tại')}</div></div>
        <div className={`metric-card ${Number(performance.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'}`}><div className="metric-label">{text('Total P/L', 'Lãi/lỗ tổng')}</div><div className="metric-value">{money(performance.total_pnl)}</div><div className="muted">{pct(performance.total_return)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.twr')}</div><div className="metric-value">{pct(returns.since_inception)}</div><div className="muted">{text('Annualized', 'Năm hóa')} {pct(performance.annualized_twr)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.xirr')}</div><div className="metric-value">{pct(performance.xirr)}</div><div className="muted">{text('Investor cash-flow return', 'Lợi suất theo dòng tiền thực tế')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Current drawdown', 'Drawdown hiện tại')}</div><div className="metric-value">{pct(performance.current_drawdown ?? 0)}</div><div className="muted">{text('Max', 'Lớn nhất')} {pct(performance.max_drawdown ?? 0)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('History coverage', 'Độ phủ lịch sử')}</div><div className="metric-value">{performance.official_snapshot_count ?? 0}</div><div className="muted">{performance.first_date || '-'} → {performance.latest_date || '-'}</div></div>
      </div>

      <div className="metric-grid compact-metrics">
        <div className="metric-card"><div className="metric-label">{t('performance.daily')}</div><div className="metric-value">{pct(returns.daily)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.mtd')}</div><div className="metric-value">{pct(returns.mtd)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.ytd')}</div><div className="metric-value">{pct(returns.ytd)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Best day', 'Ngày tốt nhất')}</div><div className="metric-value">{pct(performance.best_day)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Worst day', 'Ngày xấu nhất')}</div><div className="metric-value">{pct(performance.worst_day)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Positive days', 'Tỷ lệ ngày tăng')}</div><div className="metric-value">{pct(performance.positive_day_ratio)}</div></div>
      </div>

      <div className="card">
        <div className="section-head"><div><h3>{t('performance.nav_history')}</h3><div className="muted">{text('Built from the immutable ledger and daily market history.', 'Được dựng từ sổ cái bất biến và dữ liệu giá ngày.')}</div></div></div>
        {series.length < 2 ? <div className="empty-state"><h3>{text('No performance history yet', 'Chưa có lịch sử hiệu suất')}</h3><p>{text('Click Rebuild performance history. QPort will fetch D1 prices and reconstruct daily snapshots from your ledger.', 'Bấm Dựng lại lịch sử hiệu suất. QPort sẽ lấy giá D1 và dựng lại snapshot từng ngày từ sổ cái.')}</p></div> : <div className="chart"><EquityChart data={series} /></div>}
      </div>

      <div className="expand-grid">
        <div className="card"><h3>{t('performance.pl_accounting')}</h3><div className="diag-row"><span>{text('Unrealized P/L', 'Lãi/lỗ chưa thực hiện')}</span><b>{money(performance.unrealized_pnl)}</b></div><div className="diag-row"><span>{t('performance.realized_pl')}</span><b>{money(performance.realized_pnl)}</b></div><div className="diag-row"><span>{t('performance.dividend_income')}</span><b>{money(performance.dividend_income)}</b></div><div className="diag-row"><span>{t('performance.fees_taxes')}</span><b>{money(performance.fees_and_taxes)}</b></div><div className="diag-row"><span>{t('performance.net_contributions')}</span><b>{money(performance.net_external_contributions)}</b></div><div className="diag-row"><span>{text('Current cash', 'Tiền mặt hiện tại')}</span><b>{money(performance.cash)}</b></div></div>
        <div className="card"><h3>{t('performance.measurement_policy')}</h3><p><b>TWR</b> {t('performance.twr_explain').replace(/^TWR\s*/i, '')}</p><p><b>XIRR</b> {t('performance.xirr_explain').replace(/^XIRR\s*/i, '')}</p><p>{text('Drawdown is calculated from the TWR equity curve, so deposits and withdrawals do not create fake peaks or losses.', 'Drawdown được tính từ đường TWR nên việc nạp/rút tiền không tạo đỉnh hay khoản lỗ giả.')}</p><p className="muted">{t('performance.official_only')}</p></div>
      </div>
    </div>
  );
}
