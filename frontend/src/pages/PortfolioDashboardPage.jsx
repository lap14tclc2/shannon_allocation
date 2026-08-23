import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { getLatestDividend, syncPortfolio } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) {
  return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`;
}

function latestComponents(result) {
  return result?.latest_components?.length ? result.latest_components : (result?.latest ? [result.latest] : []);
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
  const [dividendLoading, setDividendLoading] = useState(false);
  const [dividendRows, setDividendRows] = useState([]);

  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const perf = dashboard.performance_summary || {};
  const market = dashboard.market_data || {};
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

  async function loadPositionDividends() {
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
          return { symbol, result: await getLatestDividend(symbol), error: null };
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
    if (positionSymbolsKey) loadPositionDividends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positionSymbolsKey]);

  const totalPnlPositive = Number(portfolio.total_pnl || 0) >= 0;
  const dividendFound = dividendRows.filter(row => row.result?.found).length;

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

      <section className="card holdings-card">
        <div className="section-head holdings-head">
          <div>
            <div className="eyebrow">{text('Investments', 'Khoản đầu tư')}</div>
            <h2>{t('portfolio.holdings')}</h2>
            <p className="muted">{text('Shares, cost, current value and P/L. No model or risk status is mixed into this table.', 'Chỉ hiển thị số lượng, giá vốn, giá trị hiện tại và P/L. Không trộn trạng thái model hay rủi ro vào bảng này.')}</p>
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
            <table className="ranking portfolio-table portfolio-table-core">
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
              <tbody>{visiblePositions.map(p => (
                <tr key={p.symbol}>
                  <td className="symbols-cell"><b>{p.symbol}</b><div className="muted">{p.price_date || '-'} · {p.price_source || '-'}</div></td>
                  <td className="num">{shares(p.shares)}</td>
                  <td className="num">{money(p.average_cost)}</td>
                  <td className="num">{money(p.price)}</td>
                  <td className="num emphasis">{money(p.market_value)}</td>
                  <td className={`num ${Number(p.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}`}>{money(p.unrealized_pnl)}</td>
                  <td className={`num ${Number(p.unrealized_return || 0) >= 0 ? 'pos' : 'neg'}`}>{pct(p.unrealized_return)}</td>
                  <td className="num">{formatWeight(p.weight)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card dividend-card">
        <div className="section-head">
          <div>
            <div className="eyebrow">{text('Income', 'Thu nhập')}</div>
            <h2>{text('Dividends', 'Cổ tức')}</h2>
            <p className="muted">{text('Automatically checks every stock you currently own.', 'Tự động tra toàn bộ mã cổ phiếu bạn đang nắm giữ.')}</p>
          </div>
          <button className="btn-secondary" type="button" disabled={dividendLoading || positions.length === 0} onClick={loadPositionDividends}>
            {dividendLoading ? text('Checking…', 'Đang tra…') : text('Refresh dividends', 'Tra lại cổ tức')}
          </button>
        </div>

        <div className="dividend-summary">
          <span>{positions.length} {text('holdings', 'mã')}</span>
          <span>{dividendRows.length} {text('checked', 'đã tra')}</span>
          <span className="pos">{dividendFound} {text('with data', 'có dữ liệu')}</span>
        </div>

        {positions.length === 0 ? (
          <div className="empty-state">{text('Add a position to start dividend tracking.', 'Thêm vị thế để bắt đầu theo dõi cổ tức.')}</div>
        ) : dividendRows.length === 0 && dividendLoading ? (
          <div className="loading-line"><span className="spinner" />{text('Fetching dividends…', 'Đang lấy dữ liệu cổ tức…')}</div>
        ) : (
          <div className="table-scroll">
            <table className="ranking dividend-overview-table">
              <thead><tr>
                <th>{text('Ticker', 'Mã')}</th>
                <th>{text('Latest event', 'Event mới nhất')}</th>
                <th className="num">{text('Cash / share', 'Tiền / CP')}</th>
                <th className="num">{text('Stock ratio', 'Tỷ lệ CP')}</th>
                <th>{text('Payment', 'Thanh toán')}</th>
                <th>{text('Source', 'Nguồn')}</th>
              </tr></thead>
              <tbody>{dividendRows.map(row => {
                const components = latestComponents(row.result);
                const cash = components.find(x => x.dividend_type === 'CASH_DIVIDEND');
                const stock = components.find(x => x.dividend_type === 'STOCK_DIVIDEND');
                const first = components[0];
                const sources = [...new Set(components.map(x => x.source).filter(Boolean))].join(', ');
                return (
                  <tr key={row.symbol}>
                    <td><b>{row.symbol}</b></td>
                    <td>{row.result?.latest_event_date || first?.effective_event_date || '-'}</td>
                    <td className="num">{cash?.cash_per_share != null ? money(cash.cash_per_share) : '-'}</td>
                    <td className="num">{stock?.stock_ratio_percent != null ? `${Number(stock.stock_ratio_percent).toFixed(2)}%` : '-'}</td>
                    <td>{first?.payment_date || '-'}</td>
                    <td>{sources || '-'}{row.error && <div className="muted error-copy">{row.error}</div>}</td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
