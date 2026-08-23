import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import EquityChart from '../components/EquityChart.jsx';
import { formatMoney } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

export default function PerformancePage({ performance = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null || !Number.isFinite(Number(v)) ? '-' : `${formatMoney(v, false, locale)} VND`);
  const returns = performance.returns || {};
  const series = (performance.series || []).map((x) => ({ date: x.date, nav: Number(x.nav || 0) }));
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');

  async function sync() {
    setSyncing(true); setMessage('');
    try { const result = await syncPortfolio(); setMessage(result.message || 'OK'); window.location.reload(); }
    catch (err) { setMessage(err.message); setSyncing(false); }
  }

  const historyLabel = {
    NO_HISTORY: text('NO HISTORY', 'CHƯA CÓ LỊCH SỬ'),
    STARTING: text('STARTING', 'MỚI BẮT ĐẦU'),
    SHORT_HISTORY: text('SHORT HISTORY', 'LỊCH SỬ NGẮN'),
    SUFFICIENT: text('SUFFICIENT', 'ĐỦ DỮ LIỆU'),
  }[performance.history_status] || performance.history_status || '-';

  return (
    <div className="page">
      <AppNav active="performance" locale={locale} />
      <header className="page-head portfolio-head"><div><h1>{t('performance.title')}</h1><p className="muted">{t('performance.subtitle')}</p></div><button className="btn-export" type="button" onClick={sync} disabled={syncing}>{syncing ? text('Syncing…', 'Đang đồng bộ…') : text('↻ Sync / rebuild tracked history', '↻ Đồng bộ / dựng lại lịch sử theo dõi')}</button></header>
      {message && <div className="run-message">{message}</div>}

      {performance.history_status !== 'SUFFICIENT' && <div className="run-message">ℹ {text('Performance metrics are limited until QPort has enough official snapshots after the portfolio tracking start. Missing history is shown as N/A, never as a false 0%.', 'Các chỉ số hiệu suất bị giới hạn cho đến khi QPort có đủ snapshot chính thức sau thời điểm bắt đầu theo dõi. Thiếu lịch sử được hiển thị N/A, không giả thành 0%.')}</div>}

      <div className="metric-grid">
        <div className="metric-card"><div className="metric-label">{t('performance.latest_nav')}</div><div className="metric-value">{money(performance.nav)}</div><div className="muted">{performance.latest_date || text('Live valuation', 'Định giá hiện tại')}</div></div>
        <div className={`metric-card ${Number(performance.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'}`}><div className="metric-label">{text('Total P/L', 'Lãi/lỗ tổng')}</div><div className="metric-value">{money(performance.total_pnl)}</div><div className="muted">{text('Accounting return vs recorded capital', 'Tỷ suất lãi/lỗ trên vốn ghi nhận')} {pct(performance.accounting_return)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.twr')}</div><div className="metric-value">{pct(returns.since_inception)}</div><div className="muted">{text('Annualized', 'Năm hóa')} {pct(performance.annualized_twr)}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.xirr')}</div><div className="metric-value">{pct(performance.xirr)}</div><div className="muted">{performance.xirr_status || '-'} · {performance.cashflow_history_quality || '-'}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Current drawdown', 'Drawdown hiện tại')}</div><div className="metric-value">{pct(performance.current_drawdown)}</div><div className="muted">{text('Max', 'Lớn nhất')} {pct(performance.max_drawdown)}</div></div>
        <div className="metric-card"><div className="metric-label">{text('History quality', 'Chất lượng lịch sử')}</div><div className="metric-value">{historyLabel}</div><div className="muted">{performance.official_snapshot_count ?? 0} {text('official snapshots', 'snapshot chính thức')} · {performance.first_date || '-'} → {performance.latest_date || '-'}</div></div>
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
        <div className="section-head"><div><h3>{t('performance.nav_history')}</h3><div className="muted">{text('Tracking begins from actual ledger effective dates. QPort does not invent pre-import portfolio history from current holdings.', 'Việc theo dõi bắt đầu từ ngày hiệu lực thực tế trong sổ cái. QPort không bịa lịch sử danh mục trước ngày nhập chỉ từ holdings hiện tại.')}</div></div></div>
        {series.length < 2 ? <div className="empty-state"><h3>{text('Not enough tracked performance history', 'Chưa đủ lịch sử hiệu suất được theo dõi')}</h3><p>{text('If your opening positions were imported today, this is expected. The first official performance point appears on the first valid market session on or after the import date.', 'Nếu bạn vừa nhập vị thế hôm nay thì đây là trạng thái bình thường. Điểm hiệu suất chính thức đầu tiên xuất hiện ở phiên thị trường hợp lệ đầu tiên bằng hoặc sau ngày nhập.')}</p></div> : <div className="chart"><EquityChart data={series} /></div>}
      </div>

      <div className="expand-grid">
        <div className="card"><h3>{t('performance.pl_accounting')}</h3><div className="diag-row"><span>{text('Unrealized P/L', 'Lãi/lỗ chưa thực hiện')}</span><b>{money(performance.unrealized_pnl)}</b></div><div className="diag-row"><span>{t('performance.realized_pl')}</span><b>{money(performance.realized_pnl)}</b></div><div className="diag-row"><span>{t('performance.dividend_income')}</span><b>{money(performance.dividend_income)}</b></div><div className="diag-row"><span>{t('performance.fees_taxes')}</span><b>{money(performance.fees_and_taxes)}</b></div><div className="diag-row"><span>{t('performance.net_contributions')}</span><b>{money(performance.net_external_contributions)}</b></div><div className="diag-row"><span>{text('Current cash', 'Tiền mặt hiện tại')}</span><b>{money(performance.cash)}</b></div></div>
        <div className="card"><h3>{t('performance.measurement_policy')}</h3><p><b>TWR</b> {text('starts only from tracked official snapshots and neutralizes external flows.', 'chỉ bắt đầu từ các snapshot chính thức được theo dõi và loại ảnh hưởng của dòng tiền ngoài.')}</p><p><b>XIRR</b> {performance.cashflow_history_quality === 'OPENING_BALANCE_ONLY' ? text('is intentionally unavailable because opening position imports do not prove the historical dates of investor cash flows.', 'cố ý không được tính vì việc nhập vị thế ban đầu không chứng minh ngày lịch sử của các dòng tiền đầu tư.') : t('performance.xirr_explain').replace(/^XIRR\s*/i, '')}</p><p>{text('Drawdown is derived from tracked TWR history. N/A means insufficient observations, not zero risk.', 'Drawdown được suy ra từ lịch sử TWR được theo dõi. N/A nghĩa là chưa đủ quan sát, không phải rủi ro bằng 0.')}</p><p className="muted">{t('performance.official_only')}</p></div>
      </div>
    </div>
  );
}
