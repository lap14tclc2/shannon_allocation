import React, { useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import { formatMoney, formatShares, formatWeight } from '../lib/format.js';
import { syncPortfolio } from '../lib/api.js';
import { useI18n } from '../i18n.js';

function pct(v, digits = 2) { return v == null ? '-' : `${(Number(v) * 100).toFixed(digits)}%`; }

function Metric({ label, value, note, tone = '' }) {
  return (
    <div className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note && <div className="muted">{note}</div>}
    </div>
  );
}

export default function PortfolioDashboardPage({ dashboard: initialDashboard, locale = 'en' }) {
  const { t, status } = useI18n(locale);
  const money = (v) => (v == null ? '-' : `${formatMoney(v, false, locale)} VND`);
  const shares = (v) => formatShares(v, locale);
  const [dashboard] = useState(initialDashboard || {});
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const portfolio = dashboard.portfolio || {};
  const positions = portfolio.positions || [];
  const snapshot = dashboard.latest_snapshot || {};
  const risk = dashboard.risk || {};
  const market = dashboard.market_data || {};
  const suggestions = dashboard.contribution_suggestions || {};

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

  const invariantKeys = [
    ['price movement never changes shares', 'transactions.rule_price'],
    ['model output never changes shares', 'transactions.rule_risk'],
    ['time/year-end never changes shares', null],
    ['only explicit ledger events change holdings or cash', null],
  ];
  const invariantText = (value) => {
    const found = invariantKeys.find(([raw]) => raw === value);
    if (found?.[1]) return t(found[1]);
    if (locale === 'vi' && value === 'time/year-end never changes shares') return 'Thời gian hoặc cuối năm không thay đổi số cổ phiếu.';
    if (locale === 'vi' && value === 'only explicit ledger events change holdings or cash') return 'Chỉ sự kiện sổ cái rõ ràng mới thay đổi cổ phiếu hoặc tiền mặt.';
    return value;
  };

  return (
    <div className="page">
      <AppNav active="portfolio" locale={locale} />
      <header className="page-head portfolio-head">
        <div>
          <h1>{t('portfolio.title')}</h1>
          <p className="muted">{t('portfolio.subtitle')}</p>
        </div>
        <button className="btn-export" type="button" onClick={sync} disabled={syncing}>
          {syncing ? t('portfolio.syncing') : t('portfolio.sync')}
        </button>
      </header>

      {message && <div className="run-message">{message}</div>}

      <div className="metric-grid portfolio-metrics">
        <Metric label={t('portfolio.nav')} value={money(portfolio.nav || 0)} note={snapshot.snapshot_date ? t('portfolio.snapshot', { date: snapshot.snapshot_date }) : t('portfolio.no_snapshot')} />
        <Metric label={t('portfolio.equity')} value={money(portfolio.equity_value || 0)} note={t('portfolio.holdings_count', { count: positions.length, suffix: positions.length === 1 ? '' : 's' })} />
        <Metric label={t('portfolio.cash')} value={money(portfolio.cash || 0)} note={portfolio.nav ? t('portfolio.of_nav', { value: pct((portfolio.cash || 0) / portfolio.nav) }) : '—'} />
        <Metric label={t('portfolio.total_pl')} value={money(snapshot.total_pnl ?? 0)} tone={Number(snapshot.total_pnl || 0) >= 0 ? 'positive-card' : 'negative-card'} note={t('portfolio.realized', { value: money(portfolio.realized_pnl || 0) })} />
        <Metric label={t('portfolio.current_drawdown')} value={pct(snapshot.current_drawdown)} note={t('portfolio.max', { value: pct(snapshot.max_drawdown) })} />
        <Metric label={t('portfolio.volatility_252')} value={pct(risk.volatility_252)} note={t('portfolio.risk_data', { status: status(risk.status || 'UNAVAILABLE') })} />
      </div>

      <div className="card">
        <div className="section-head">
          <div>
            <h3>{t('portfolio.holdings')}</h3>
            <div className="muted">{t('portfolio.holdings_note')}</div>
          </div>
          <div className={`status-pill status-${String(market.status || 'MISSING').toLowerCase()}`}>
            {t('common.data')} {status(market.status || 'MISSING')}
          </div>
        </div>

        {positions.length === 0 ? (
          <div className="empty-state">
            <h3>{t('portfolio.no_holdings')}</h3>
            <p>{t('portfolio.no_holdings_note')}</p>
            <a className="btn-export" href="/transactions">{t('portfolio.add_opening')}</a>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="ranking portfolio-table">
              <thead><tr>
                <th>{t('portfolio.ticker')}</th>
                <th>{t('portfolio.shares')}</th>
                <th>{t('portfolio.avg_cost')}</th>
                <th>{t('portfolio.price')}</th>
                <th>{t('portfolio.cost_value')}</th>
                <th>{t('portfolio.market_value')}</th>
                <th>{t('portfolio.unrealized_pl')}</th>
                <th>{t('portfolio.return')}</th>
                <th>{t('portfolio.weight')}</th>
                <th>{t('portfolio.risk_contrib')}</th>
                <th>{t('portfolio.status')}</th>
              </tr></thead>
              <tbody>
                {positions.map((p) => {
                  const costValue = p.cost_value ?? (Number(p.shares || 0) * Number(p.average_cost || 0));
                  return (
                    <tr key={p.symbol}>
                      <td className="symbols-cell"><b>{p.symbol}</b><div className="muted">{p.price_date || '-'} · {p.price_source || '-'}</div></td>
                      <td>{shares(p.shares)}</td>
                      <td>{money(p.average_cost)}</td>
                      <td>{money(p.price)}</td>
                      <td>{money(costValue)}</td>
                      <td>{money(p.market_value)}</td>
                      <td className={Number(p.unrealized_pnl || 0) >= 0 ? 'pos' : 'neg'}>{money(p.unrealized_pnl)}</td>
                      <td className={Number(p.unrealized_return || 0) >= 0 ? 'pos' : 'neg'}>{pct(p.unrealized_return)}</td>
                      <td>{formatWeight(p.weight)}</td>
                      <td>{pct(p.risk_contribution)}</td>
                      <td><span className={`signal signal-${String(p.status || 'HOLD').toLowerCase()}`}>{status(p.status || 'HOLD')}</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="expand-grid">
        <div className="card">
          <h3>{t('portfolio.health')}</h3>
          <div className="diag-row"><span>{t('portfolio.risk_status')}</span><b>{status(risk.status || 'UNAVAILABLE')}</b></div>
          <div className="diag-row"><span>{t('portfolio.volatility_63')}</span><b>{pct(risk.volatility_63)}</b></div>
          <div className="diag-row"><span>{t('portfolio.volatility_252')}</span><b>{pct(risk.volatility_252)}</b></div>
          <div className="diag-row"><span>{t('portfolio.largest_position')}</span><b>{pct(risk.max_position_weight)}</b></div>
          <div className="diag-row"><span>{t('portfolio.hhi')}</span><b>{risk.hhi == null ? '-' : Number(risk.hhi).toFixed(3)}</b></div>
          <div className="muted" style={{ marginTop: 10 }}>{t('portfolio.risk_info_only')}</div>
        </div>

        <div className="card">
          <h3>{t('portfolio.deploy_cash')}</h3>
          <div className="muted">{t('portfolio.buy_only', { policy: suggestions.policy || '—' })}</div>
          {(suggestions.suggestions || []).length === 0 ? (
            <p>{t('portfolio.no_suggestion')}</p>
          ) : (
            <div className="suggestion-list">
              {suggestions.suggestions.slice(0, 6).map((s) => (
                <div className="diag-row" key={s.symbol}>
                  <span><b>{s.symbol}</b> · {pct(s.current_weight)} → {t('portfolio.reference', { value: pct(s.target_weight) })}</span>
                  <b>{money(s.amount)}</b>
                </div>
              ))}
            </div>
          )}
          <div className="diag-row"><span>{t('portfolio.available_cash')}</span><b>{money(suggestions.available_cash || 0)}</b></div>
        </div>
      </div>

      <div className="card invariant-card">
        <h3>{t('portfolio.invariants')}</h3>
        <div className="invariant-grid">
          {(dashboard.invariants || []).map((x) => <div key={x}>✓ {invariantText(x)}</div>)}
        </div>
      </div>
    </div>
  );
}
