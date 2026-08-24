import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { getLatestDividend, syncPortfolio } from '../lib/api.js';

function pct(value, digits = 2) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${(Number(value) * 100).toFixed(digits)}%`;
}

function money(value, locale = 'vi') {
  return value == null || !Number.isFinite(Number(value)) ? '-' : `${formatMoney(value, false, locale)} VND`;
}

function Metric({ label, value, note }) {
  return <div className="metric-card">
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    {note && <div className="metric-note">{note}</div>}
  </div>;
}

function latestEventDate(result) {
  const latest = result?.latest || result?.latest_components?.[0] || null;
  return result?.latest_event_date || latest?.effective_event_date || latest?.record_date || latest?.ex_date || latest?.announcement_date || latest?.payment_date || '-';
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

  const visiblePositions = useMemo(() => {
    const q = query.trim().toUpperCase();
    return q ? positions.filter(row => String(row.symbol || '').toUpperCase().includes(q)) : positions;
  }, [positions, query]);

  const attentionItems = useMemo(() => {
    const items = [];
    const warnings = (health.flags || []).filter(flag => flag.level === 'WARNING');
    for (const flag of warnings.slice(0, 2)) items.push(flag.message);
    if (!warnings.length && risk.max_equity_weight != null && Number(risk.max_equity_weight) >= 0.40) {
      items.push(`Một mã đang chiếm ${pct(risk.max_equity_weight)} phần cổ phiếu của danh mục. Hãy kiểm tra lại mức tập trung này có còn phù hợp với kế hoạch đầu tư hay không.`);
    }
    if (market.status && !['VALID', 'READY', 'OK'].includes(String(market.status).toUpperCase())) {
      items.push('Dữ liệu giá hiện chưa đầy đủ hoặc chưa cập nhật đồng bộ. Các giá trị định giá có thể chưa phản ánh phiên gần nhất.');
    }
    return items;
  }, [health, risk.max_equity_weight, market.status]);

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
          return { symbol, result: await getLatestDividend(symbol, { refresh }), error: null };
        } catch (error) {
          return { symbol, result: null, error: error.message };
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

  const totalPnl = Number(portfolio.total_pnl || 0);
  const totalPositive = totalPnl >= 0;

  return <div className="page">
    <AppNav active="portfolio" locale={locale} />

    <header className="portfolio-hero">
      <div className="hero-primary">
        <div className="eyebrow">Tổng giá trị danh mục</div>
        <h1>{money(portfolio.nav || 0, locale)}</h1>
        <div className={`hero-return ${totalPositive ? 'pos' : 'neg'}`}>
          <strong>{totalPositive ? '+' : ''}{money(totalPnl, locale)}</strong>
          <span>{pct(portfolio.accounting_return)} tổng lãi/lỗ</span>
        </div>
        <div className="hero-meta">
          <span>{positions.length} mã đang nắm giữ</span>
          {market.market_date && <span>Giá cập nhật đến {market.market_date}</span>}
        </div>
      </div>
      <div className="hero-actions">
        <a className="btn-primary" href="/transactions">+ Thêm giao dịch</a>
        <button className="btn-secondary" type="button" onClick={sync} disabled={syncing}>{syncing ? 'Đang cập nhật…' : '↻ Cập nhật dữ liệu'}</button>
      </div>
    </header>

    {message && <div className="run-message banner-message">{message}</div>}

    <div className="metric-grid portfolio-metrics overview-metrics">
      <Metric label="Giá trị cổ phiếu" value={money(portfolio.equity_value || 0, locale)} note={`${positions.length} mã`} />
      <Metric label="Tiền mặt" value={money(portfolio.cash || 0, locale)} note={portfolio.nav ? `${pct((portfolio.cash || 0) / portfolio.nav)} danh mục` : undefined} />
      <Metric label="Tổng giá vốn" value={money(portfolio.cost_value || 0, locale)} note="Giá vốn đã ghi nhận" />
      <Metric label="Cổ tức đã ghi nhận" value={money(performance.dividend_income || 0, locale)} note="Cổ tức tiền mặt trước thuế" />
    </div>

    {attentionItems.length > 0 && <section className="card portfolio-assessment-card">
      <div className="section-head">
        <div><div className="eyebrow">Cần chú ý</div><h2>Điểm đáng xem trong danh mục</h2></div>
        <a className="text-link" href="/risk">Xem phân tích chi tiết →</a>
      </div>
      <div className="assessment-flags">
        {attentionItems.map((item, index) => <div className="assessment-flag warn-flag" key={index}><span>!</span><div><p>{item}</p></div></div>)}
      </div>
    </section>}

    <section className="card holdings-card">
      <div className="section-head holdings-head">
        <div>
          <div className="eyebrow">Khoản đầu tư</div>
          <h2>Cổ phiếu đang nắm giữ</h2>
          <p className="muted">Giá trị và lãi/lỗ được tính từ số lượng, giá vốn đã ghi nhận và giá thị trường gần nhất.</p>
        </div>
        {positions.length > 6 && <input className="search-input" value={query} onChange={event => setQuery(event.target.value)} placeholder="Tìm mã…" aria-label="Tìm mã cổ phiếu" />}
      </div>

      {positions.length === 0 ? <div className="empty-state">
        <h3>Chưa có cổ phiếu trong danh mục</h3>
        <p>Hãy nhập danh mục hiện có hoặc ghi giao dịch mua đầu tiên.</p>
        <a className="btn-primary" href="/transactions">Nhập danh mục ban đầu</a>
      </div> : <div className="table-scroll">
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
            const pnl = Number(row.unrealized_pnl || 0);
            const symbol = String(row.symbol || '').toUpperCase();
            return <tr key={symbol}>
              <td><b>{symbol}</b>{row.price_date && <div className="muted">{row.price_date}</div>}</td>
              <td className="num">{formatShares(row.shares, locale)}</td>
              <td className="num">{money(row.average_cost, locale)}</td>
              <td className="num">{money(row.price, locale)}</td>
              <td className="num emphasis">{money(row.market_value, locale)}</td>
              <td className={`num ${pnl >= 0 ? 'pos' : 'neg'}`}>{money(row.unrealized_pnl, locale)}</td>
              <td className={`num ${Number(row.unrealized_return || 0) >= 0 ? 'pos' : 'neg'}`}>{pct(row.unrealized_return)}</td>
              <td className="num">{formatWeight(row.weight)}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>}
    </section>

    {positions.length > 0 && <section className="card dividend-card">
      <div className="section-head">
        <div>
          <div className="eyebrow">Thu nhập & quyền</div>
          <h2>Cổ tức và sự kiện gần nhất</h2>
          <p className="muted">Thông tin công bố gần nhất của từng mã. Cổ tức thực nhận chỉ được tính vào danh mục sau khi hệ thống ghi nhận giao dịch tương ứng.</p>
        </div>
        <button className="btn-secondary" type="button" onClick={() => loadDividends(true)} disabled={dividendLoading}>{dividendLoading ? 'Đang cập nhật…' : 'Cập nhật cổ tức'}</button>
      </div>

      {dividends.length === 0 && dividendLoading ? <div className="loading-line"><span className="spinner" />Đang tải thông tin cổ tức…</div> : <div className="dividend-symbol-list">
        {dividends.filter(row => row.result?.found).map(row => {
          const result = row.result || {};
          const components = result.latest_components?.length ? result.latest_components : (result.latest ? [result.latest] : []);
          const cash = components.find(item => item.dividend_type === 'CASH_DIVIDEND');
          const stock = components.find(item => item.dividend_type === 'STOCK_DIVIDEND');
          const first = components[0] || {};
          return <details className="dividend-symbol-node" key={row.symbol}>
            <summary>
              <div className="dividend-node-symbol"><b>{row.symbol}</b><span className="muted">Sự kiện gần nhất: {latestEventDate(result)}</span></div>
              <div className="dividend-node-stat"><span>Tiền/CP</span><b>{cash?.cash_per_share != null ? money(cash.cash_per_share, locale) : '-'}</b></div>
              <div className="dividend-node-stat"><span>Cổ phiếu</span><b>{stock?.stock_ratio_percent != null ? `${Number(stock.stock_ratio_percent).toFixed(2)}%` : '-'}</b></div>
              <div className="dividend-node-stat"><span>Ngày thanh toán</span><b>{first.payment_date || '-'}</b></div>
            </summary>
            <div className="dividend-history-body">
              <p className="muted">Ngày GDKHQ: <b>{first.ex_date || '-'}</b> · Ngày đăng ký cuối cùng: <b>{first.record_date || '-'}</b> · Nguồn: <b>{result.canonical_source || first.source || '-'}</b></p>
            </div>
          </details>;
        })}
        {!dividendLoading && dividends.length > 0 && dividends.every(row => !row.result?.found) && <div className="empty-state compact-empty">Chưa tìm thấy lịch sử cổ tức cho các mã hiện tại.</div>}
      </div>}
    </section>}
  </div>;
}
