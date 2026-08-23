import React, { useEffect, useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { createPortfolioTransaction, getLatestDividend, syncPortfolio } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { validateCashAmount } from '../lib/validation.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null || !Number.isFinite(Number(v)) ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }
function num(v, digits = 2) { return v == null || !Number.isFinite(Number(v)) ? '-' : Number(v).toFixed(digits); }
function latestComponents(result) { return result?.latest_components?.length ? result.latest_components : (result?.latest ? [result.latest] : []); }

function Metric({ label, value, note, tone = '' }) {
  return <div className={`metric-card ${tone}`}><div className="metric-label">{label}</div><div className="metric-value">{value}</div>{note && <div className="metric-note">{note}</div>}</div>;
}

export default function PortfolioDashboardPage({ dashboard: initialDashboard, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null || !Number.isFinite(Number(v)) ? '-' : `${formatMoney(v, false, locale)} VND`);
  const shares = (v) => formatShares(v, locale);
  const [dashboard] = useState(initialDashboard || {});
  const [syncing, setSyncing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [cashSaving, setCashSaving] = useState(false);
  const [cashAmount, setCashAmount] = useState('');
  const [cashError, setCashError] = useState('');
  const [message, setMessage] = useState('');
  const [positionQuery, setPositionQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [dividendLoading, setDividendLoading] = useState(false);
  const [dividendRows, setDividendRows] = useState([]);
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const perf = dashboard.performance_summary || {};
  const risk = dashboard.risk || {};
  const health = dashboard.health || {};
  const market = dashboard.market_data || {};
  const suggestions = dashboard.contribution_suggestions || {};
  const lineage = dashboard.data_lineage || {};
  const positionSymbolsKey = positions.map(p => p.symbol).sort().join('|');

  const visiblePositions = useMemo(() => {
    const q = positionQuery.trim().toUpperCase();
    return q ? positions.filter(p => String(p.symbol || '').includes(q)) : positions;
  }, [positions, positionQuery]);

  const allocationPositions = useMemo(
    () => positions.filter(p => Number(p.equity_weight || 0) > 0).sort((a, b) => Number(b.equity_weight || 0) - Number(a.equity_weight || 0)),
    [positions],
  );

  const positionStatus = (value) => {
    if (value === 'MONITOR') return text('MONITOR', 'THEO DÕI');
    return status(value || 'MONITOR');
  };

  async function sync() {
    setSyncing(true); setMessage('');
    try { const result = await syncPortfolio(); setMessage(result.message || t('portfolio.sync_done')); window.location.reload(); }
    catch (err) { setMessage(t('portfolio.sync_failed', { error: err.message })); setSyncing(false); }
  }

  async function exportAI() {
    setExporting(true); setMessage('');
    try {
      const filename = await downloadAIExport();
      setMessage(text(`Exported ${filename}. Upload this Markdown file directly to your AI.`, `Đã xuất ${filename}. Bạn có thể tải trực tiếp file Markdown này lên AI.`));
    } catch (err) {
      setMessage(text(`AI export failed: ${err.message}`, `Xuất dữ liệu cho AI thất bại: ${err.message}`));
    } finally { setExporting(false); }
  }

  async function changeCash(eventType) {
    setCashError(''); setMessage('');
    let amount;
    try { amount = validateCashAmount(cashAmount, locale); }
    catch (err) { setCashError(err.message); return; }
    setCashSaving(true);
    try {
      await createPortfolioTransaction({ event_type: eventType, event_date: dashboard.today, amount, note: 'Portfolio cash management' });
      window.location.reload();
    } catch (err) { setCashError(err.message); setCashSaving(false); }
  }

  async function loadPositionDividends() {
    const symbols = [...new Set(positions.map(p => String(p.symbol || '').toUpperCase()).filter(Boolean))];
    if (!symbols.length) { setDividendRows([]); return; }
    setDividendLoading(true);
    const collected = [];
    for (let i = 0; i < symbols.length; i += 4) {
      const batch = symbols.slice(i, i + 4);
      const rows = await Promise.all(batch.map(async symbol => {
        try { return { symbol, result: await getLatestDividend(symbol), error: null }; }
        catch (err) { return { symbol, result: null, error: err.message }; }
      }));
      collected.push(...rows);
      setDividendRows([...collected]);
    }
    setDividendLoading(false);
  }

  useEffect(() => {
    if (positionSymbolsKey) loadPositionDividends();
    // The symbol key changes only when the current position set changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positionSymbolsKey]);

  const healthFlagText = (flag) => {
    if (locale !== 'vi') return flag.message;
    const map = {
      MARKET_DATA: 'Dữ liệu thị trường chưa đồng nhất cho toàn bộ mã đang nắm giữ.',
      CAPITAL_CONCENTRATION: 'Số vị thế hiệu dụng thấp hơn 75% số mã thực tế.',
      RISK_CONCENTRATION: `${health.largest_risk_symbol || 'Một mã'} đang đóng góp rủi ro quá lớn cho danh mục.`,
      CORRELATION: 'Các cổ phiếu có tương quan trung bình cao.',
      DRAWDOWN: 'Drawdown đang theo dõi từ 20% trở lên.',
      VOLATILITY: 'Biến động năm hóa 252 ngày đang cao.',
      RISK_COVERAGE: 'Độ phủ dữ liệu rủi ro dưới 90%.',
      PERFORMANCE_HISTORY: 'Lịch sử hiệu suất chưa đủ dài để kết luận mạnh về drawdown/hiệu suất.',
    };
    return map[flag.code] || flag.message;
  };

  const drawdownNote = perf.history_status === 'NO_HISTORY'
    ? text('No official performance history yet', 'Chưa có lịch sử hiệu suất chính thức')
    : `${text('Max', 'Lớn nhất')} ${pct(perf.max_drawdown)} · ${perf.official_snapshot_count || 0} ${text('observations', 'quan sát')}`;
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
            <span>{pct(portfolio.accounting_return)} {text('on recorded capital', 'trên vốn ghi nhận')}</span>
          </div>
          <div className="hero-meta">
            <span><i className={`mini-dot status-${String(market.status || 'missing').toLowerCase()}`} />{text('Market', 'Thị trường')} {market.market_date || '-'}</span>
            <span>{positions.length} {text(positions.length === 1 ? 'holding' : 'holdings', 'mã đang nắm giữ')}</span>
            <span className={health.status === 'HEALTHY' ? 'pos' : 'warn'}>{health.status === 'HEALTHY' ? text('Healthy', 'Tốt') : text('Needs attention', 'Cần chú ý')}</span>
          </div>
        </div>
        <div className="hero-actions">
          <button className="btn-primary" type="button" onClick={sync} disabled={syncing}>{syncing ? t('portfolio.syncing') : text('Refresh portfolio', 'Cập nhật danh mục')}</button>
          <a className="btn-secondary" href="/transactions">{text('+ Add transaction', '+ Thêm giao dịch')}</a>
          <button className="btn-ghost" type="button" onClick={exportAI} disabled={exporting}>{exporting ? text('Exporting…', 'Đang xuất…') : text('Export for AI', 'Xuất cho AI')}</button>
        </div>
      </header>
      {message && <div className="run-message banner-message">{message}</div>}

      <div className="metric-grid portfolio-metrics overview-metrics">
        <Metric label={t('portfolio.equity')} value={money(portfolio.equity_value || 0)} note={t('portfolio.holdings_count', { count: positions.length, suffix: positions.length === 1 ? '' : 's' })} />
        <Metric label={t('portfolio.cash')} value={money(portfolio.cash || 0)} note={portfolio.nav ? t('portfolio.of_nav', { value: pct((portfolio.cash || 0) / portfolio.nav) }) : '—'} />
        <Metric label={t('portfolio.current_drawdown')} value={pct(perf.current_drawdown)} note={drawdownNote} />
        <Metric label={t('portfolio.volatility_252')} value={pct(risk.volatility_252)} note={`${text('63D', '63 ngày')} ${pct(risk.volatility_63)}`} />
      </div>

      <section className="card holdings-card">
        <div className="section-head holdings-head">
          <div>
            <div className="eyebrow">{text('Investments', 'Khoản đầu tư')}</div>
            <h2>{t('portfolio.holdings')}</h2>
            <p className="muted">{text('Core columns first. Turn on details only when you need cost, equity weight, risk contribution and source lineage.', 'Ưu tiên các cột cốt lõi. Chỉ bật chi tiết khi cần giá vốn, tỷ trọng cổ phiếu, đóng góp rủi ro và nguồn dữ liệu.')}</p>
          </div>
          <div className="table-tools">
            <input className="search-input" value={positionQuery} onChange={e => setPositionQuery(e.target.value)} placeholder={text('Search ticker…', 'Tìm mã…')} aria-label={text('Search holdings', 'Tìm mã đang nắm giữ')} />
            <button className={`seg-button ${showAdvanced ? 'active' : ''}`} type="button" onClick={() => setShowAdvanced(v => !v)}>{showAdvanced ? text('Hide details', 'Ẩn chi tiết') : text('Show details', 'Hiện chi tiết')}</button>
            <span className={`status-pill status-${String(market.status || 'MISSING').toLowerCase()}`}>{status(market.status || 'MISSING')}</span>
          </div>
        </div>
        {positions.length === 0 ? <div className="empty-state"><h3>{t('portfolio.no_holdings')}</h3><p>{t('portfolio.no_holdings_note')}</p><a className="btn-primary" href="/transactions">{t('portfolio.add_opening')}</a></div> : visiblePositions.length === 0 ? <div className="empty-state">{text('No holding matches that ticker.', 'Không có mã nào khớp tìm kiếm.')}</div> : (
          <div className="table-scroll"><table className={`ranking portfolio-table ${showAdvanced ? 'portfolio-table-advanced' : 'portfolio-table-core'}`}><thead><tr>
            <th>{t('portfolio.ticker')}</th><th className="num">{t('portfolio.shares')}</th>{showAdvanced && <th className="num">{t('portfolio.avg_cost')}</th>}<th className="num">{t('portfolio.price')}</th>{showAdvanced && <th className="num">{t('portfolio.cost_value')}</th>}<th className="num">{t('portfolio.market_value')}</th><th className="num">{t('portfolio.unrealized_pl')}</th><th className="num">{t('portfolio.return')}</th><th className="num">{t('portfolio.weight')}</th>{showAdvanced && <><th className="num">{text('Equity wt.', 'Tỷ trọng CP')}</th><th className="num">{t('portfolio.risk_contrib')}</th></>}<th>{t('portfolio.status')}</th>
          </tr></thead><tbody>{visiblePositions.map((p) => <tr key={p.symbol}>
            <td className="symbols-cell"><b>{p.symbol}</b>{showAdvanced && <div className="muted">{p.price_date || '-'} · {p.price_source || '-'}</div>}</td>
            <td className="num">{shares(p.shares)}</td>
            {showAdvanced && <td className="num">{money(p.average_cost)}</td>}
            <td className="num">{money(p.price)}</td>
            {showAdvanced && <td className="num">{money(p.cost_value)}</td>}
            <td className="num emphasis">{money(p.market_value)}</td>
            <td className={`num ${Number(p.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}`}>{money(p.unrealized_pnl)}</td>
            <td className={`num ${Number(p.unrealized_return || 0) >= 0 ? 'pos' : 'neg'}`}>{pct(p.unrealized_return)}</td>
            <td className="num">{formatWeight(p.weight)}</td>
            {showAdvanced && <><td className="num">{pct(p.equity_weight)}</td><td className="num">{pct(p.risk_contribution)}</td></>}
            <td><span className={`signal signal-${String(p.status || 'monitor').toLowerCase()}`}>{positionStatus(p.status)}</span></td>
          </tr>)}</tbody></table></div>
        )}
      </section>

      <div className="dashboard-grid">
        <section className="card allocation-card">
          <div className="section-head"><div><div className="eyebrow">{text('Allocation', 'Phân bổ')}</div><h2>{text('Where your equity sits', 'Phân bổ phần cổ phiếu')}</h2></div><a className="text-link" href="/risk">{text('Open risk →', 'Mở rủi ro →')}</a></div>
          <div className="allocation-list">{allocationPositions.length === 0 ? <div className="empty-state">{text('No valued positions yet.', 'Chưa có vị thế được định giá.')}</div> : allocationPositions.map(p => <div className="allocation-row" key={p.symbol}>
            <div className="allocation-label"><b>{p.symbol}</b><span>{pct(p.equity_weight)}</span></div>
            <div className="allocation-track"><span style={{ width: `${Math.max(1, Math.min(100, Number(p.equity_weight || 0) * 100))}%` }} /></div>
          </div>)}</div>
        </section>

        <section className="card cash-card">
          <div className="eyebrow">{text('Cash', 'Tiền mặt')}</div>
          <h2>{text('Cash & deployment', 'Tiền mặt & khả năng phân bổ')}</h2>
          <div className="cash-summary"><strong>{money(portfolio.cash || 0)}</strong><span>{suggestions.policy || '—'}</span></div>
          <div className="cash-entry"><input type="number" min="1" step="1000" value={cashAmount} onChange={(e) => { setCashAmount(e.target.value); setCashError(''); }} placeholder={text('Amount (VND)', 'Số tiền (VND)')} aria-invalid={!!cashError} /><button className="btn-primary" type="button" disabled={cashSaving} onClick={() => changeCash('CASH_DEPOSIT')}>{text('Add', 'Nạp')}</button><button className="btn-secondary" type="button" disabled={cashSaving} onClick={() => changeCash('CASH_WITHDRAW')}>{text('Withdraw', 'Rút')}</button></div>
          {cashError && <div className="field-error">{cashError}</div>}
          <div className="compact-list">
            <div><span>{text('Strategic reserve', 'Dự trữ chiến lược')}</span><b>{suggestions.strategic_cash_reserve == null ? text('Not set', 'Chưa đặt') : money(suggestions.strategic_cash_reserve)}</b></div>
            <div><span>{text('Deployable cash', 'Tiền có thể phân bổ')}</span><b>{suggestions.deployable_cash == null ? text('Undefined', 'Chưa xác định') : money(suggestions.deployable_cash)}</b></div>
          </div>
          {(suggestions.suggestions || []).length > 0 && <div className="suggestion-list">{suggestions.suggestions.slice(0, 4).map(s => <div className="compact-list-row" key={s.symbol}><span><b>{s.symbol}</b> · {pct(s.current_weight)} → {pct(s.target_weight)}</span><b>{money(s.amount)}</b></div>)}</div>}
          {suggestions.policy !== 'EXPLICIT_REFERENCE_WEIGHT_DEFICITS' && <a className="text-link" href="/settings">{text('Configure cash & target policy →', 'Cấu hình tiền mặt & tỷ trọng →')}</a>}
        </section>
      </div>

      <section className="card dividend-card">
        <div className="section-head">
          <div><div className="eyebrow">{text('Income', 'Thu nhập')}</div><h2>{text('Latest dividends for current holdings', 'Cổ tức mới nhất của toàn bộ mã đang nắm giữ')}</h2><p className="muted">{text('QPort checks every current position automatically in small parallel batches. Discovery is read-only and never changes shares or cash.', 'QPort tự tra toàn bộ position hiện tại theo các batch nhỏ song song. Discovery chỉ đọc và không bao giờ tự thay đổi cổ phiếu hoặc tiền mặt.')}</p></div>
          <button className="btn-secondary" type="button" disabled={dividendLoading || positions.length === 0} onClick={loadPositionDividends}>{dividendLoading ? text('Checking…', 'Đang tra…') : text('Refresh dividends', 'Tra lại cổ tức')}</button>
        </div>
        <div className="dividend-summary"><span>{positions.length} {text('positions', 'position')}</span><span>{dividendRows.length} {text('checked', 'đã tra')}</span><span className="pos">{dividendFound} {text('with dividend data', 'có dữ liệu cổ tức')}</span></div>
        {positions.length === 0 ? <div className="empty-state">{text('Add a position to start dividend tracking.', 'Thêm position để bắt đầu theo dõi cổ tức.')}</div> : dividendRows.length === 0 && dividendLoading ? <div className="loading-line"><span className="spinner" />{text('Fetching dividends for all current holdings…', 'Đang lấy cổ tức cho toàn bộ mã đang nắm giữ…')}</div> : (
          <div className="table-scroll"><table className="ranking dividend-overview-table"><thead><tr><th>{text('Ticker', 'Mã')}</th><th>{text('Latest event', 'Event mới nhất')}</th><th className="num">{text('Cash / share', 'Tiền / CP')}</th><th className="num">{text('Stock ratio', 'Tỷ lệ CP')}</th><th>{text('Record / payment', 'ĐKCC / thanh toán')}</th><th>{text('Source', 'Nguồn')}</th><th>{text('Status', 'Trạng thái')}</th></tr></thead><tbody>{dividendRows.map(row => {
            const components = latestComponents(row.result);
            const cash = components.find(x => x.dividend_type === 'CASH_DIVIDEND');
            const stock = components.find(x => x.dividend_type === 'STOCK_DIVIDEND');
            const first = components[0];
            const sources = [...new Set(components.map(x => x.source).filter(Boolean))].join(', ');
            return <tr key={row.symbol}><td><b>{row.symbol}</b></td><td>{row.result?.latest_event_date || first?.effective_event_date || '-'}</td><td className="num">{cash?.cash_per_share != null ? money(cash.cash_per_share) : '-'}</td><td className="num">{stock?.stock_ratio_percent != null ? `${Number(stock.stock_ratio_percent).toFixed(2)}%` : '-'}</td><td>{first ? <><span>{first.record_date || first.ex_date || '-'}</span><div className="muted">{first.payment_date || '-'}</div></> : '-'}</td><td>{sources || '-'}</td><td>{row.error ? <span className="signal signal-review">{text('ERROR', 'LỖI')}</span> : row.result?.found ? <span className="signal signal-hold">{text('FOUND', 'CÓ DỮ LIỆU')}</span> : <span className="signal signal-monitor">{text('NO EVENT', 'CHƯA CÓ')}</span>}{row.error && <div className="muted error-copy">{row.error}</div>}</td></tr>;
          })}</tbody></table></div>
        )}
        <div className="section-foot"><span className="muted">{text('Verification and posting remain in Operations.', 'Xác minh và post vào ledger vẫn thực hiện tại Vận hành.')}</span><a className="text-link" href="/operations">{text('Open Operations →', 'Mở Vận hành →')}</a></div>
      </section>

      <details className="card health-card disclosure-card">
        <summary>
          <div><div className="eyebrow">{text('Portfolio health', 'Sức khỏe danh mục')}</div><h2>{health.status === 'HEALTHY' ? text('Portfolio looks healthy', 'Danh mục đang ổn') : text('Portfolio needs attention', 'Danh mục cần chú ý')}</h2><p className="muted">{(health.flags || []).length ? `${health.flags.length} ${text('diagnostic item(s)', 'mục chẩn đoán')}` : text('No diagnostic warnings.', 'Không có cảnh báo chẩn đoán.')}</p></div>
          <span className={`status-pill ${health.status === 'HEALTHY' ? 'status-valid' : 'status-stale'}`}>{health.status === 'HEALTHY' ? text('HEALTHY', 'TỐT') : text('ATTENTION', 'CHÚ Ý')}</span>
        </summary>
        <div className="health-grid">
          <div><span>{text('Accounting return', 'Tỷ suất kế toán')}</span><b>{pct(health.accounting_return)}</b></div>
          <div><span>{text('Performance history', 'Lịch sử hiệu suất')}</span><b>{health.performance_history_status || '-'}</b></div>
          <div><span>{text('Current / max drawdown', 'Drawdown hiện tại / lớn nhất')}</span><b>{pct(health.current_drawdown)} / {pct(health.max_drawdown)}</b></div>
          <div><span>{text('63D / 252D volatility', 'Biến động 63 / 252 ngày')}</span><b>{pct(risk.volatility_63)} / {pct(risk.volatility_252)}</b></div>
          <div><span>{text('Largest NAV / equity weight', 'Tỷ trọng NAV / CP lớn nhất')}</span><b>{pct(risk.max_position_weight)} / {pct(risk.max_equity_weight)}</b></div>
          <div><span>{text('Equity HHI', 'HHI phần cổ phiếu')}</span><b>{num(health.equity_hhi, 3)}</b></div>
          <div><span>{text('Effective positions / ratio', 'Vị thế hiệu dụng / tỷ lệ')}</span><b>{num(health.effective_positions, 2)} / {pct(health.effective_position_ratio)}</b></div>
          <div><span>{text('Average / max correlation', 'Tương quan TB / lớn nhất')}</span><b>{num(health.average_correlation)} / {num(health.max_correlation)}</b></div>
          <div><span>{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</span><b>{num(health.diversification_ratio)}</b></div>
          <div><span>{text('Largest risk contributor', 'Mã đóng góp rủi ro lớn nhất')}</span><b>{health.largest_risk_symbol || '-'} {pct(health.largest_risk_contribution)}</b></div>
          <div><span>{text('Daily VaR / CVaR 95%', 'VaR / CVaR ngày 95%')}</span><b>{pct(health.daily_var_95)} / {pct(health.daily_cvar_95)}</b></div>
          <div><span>{text('Risk data coverage', 'Độ phủ dữ liệu rủi ro')}</span><b>{pct(health.risk_coverage)}</b></div>
        </div>
        {(health.flags || []).length > 0 && <div className="health-flags">{health.flags.map((f) => <div className="health-flag" key={f.code}><span>{f.level === 'WARNING' ? '!' : 'i'}</span><div><b>{f.code}</b><p>{healthFlagText(f)}</p></div></div>)}</div>}
        {lineage.analytics?.status === 'UNVERIFIED' && <div className="info-callout">{text('Analytics price adjustment lineage is not yet verified; interpret long-window risk around corporate actions cautiously.', 'Nguồn điều chỉnh giá dùng cho analytics chưa được xác minh; cần thận trọng khi đọc rủi ro dài hạn quanh các sự kiện doanh nghiệp.')}</div>}
        <div className="muted">{t('portfolio.risk_info_only')}</div>
      </details>
    </div>
  );
}
