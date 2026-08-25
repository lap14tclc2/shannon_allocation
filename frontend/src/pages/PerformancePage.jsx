import React, { useMemo, useState } from 'react';
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

function cashflowQualityLabel(value) {
  return ({
    OPENING_BALANCE_ONLY: 'Chỉ có số dư đầu kỳ',
    COMPLETE: 'Đầy đủ dòng tiền',
    PARTIAL: 'Chưa đầy đủ',
  })[value] || value || '-';
}

export default function PerformancePage({ performance = {}, locale = 'vi' }) {
  const dispatch = useDispatch();
  const returns = performance.returns || {};
  const series = useMemo(() => (performance.series || [])
    .filter(row => row?.date && row.nav != null && Number.isFinite(Number(row.nav)))
    .map(row => ({ date: row.date, nav: Number(row.nav), daily_return: row.daily_return })), [performance.series]);
  const [range, setRange] = useState('ALL');
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const chartData = useMemo(() => {
    if (range === 'ALL' || series.length < 2) return series;
    const latest = new Date(`${series[series.length - 1].date}T00:00:00Z`);
    const cutoff = new Date(latest);
    if (range === 'YTD') cutoff.setUTCMonth(0, 1);
    else cutoff.setUTCMonth(cutoff.getUTCMonth() - ({ '1M': 1, '3M': 3, '6M': 6, '1Y': 12 }[range] || 0));
    const filtered = series.filter(row => new Date(`${row.date}T00:00:00Z`) >= cutoff);
    return filtered.length >= 2 ? filtered : series;
  }, [series, range]);
  const benchmarkSeries = performance.benchmark?.series || [];

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
        <div className="metric-value">{money(performance.nav, locale)}</div>
        <div className="metric-note">{performance.latest_date || '-'}</div>
      </div>
      <div className={`metric-card ${totalPositive == null ? '' : totalPositive ? 'positive-card' : 'negative-card'}`}>
        <div className="metric-label">Tổng lãi/lỗ</div>
        <div className="metric-value">{signedMoney(totalPnl, locale)}</div>
        <div className="metric-note">{pct(performance.accounting_return)} trên vốn đã ghi nhận</div>
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
        <div className="chart-range-switch" role="group" aria-label="Khoảng thời gian biểu đồ">
          {['1M', '3M', '6M', 'YTD', '1Y', 'ALL'].map(value => <button type="button" key={value} className={range === value ? 'active' : ''} onClick={() => setRange(value)}>{value === 'ALL' ? 'TẤT CẢ' : value}</button>)}
        </div>
      </div>
      {series.length < 2 ? <div className="empty-state">
        <h3>Chưa đủ lịch sử để vẽ biểu đồ</h3>
        <p>Hiện có {historyCount == null ? '-' : historyCount} ngày dữ liệu. QPort sẽ tự bổ sung khi tiếp tục theo dõi hằng ngày.</p>
      </div> : <>
        <div className="chart-legend"><span><i className="portfolio-swatch" />Danh mục</span>{performance.benchmark?.status === 'AVAILABLE' && <span><i className="benchmark-swatch" />VN-Index (chuẩn hóa)</span>}</div>
        <div className="chart"><EquityChart data={chartData} benchmark={benchmarkSeries} /></div>
        {performance.benchmark?.status !== 'AVAILABLE' && <p className="muted chart-benchmark-note">VN-Index sẽ xuất hiện sau lần đồng bộ dữ liệu thị trường kế tiếp; QPort không dựng benchmark giả.</p>}
        <p className="muted chart-benchmark-note">NAV dùng giá đóng cửa raw và các sự kiện cổ tức/chia tách đã ghi trong sổ cái; VN-Index được chuẩn hóa về cùng điểm bắt đầu để so sánh tương đối.</p>
      </>}
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
        <div className="diag-row"><span>Lãi/lỗ tạm tính</span><b>{money(performance.unrealized_pnl, locale)}</b></div>
        <div className="diag-row"><span>Lãi/lỗ đã chốt</span><b>{money(performance.realized_pnl, locale)}</b></div>
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
      <dl className="performance-health-grid">
        <div><dt>Lợi suất từ khi bắt đầu theo dõi</dt><dd>{pct(returns.since_inception)}</dd></div>
        <div><dt>TWR năm hóa</dt><dd>{pct(performance.annualized_twr)}</dd></div>
        <div><dt>XIRR</dt><dd>{pct(performance.xirr)}</dd></div>
        <div><dt>Từ đầu tháng</dt><dd>{pct(returns.mtd)}</dd></div>
        <div><dt>Ngày gần nhất</dt><dd>{pct(returns.daily)}</dd></div>
        <div><dt>Ngày tốt nhất / xấu nhất</dt><dd>{pct(performance.best_day)} / {pct(performance.worst_day)}</dd></div>
        <div><dt>Số ngày dữ liệu chính thức</dt><dd>{historyCount == null ? '-' : historyCount}</dd></div>
        <div><dt>Chất lượng dòng tiền</dt><dd>{cashflowQualityLabel(performance.cashflow_history_quality)}</dd></div>
      </dl>
      <p className="muted"><b>TWR</b> giúp đo hiệu quả danh mục sau khi loại ảnh hưởng của tiền nạp/rút. <b>XIRR</b> phản ánh lợi suất thực tế theo thời điểm dòng tiền của nhà đầu tư.</p>
    </details>
  </div>;
}
