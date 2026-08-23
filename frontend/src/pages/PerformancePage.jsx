import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import EquityChart from '../components/EquityChart.jsx';
import { formatMoney } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) {
  return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`;
}

export default function PerformancePage({ performance = {}, locale = 'en' }) {
  const { t } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null || !Number.isFinite(Number(v)) ? '-' : `${formatMoney(v, false, locale)} VND`);
  const returns = performance.returns || {};
  const series = (performance.series || []).map(x => ({ date: x.date, nav: Number(x.nav || 0) }));
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');

  const historyCount = Number(performance.official_snapshot_count || 0);
  const historyTarget = historyCount < 20 ? 20 : 252;
  const historyProgress = Math.min(1, historyCount / historyTarget);
  const historyLabel = historyCount < 20
    ? text(`${historyCount}/20 days for basic statistics`, `${historyCount}/20 ngày cho thống kê cơ bản`)
    : historyCount < 252
      ? text(`${historyCount}/252 days for a full 1-year view`, `${historyCount}/252 ngày cho góc nhìn đủ 1 năm`)
      : text('Full 1-year history available', 'Đã đủ lịch sử 1 năm');

  async function sync() {
    setSyncing(true);
    setMessage('');
    try {
      const result = await syncPortfolio();
      setMessage(result.message || 'OK');
      window.location.reload();
    } catch (err) {
      setMessage(err.message);
      setSyncing(false);
    }
  }

  return (
    <div className="page">
      <AppNav active="performance" locale={locale} />

      <header className="page-head portfolio-head">
        <div>
          <h1>{t('performance.title')}</h1>
          <p className="muted">{text('Portfolio return, drawdown, cash-flow quality, income and tax impact from the same ledger used by Holdings.', 'Lợi nhuận, drawdown, chất lượng dòng tiền, thu nhập và tác động thuế từ cùng ledger đang dùng cho Holdings.')}</p>
        </div>
        <button className="btn-export" type="button" onClick={sync} disabled={syncing}>
          {syncing ? text('Syncing…', 'Đang đồng bộ…') : text('↻ Refresh history', '↻ Cập nhật lịch sử')}
        </button>
      </header>

      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid portfolio-metrics overview-metrics">
        <div className="metric-card"><div className="metric-label">{t('performance.latest_nav')}</div><div className="metric-value">{money(performance.nav)}</div><div className="muted">{performance.latest_date || text('Live valuation', 'Định giá hiện tại')}</div></div>
        <div className={`metric-card ${Number(performance.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'}`}><div className="metric-label">{text('Total P/L', 'Lãi/lỗ tổng')}</div><div className="metric-value">{money(performance.total_pnl)}</div><div className="muted">{pct(performance.accounting_return)} {text('on recorded capital', 'trên vốn ghi nhận')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Since inception TWR', 'TWR từ khi bắt đầu')}</div><div className="metric-value">{pct(returns.since_inception)}</div><div className="muted">{performance.first_date || '-'} → {performance.latest_date || '-'}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Annualized TWR', 'TWR năm hóa')}</div><div className="metric-value">{pct(performance.annualized_twr)}</div><div className="muted">{text('Available after enough elapsed time', 'Có sau khi đủ thời gian quan sát')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Daily / MTD', 'Ngày / MTD')}</div><div className="metric-value">{pct(returns.daily)} / {pct(returns.mtd)}</div><div className="muted">{text('Latest day / month-to-date', 'Ngày gần nhất / từ đầu tháng')}</div></div>
        <div className="metric-card"><div className="metric-label">{t('performance.ytd')}</div><div className="metric-value">{pct(returns.ytd)}</div><div className="muted">{text('Year to date', 'Từ đầu năm')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Current / max drawdown', 'Drawdown hiện tại / lớn nhất')}</div><div className="metric-value">{pct(performance.current_drawdown)} / {pct(performance.max_drawdown)}</div><div className="muted">{text('Measured from TWR peak', 'Đo từ đỉnh TWR')}</div></div>
        <div className="metric-card"><div className="metric-label">{text('Best / worst day', 'Ngày tốt / xấu nhất')}</div><div className="metric-value">{pct(performance.best_day)} / {pct(performance.worst_day)}</div><div className="muted">{pct(performance.positive_day_ratio)} {text('positive days', 'ngày tăng')}</div></div>
      </div>

      <div className="expand-grid">
        <div className="card">
          <h3>{text('Income after dividend tax', 'Thu nhập sau thuế cổ tức')}</h3>
          <div className="diag-row"><span>{text('Gross cash-dividend income', 'Cổ tức tiền mặt gross')}</span><b>{money(performance.dividend_income)}</b></div>
          <div className="diag-row"><span>{text('5% cash-dividend withholding', 'Thuế 5% cổ tức tiền mặt')}</span><b>{money(performance.cash_dividend_tax || 0)}</b></div>
          <div className="diag-row"><span>{text('Net cash-dividend income', 'Cổ tức tiền mặt net')}</span><b>{money(performance.net_dividend_income ?? performance.dividend_income)}</b></div>
          <div className="diag-row"><span>{text('Deferred stock-dividend tax paid on sale', 'Thuế CP cổ tức đã trả khi bán')}</span><b>{money(performance.stock_dividend_sale_tax || 0)}</b></div>
          <p className="muted">{text('Cash dividends are recorded gross, with 5% withholding reducing cash. Stock dividends are untaxed at receipt; the configured 5% par-value tax is recognized when taxable dividend shares are sold.', 'Cổ tức tiền được ghi gross, thuế khấu trừ 5% làm giảm cash. Cổ tức cổ phiếu chưa tính thuế lúc nhận; thuế 5% theo mệnh giá được ghi khi bán số cổ phiếu cổ tức chịu thuế.')}</p>
        </div>
        <div className="card">
          <h3>{text('History readiness', 'Độ sẵn sàng lịch sử')}</h3>
          <div className="diag-row"><span>{text('Status', 'Trạng thái')}</span><b>{performance.history_status || '-'}</b></div>
          <div className="diag-row"><span>{text('Official snapshots', 'Snapshot chính thức')}</span><b>{historyCount}</b></div>
          <div className="diag-row"><span>{text('Coverage milestone', 'Mốc độ phủ')}</span><b>{pct(historyProgress, 0)}</b></div>
          <div className="diag-row"><span>{text('Cash-flow quality', 'Chất lượng dòng tiền')}</span><b>{performance.cashflow_history_quality || '-'}</b></div>
          <div className="diag-row"><span>XIRR</span><b>{pct(performance.xirr)} · {performance.xirr_status || '-'}</b></div>
          <p className="muted">{historyLabel}. {text('Missing statistics mean insufficient evidence, not zero return or zero risk.', 'Chỉ số trống nghĩa là chưa đủ bằng chứng, không phải lợi nhuận/rủi ro bằng 0.')}</p>
        </div>
      </div>

      <div className="card">
        <div className="section-head"><div><h3>{t('performance.nav_history')}</h3><div className="muted">{text('Portfolio value over the period QPort has actually tracked.', 'Giá trị danh mục trong khoảng thời gian QPort thực sự theo dõi.')}</div></div></div>
        {series.length < 2 ? (
          <div className="empty-state"><h3>{text('Not enough history yet', 'Chưa đủ lịch sử')}</h3><p>{historyLabel}. {text('Keep daily tracking enabled; QPort will fill this automatically.', 'Tiếp tục bật theo dõi hàng ngày; QPort sẽ tự động bổ sung.')}</p></div>
        ) : <div className="chart"><EquityChart data={series} /></div>}
      </div>

      <div className="card">
        <h3>{text('P/L bridge', 'Cầu nối P/L')}</h3>
        <div className="diag-row"><span>{text('Unrealized P/L', 'Lãi/lỗ chưa thực hiện')}</span><b>{money(performance.unrealized_pnl)}</b></div>
        <div className="diag-row"><span>{t('performance.realized_pl')}</span><b>{money(performance.realized_pnl)}</b></div>
        <div className="diag-row"><span>{t('performance.dividend_income')}</span><b>{money(performance.dividend_income)}</b></div>
        <div className="diag-row"><span>{t('performance.fees_taxes')}</span><b>{money(performance.fees_and_taxes)}</b></div>
        <div className="diag-row"><span>{text('Current cash', 'Tiền mặt hiện tại')}</span><b>{money(performance.cash)}</b></div>
        <div className="diag-row"><span>{text('Current equity', 'Giá trị cổ phiếu hiện tại')}</span><b>{money(performance.equity_value)}</b></div>
      </div>

      <details className="card disclosure-card">
        <summary><div><div className="eyebrow">{text('Methodology', 'Phương pháp')}</div><h3>{text('How QPort measures performance', 'QPort đo hiệu suất như thế nào')}</h3><p className="muted">TWR · XIRR · drawdown · ledger accounting</p></div></summary>
        <div className="health-grid">
          <div><span>TWR</span><b>{pct(returns.since_inception)}</b></div>
          <div><span>{text('Annualized TWR', 'TWR năm hóa')}</span><b>{pct(performance.annualized_twr)}</b></div>
          <div><span>XIRR</span><b>{pct(performance.xirr)}</b></div>
          <div><span>{text('Current / max drawdown', 'Drawdown hiện tại / lớn nhất')}</span><b>{pct(performance.current_drawdown)} / {pct(performance.max_drawdown)}</b></div>
          <div><span>{text('History status', 'Trạng thái lịch sử')}</span><b>{performance.history_status || '-'}</b></div>
          <div><span>{text('Official snapshots', 'Snapshot chính thức')}</span><b>{performance.official_snapshot_count ?? 0}</b></div>
        </div>
        <p className="muted">{text('TWR neutralizes external flows. XIRR requires reliable dated investor cash flows. Tax and fee events remain inside economic performance.', 'TWR loại ảnh hưởng của dòng tiền ngoài. XIRR cần dòng tiền nhà đầu tư có ngày đáng tin cậy. Thuế và phí vẫn nằm trong hiệu suất kinh tế thực tế.')}</p>
      </details>
    </div>
  );
}
