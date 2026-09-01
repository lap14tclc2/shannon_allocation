import React, { useMemo } from 'react';
import { pct } from '../lib/format.js';
import { chooseText } from '../i18n.js';



function chainReturn(rows, count) {
  const values = rows.map(row => row.daily_return).filter(value => value != null && Number.isFinite(Number(value)));
  if (values.length < count) return null;
  return values.slice(-count).reduce((factor, value) => factor * (1 + Number(value)), 1) - 1;
}

function annualizedVol(rows, count) {
  const values = rows.map(row => row.daily_return).filter(value => value != null && Number.isFinite(Number(value)));
  if (values.length < Math.min(count, 20)) return null;
  const sample = values.slice(-count).map(Number);
  if (sample.length < 2) return null;
  const mean = sample.reduce((a, b) => a + b, 0) / sample.length;
  const variance = sample.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (sample.length - 1);
  return Math.sqrt(Math.max(0, variance)) * Math.sqrt(252);
}

function calendarDays(a, b) {
  if (!a || !b) return null;
  const start = new Date(`${a}T00:00:00Z`);
  const end = new Date(`${b}T00:00:00Z`);
  const ms = end.getTime() - start.getTime();
  return Number.isFinite(ms) ? Math.max(0, Math.round(ms / 86400000)) : null;
}

function drawdownEpisode(rows) {
  const valid = rows.filter(row => row.twr_index != null && Number.isFinite(Number(row.twr_index)));
  if (valid.length < 2) return null;

  let peakIndex = Number(valid[0].twr_index);
  let peakDate = valid[0].date;
  let worst = 0;
  let troughDate = null;
  let troughPeakDate = peakDate;
  let troughPeakIndex = peakIndex;

  for (const row of valid) {
    const index = Number(row.twr_index);
    if (index > peakIndex) {
      peakIndex = index;
      peakDate = row.date;
    }
    const dd = peakIndex > 0 ? index / peakIndex - 1 : 0;
    if (dd < worst) {
      worst = dd;
      troughDate = row.date;
      troughPeakDate = peakDate;
      troughPeakIndex = peakIndex;
    }
  }

  let recoveryDate = null;
  if (troughDate) {
    const troughPos = valid.findIndex(row => row.date === troughDate);
    for (const row of valid.slice(troughPos + 1)) {
      if (Number(row.twr_index) >= troughPeakIndex) {
        recoveryDate = row.date;
        break;
      }
    }
  }

  let latestPeakIndex = Number(valid[0].twr_index);
  let latestPeakDate = valid[0].date;
  for (const row of valid) {
    const index = Number(row.twr_index);
    if (index >= latestPeakIndex) {
      latestPeakIndex = index;
      latestPeakDate = row.date;
    }
  }
  const latest = valid[valid.length - 1];
  const underwaterDays = Number(latest.twr_index) < latestPeakIndex ? calendarDays(latestPeakDate, latest.date) : 0;

  return {
    peak_date: troughPeakDate,
    trough_date: troughDate,
    recovery_date: recoveryDate,
    max_drawdown: worst,
    current_peak_date: latestPeakDate,
    underwater_days: underwaterDays,
  };
}

function monthlyReturns(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (!row.date || row.daily_return == null || !Number.isFinite(Number(row.daily_return))) continue;
    const month = String(row.date).slice(0, 7);
    const current = groups.get(month) || [];
    current.push(Number(row.daily_return));
    groups.set(month, current);
  }
  return [...groups.entries()]
    .map(([month, values]) => ({
      month,
      observations: values.length,
      return_value: values.reduce((factor, value) => factor * (1 + value), 1) - 1,
    }))
    .sort((a, b) => b.month.localeCompare(a.month))
    .slice(0, 12);
}

export default function PerformanceHistoryPanel({ performance = {}, locale = 'en' }) {
  const text = (en, vi) => chooseText(locale, en, vi);
  const rows = useMemo(() => [...(performance.series || [])].sort((a, b) => String(a.date || '').localeCompare(String(b.date || ''))), [performance.series]);
  const validReturns = rows.filter(row => row.daily_return != null && Number.isFinite(Number(row.daily_return)));
  const first = rows[0]?.date || performance.first_date || null;
  const last = rows[rows.length - 1]?.date || performance.latest_date || null;
  const spanDays = calendarDays(first, last);
  const drawdown = drawdownEpisode(rows);
  const months = monthlyReturns(rows);

  const best = validReturns.length ? validReturns.reduce((a, b) => Number(a.daily_return) >= Number(b.daily_return) ? a : b) : null;
  const worst = validReturns.length ? validReturns.reduce((a, b) => Number(a.daily_return) <= Number(b.daily_return) ? a : b) : null;
  const stage = rows.length >= 252 ? 'MATURE_1Y' : rows.length >= 63 ? 'PARTIAL_3M_PLUS' : rows.length >= 20 ? 'BASIC_READY' : rows.length > 1 ? 'BUILDING' : 'STARTING';

  const windows = [
    ['5D', 5], ['21D', 21], ['63D', 63], ['126D', 126], ['252D', 252],
  ].map(([label, count]) => ({ label, count, value: chainReturn(rows, count) }));
  const vols = [
    ['20D', 20], ['63D', 63], ['252D', 252],
  ].map(([label, count]) => ({ label, value: annualizedVol(rows, count) }));

  if (!rows.length) return null;

  return <section className="card performance-history-depth" data-testid="performance-history-depth">
    <div className="section-head">
      <div>
        <div className="eyebrow">{text('Tracked evidence', 'Bằng chứng đã theo dõi')}</div>
        <h2>{text('Performance history detail', 'Chi tiết lịch sử hiệu suất')}</h2>
        <p className="muted">{text('Derived only from official daily snapshots already stored by QPort. No benchmark or synthetic history is invented.', 'Chỉ derive từ official daily snapshots QPort đã lưu. Không tự tạo benchmark hay lịch sử giả.')}</p>
      </div>
      <span className={`status-pill ${rows.length >= 20 ? 'status-valid' : 'status-partial'}`}>{stage}</span>
    </div>

    <div className="performance-history-grid">
      <div className="assessment-depth-block">
        <h4>{text('Trailing TWR windows', 'TWR theo cửa sổ')}</h4>
        {windows.map(item => <div className="diag-row" key={item.label}><span>{item.label}</span><b>{pct(item.value)}</b></div>)}
        <p className="muted">{text('A window stays blank until that many official daily return observations exist.', 'Cửa sổ để trống cho đến khi đủ số quan sát daily return chính thức tương ứng.')}</p>
      </div>

      <div className="assessment-depth-block">
        <h4>{text('Realized volatility of tracked returns', 'Volatility thực tế của return đã theo dõi')}</h4>
        {vols.map(item => <div className="diag-row" key={item.label}><span>{item.label}</span><b>{pct(item.value)}</b></div>)}
        <div className="diag-row"><span>{text('Return observations', 'Quan sát return')}</span><b>{validReturns.length}</b></div>
        <div className="diag-row"><span>{text('Calendar span', 'Khoảng thời gian')}</span><b>{spanDays == null ? '-' : `${spanDays} ${text('days', 'ngày')}`}</b></div>
      </div>

      <div className="assessment-depth-block">
        <h4>{text('Drawdown anatomy', 'Cấu trúc drawdown')}</h4>
        <div className="diag-row"><span>{text('Peak before max drawdown', 'Đỉnh trước max drawdown')}</span><b>{drawdown?.peak_date || '-'}</b></div>
        <div className="diag-row"><span>{text('Trough', 'Đáy')}</span><b>{drawdown?.trough_date || '-'}</b></div>
        <div className="diag-row"><span>{text('Maximum drawdown', 'Drawdown lớn nhất')}</span><b>{pct(drawdown?.max_drawdown)}</b></div>
        <div className="diag-row"><span>{text('Recovery date', 'Ngày hồi phục')}</span><b>{drawdown?.recovery_date || text('Not recovered / not applicable', 'Chưa hồi phục / không áp dụng')}</b></div>
        <div className="diag-row"><span>{text('Current underwater duration', 'Số ngày đang dưới đỉnh')}</span><b>{drawdown?.underwater_days == null ? '-' : `${drawdown.underwater_days} ${text('days', 'ngày')}`}</b></div>
      </div>

      <div className="assessment-depth-block">
        <h4>{text('Extreme tracked days', 'Các ngày cực trị đã theo dõi')}</h4>
        <div className="diag-row"><span>{text('Best day', 'Ngày tốt nhất')}</span><b>{best ? `${best.date} · ${pct(best.daily_return)}` : '-'}</b></div>
        <div className="diag-row"><span>{text('Worst day', 'Ngày xấu nhất')}</span><b>{worst ? `${worst.date} · ${pct(worst.daily_return)}` : '-'}</b></div>
        <div className="diag-row"><span>{text('Positive-day ratio', 'Tỷ lệ ngày tăng')}</span><b>{pct(performance.positive_day_ratio)}</b></div>
        <div className="diag-row"><span>{text('History status', 'Trạng thái lịch sử')}</span><b>{performance.history_status || '-'}</b></div>
        <div className="diag-row"><span>{text('Range', 'Khoảng')}</span><b>{first || '-'} → {last || '-'}</b></div>
      </div>
    </div>

    {months.length > 0 && <div className="performance-monthly-block">
      <div className="section-head compact-section-head"><div><h3>{text('Recent monthly TWR', 'TWR theo tháng gần đây')}</h3><p className="muted">{text('Chain-linked from official daily returns inside each calendar month.', 'Chain-link từ official daily return trong từng tháng dương lịch.')}</p></div></div>
      <div className="table-scroll">
        <table className="ranking performance-monthly-table">
          <thead><tr><th>{text('Month', 'Tháng')}</th><th className="num">{text('TWR', 'TWR')}</th><th className="num">{text('Daily observations', 'Quan sát ngày')}</th></tr></thead>
          <tbody>{months.map(row => <tr key={row.month}><td><b>{row.month}</b></td><td className={`num ${Number(row.return_value) >= 0 ? 'pos' : 'neg'}`}>{pct(row.return_value)}</td><td className="num">{row.observations}</td></tr>)}</tbody>
        </table>
      </div>
    </div>}
  </section>;
}
