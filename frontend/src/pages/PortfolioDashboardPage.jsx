import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { createPortfolioTransaction, syncPortfolio } from '../lib/api.js';
import { downloadAIExport } from '../lib/aiExport.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }
function num(v, digits = 2) { return v == null ? '-' : Number(v).toFixed(digits); }

function Metric({ label, value, note, tone = '' }) {
  return <div className={`metric-card ${tone}`}><div className="metric-label">{label}</div><div className="metric-value">{value}</div>{note && <div className="muted">{note}</div>}</div>;
}

export default function PortfolioDashboardPage({ dashboard: initialDashboard, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  const shares = (v) => formatShares(v, locale);
  const [dashboard] = useState(initialDashboard || {});
  const [syncing, setSyncing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [cashSaving, setCashSaving] = useState(false);
  const [cashAmount, setCashAmount] = useState('');
  const [message, setMessage] = useState('');
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const perf = dashboard.performance_summary || {};
  const risk = dashboard.risk || {};
  const health = dashboard.health || {};
  const market = dashboard.market_data || {};
  const suggestions = dashboard.contribution_suggestions || {};

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
    } finally {
      setExporting(false);
    }
  }

  async function changeCash(eventType) {
    const amount = Number(cashAmount || 0);
    if (!Number.isFinite(amount) || amount <= 0) return setMessage(text('Enter a positive cash amount.', 'Nhập số tiền lớn hơn 0.'));
    setCashSaving(true); setMessage('');
    try {
      await createPortfolioTransaction({ event_type: eventType, event_date: dashboard.today, amount, note: 'Portfolio cash management' });
      window.location.reload();
    } catch (err) { setMessage(err.message); setCashSaving(false); }
  }

  const healthFlagText = (flag) => {
    if (locale !== 'vi') return flag.message;
    const map = {
      MARKET_DATA: 'Dữ liệu thị trường chưa hoàn toàn mới.', CONCENTRATION: 'Vị thế lớn nhất chiếm ít nhất 40% NAV.',
      HHI: 'Danh mục đang tập trung cao (HHI ≥ 0,25).', CORRELATION: 'Các cổ phiếu có tương quan trung bình cao.',
      DRAWDOWN: 'Drawdown hiện tại từ 20% trở lên.', VOLATILITY: 'Biến động năm hóa 252 ngày đang cao.',
      RISK_COVERAGE: 'Độ phủ dữ liệu rủi ro dưới 90%.',
    };
    return map[flag.code] || flag.message;
  };

  return (
    <div className="page">
      <AppNav active="portfolio" locale={locale} />
      <header className="page-head portfolio-head">
        <div><h1>{t('portfolio.title')}</h1><p className="muted">{t('portfolio.subtitle')}</p></div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button className="btn-variant" type="button" onClick={exportAI} disabled={exporting}>{exporting ? text('Exporting…', 'Đang xuất…') : text('⇩ Export for AI', '⇩ Xuất dữ liệu cho AI')}</button>
          <button className="btn-export" type="button" onClick={sync} disabled={syncing}>{syncing ? t('portfolio.syncing') : t('portfolio.sync')}</button>
        </div>
      </header>
      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid portfolio-metrics">
        <Metric label={t('portfolio.nav')} value={money(portfolio.nav || 0)} note={perf.latest_date ? `${text('As of', 'Tính đến')} ${perf.latest_date}` : text('Live valuation', 'Định giá hiện tại')} />
        <Metric label={t('portfolio.equity')} value={money(portfolio.equity_value || 0)} note={t('portfolio.holdings_count', { count: positions.length, suffix: positions.length === 1 ? '' : 's' })} />
        <Metric label={t('portfolio.cash')} value={money(portfolio.cash || 0)} note={portfolio.nav ? t('portfolio.of_nav', { value: pct((portfolio.cash || 0) / portfolio.nav) }) : '—'} />
        <Metric label={t('portfolio.total_pl')} value={money(portfolio.total_pnl)} tone={Number(portfolio.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'} note={`${text('Return', 'Tỷ suất')} ${pct(portfolio.total_return)}`} />
        <Metric label={t('portfolio.current_drawdown')} value={pct(perf.current_drawdown ?? 0)} note={`${text('Max', 'Lớn nhất')} ${pct(perf.max_drawdown ?? 0)}`} />
        <Metric label={t('portfolio.volatility_252')} value={pct(risk.volatility_252)} note={`${text('63D', '63 ngày')} ${pct(risk.volatility_63)}`} />
      </div>

      <div className="card">
        <div className="section-head"><div><h3>{t('portfolio.holdings')}</h3><div className="muted">{t('portfolio.holdings_note')}</div></div><div className={`status-pill status-${String(market.status || 'MISSING').toLowerCase()}`}>{t('common.data')} {status(market.status || 'MISSING')}</div></div>
        {positions.length === 0 ? <div className="empty-state"><h3>{t('portfolio.no_holdings')}</h3><p>{t('portfolio.no_holdings_note')}</p><a className="btn-export" href="/transactions">{t('portfolio.add_opening')}</a></div> : (
          <div className="table-scroll"><table className="ranking portfolio-table"><thead><tr>
            <th>{t('portfolio.ticker')}</th><th>{t('portfolio.shares')}</th><th>{t('portfolio.avg_cost')}</th><th>{t('portfolio.price')}</th><th>{t('portfolio.cost_value')}</th><th>{t('portfolio.market_value')}</th><th>{t('portfolio.unrealized_pl')}</th><th>{t('portfolio.return')}</th><th>{t('portfolio.weight')}</th><th>{t('portfolio.risk_contrib')}</th><th>{t('portfolio.status')}</th>
          </tr></thead><tbody>{positions.map((p) => <tr key={p.symbol}>
            <td className="symbols-cell"><b>{p.symbol}</b><div className="muted">{p.price_date || '-'} · {p.price_source || '-'}</div></td><td>{shares(p.shares)}</td><td>{money(p.average_cost)}</td><td>{money(p.price)}</td><td>{money(p.cost_value)}</td><td>{money(p.market_value)}</td><td className={Number(p.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}>{money(p.unrealized_pnl)}</td><td className={Number(p.unrealized_return || 0) >= 0 ? 'pos' : 'neg'}>{pct(p.unrealized_return)}</td><td>{formatWeight(p.weight)}</td><td>{pct(p.risk_contribution)}</td><td><span className={`signal signal-${String(p.status || 'HOLD').toLowerCase()}`}>{status(p.status || 'HOLD')}</span></td>
          </tr>)}</tbody></table></div>
        )}
      </div>

      <div className="expand-grid">
        <div className="card">
          <h3>{text('Cash management', 'Quản lý tiền mặt')}</h3>
          <p className="muted">{text('Available cash is part of the ledger. Record deposits/withdrawals here; QPort never invents cash.', 'Tiền mặt khả dụng là một phần của sổ cái. Ghi nạp/rút tiền tại đây; QPort không tự tạo tiền.')}</p>
          <div className="cash-entry"><input type="number" min="0" step="1000" value={cashAmount} onChange={(e) => setCashAmount(e.target.value)} placeholder={text('Amount (VND)', 'Số tiền (VND)')} /><button className="btn-export" type="button" disabled={cashSaving} onClick={() => changeCash('CASH_DEPOSIT')}>{text('Add cash', 'Nạp tiền')}</button><button className="btn-variant" type="button" disabled={cashSaving} onClick={() => changeCash('CASH_WITHDRAW')}>{text('Withdraw', 'Rút tiền')}</button></div>
          <div className="diag-row"><span>{text('Ledger cash balance', 'Số dư tiền mặt')}</span><b>{money(portfolio.cash || 0)}</b></div>
        </div>
        <div className="card">
          <h3>{t('portfolio.deploy_cash')}</h3><div className="muted">{t('portfolio.buy_only', { policy: suggestions.policy || '—' })}</div>
          {(suggestions.suggestions || []).length === 0 ? <p>{t('portfolio.no_suggestion')}</p> : <div className="suggestion-list">{suggestions.suggestions.slice(0, 6).map((s) => <div className="diag-row" key={s.symbol}><span><b>{s.symbol}</b> · {pct(s.current_weight)} → {t('portfolio.reference', { value: pct(s.target_weight) })}</span><b>{money(s.amount)}</b></div>)}</div>}
          <div className="diag-row"><span>{t('portfolio.available_cash')}</span><b>{money(suggestions.available_cash || 0)}</b></div>
        </div>
      </div>

      <div className="card health-card">
        <div className="section-head"><div><h3>{t('portfolio.health')}</h3><div className="muted">{text('A diagnostic summary, not a trading signal.', 'Tổng hợp chẩn đoán, không phải tín hiệu giao dịch.')}</div></div><span className={`status-pill ${health.status === 'HEALTHY' ? 'status-valid' : 'status-stale'}`}>{health.status === 'HEALTHY' ? text('HEALTHY', 'TỐT') : text('ATTENTION', 'CẦN CHÚ Ý')}</span></div>
        <div className="health-grid">
          <div><span>{text('Total return', 'Tỷ suất tổng')}</span><b>{pct(health.total_return)}</b></div><div><span>{text('Current / max drawdown', 'Drawdown hiện tại / lớn nhất')}</span><b>{pct(health.current_drawdown)} / {pct(health.max_drawdown)}</b></div><div><span>{text('63D / 252D volatility', 'Biến động 63 / 252 ngày')}</span><b>{pct(risk.volatility_63)} / {pct(risk.volatility_252)}</b></div><div><span>{text('Largest position', 'Vị thế lớn nhất')}</span><b>{pct(risk.max_position_weight)}</b></div><div><span>{text('Effective positions', 'Số vị thế hiệu dụng')}</span><b>{num(health.effective_positions, 1)}</b></div><div><span>{text('Average / max correlation', 'Tương quan TB / lớn nhất')}</span><b>{num(health.average_correlation)} / {num(health.max_correlation)}</b></div><div><span>{text('Diversification ratio', 'Tỷ lệ đa dạng hóa')}</span><b>{num(health.diversification_ratio)}</b></div><div><span>{text('Largest risk contributor', 'Mã đóng góp rủi ro lớn nhất')}</span><b>{health.largest_risk_symbol || '-'} {pct(health.largest_risk_contribution)}</b></div><div><span>{text('Daily VaR / CVaR 95%', 'VaR / CVaR ngày 95%')}</span><b>{pct(health.daily_var_95)} / {pct(health.daily_cvar_95)}</b></div><div><span>{text('Risk data coverage', 'Độ phủ dữ liệu rủi ro')}</span><b>{pct(health.risk_coverage)}</b></div><div><span>{text('Official snapshots', 'Snapshot chính thức')}</span><b>{health.official_snapshot_count ?? 0}</b></div><div><span>{text('Cash weight', 'Tỷ trọng tiền mặt')}</span><b>{pct(health.cash_weight)}</b></div>
        </div>
        {(health.flags || []).length > 0 && <div className="health-flags">{health.flags.map((f) => <div className="run-message" key={f.code}>⚠ {healthFlagText(f)}</div>)}</div>}
        <div className="muted" style={{ marginTop: 10 }}>{t('portfolio.risk_info_only')}</div>
      </div>
    </div>
  );
}
