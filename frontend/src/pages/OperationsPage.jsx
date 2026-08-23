import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import {
  confirmSettlement,
  lockNav,
  reconcileBroker,
  recordCorporateActionReceipt,
  resolveRestatement,
  syncCorporateActions,
  updateSecurity,
  verifyCorporateAction,
} from '../lib/api.js';
import { formatMoney, formatShares } from '../lib/format.js';

function parsePositions(text) {
  const out = {};
  for (const raw of String(text || '').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    const [symbolRaw, qtyRaw] = line.split(/[=,:;\s]+/, 2);
    const symbol = String(symbolRaw || '').toUpperCase();
    const qty = Number(String(qtyRaw || '').replaceAll(',', ''));
    if (!/^[A-Z0-9]{2,10}$/.test(symbol) || !Number.isFinite(qty) || qty < 0) {
      throw new Error(`Invalid broker position line: ${line}`);
    }
    out[symbol] = qty;
  }
  return out;
}

export default function OperationsPage({ operations = {}, today = '', locale = 'en' }) {
  const vi = locale === 'vi';
  const text = (en, viText) => vi ? viText : en;
  const money = (v) => v == null ? '-' : `${formatMoney(v, false, locale)} VND`;
  const pct = (v) => v == null ? '-' : `${(Number(v) * 100).toFixed(2)}%`;
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [brokerCash, setBrokerCash] = useState('');
  const defaultPositions = useMemo(() => {
    const grouped = {};
    for (const lot of operations.tax_lots || []) grouped[lot.symbol] = (grouped[lot.symbol] || 0) + Number(lot.remaining_quantity || 0);
    return Object.entries(grouped).map(([s, q]) => `${s}=${q}`).join('\n');
  }, [operations.tax_lots]);
  const [brokerPositions, setBrokerPositions] = useState(defaultPositions);

  async function run(action) {
    setBusy(true); setMessage('');
    try { const result = await action(); setMessage(result?.message || text('Saved. Reloading…', 'Đã lưu. Đang tải lại…')); setTimeout(() => window.location.reload(), 250); }
    catch (err) { setMessage(err.message); setBusy(false); }
  }

  const settlement = operations.settlement || {};
  const exceptions = operations.exceptions || [];
  const taxLots = operations.tax_lots || [];
  const actions = operations.corporate_actions || [];
  const securities = operations.securities || [];
  const reconciliations = operations.reconciliations || [];
  const navs = operations.nav_controls || [];
  const restatements = operations.restatements || [];
  const attribution = operations.pnl_attribution || [];

  return <div className="page">
    <AppNav active="operations" locale={locale} />
    <header className="page-head"><div>
      <h1>{text('Operations & Book Controls', 'Vận hành & Kiểm soát sổ')}</h1>
      <p className="muted">{text('Institutional-lite IBOR controls: settlement, tax lots, reconciliation, corporate actions, NAV restatement and exceptions.', 'Kiểm soát IBOR institutional-lite: thanh toán, tax lot, đối soát, quyền doanh nghiệp, restatement NAV và ngoại lệ.')}</p>
    </div></header>

    <div className="metric-grid compact-metrics">
      <div className="metric-card"><span>{text('Book', 'Loại sổ')}</span><b>{operations.book_type || '-'}</b></div>
      <div className="metric-card"><span>{text('Open exceptions', 'Ngoại lệ mở')}</span><b>{exceptions.length}</b></div>
      <div className="metric-card"><span>{text('Settled cash', 'Tiền đã thanh toán')}</span><b>{money(settlement.settled_cash)}</b></div>
      <div className="metric-card"><span>{text('Projected cash', 'Tiền dự kiến')}</span><b>{money(settlement.projected_cash)}</b></div>
      <div className="metric-card"><span>{text('Unsettled payable', 'Phải trả chưa thanh toán')}</span><b>{money(settlement.unsettled_payable)}</b></div>
      <div className="metric-card"><span>{text('Available to invest', 'Có thể đầu tư')}</span><b>{money(settlement.available_to_invest)}</b></div>
    </div>

    <section className="card">
      <div className="section-head"><div><h3>{text('Exceptions', 'Ngoại lệ')}</h3><p className="muted">{text('Work this list first. It is the operational control queue.', 'Ưu tiên xử lý danh sách này. Đây là hàng đợi kiểm soát vận hành.')}</p></div></div>
      {exceptions.length ? <div className="health-flags">{exceptions.map((x, i) => <div key={`${x.code}-${i}`} className="diag-row"><span><b>{x.severity}</b> · {x.code}</span><span>{x.message}</span></div>)}</div> : <div className="empty-state">{text('No open operational exceptions.', 'Không có ngoại lệ vận hành đang mở.')}</div>}
    </section>

    <section className="card">
      <div className="section-head"><div><h3>{text('Settlement book', 'Sổ thanh toán')}</h3><p className="muted">{text('Positions are recognized on trade date; cash is separated into settled and unsettled components.', 'Vị thế ghi nhận theo ngày giao dịch; tiền được tách đã thanh toán và chưa thanh toán.')}</p></div></div>
      <div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>{text('Side', 'Chiều')}</th><th>{text('Ticker', 'Mã')}</th><th>{text('Trade date', 'Ngày GD')}</th><th>{text('Settlement', 'Ngày TT')}</th><th>{text('Cash effect', 'Tác động tiền')}</th><th>Status</th><th>{text('Action', 'Thao tác')}</th></tr></thead>
        <tbody>{(settlement.trades || []).map(t => <tr key={t.event_id}><td>{t.event_id}</td><td>{t.side}</td><td>{t.symbol}</td><td>{t.trade_date}</td><td>{t.settlement_date}<div className="muted">{t.settlement_date_source}</div></td><td>{money(t.cash_effect)}</td><td>{t.status}</td><td>{t.status !== 'SETTLED' ? <button className="btn-small" disabled={busy} onClick={() => run(() => confirmSettlement(t.event_id, 'Confirmed against broker/custodian'))}>{text('Confirm settled', 'Xác nhận đã TT')}</button> : '✓'}</td></tr>)}</tbody>
      </table></div>
    </section>

    <section className="card">
      <h3>{text('Broker reconciliation', 'Đối soát với broker')}</h3>
      <p className="muted">{text('Enter the broker statement quantities and settled cash. QPort stores each reconciliation run; it never changes the ledger automatically.', 'Nhập số lượng và tiền đã thanh toán theo sao kê broker. QPort lưu từng lần đối soát; không tự sửa ledger.')}</p>
      <div className="form-grid"><label>{text('Broker cash (VND)', 'Tiền broker (VND)')}<input value={brokerCash} onChange={e => setBrokerCash(e.target.value)} placeholder="50000000" /></label><label>{text('As of date', 'Ngày đối soát')}<input value={today} readOnly /></label></div>
      <label>{text('Positions — one SYMBOL=QTY per line', 'Vị thế — mỗi dòng MÃ=SỐ_LƯỢNG')}<textarea className="ops-textarea" value={brokerPositions} onChange={e => setBrokerPositions(e.target.value)} /></label>
      <div className="button-row"><button className="btn-export" disabled={busy} onClick={() => run(() => reconcileBroker({ as_of_date: today, cash: Number(String(brokerCash).replaceAll(',', '')), positions: parsePositions(brokerPositions), source: 'MANUAL_BROKER' }))}>{text('Run reconciliation', 'Chạy đối soát')}</button></div>
      {reconciliations[0] && <div className="run-message">{text('Latest', 'Gần nhất')} #{reconciliations[0].id}: <b>{reconciliations[0].status}</b> · cash diff {money(reconciliations[0].cash_difference)}</div>}
    </section>

    <section className="card">
      <div className="section-head"><div><h3>{text('Tax lots · FIFO', 'Tax lot · FIFO')}</h3><p className="muted">{text('Average cost remains a display metric; disposal accounting is lot-aware FIFO.', 'Giá vốn bình quân vẫn là metric hiển thị; hạch toán bán dùng FIFO theo lot.')}</p></div></div>
      <div className="table-scroll"><table className="ranking"><thead><tr><th>Lot</th><th>{text('Ticker', 'Mã')}</th><th>{text('Acquired', 'Ngày mua')}</th><th>{text('Original qty', 'SL gốc')}</th><th>{text('Remaining', 'Còn lại')}</th><th>{text('Unit cost', 'Giá vốn/CP')}</th><th>{text('Cost basis', 'Tổng giá vốn')}</th></tr></thead><tbody>{taxLots.map(l => <tr key={l.lot_id}><td>{l.lot_id}</td><td>{l.symbol}</td><td>{l.acquisition_date}</td><td>{formatShares(l.original_quantity, locale)}</td><td>{formatShares(l.remaining_quantity, locale)}</td><td>{money(l.unit_cost)}</td><td>{money(l.cost_basis)}</td></tr>)}</tbody></table></div>
    </section>

    <section className="card">
      <div className="section-head"><div><h3>{text('Corporate actions', 'Quyền doanh nghiệp')}</h3><p className="muted">{text('Vnstock is discovery. Verify important events against VSDC/exchange before treating them as authoritative. Detected events never auto-post shares/cash.', 'Vnstock dùng để phát hiện. Xác minh sự kiện quan trọng với VSDC/Sở trước khi coi là authoritative. Event phát hiện không tự ghi cổ phiếu/tiền.')}</p></div><button className="btn-export" disabled={busy} onClick={() => run(() => syncCorporateActions())}>{text('Sync events', 'Đồng bộ sự kiện')}</button></div>
      <div className="muted">Provider: {operations.corporate_action_provider?.provider || '-'} · {operations.corporate_action_provider?.available ? 'AVAILABLE' : 'UNAVAILABLE'}</div>
      <div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>{text('Ticker', 'Mã')}</th><th>{text('Type', 'Loại')}</th><th>{text('Record date', 'Ngày ĐKCC')}</th><th>{text('Expected', 'Dự kiến')}</th><th>{text('Verification', 'Xác minh')}</th><th>Status</th><th>{text('Actions', 'Thao tác')}</th></tr></thead><tbody>{actions.map(a => <tr key={a.id}><td>{a.id}</td><td>{a.symbol}</td><td>{a.action_type}</td><td>{a.record_date || '-'}</td><td>{a.expected_cash != null ? money(a.expected_cash) : a.expected_shares != null ? `${formatShares(a.expected_shares, locale)} shares` : '-'}</td><td>{a.verification_status}</td><td>{a.status}</td><td><div className="row-actions"><button className="btn-small" onClick={() => { const url = window.prompt(text('Paste VSDC/exchange source URL', 'Dán URL nguồn VSDC/Sở')); if (url) run(() => verifyCorporateAction(a.id, url)); }}>{text('Verify', 'Xác minh')}</button><button className="btn-small" onClick={() => { const cash = window.prompt(text('Actual cash received (0 if none)', 'Tiền thực nhận (0 nếu không có)'), '0'); if (cash == null) return; const shares = window.prompt(text('Actual shares received (0 if none)', 'Cổ phiếu thực nhận (0 nếu không có)'), '0'); if (shares == null) return; run(() => recordCorporateActionReceipt(a.id, { received_date: today, actual_cash: Number(cash), actual_shares: Number(shares) })); }}>{text('Record receipt', 'Ghi thực nhận')}</button></div></td></tr>)}</tbody></table></div>
    </section>

    <section className="card"><h3>{text('Security master', 'Security master')}</h3><div className="table-scroll"><table className="ranking"><thead><tr><th>Security ID</th><th>{text('Ticker', 'Mã')}</th><th>{text('Exchange', 'Sàn')}</th><th>ISIN</th><th>{text('Currency', 'Tiền tệ')}</th><th>{text('Action', 'Thao tác')}</th></tr></thead><tbody>{securities.map(s => <tr key={s.security_id}><td>{s.security_id}</td><td>{s.symbol}</td><td>{s.exchange}</td><td>{s.isin || '-'}</td><td>{s.currency}</td><td><button className="btn-small" onClick={() => { const exchange = window.prompt(text('Exchange (HOSE/HNX/UPCOM)', 'Sàn (HOSE/HNX/UPCOM)'), s.exchange || 'UNKNOWN'); if (!exchange) return; const isin = window.prompt('ISIN', s.isin || ''); run(() => updateSecurity(s.symbol, { exchange, isin, currency: s.currency, asset_type: s.asset_type, lot_size: s.lot_size })); }}>{text('Edit', 'Sửa')}</button></td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('NAV controls & restatement', 'Kiểm soát NAV & restatement')}</h3>{restatements.filter(r => r.status === 'OPEN').map(r => <div key={r.id} className="diag-row"><span><b>RESTATEMENT #{r.id}</b> · {r.affected_from_date}<div className="muted">{r.reason}</div></span><button className="btn-small" onClick={() => run(() => resolveRestatement(r.id))}>{text('Resolve after review', 'Đóng sau khi review')}</button></div>)}<div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Date', 'Ngày')}</th><th>NAV</th><th>{text('Quality', 'Chất lượng')}</th><th>{text('NAV status', 'Trạng thái NAV')}</th><th>{text('Action', 'Thao tác')}</th></tr></thead><tbody>{navs.slice(0, 30).map(n => <tr key={n.snapshot_date}><td>{n.snapshot_date}</td><td>{money(n.nav)}</td><td>{n.data_quality}</td><td>{n.nav_status}</td><td>{n.official && n.nav_status !== 'LOCKED' ? <button className="btn-small" onClick={() => run(() => lockNav(n.snapshot_date))}>{text('Lock', 'Khóa')}</button> : '-'}</td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('P/L attribution · since recorded capital', 'Phân rã P/L · từ vốn ghi nhận')}</h3><div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Ticker', 'Mã')}</th><th>{text('Unrealized', 'Chưa thực hiện')}</th><th>{text('Realized', 'Đã thực hiện')}</th><th>{text('Dividends', 'Cổ tức')}</th><th>{text('Total contribution', 'Đóng góp tổng')}</th></tr></thead><tbody>{attribution.map(a => <tr key={a.symbol}><td>{a.symbol}</td><td>{money(a.unrealized_pnl)}</td><td>{money(a.realized_pnl)}</td><td>{money(a.dividend_income)}</td><td>{money(a.total_contribution_vnd)}</td></tr>)}</tbody></table></div></section>

    {message && <div className="run-message" style={{ marginTop: 12 }}>{message}</div>}
  </div>;
}
