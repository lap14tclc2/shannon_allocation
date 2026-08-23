import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import {
  confirmSettlement, lockNav, postCorporateActionReceipt, reconcileBroker,
  recordCorporateActionReceipt, resolveRestatement, syncCorporateActions,
  updateSecurity, verifyCorporateAction,
} from '../lib/api.js';
import { formatMoney, formatShares } from '../lib/format.js';
import { parseVndMoneyInput } from '../lib/validation.js';

function parsePositions(text) {
  const out = {};
  for (const raw of String(text || '').split(/\r?\n/)) {
    const line = raw.trim(); if (!line) continue;
    const [symbolRaw, qtyRaw] = line.split(/[=,:;\s]+/, 2);
    const symbol = String(symbolRaw || '').toUpperCase();
    const qty = Number(String(qtyRaw || '').replaceAll(',', ''));
    if (!/^[A-Z0-9]{2,10}$/.test(symbol) || !Number.isFinite(qty) || qty < 0) throw new Error(`Invalid broker position line: ${line}`);
    out[symbol] = qty;
  }
  return out;
}

export default function OperationsPage({ operations = {}, today = '', locale = 'en' }) {
  const vi = locale === 'vi';
  const text = (en, v) => vi ? v : en;
  const money = (v) => v == null ? '-' : `${formatMoney(v, false, locale)} VND`;
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [brokerCash, setBrokerCash] = useState('');
  const defaultPositions = useMemo(() => {
    const g = {}; for (const lot of operations.tax_lots || []) g[lot.symbol] = (g[lot.symbol] || 0) + Number(lot.remaining_quantity || 0);
    return Object.entries(g).map(([s,q]) => `${s}=${q}`).join('\n');
  }, [operations.tax_lots]);
  const [brokerPositions, setBrokerPositions] = useState(defaultPositions);

  async function run(action) {
    setBusy(true); setMessage('');
    try { const result = await action(); setMessage(result?.message || text('Saved. Reloading…','Đã lưu. Đang tải lại…')); setTimeout(() => window.location.reload(), 200); }
    catch (err) { setMessage(err.message); setBusy(false); }
  }

  const settlement = operations.settlement || {};
  const exceptions = operations.exceptions || [];
  const actions = operations.corporate_actions || [];
  const recs = operations.reconciliations || [];
  const restatements = operations.restatements || [];

  function recordReceipt(action) {
    const cashRaw = window.prompt(text('Actual cash received (supports 20tr/20m/20.000.000)', 'Tiền thực nhận (hỗ trợ 20tr/20m/20.000.000)'), '0');
    if (cashRaw == null) return;
    const sharesRaw = window.prompt(text('Actual shares received', 'Cổ phiếu thực nhận'), '0');
    if (sharesRaw == null) return;
    let cash;
    try { cash = String(cashRaw).trim() === '0' ? 0 : parseVndMoneyInput(cashRaw, 'actual_cash', locale); }
    catch (err) { setMessage(err.message); return; }
    const shares = Number(sharesRaw);
    if (!Number.isFinite(shares) || shares < 0) { setMessage(text('Invalid share quantity.','Số lượng cổ phiếu không hợp lệ.')); return; }
    run(() => recordCorporateActionReceipt(action.id, { received_date: today, actual_cash: cash, actual_shares: shares }));
  }

  return <div className="page">
    <AppNav active="operations" locale={locale} />
    <header className="page-head"><div><h1>{text('Operations & Book Controls','Vận hành & Kiểm soát sổ')}</h1><p className="muted">{text('Institutional-lite IBOR: settlement, FIFO lots, broker reconciliation, corporate actions, NAV controls and exceptions.','IBOR institutional-lite: settlement, lot FIFO, đối soát broker, quyền doanh nghiệp, kiểm soát NAV và ngoại lệ.')}</p></div></header>

    <div className="metric-grid compact-metrics">
      <div className="metric-card"><span>{text('Book','Loại sổ')}</span><b>{operations.book_type || '-'}</b></div>
      <div className="metric-card"><span>{text('Open exceptions','Ngoại lệ mở')}</span><b>{exceptions.length}</b></div>
      <div className="metric-card"><span>{text('Settled cash','Tiền đã thanh toán')}</span><b>{money(settlement.settled_cash)}</b></div>
      <div className="metric-card"><span>{text('Projected cash','Tiền dự kiến')}</span><b>{money(settlement.projected_cash)}</b></div>
      <div className="metric-card"><span>{text('Unsettled payable','Phải trả chưa TT')}</span><b>{money(settlement.unsettled_payable)}</b></div>
      <div className="metric-card"><span>{text('Available to invest','Có thể đầu tư')}</span><b>{money(settlement.available_to_invest)}</b></div>
    </div>

    <section className="card"><h3>{text('Exception queue','Hàng đợi ngoại lệ')}</h3><p className="muted">{text('Resolve operational exceptions before relying on the book.','Xử lý ngoại lệ vận hành trước khi dựa vào sổ.')}</p>{exceptions.length ? <div className="health-flags">{exceptions.map((x,i)=><div className="diag-row" key={`${x.code}-${i}`}><span><b>{x.severity}</b> · {x.code}</span><span>{x.message}</span></div>)}</div> : <div className="empty-state">{text('No open exceptions.','Không có ngoại lệ mở.')}</div>}</section>

    <section className="card"><h3>{text('Settlement book','Sổ settlement')}</h3><p className="muted">{text('Trade-date positions; settled and unsettled cash are tracked separately. T+2 is an estimate unless explicitly entered/confirmed.','Vị thế theo ngày giao dịch; tiền settled/unsettled được tách riêng. T+2 chỉ là ước tính nếu chưa nhập/xác nhận.')}</p><div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>Side</th><th>{text('Ticker','Mã')}</th><th>{text('Trade date','Ngày GD')}</th><th>{text('Settlement','Ngày TT')}</th><th>{text('Cash effect','Tác động tiền')}</th><th>Status</th><th>{text('Action','Thao tác')}</th></tr></thead><tbody>{(settlement.trades||[]).map(t=><tr key={t.event_id}><td>{t.event_id}</td><td>{t.side}</td><td>{t.symbol}</td><td>{t.trade_date}</td><td>{t.settlement_date}<div className="muted">{t.settlement_date_source}</div></td><td>{money(t.cash_effect)}</td><td>{t.status}</td><td>{t.status==='SETTLED'?'✓':<button className="btn-small" disabled={busy} onClick={()=>run(()=>confirmSettlement(t.event_id,'Confirmed against broker/custodian'))}>{text('Confirm settled','Xác nhận settled')}</button>}</td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('Broker reconciliation','Đối soát broker')}</h3><p className="muted">{text('Compare broker settled cash and quantities against QPort. Differences create exceptions; they never auto-correct the ledger.','So sánh tiền settled và số lượng broker với QPort. Sai lệch tạo ngoại lệ; không tự sửa ledger.')}</p><div className="form-grid"><label>{text('Broker settled cash','Tiền settled theo broker')}<input value={brokerCash} onChange={e=>setBrokerCash(e.target.value)} placeholder="50tr" /></label><label>{text('As of','Ngày đối soát')}<input value={today} readOnly /></label></div><label>{text('Positions — SYMBOL=QTY per line','Vị thế — mỗi dòng MÃ=SỐ_LƯỢNG')}<textarea className="ops-textarea" value={brokerPositions} onChange={e=>setBrokerPositions(e.target.value)} /></label><div className="button-row"><button className="btn-export" disabled={busy} onClick={()=>run(()=>reconcileBroker({ as_of_date:today, cash:parseVndMoneyInput(brokerCash,'broker_cash',locale), positions:parsePositions(brokerPositions), source:'MANUAL_BROKER' }))}>{text('Run reconciliation','Chạy đối soát')}</button></div>{recs[0]&&<div className="run-message">#{recs[0].id} <b>{recs[0].status}</b> · cash diff {money(recs[0].cash_difference)}</div>}</section>

    <section className="card"><h3>{text('Tax lots · FIFO','Tax lot · FIFO')}</h3><p className="muted">{text('Average cost is display-only; realized disposal accounting consumes lots FIFO.','Giá vốn bình quân chỉ để hiển thị; realized P/L khi bán xuất lot FIFO.')}</p><div className="table-scroll"><table className="ranking"><thead><tr><th>Lot</th><th>{text('Ticker','Mã')}</th><th>{text('Acquired','Ngày mua')}</th><th>{text('Original','SL gốc')}</th><th>{text('Remaining','Còn lại')}</th><th>{text('Unit cost','Giá vốn/CP')}</th><th>{text('Cost basis','Tổng giá vốn')}</th><th>Account</th></tr></thead><tbody>{(operations.tax_lots||[]).map(l=><tr key={l.lot_id}><td>{l.lot_id}</td><td>{l.symbol}</td><td>{l.acquisition_date}</td><td>{formatShares(l.original_quantity,locale)}</td><td>{formatShares(l.remaining_quantity,locale)}</td><td>{money(l.unit_cost)}</td><td>{money(l.cost_basis)}</td><td>{l.account_id}</td></tr>)}</tbody></table></div></section>

    <section className="card"><div className="section-head"><div><h3>{text('Corporate actions','Quyền doanh nghiệp')}</h3><p className="muted">{text('Vnstock discovers events. VERIFIED requires VSDC/HOSE/HNX URL. Receipt and ledger posting are separate explicit steps.','Vnstock phát hiện event. VERIFIED yêu cầu URL VSDC/HOSE/HNX. Thực nhận và post vào ledger là hai bước explicit riêng.')}</p></div><button className="btn-export" disabled={busy} onClick={()=>run(()=>syncCorporateActions())}>{text('Sync events','Đồng bộ event')}</button></div><div className="muted">Provider: {operations.corporate_action_provider?.provider || '-'} · {operations.corporate_action_provider?.available?'AVAILABLE':'UNAVAILABLE'}</div><div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>{text('Ticker','Mã')}</th><th>{text('Type','Loại')}</th><th>{text('Record date','Ngày ĐKCC')}</th><th>{text('Expected','Dự kiến')}</th><th>{text('Verification','Xác minh')}</th><th>Status</th><th>{text('Ledger','Ledger')}</th><th>{text('Actions','Thao tác')}</th></tr></thead><tbody>{actions.map(a=><tr key={a.id}><td>{a.id}</td><td>{a.symbol}</td><td>{a.action_type}</td><td>{a.record_date||'-'}</td><td>{a.expected_cash!=null?money(a.expected_cash):a.expected_shares!=null?`${formatShares(a.expected_shares,locale)} shares`:'-'}</td><td>{a.verification_status}</td><td>{a.status}</td><td>{a.ledger_posted?`POSTED #${(a.postings||[]).map(p=>p.event_id).join(', #')}`:'NOT POSTED'}</td><td><div className="row-actions"><button className="btn-small" onClick={()=>{const url=window.prompt(text('Paste authoritative VSDC/HOSE/HNX URL','Dán URL authoritative VSDC/HOSE/HNX')); if(url)run(()=>verifyCorporateAction(a.id,url));}}>{text('Verify','Xác minh')}</button><button className="btn-small" onClick={()=>recordReceipt(a)}>{text('Record receipt','Ghi thực nhận')}</button>{a.status==='RECONCILED'&&a.verification_status==='VERIFIED'&&!a.ledger_posted&&<button className="btn-export btn-small" onClick={()=>{if(window.confirm(text('Post this reconciled receipt into the immutable ledger?','Post thực nhận đã đối soát này vào immutable ledger?')))run(()=>postCorporateActionReceipt(a.id));}}>{text('Post to ledger','Post vào ledger')}</button>}</div></td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('Security master','Security master')}</h3><div className="table-scroll"><table className="ranking"><thead><tr><th>Security ID</th><th>{text('Ticker','Mã')}</th><th>{text('Exchange','Sàn')}</th><th>ISIN</th><th>Currency</th><th>{text('Action','Thao tác')}</th></tr></thead><tbody>{(operations.securities||[]).map(s=><tr key={s.security_id}><td>{s.security_id}</td><td>{s.symbol}</td><td>{s.exchange}</td><td>{s.isin||'-'}</td><td>{s.currency}</td><td><button className="btn-small" onClick={()=>{const exchange=window.prompt(text('Exchange','Sàn'),s.exchange||'UNKNOWN'); if(!exchange)return; const isin=window.prompt('ISIN',s.isin||''); run(()=>updateSecurity(s.symbol,{exchange,isin,currency:s.currency,asset_type:s.asset_type,lot_size:s.lot_size}));}}>{text('Edit','Sửa')}</button></td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('NAV controls & restatement','Kiểm soát NAV & restatement')}</h3>{restatements.filter(r=>r.status==='OPEN').map(r=><div className="diag-row" key={r.id}><span><b>RESTATEMENT #{r.id}</b> · {r.affected_from_date}<div className="muted">{r.reason}</div></span><button className="btn-small" onClick={()=>run(()=>resolveRestatement(r.id))}>{text('Resolve after review','Đóng sau review')}</button></div>)}<div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Date','Ngày')}</th><th>NAV</th><th>{text('Quality','Chất lượng')}</th><th>Status</th><th>{text('Action','Thao tác')}</th></tr></thead><tbody>{(operations.nav_controls||[]).slice(0,30).map(n=><tr key={n.snapshot_date}><td>{n.snapshot_date}</td><td>{money(n.nav)}</td><td>{n.data_quality}</td><td>{n.nav_status}</td><td>{n.official&&!['LOCKED','RESTATED'].includes(n.nav_status)?<button className="btn-small" onClick={()=>run(()=>lockNav(n.snapshot_date))}>{text('Lock','Khóa')}</button>:'-'}</td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('P/L attribution','Phân rã P/L')}</h3><div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Ticker','Mã')}</th><th>{text('Unrealized','Chưa thực hiện')}</th><th>{text('Realized','Đã thực hiện')}</th><th>{text('Dividends','Cổ tức')}</th><th>{text('Total','Tổng đóng góp')}</th></tr></thead><tbody>{(operations.pnl_attribution||[]).map(a=><tr key={a.symbol}><td>{a.symbol}</td><td>{money(a.unrealized_pnl)}</td><td>{money(a.realized_pnl)}</td><td>{money(a.dividend_income)}</td><td>{money(a.total_contribution_vnd)}</td></tr>)}</tbody></table></div></section>
    {message&&<div className="run-message">{message}</div>}
  </div>;
}
