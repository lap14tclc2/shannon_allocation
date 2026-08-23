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
          <p className="muted">{text('Simple portfolio performance from your recorded ledger and daily valuations.', 'Hiệu suất danh mục đơn giản từ ledger đã ghi nhận và định giá hàng ngày.')}</p>
        </div>
        <button className="btn-export" type="button" onClick={sync} disabled={syncing}>
          {syncing ? text('Syncing…', 'Đang đồng bộ…') : text('↻ Refresh history', '↻ Cập nhật lịch sử')}
        </button>
      </header>

      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid portfolio-metrics overview-metrics">
        <div className="metric-card">
          <div className="metric-label">{t('performance.latest_nav')}</div>
          <div className="metric-value">{money(performance.nav)}</div>
          <div className="muted">{performance.latest_date || text('Live valuation', 'Định giá hiện tại')}</div>
        </div>
        <div className={`metric-card ${Number(performance.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'}`}>
          <div className="metric-label">{text('Total P/L', 'Lãi/lỗ tổng')}</div>
          <div className="metric-value">{money(performance.total_pnl)}</div>
          <div className="muted">{pct(performance.accounting_return)} {text('on recorded capital', 'trên vốn ghi nhận')}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">{text('Since inception', 'Từ khi bắt đầu')}</div>
          <div className="metric-value">{pct(returns.since_inception)}</div>
          <div className="muted">{performance.first_date || '-'} → {performance.latest_date || '-'}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">{t('performance.ytd')}</div>
          <div className="metric-value">{pct(returns.ytd)}</div>
          <div className="muted">{text('Year to date', 'Từ đầu năm')}</div>
        </div>
      </div>

      <div className="card">
        <div className="section-head">
          <div>
            <h3>{t('performance.nav_history')}</h3>
            <div className="muted">{text('Portfolio value over the period QPort has actually tracked.', 'Giá trị danh mục trong khoảng thời gian QPort thực sự theo dõi.')}</div>
          </div>
        </div>
        {series.length < 2 ? (
          <div className="empty-state">
            <h3>{text('Not enough history yet', 'Chưa đủ lịch sử')}</h3>
            <p>{text('Keep daily tracking enabled. The chart will fill in as official market snapshots are recorded.', 'Tiếp tục bật theo dõi hàng ngày. Biểu đồ sẽ được bổ sung khi có snapshot thị trường chính thức.')}</p>
          </div>
        ) : <div className="chart"><EquityChart data={series} /></div>}
      </div>

      <div className="card">
        <h3>{text('P/L breakdown', 'Phân rã lãi/lỗ')}</h3>
        <div className="diag-row"><span>{text('Unrealized P/L', 'Lãi/lỗ chưa thực hiện')}</span><b>{money(performance.unrealized_pnl)}</b></div>
        <div className="diag-row"><span>{t('performance.realized_pl')}</span><b>{money(performance.realized_pnl)}</b></div>
        <div className="diag-row"><span>{t('performance.dividend_income')}</span><b>{money(performance.dividend_income)}</b></div>
        <div className="diag-row"><span>{t('performance.fees_taxes')}</span><b>{money(performance.fees_and_taxes)}</b></div>
        <div className="diag-row"><span>{text('Current cash', 'Tiền mặt hiện tại')}</span><b>{money(performance.cash)}</b></div>
      </div>

      <details className="card disclosure-card">
        <summary>
          <div>
            <div className="eyebrow">{text('Advanced', 'Nâng cao')}</div>
            <h3>{text('Performance methodology', 'Phương pháp đo hiệu suất')}</h3>
            <p className="muted">{text('Open only when you need TWR, XIRR, drawdown or data-history diagnostics.', 'Chỉ mở khi cần TWR, XIRR, drawdown hoặc chẩn đoán lịch sử dữ liệu.')}</p>
          </div>
        </summary>
        <div className="health-grid">
          <div><span>TWR</span><b>{pct(returns.since_inception)}</b></div>
          <div><span>{text('Annualized TWR', 'TWR năm hóa')}</span><b>{pct(performance.annualized_twr)}</b></div>
          <div><span>XIRR</span><b>{pct(performance.xirr)}</b></div>
          <div><span>{text('Current / max drawdown', 'Drawdown hiện tại / lớn nhất')}</span><b>{pct(performance.current_drawdown)} / {pct(performance.max_drawdown)}</b></div>
          <div><span>{text('History status', 'Trạng thái lịch sử')}</span><b>{performance.history_status || '-'}</b></div>
          <div><span>{text('Official snapshots', 'Snapshot chính thức')}</span><b>{performance.official_snapshot_count ?? 0}</b></div>
        </div>
        <p className="muted">{text('TWR neutralizes external flows. XIRR depends on reliable dated investor cash flows. Missing values mean insufficient evidence, not zero risk or zero return.', 'TWR loại ảnh hưởng của dòng tiền ngoài. XIRR phụ thuộc vào dòng tiền nhà đầu tư có ngày tháng đáng tin cậy. Giá trị thiếu nghĩa là chưa đủ bằng chứng, không phải rủi ro hay lợi nhuận bằng 0.')}</p>
      </details>
    </div>
  );
}
