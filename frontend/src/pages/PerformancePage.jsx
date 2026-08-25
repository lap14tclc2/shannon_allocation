import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import AppNav from '../components/AppNav.jsx';
import EquityChart from '../components/EquityChart.jsx';
import { formatMoney } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';
import { loadRoute } from '../lib/store.js';

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} ₫`;
}

function signedMoney(value, locale = 'vi') {
  if (value == null || !Number.isFinite(Number(value))) return '-';
  return `${Number(value) >= 0 ? '+' : ''}${money(value, locale)}`;
}

export default function PerformancePage({ performance = {}, locale = 'vi' }) {
  const dispatch = useDispatch();
  const returns = performance.returns || {};
  const series = (performance.series || [])
    .filter(row => row?.date && row.nav != null && Number.isFinite(Number(row.nav)))
    .map(row => ({ date: row.date, nav: Number(row.nav) }));
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');

  async function sync() {
    setSyncing(true);
    setMessage('');
    try {
      await syncPortfolio();
      await dispatch(loadRoute({ pathname: '/performance' })).unwrap();
      setMessage('Lịch sử hiệu quả đã được cập nhật.');
    } catch (error) {
      setMessage(`Không thể cập nhật lịch sử: ${error.message}`);
    } finally {
      setSyncing(false);
    }
  }

  const hasTotalPnl = performance.total_pnl != null && Number.isFinite(Number(performance.total_pnl));
  const totalPnl = hasTotalPnl ? Number(performance.total_pnl) : null;
  const totalPositive = totalPnl == null ? null : totalPnl >= 0;
  const historyCount = performance.official_snapshot_count == null || !Number.isFinite(Number(performance.official_snapshot_count))
    ? null
    : Number(performance.official_snapshot_count);

  return <div className="page investor-performance-page">
    <AppNav active="performance" locale={locale} />

    <header className="page-head portfolio-head">
      <div>
        <div className="eyebrow">Kết quả đầu tư</div>
        <h1>Hiệu quả danh mục</h1>
        <p className="muted">Theo dõi mức tăng trưởng thực tế của danh mục, không nhầm tiền nạp thêm với lợi nhuận.</p>
      </div>
      <button className="btn-secondary" type="button" onClick={sync} disabled={syncing}>{syncing ? 'Đang cập nhật…' : '↻ Cập nhật lịch sử'}</button>
    </header>

    {message && <div className="run-message data-error-message" role="alert">{message}</div>}

    <div className="metric-grid portfolio-metrics overview-metrics investor-overview">
      <div className="metric-card">
        <div className="metric-label">Giá trị hiện tại</div>
        <div className="metric-value" data-sensitive="money">{money(performance.nav, locale)}</div>
        <div className="metric-note">{performance.latest_date || '-'}</div>
      </div>
      <div className={`metric-card ${totalPositive == null ? '' : totalPositive ? 'positive-card' : 'negative-card'}`}>
        <div className="metric-label">Tổng lãi/lỗ</div>
        <div className="metric-value" data-sensitive="pnl">{signedMoney(totalPnl, locale)}</div>
        <div className="metric-note"><span data-sensitive="pnl">{pct(performance.accounting_return)}</span> trên vốn đã ghi nhận</div>
      </div>
      <div className="metric-card">
        <div className="metric-label">Từ đầu năm</div>
        <div className="metric-value">{pct(returns.ytd)}</div>
        <div className="metric-note">Lợi suất từ đầu năm</div>
      </div>
      <div className="metric-card">
        <div className="metric-label">Mức giảm từ đỉnh</div>
        <div className="metric-value">{pct(performance.current_drawdown)}</div>
        <div className="metric-note">Lớn nhất: {pct(performance.max_drawdown)}</div>
      </div>
    </div>

    <section className="card">
      <div className="section-head">
        <div>
          <h2>Giá trị danh mục theo thời gian</h2>
          <p className="muted">Biểu đồ chỉ dùng giai đoạn QPort thực sự theo dõi được danh mục.</p>
        </div>
      </div>
      {series.length < 2 ? <div className="empty-state">
        <h3>Chưa đủ lịch sử để vẽ biểu đồ</h3>
        <p>Hiện có {historyCount == null ? '-' : historyCount} ngày dữ liệu. QPort sẽ tự bổ sung khi tiếp tục theo dõi hằng ngày.</p>
      </div> : <div className="chart"><EquityChart data={series} /></div>}
    </section>

    <div className="expand-grid">
      <section className="card">
        <h3>Thu nhập từ cổ tức</h3>
        <div className="diag-row"><span>Cổ tức tiền mặt trước thuế</span><b>{money(performance.dividend_income, locale)}</b></div>
        <div className="diag-row"><span>Thuế khấu trừ cổ tức tiền mặt</span><b>{money(performance.cash_dividend_tax, locale)}</b></div>
        <div className="diag-row"><span>Cổ tức tiền mặt thực nhận</span><b>{money(performance.net_dividend_income ?? performance.dividend_income, locale)}</b></div>
        <div className="diag-row"><span>Thuế cổ tức cổ phiếu đã ghi khi bán</span><b>{money(performance.stock_dividend_sale_tax, locale)}</b></div>
      </section>

      <section className="card">
        <h3>Tóm tắt kết quả</h3>
        <div className="diag-row"><span>Lãi/lỗ tạm tính</span><b data-sensitive="pnl">{money(performance.unrealized_pnl, locale)}</b></div>
        <div className="diag-row"><span>Lãi/lỗ đã chốt</span><b data-sensitive="pnl">{money(performance.realized_pnl, locale)}</b></div>
        <div className="diag-row"><span>Phí và thuế</span><b>{money(performance.fees_and_taxes, locale)}</b></div>
        <div className="diag-row"><span>Tiền mặt hiện tại</span><b>{money(performance.cash, locale)}</b></div>
      </section>
    </div>

    <details className="card disclosure-card">
      <summary>
        <div>
          <div className="eyebrow">Nâng cao</div>
          <h3>Các chỉ số dành cho phân tích sâu</h3>
          <p className="muted">TWR, XIRR, lợi suất theo kỳ và chất lượng lịch sử.</p>
        </div>
      </summary>
      <div className="health-grid">
        <div><span>Lợi suất từ khi bắt đầu theo dõi</span><b>{pct(returns.since_inception)}</b></div>
        <div><span>TWR năm hóa</span><b>{pct(performance.annualized_twr)}</b></div>
        <div><span>XIRR</span><b>{pct(performance.xirr)}</b></div>
        <div><span>Từ đầu tháng</span><b>{pct(returns.mtd)}</b></div>
        <div><span>Ngày gần nhất</span><b>{pct(returns.daily)}</b></div>
        <div><span>Ngày tốt nhất / xấu nhất</span><b>{pct(performance.best_day)} / {pct(performance.worst_day)}</b></div>
        <div><span>Số ngày dữ liệu chính thức</span><b>{historyCount == null ? '-' : historyCount}</b></div>
        <div><span>Chất lượng dòng tiền</span><b>{performance.cashflow_history_quality || '-'}</b></div>
      </div>
      <p className="muted"><b>TWR</b> giúp đo hiệu quả danh mục sau khi loại ảnh hưởng của tiền nạp/rút. <b>XIRR</b> phản ánh lợi suất thực tế theo thời điểm dòng tiền của nhà đầu tư.</p>
    </details>
  </div>;
}
