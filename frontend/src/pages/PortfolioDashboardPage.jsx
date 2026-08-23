import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { getLatestDividend, getPortfolioOperations, syncPortfolio } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) {
  return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`;
}

function latestComponents(result) {
  return result?.latest_components?.length ? result.latest_components : (result?.latest ? [result.latest] : []);
}

function eventDate(event) {
  return event?.effective_event_date || event?.record_date || event?.ex_date || event?.announcement_date || event?.payment_date || '-';
}

function groupBrokerSources(lots, position) {
  const groups = new Map();
  const symbol = String(position?.symbol || '').toUpperCase();
  for (const lot of lots || []) {
    if (String(lot?.symbol || '').toUpperCase() !== symbol) continue;
    const quantity = Number(lot?.remaining_quantity || 0);
    if (!(quantity > 0)) continue;
    const broker = String(lot?.broker_code || 'UNASSIGNED').toUpperCase();
    const account = String(lot?.account_id || 'PRIMARY').toUpperCase();
    const key = `${broker}::${account}`;
    const current = groups.get(key) || {
      broker,
      account,
      shares: 0,
      cost_value: 0,
      lot_count: 0,
    };
    current.shares += quantity;
    current.cost_value += Number(lot?.cost_basis || 0);
    current.lot_count += 1;
    groups.set(key, current);
  }

  const price = position?.price == null ? null : Number(position.price);
  const totalShares = Number(position?.shares || 0);
  return [...groups.values()]
    .map(source => {
      const marketValue = price == null ? null : source.shares * price;
      return {
        ...source,
        average_cost: source.shares > 0 ? source.cost_value / source.shares : 0,
        market_value: marketValue,
        unrealized_pnl: marketValue == null ? null : marketValue - source.cost_value,
        unrealized_return: marketValue != null && source.cost_value > 0 ? marketValue / source.cost_value - 1 : null,
        symbol_weight: totalShares > 0 ? source.shares / totalShares : 0,
      };
    })
    .sort((a, b) => b.shares - a.shares || a.broker.localeCompare(b.broker) || a.account.localeCompare(b.account));
}

function Metric({ label, value, note, tone = '' }) {
  return <div className={`metric-card ${tone}`}>
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    {note && <div className="metric-note">{note}</div>}
  </div>;
}

export default function PortfolioDashboardPage({ dashboard: initialDashboard, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null || !Number.isFinite(Number(v)) ? '-' : `${formatMoney(v, false, locale)} VND`);
  const shares = (v) => formatShares(v, locale);
  const [dashboard] = useState(initialDashboard || {});
  const [syncing, setSyncing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState('');
  const [positionQuery, setPositionQuery] = useState('');
  const [expandedHoldings, setExpandedHoldings] = useState({});
  const [brokerLots, setBrokerLots] = useState(null);
  const [brokerLotsLoading, setBrokerLotsLoading] = useState(false);
  const [brokerLotsError, setBrokerLotsError] = useState('');
  const [dividendLoading, setDividendLoading] = useState(false);
  const [dividendRows, setDividendRows] = useState([]);

  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const perf = dashboard.performance_summary || {};
  const market = dashboard.market_data || {};
  const risk = dashboard.risk || {};
  const health = dashboard.health || {};
  const healthFlags = health.flags || [];
  const warningFlags = healthFlags.filter(flag => flag.level === 'WARNING');
  const infoFlags = healthFlags.filter(flag => flag.level !== 'WARNING');
  const riskCoverage = health.risk_coverage ?? risk.quality?.coverage_weight;
  const positionSymbolsKey = positions.map(p => p.symbol).sort().join('|');

  const visiblePositions = useMemo(() => {
    const q = positionQuery.trim().toUpperCase();
    return q ? positions.filter(p => String(p.symbol || '').includes(q)) : positions;
  }, [positions, positionQuery]);

  async function sync() {
    setSyncing(true);
    setMessage('');
    try {
      const result = await syncPortfolio();
      setMessage(result.message || t('portfolio.sync_done'));
      window.location.reload();
    } catch (err) {
      setMessage(t('portfolio.sync_failed', { error: err.message }));
      setSyncing(false);
    }
  }

  async function exportAI() {
    setExporting(true);
    setMessage('');
    try {
      const filename = await downloadAIExport();
      setMessage(text(`Exported ${filename}.`, `Đã xuất ${filename}.`));
    } catch (err) {
      setMessage(text(`AI export failed: ${err.message}`, `Xuất dữ liệu cho AI thất bại: ${err.message}`));
    } finally {
      setExporting(false);
    }
  }

  async function loadBrokerLots() {
    if (brokerLots !== null || brokerLotsLoading) return;
    setBrokerLotsLoading(true);
    setBrokerLotsError('');
    try {
      const operations = await getPortfolioOperations();
      setBrokerLots(Array.isArray(operations?.tax_lots) ? operations.tax_lots : []);
    } catch (err) {
      setBrokerLotsError(err.message);
      setBrokerLots([]);
    } finally {
      setBrokerLotsLoading(false);
    }
  }

  async function toggleHolding(symbol) {
    const opening = !expandedHoldings[symbol];
    setExpandedHoldings(current => ({ ...current, [symbol]: opening }));
    if (opening) await loadBrokerLots();
  }

  async function loadPositionDividends(refresh = false) {
    const symbols = [...new Set(positions.map(p => String(p.symbol || '').toUpperCase()).filter(Boolean))];
    if (!symbols.length) {
      setDividendRows([]);
      return;
    }

    setDividendLoading(true);
    const collected = [];
    for (let i = 0; i < symbols.length; i += 4) {
      const batch = symbols.slice(i, i + 4);
      const rows = await Promise.all(batch.map(async symbol => {
        try {
          return { symbol, result: await getLatestDividend(symbol, { refresh }), error: null };
        } catch (err) {
          return { symbol, result: null, error: err.message };
        }
      }));
      collected.push(...rows);
      setDividendRows([...collected]);
    }
    setDividendLoading(false);
  }

  useEffect(() => {
    if (positionSymbolsKey) loadPositionDividends(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positionSymbolsKey]);

  const totalPnlPositive = Number(portfolio.total_pnl || 0) >= 0;
  const dividendFound = dividendRows.filter(row => row.result?.found).length;
  const assessmentStatus = health.status || (positions.length ? 'UNKNOWN' : 'NO_HOLDINGS');
  const assessmentTone = assessmentStatus === 'HEALTHY' ? 'status-valid' : assessmentStatus === 'ATTENTION' ? 'status-partial' : 'status-missing';
  const assessmentSummary = warningFlags.length
    ? text(
        `${warningFlags.length} portfolio risk signal${warningFlags.length === 1 ? '' : 's'} need attention. These are diagnostics, not automatic trade instructions.`,
        `${warningFlags.length} tín hiệu rủi ro của toàn danh mục cần chú ý. Đây là chẩn đoán thông tin, không phải lệnh giao dịch tự động.`
      )
    : text(
        'No major portfolio-level warning is currently triggered by concentration, correlation, drawdown, volatility or data coverage rules.',
        'Hiện chưa có cảnh báo lớn ở cấp toàn danh mục theo các tiêu chí tập trung, tương quan, drawdown, biến động hoặc độ phủ dữ liệu.'
      );

  return (
    <div className="page">
      <AppNav active="portfolio" locale={locale} />

      <header className="portfolio-hero">
        <div className="hero-primary">
          <div className="eyebrow">{text('Total portfolio', 'Tổng danh mục')}</div>
          <h1>{money(portfolio.nav || 0)}</h1>
          <div className={`hero-return ${totalPnlPositive ? 'pos' : 'neg'}`}>
            <strong>{totalPnlPositive ? '+' : ''}{money(portfolio.total_pnl)}</strong>
            <span>{pct(portfolio.accounting_return)} {text('return', 'lợi nhuận')}</span>
          </div>
          <div className="hero-meta">
            <span><i className={`mini-dot status-${String(market.status || 'missing').toLowerCase()}`} />{text('Market data', 'Dữ liệu thị trường')}: {market.market_date || '-'}</span>
            <span>{positions.length} {text(positions.length === 1 ? 'holding' : 'holdings', 'mã đang nắm giữ')}</span>
          </div>
        </div>
        <div className="hero-actions">
          <button className="btn-primary" type="button" onClick={sync} disabled={syncing}>
            {syncing ? t('portfolio.syncing') : text('Refresh portfolio', 'Cập nhật danh mục')}
          </button>
          <a className="btn-secondary" href="/transactions">{text('+ Add transaction', '+ Thêm giao dịch')}</a>
          <button className="btn-ghost" type="button" onClick={exportAI} disabled={exporting}>
            {exporting ? text('Exporting…', 'Đang xuất…') : text('Export for AI', 'Xuất cho AI')}
          </button>
        </div>
      </header>

      {message && <div className="run-message banner-message">{message}</div>}

      <div className="metric-grid portfolio-metrics overview-metrics">
        <Metric
          label={t('portfolio.equity')}
          value={money(portfolio.equity_value || 0)}
          note={t('portfolio.holdings_count', { count: positions.length, suffix: positions.length === 1 ? '' : 's' })}
        />
        <Metric
          label={t('portfolio.cash')}
          value={money(portfolio.cash || 0)}
          note={portfolio.nav ? t('portfolio.of_nav', { value: pct((portfolio.cash || 0) / portfolio.nav) }) : '—'}
        />
        <Metric
          label={text('Cost basis', 'Tổng giá vốn')}
          value={money(portfolio.cost_value || 0)}
          note={text('Recorded position cost', 'Giá vốn vị thế đã ghi nhận')}
        />
        <Metric
          label={text('Dividend income', 'Thu nhập cổ tức')}
          value={money(perf.dividend_income || 0)}
          note={text('Cash dividends recorded in the ledger', 'Cổ tức tiền mặt đã ghi vào sổ')}
        />
      </div>

      <section className="card portfolio-assessment-card">
        <div className="section-head assessment-head">
          <div>
            <div className="eyebrow">{text('Portfolio intelligence', 'Đánh giá danh mục')}</div>
            <h2>{text('Portfolio assessment', 'Đánh giá toàn danh mục')}</h2>
            <p className="muted">{text('QPort evaluates the current portfolio from stored market history, position weights, correlations and tracked performance. It never changes holdings automatically.', 'QPort đánh giá danh mục hiện tại từ lịch sử thị trường đã lưu, tỷ trọng vị thế, tương quan và hiệu suất theo dõi. Hệ thống không tự động thay đổi vị thế.')}</p>
          </div>
          <div className="assessment-status-block">
            <span className={`status-pill ${assessmentTone}`}>{assessmentStatus}</span>
            <span className="muted">{risk.as_of || market.market_date || '-'}</span>
          </div>
        </div>

        <div className="assessment-copy">{assessmentSummary}</div>

        <div className="assessment-metrics">
          <div><span>{text('252D volatility', 'Biến động 252D')}</span><b>{pct(risk.volatility_252)}</b></div>
          <div><span>{text('Current drawdown', 'Drawdown hiện tại')}</span><b className={Number(perf.current_drawdown || 0) < 0 ? 'neg' : ''}>{pct(perf.current_drawdown)}</b></div>
          <div><span>{text('Effective positions', 'Số vị thế hiệu dụng')}</span><b>{risk.effective_positions == null ? '-' : Number(risk.effective_positions).toFixed(2)}</b></div>
          <div><span>{text('Risk coverage', 'Độ phủ dữ liệu rủi ro')}</span><b>{pct(riskCoverage)}</b></div>
          <div><span>{text('Largest risk contributor', 'Đóng góp rủi ro lớn nhất')}</span><b>{risk.largest_risk_symbol || '-'} {risk.largest_risk_contribution != null ? pct(risk.largest_risk_contribution) : ''}</b></div>
          <div><span>{text('Daily CVaR 95%', 'CVaR ngày 95%')}</span><b className={Number(risk.daily_cvar_95 || 0) < 0 ? 'neg' : ''}>{pct(risk.daily_cvar_95)}</b></div>
        </div>

        {(warningFlags.length > 0 || infoFlags.length > 0) && <div className="assessment-flags">
          {healthFlags.map(flag => (
            <div className={`assessment-flag ${flag.level === 'WARNING' ? 'warn-flag' : 'info-flag'}`} key={`${flag.code}-${flag.message}`}>
              <span>{flag.level === 'WARNING' ? '!' : 'i'}</span>
              <div><b>{flag.code}</b><p>{flag.message}</p></div>
            </div>
          ))}
        </div>}

        <div className="section-foot">
          <span className="muted">{text('Risk is informational only; no BUY/SELL action is generated from this assessment.', 'Rủi ro chỉ mang tính thông tin; đánh giá này không tạo lệnh BUY/SELL.')}</span>
          <a className="text-link" href="/risk">{text('Advanced risk details →', 'Chi tiết rủi ro nâng cao →')}</a>
        </div>
      </section>

      <section className="card holdings-card">
        <div className="section-head holdings-head">
          <div>
            <div className="eyebrow">{text('Investments', 'Khoản đầu tư')}</div>
            <h2>{t('portfolio.holdings')}</h2>
            <p className="muted">{text('Each ticker is consolidated across brokers. Expand a holding to see the current shares and cost basis by broker/account.', 'Mỗi mã được tổng hợp từ tất cả broker. Mở rộng một mã để xem số lượng và giá vốn hiện tại theo từng broker/account.')}</p>
          </div>
          <div className="table-tools">
            <input
              className="search-input"
              value={positionQuery}
              onChange={e => setPositionQuery(e.target.value)}
              placeholder={text('Search ticker…', 'Tìm mã…')}
              aria-label={text('Search holdings', 'Tìm mã đang nắm giữ')}
            />
            <span className={`status-pill status-${String(market.status || 'MISSING').toLowerCase()}`}>{status(market.status || 'MISSING')}</span>
          </div>
        </div>

        {positions.length === 0 ? (
          <div className="empty-state">
            <h3>{t('portfolio.no_holdings')}</h3>
            <p>{t('portfolio.no_holdings_note')}</p>
            <a className="btn-primary" href="/transactions">{t('portfolio.add_opening')}</a>
          </div>
        ) : visiblePositions.length === 0 ? (
          <div className="empty-state">{text('No holding matches that ticker.', 'Không có mã nào khớp tìm kiếm.')}</div>
        ) : (
          <div className="table-scroll">
            <table className="ranking portfolio-table portfolio-table-core holdings-expand-table">
              <thead><tr>
                <th>{t('portfolio.ticker')}</th>
                <th className="num">{t('portfolio.shares')}</th>
                <th className="num">{t('portfolio.avg_cost')}</th>
                <th className="num">{t('portfolio.price')}</th>
                <th className="num">{t('portfolio.market_value')}</th>
                <th className="num">{t('portfolio.unrealized_pl')}</th>
                <th className="num">{t('portfolio.return')}</th>
                <th className="num">{t('portfolio.weight')}</th>
              </tr></thead>
              <tbody>{visiblePositions.map(p => {
                const expanded = Boolean(expandedHoldings[p.symbol]);
                const sources = brokerLots === null ? [] : groupBrokerSources(brokerLots, p);
                return <React.Fragment key={p.symbol}>
                  <tr className={`holding-parent-row ${expanded ? 'is-expanded' : ''}`}>
                    <td className="symbols-cell">
                      <button
                        className="holding-expand-button"
                        type="button"
                        aria-expanded={expanded}
                        aria-controls={`holding-sources-${p.symbol}`}
                        onClick={() => toggleHolding(p.symbol)}
                      >
                        <span className="holding-expand-icon" aria-hidden="true">{expanded ? '−' : '+'}</span>
                        <span className="holding-symbol-copy">
                          <b>{p.symbol}</b>
                          <span className="muted">{p.price_date || '-'} · {p.price_source || '-'}</span>
                        </span>
                      </button>
                    </td>
                    <td className="num">{shares(p.shares)}</td>
                    <td className="num">{money(p.average_cost)}</td>
                    <td className="num">{money(p.price)}</td>
                    <td className="num emphasis">{money(p.market_value)}</td>
                    <td className={`num ${Number(p.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}`}>{money(p.unrealized_pnl)}</td>
                    <td className={`num ${Number(p.unrealized_return || 0) >= 0 ? 'pos' : 'neg'}`}>{pct(p.unrealized_return)}</td>
                    <td className="num">{formatWeight(p.weight)}</td>
                  </tr>
                  {expanded && <tr className="holding-source-row" id={`holding-sources-${p.symbol}`}>
                    <td colSpan="8">
                      <div className="holding-source-panel">
                        <div className="holding-source-head">
                          <div>
                            <b>{p.symbol} · {text('broker sources', 'nguồn theo broker')}</b>
                            <span className="muted">{text('Open tax lots grouped by broker and account. Totals reconcile to the consolidated row above.', 'Các tax lot còn mở được nhóm theo broker và account. Tổng số liệu khớp với dòng tổng hợp phía trên.')}</span>
                          </div>
                          {brokerLots !== null && <span className="source-count-badge">{sources.length} {text(sources.length === 1 ? 'source' : 'sources', 'nguồn')}</span>}
                        </div>

                        {brokerLotsLoading && brokerLots === null ? (
                          <div className="holding-source-state"><span className="spinner" />{text('Loading broker positions…', 'Đang tải vị thế theo broker…')}</div>
                        ) : brokerLotsError ? (
                          <div className="holding-source-state error">{brokerLotsError}</div>
                        ) : sources.length === 0 ? (
                          <div className="holding-source-state">{text('No open broker/account lots were found for this holding.', 'Không tìm thấy tax lot broker/account đang mở cho mã này.')}</div>
                        ) : (
                          <div className="holding-source-scroll">
                            <table className="ranking holding-source-table">
                              <thead><tr>
                                <th>{text('Broker', 'Broker')}</th>
                                <th>{text('Account', 'Tài khoản')}</th>
                                <th className="num">{text('Shares', 'Số lượng')}</th>
                                <th className="num">{text('Avg cost', 'Giá vốn TB')}</th>
                                <th className="num">{text('Cost value', 'Tổng giá vốn')}</th>
                                <th className="num">{text('Market value', 'Giá trị hiện tại')}</th>
                                <th className="num">{text('Unrealized P/L', 'P/L chưa thực hiện')}</th>
                                <th className="num">{text('% of symbol', '% của mã')}</th>
                              </tr></thead>
                              <tbody>{sources.map(source => (
                                <tr key={`${p.symbol}-${source.broker}-${source.account}`}>
                                  <td><b>{source.broker}</b></td>
                                  <td>{source.account}</td>
                                  <td className="num">{shares(source.shares)}</td>
                                  <td className="num">{money(source.average_cost)}</td>
                                  <td className="num">{money(source.cost_value)}</td>
                                  <td className="num">{money(source.market_value)}</td>
                                  <td className={`num ${Number(source.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}`}>{money(source.unrealized_pnl)}</td>
                                  <td className="num">{pct(source.symbol_weight)}</td>
                                </tr>
                              ))}</tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>}
                </React.Fragment>;
              })}</tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card dividend-card">
        <div className="section-head">
          <div>
            <div className="eyebrow">{text('Income', 'Thu nhập')}</div>
            <h2>{text('Dividends', 'Cổ tức')}</h2>
            <p className="muted">{text('Latest event is shown by default. Expand a ticker to see its full stored history. QPort reads SQLite first and calls providers only when the database has no cached result.', 'Mặc định hiển thị sự kiện mới nhất. Mở rộng từng mã để xem toàn bộ lịch sử đã lưu. QPort đọc SQLite trước và chỉ gọi provider khi cơ sở dữ liệu chưa có kết quả cache.')}</p>
          </div>
          <button className="btn-secondary" type="button" disabled={dividendLoading || positions.length === 0} onClick={() => loadPositionDividends(true)}>
            {dividendLoading ? text('Refreshing…', 'Đang cập nhật…') : text('Refresh from providers', 'Cập nhật từ provider')}
          </button>
        </div>

        <div className="dividend-summary">
          <span>{positions.length} {text('holdings', 'mã')}</span>
          <span>{dividendRows.length} {text('loaded', 'đã tải')}</span>
          <span className="pos">{dividendFound} {text('with history', 'có lịch sử')}</span>
        </div>

        {positions.length === 0 ? (
          <div className="empty-state">{text('Add a position to start dividend tracking.', 'Thêm vị thế để bắt đầu theo dõi cổ tức.')}</div>
        ) : dividendRows.length === 0 && dividendLoading ? (
          <div className="loading-line"><span className="spinner" />{text('Loading dividend history…', 'Đang tải lịch sử cổ tức…')}</div>
        ) : (
          <div className="dividend-symbol-list">
            {dividendRows.map(row => {
              const result = row.result || {};
              const components = latestComponents(result);
              const history = result.events || components;
              const cash = components.find(x => x.dividend_type === 'CASH_DIVIDEND');
              const stock = components.find(x => x.dividend_type === 'STOCK_DIVIDEND');
              const first = components[0];
              const sources = [...new Set(components.map(x => x.source).filter(Boolean))].join(', ');
              const origin = result.data_origin === 'SQLITE_CACHE'
                ? text('database', 'database')
                : result.data_origin === 'PROVIDER_REFRESH'
                  ? text('provider refreshed', 'đã cập nhật provider')
                  : '-';
              return (
                <details className="dividend-symbol-node" key={row.symbol}>
                  <summary>
                    <div className="dividend-node-symbol">
                      <b>{row.symbol}</b>
                      <span className="muted">{history.length} {text('events', 'sự kiện')} · {origin}</span>
                    </div>
                    <div className="dividend-node-stat"><span>{text('Latest', 'Mới nhất')}</span><b>{result.latest_event_date || eventDate(first)}</b></div>
                    <div className="dividend-node-stat"><span>{text('Cash/share', 'Tiền/CP')}</span><b>{cash?.cash_per_share != null ? money(cash.cash_per_share) : '-'}</b></div>
                    <div className="dividend-node-stat"><span>{text('Stock ratio', 'Tỷ lệ CP')}</span><b>{stock?.stock_ratio_percent != null ? `${Number(stock.stock_ratio_percent).toFixed(2)}%` : '-'}</b></div>
                    <div className="dividend-node-stat"><span>{text('Payment', 'Thanh toán')}</span><b>{first?.payment_date || '-'}</b></div>
                    <div className="dividend-node-stat"><span>{text('Source', 'Nguồn')}</span><b>{sources || '-'}</b></div>
                  </summary>

                  <div className="dividend-history-body">
                    {row.error && <div className="run-message">{row.error}</div>}
                    {!history.length ? (
                      <div className="empty-state compact-empty">{text('No dividend event is stored for this ticker.', 'Chưa lưu sự kiện cổ tức nào cho mã này.')}</div>
                    ) : (
                      <div className="table-scroll">
                        <table className="ranking dividend-history-table">
                          <thead><tr>
                            <th>{text('Event date', 'Ngày sự kiện')}</th>
                            <th>{text('Type', 'Loại')}</th>
                            <th>{text('Announcement', 'Công bố')}</th>
                            <th>{text('Ex date', 'GDKHQ')}</th>
                            <th>{text('Record date', 'ĐKCC')}</th>
                            <th>{text('Payment', 'Thanh toán')}</th>
                            <th className="num">{text('Cash/share', 'Tiền/CP')}</th>
                            <th className="num">{text('Stock ratio', 'Tỷ lệ CP')}</th>
                            <th>{text('Source', 'Nguồn')}</th>
                          </tr></thead>
                          <tbody>{history.map((event, index) => (
                            <tr key={`${event.event_key || event.source_event_id || eventDate(event)}-${event.dividend_type}-${index}`}>
                              <td>{eventDate(event)}</td>
                              <td><b>{event.dividend_type === 'CASH_DIVIDEND' ? text('Cash', 'Tiền mặt') : text('Stock', 'Cổ phiếu')}</b></td>
                              <td>{event.announcement_date || '-'}</td>
                              <td>{event.ex_date || '-'}</td>
                              <td>{event.record_date || '-'}</td>
                              <td>{event.payment_date || '-'}</td>
                              <td className="num">{event.cash_per_share != null ? money(event.cash_per_share) : '-'}</td>
                              <td className="num">{event.stock_ratio_percent != null ? `${Number(event.stock_ratio_percent).toFixed(2)}%` : '-'}</td>
                              <td>{event.source || '-'}</td>
                            </tr>
                          ))}</tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </details>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}