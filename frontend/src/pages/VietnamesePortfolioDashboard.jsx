import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { getDividendHistory, syncPortfolio } from '../lib/api.js';

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

function Metric({ label, value, note, tone = '' }) {
  return <div className={`metric-card overview-metric ${tone}`}>
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    {note && <div className="metric-note">{note}</div>}
  </div>;
}

function currentVietnamYear() {
  return Number(new Intl.DateTimeFormat('en', { timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric' }).format(new Date()));
}

function eventDate(event) {
  return event?.effective_event_date || event?.record_date || event?.ex_date || event?.announcement_date || event?.payment_date || null;
}

function eventYear(event) {
  const dateValue = eventDate(event);
  if (!dateValue) return null;
  const year = Number(String(dateValue).slice(0, 4));
  return Number.isInteger(year) && year >= 1900 ? year : null;
}

function HoldingMobileCard({ row, locale }) {
  const hasPnl = row.unrealized_pnl != null && Number.isFinite(Number(row.unrealized_pnl));
  const pnl = hasPnl ? Number(row.unrealized_pnl) : null;
  const positive = pnl == null ? null : pnl >= 0;
  const symbol = String(row.symbol || '').toUpperCase();
  const sharesText = formatShares(row.shares, locale);
  return <article className="holding-mobile-card">
    <div className="holding-mobile-head">
      <div className="holding-mobile-symbol">
        <strong>{symbol}</strong>
        <span>{row.price_date ? `Giá ngày ${row.price_date}` : 'Giá chưa cập nhật'}</span>
      </div>
      <div className="holding-mobile-value">
        <strong>{money(row.market_value, locale)}</strong>
        <span className={positive == null ? '' : positive ? 'pos' : 'neg'}>
          {signedMoney(row.unrealized_pnl, locale)} · {pct(row.unrealized_return)}
        </span>
      </div>
    </div>
    <div className="holding-mobile-facts">
      <div><span>Số lượng</span><b>{sharesText === '-' ? '-' : `${sharesText} CP`}</b></div>
      <div><span>Giá vốn</span><b>{money(row.average_cost, locale)}</b></div>
      <div><span>Giá hiện tại</span><b>{money(row.price, locale)}</b></div>
      <div><span>Tỷ trọng</span><b>{formatWeight(row.weight)}</b></div>
    </div>
  </article>;
}

export default function VietnamesePortfolioDashboard({ dashboard: initialDashboard = {}, locale = 'vi' }) {
  const [dashboard] = useState(initialDashboard);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const [dividends, setDividends] = useState([]);
  const [dividendLoading, setDividendLoading] = useState(false);

  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const performance = dashboard.performance_summary || {};
  const market = dashboard.market_data || {};
  const risk = dashboard.risk || {};
  const health = dashboard.health || {};
  const currentYear = currentVietnamYear();

  const visiblePositions = useMemo(() => {
    const q = query.trim().toUpperCase();
    return q ? positions.filter(row => String(row.symbol || '').toUpperCase().includes(q)) : positions;
  }, [positions, query]);

  const attentionItems = useMemo(() => {
    const items = [];
    const warnings = (health.flags || []).filter(flag => flag.level === 'WARNING');
    for (const flag of warnings.slice(0, 2)) items.push(flag.message);
    if (!warnings.length && risk.max_equity_weight != null && Number(risk.max_equity_weight) >= 0.40) {
      items.push(`Một mã đang chiếm ${pct(risk.max_equity_weight)} phần cổ phiếu của danh mục. Hãy kiểm tra mức tập trung này có còn phù hợp với kế hoạch đầu tư hay không.`);
    }
    if (market.status && !['VALID', 'READY', 'OK'].includes(String(market.status).toUpperCase())) {
      items.push('Dữ liệu giá hiện chưa đầy đủ hoặc chưa đồng bộ. Giá trị danh mục có thể chưa phản ánh phiên gần nhất.');
    }
    return items;
  }, [health, risk.max_equity_weight, market.status]);

  const latestDividendWindow = useMemo(() => {
    const allEvents = [];
    let latestYear = null;

    for (const item of dividends) {
      for (const event of item.result?.events || []) {
        const year = eventYear(event);
        if (year == null || year > currentYear) continue;
        const dateValue = eventDate(event);
        allEvents.push({ symbol: item.symbol, ...event, display_date: dateValue, display_year: year });
        if (latestYear == null || year > latestYear) latestYear = year;
      }
    }

    const events = latestYear == null
      ? []
      : allEvents
          .filter(event => event.display_year === latestYear)
          .sort((a, b) => String(b.display_date || '').localeCompare(String(a.display_date || '')) || String(a.symbol).localeCompare(String(b.symbol)));

    return { year: latestYear, events };
  }, [dividends, currentYear]);

  const dividendErrors = useMemo(() => dividends.filter(row => row.error), [dividends]);

  async function sync() {
    setSyncing(true);
    setMessage('');
    try {
      await syncPortfolio();
      window.location.reload();
    } catch (error) {
      setMessage(`Không thể cập nhật dữ liệu: ${error.message}`);
      setSyncing(false);
    }
  }

  async function loadDividends(refresh = false) {
    const symbols = positions.map(row => String(row.symbol || '').toUpperCase()).filter(Boolean);
    if (!symbols.length) return;
    setDividendLoading(true);
    const rows = [];
    for (let i = 0; i < symbols.length; i += 4) {
      const batch = symbols.slice(i, i + 4);
      const batchRows = await Promise.all(batch.map(async symbol => {
        try {
          return { symbol, result: await getDividendHistory(symbol, { refresh }), error: null };
        } catch (error) {
          return { symbol, result: null, error: error.message || 'Không thể tải dữ liệu cổ tức.' };
        }
      }));
      rows.push(...batchRows);
      setDividends([...rows]);
    }
    setDividendLoading(false);
  }

  useEffect(() => {
    if (positions.length) loadDividends(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positions.map(row => row.symbol).join('|')]);

  const hasTotalPnl = portfolio.total_pnl != null && Number.isFinite(Number(portfolio.total_pnl));
  const totalPnl = hasTotalPnl ? Number(portfolio.total_pnl) : null;
  const totalPositive = totalPnl == null ? null : totalPnl >= 0;
  const dividendIncome = performance.net_dividend_income ?? performance.dividend_income ?? null;
  const hasCashRatio = portfolio.cash != null && portfolio.nav != null && Number(portfolio.nav) !== 0;

  return <div className="page investor-dashboard">
    <AppNav active="portfolio" locale={locale} />

    <header className="portfolio-hero investor-hero">
      <div className="hero-primary">
        <div className="eyebrow">Tổng tài sản</div>
        <h1>{money(portfolio.nav, locale)}</h1>
        <div className={`hero-return ${totalPositive == null ? '' : totalPositive ? 'pos' : 'neg'}`}>
          <strong>{signedMoney(totalPnl, locale)}</strong>
          <span>{pct(portfolio.accounting_return)} từ giá vốn và dòng tiền đã ghi nhận</span>
        </div>
        <div className="hero-meta">
          <span>{positions.length} mã cổ phiếu</span>
          <span>{market.market_date ? `Dữ liệu giá đến ${market.market_date}` : 'Dữ liệu giá: -'}</span>
        </div>
      </div>
      <div className="hero-actions">
        <a className="btn-primary" href="/transactions">+ Thêm giao dịch</a>
        <button className="btn-secondary" type="button" onClick={sync} disabled={syncing}>{syncing ? 'Đang cập nhật…' : '↻ Cập nhật dữ liệu'}</button>
      </div>
    </header>

    {message && <div className="run-message banner-message">{message}</div>}

    <div className="metric-grid portfolio-metrics overview-metrics investor-overview">
      <Metric label="Cổ phiếu" value={money(portfolio.equity_value, locale)} note={`${positions.length} mã đang nắm giữ`} />
      <Metric label="Tiền mặt" value={money(portfolio.cash, locale)} note={hasCashRatio ? `${pct(Number(portfolio.cash) / Number(portfolio.nav))} tổng tài sản` : undefined} />
      <Metric label="Tổng giá vốn" value={money(portfolio.cost_value, locale)} note="Giá vốn các cổ phiếu hiện có" />
      <Metric label="Cổ tức thực nhận" value={money(dividendIncome, locale)} note="Tiền mặt sau thuế đã ghi nhận" tone="income-metric" />
    </div>

    {attentionItems.length > 0 && <section className="card portfolio-assessment-card investor-attention-card">
      <div className="section-head">
        <div><div className="eyebrow">Cần chú ý</div><h2>Danh mục có điểm cần xem lại</h2></div>
        <a className="text-link" href="/risk">Xem phân tích →</a>
      </div>
      <div className="assessment-flags">
        {attentionItems.map((item, index) => <div className="assessment-flag warn-flag" key={index}><span aria-hidden="true">!</span><div><p>{item}</p></div></div>)}
      </div>
    </section>}

    <section className="card holdings-card investor-holdings-card">
      <div className="section-head holdings-head">
        <div>
          <div className="eyebrow">Danh mục hiện tại</div>
          <h2>Cổ phiếu đang nắm giữ</h2>
          <p className="muted">Theo dõi số lượng, giá vốn, giá hiện tại và lãi/lỗ của từng mã.</p>
        </div>
        {positions.length > 6 && <input className="search-input" value={query} onChange={event => setQuery(event.target.value)} placeholder="Tìm mã cổ phiếu…" aria-label="Tìm mã cổ phiếu" />}
      </div>

      {positions.length === 0 ? <div className="empty-state">
        <h3>Chưa có cổ phiếu trong danh mục</h3>
        <p>Hãy nhập danh mục hiện có hoặc ghi giao dịch mua đầu tiên.</p>
        <a className="btn-primary" href="/transactions">Nhập danh mục ban đầu</a>
      </div> : visiblePositions.length === 0 ? <div className="empty-state compact-empty">Không tìm thấy mã phù hợp.</div> : <>
        <div className="holding-mobile-list">
          {visiblePositions.map(row => <HoldingMobileCard key={String(row.symbol || '').toUpperCase()} row={row} locale={locale} />)}
        </div>
        <div className="table-scroll portfolio-table-desktop">
          <table className="ranking portfolio-table portfolio-table-core">
            <thead><tr>
              <th>Mã</th>
              <th className="num">SL</th>
              <th className="num">Giá vốn</th>
              <th className="num">Giá hiện tại</th>
              <th className="num">Giá trị</th>
              <th className="num">Lãi/lỗ tạm tính</th>
              <th className="num">% Lãi/lỗ</th>
              <th className="num">Tỷ trọng</th>
            </tr></thead>
            <tbody>{visiblePositions.map(row => {
              const hasPnl = row.unrealized_pnl != null && Number.isFinite(Number(row.unrealized_pnl));
              const pnl = hasPnl ? Number(row.unrealized_pnl) : null;
              const hasReturn = row.unrealized_return != null && Number.isFinite(Number(row.unrealized_return));
              const symbol = String(row.symbol || '').toUpperCase();
              return <tr key={symbol}>
                <td><b>{symbol}</b>{row.price_date && <div className="muted">{row.price_date}</div>}</td>
                <td className="num">{formatShares(row.shares, locale)}</td>
                <td className="num">{money(row.average_cost, locale)}</td>
                <td className="num">{money(row.price, locale)}</td>
                <td className="num emphasis">{money(row.market_value, locale)}</td>
                <td className={`num ${pnl == null ? '' : pnl >= 0 ? 'pos' : 'neg'}`}>{signedMoney(row.unrealized_pnl, locale)}</td>
                <td className={`num ${!hasReturn ? '' : Number(row.unrealized_return) >= 0 ? 'pos' : 'neg'}`}>{pct(row.unrealized_return)}</td>
                <td className="num">{formatWeight(row.weight)}</td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      </>}
    </section>

    {positions.length > 0 && <section className="card dividend-card investor-dividend-card">
      <div className="section-head">
        <div>
          <div className="eyebrow">Cổ tức & quyền</div>
          <h2>{latestDividendWindow.year != null ? `Sự kiện cổ tức năm ${latestDividendWindow.year}` : 'Sự kiện cổ tức gần nhất'}</h2>
          <p className="muted">
            {latestDividendWindow.year != null
              ? `Hiển thị tất cả sự kiện cổ tức của năm gần nhất có dữ liệu (${latestDividendWindow.year}) cho các mã đang nắm giữ.`
              : 'QPort sẽ tự chọn năm gần nhất có dữ liệu cổ tức của các mã đang nắm giữ.'}
          </p>
        </div>
        <div className="section-actions">
          <a className="text-link" href="/dividends">Xem toàn bộ lịch sử →</a>
          <button className="btn-secondary" type="button" onClick={() => loadDividends(true)} disabled={dividendLoading}>{dividendLoading ? 'Đang cập nhật…' : 'Cập nhật cổ tức'}</button>
        </div>
      </div>

      {dividendErrors.length > 0 && <div className="data-error-message" role="alert">
        Không thể tải dữ liệu cổ tức cho <b>{dividendErrors.map(row => row.symbol).join(', ')}</b>. Hãy thử cập nhật lại sau. Dữ liệu của các mã khác vẫn được giữ nguyên nếu tải thành công.
      </div>}

      {dividendLoading && dividends.length === 0 ? <div className="dividend-year-list is-loading">
        {positions.map(row => <div className="dividend-year-event" key={String(row.symbol || '').toUpperCase()}>
          <div><strong>{String(row.symbol || '').toUpperCase()}</strong><span>-</span></div>
          <div><span>Loại</span><b>-</b></div>
          <div><span>Giá trị</span><b>-</b></div>
          <div><span>Thanh toán</span><b>-</b></div>
        </div>)}
      </div> : latestDividendWindow.events.length > 0 ? <div className="dividend-year-list">
        {latestDividendWindow.events.map((event, index) => {
          const cash = event.dividend_type === 'CASH_DIVIDEND';
          return <div className="dividend-year-event" key={`${event.symbol}-${event.display_date}-${event.dividend_type}-${event.source_event_id || index}`}>
            <div><strong>{event.symbol}</strong><span>{event.display_date || '-'}</span></div>
            <div><span>Loại</span><b>{cash ? 'Tiền mặt' : 'Cổ phiếu'}</b></div>
            <div><span>{cash ? 'Tiền/CP' : 'Tỷ lệ'}</span><b>{cash ? money(event.cash_per_share, locale) : event.stock_ratio_percent != null ? `${Number(event.stock_ratio_percent).toFixed(2)}%` : '-'}</b></div>
            <div><span>Thanh toán</span><b>{event.payment_date || '-'}</b></div>
          </div>;
        })}
      </div> : !dividendLoading && <div className="empty-state compact-empty">Chưa tìm thấy sự kiện cổ tức nào đến năm {currentYear} cho các mã hiện đang nắm giữ.</div>}
    </section>}
  </div>;
}
