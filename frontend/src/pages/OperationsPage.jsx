import React, { useMemo, useState } from 'react';
import AppNav from '../components/AppNav.jsx';
import {
  confirmSettlement, getLatestDividend, lockNav, postCorporateActionReceipt, reconcileBroker,
  recordCorporateActionReceipt, resolveAllSecurities, resolveRestatement, resolveSecurity,
  syncCorporateActions, updateSecurity, verifyCorporateAction,
} from '../lib/api.js';
import { BROKERS } from '../lib/brokers.js';
import { formatShares, money as moneyFn } from '../lib/format.js';
import { parseVndMoneyInput, validateBrokerAccount } from '../lib/validation.js';
import { chooseText } from '../i18n.js';

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

function lotsToText(lots, broker, account) {
  const grouped = {};
  for (const lot of lots || []) {
    if ((lot.broker_code || 'UNASSIGNED') !== broker || (lot.account_id || 'PRIMARY') !== account) continue;
    grouped[lot.symbol] = (grouped[lot.symbol] || 0) + Number(lot.remaining_quantity || 0);
  }
  return Object.entries(grouped).map(([s,q]) => `${s}=${q}`).join('\n');
}

export default function OperationsPage({ operations = {}, today = '', locale = 'en' }) {
  const text = (en, vi) => chooseText(locale, en, vi);
  const money = (v) => moneyFn(v, locale, 'VND');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [brokerCash, setBrokerCash] = useState('');
  const [brokerCode, setBrokerCode] = useState('UNASSIGNED');
  const [accountId, setAccountId] = useState('PRIMARY');
  const [brokerPositions, setBrokerPositions] = useState(() => lotsToText(operations.tax_lots, 'UNASSIGNED', 'PRIMARY'));
  const [caEdits, setCaEdits] = useState({});
  const [securityEdits, setSecurityEdits] = useState({});
  const [dividendSymbol, setDividendSymbol] = useState(() => operations.securities?.[0]?.symbol || '');
  const [dividendBusy, setDividendBusy] = useState(false);
  const [dividendResult, setDividendResult] = useState(null);
  const [dividendError, setDividendError] = useState('');

  async function run(action, reload = true) {
    setBusy(true); setMessage('');
    try {
      const result = await action();
      setMessage(result?.message || text('Saved.','Đã lưu.'));
      if (reload) setTimeout(() => window.location.reload(), 200);
      else setBusy(false);
      return result;
    } catch (err) { setMessage(err.message); setBusy(false); return null; }
  }

  const settlement = operations.settlement || {};
  const exceptions = operations.exceptions || [];
  const actions = operations.corporate_actions || [];
  const recs = operations.reconciliations || [];
  const restatements = operations.restatements || [];
  const securities = operations.securities || [];
  const caProvider = operations.corporate_action_provider || {};

  async function lookupDividend() {
    const symbol = String(dividendSymbol || '').toUpperCase().trim();
    if (!/^[A-Z0-9]{2,10}$/.test(symbol)) {
      setDividendError(text('Enter a valid ticker.', 'Nhập mã cổ phiếu hợp lệ.'));
      setDividendResult(null); return;
    }
    setDividendBusy(true); setDividendError(''); setDividendResult(null);
    try { setDividendResult(await getLatestDividend(symbol)); }
    catch (err) { setDividendError(err.message); }
    finally { setDividendBusy(false); }
  }

  function changeBroker(code) {
    setBrokerCode(code);
    setBrokerPositions(lotsToText(operations.tax_lots, code, accountId));
  }
  function changeAccount(value) {
    const clean = value.toUpperCase().replace(/[^A-Z0-9_.-]/g,'');
    setAccountId(clean);
    setBrokerPositions(lotsToText(operations.tax_lots, brokerCode, clean || 'PRIMARY'));
  }
  function caValue(action) {
    return caEdits[action.id] || { source_url: action.source_url || '', actual_cash: action.receipt?.actual_cash ? String(action.receipt.actual_cash) : '0', actual_shares: action.receipt?.actual_shares ? String(action.receipt.actual_shares) : '0' };
  }
  function setCA(action, key, value) { setCaEdits(x => ({ ...x, [action.id]: { ...caValue(action), [key]: value } })); }
  async function recordReceipt(action) {
    const edit = caValue(action);
    let cash;
    try { cash = String(edit.actual_cash).trim() === '0' ? 0 : parseVndMoneyInput(edit.actual_cash, 'actual_cash', locale); }
    catch (err) { setMessage(err.message); return; }
    const shares = Number(edit.actual_shares || 0);
    if (!Number.isFinite(shares) || shares < 0) { setMessage(text('Invalid share quantity.','Số lượng cổ phiếu không hợp lệ.')); return; }
    return run(() => recordCorporateActionReceipt(action.id, { received_date: today, actual_cash: cash, actual_shares: shares }));
  }
  function securityValue(s) { return securityEdits[s.symbol] || { exchange: s.exchange || 'UNKNOWN', lot_size: s.lot_size == null ? '' : String(s.lot_size) }; }
  function setSecurity(s, key, value) { setSecurityEdits(x => ({ ...x, [s.symbol]: { ...securityValue(s), [key]: value } })); }
  function securityDirty(s) {
    const edit = securityEdits[s.symbol]; if (!edit) return false;
    return edit.exchange !== (s.exchange || 'UNKNOWN') || edit.lot_size !== (s.lot_size == null ? '' : String(s.lot_size));
  }
  async function saveSecurity(s) {
    const edit = securityValue(s);
    const lot = edit.lot_size === '' ? null : Number(edit.lot_size);
    if (lot != null && (!Number.isFinite(lot) || lot <= 0)) { setMessage(text('Lot size must be positive.','Kích thước lot phải lớn hơn 0.')); return; }
    return run(() => updateSecurity(s.symbol, { exchange: edit.exchange, isin: s.isin, currency: s.currency, asset_type: s.asset_type, lot_size: lot }));
  }

  const latestRecon = useMemo(() => recs.find(r => (r.broker_code || 'UNASSIGNED') === brokerCode && (r.account_id || 'PRIMARY') === accountId) || recs[0], [recs, brokerCode, accountId]);
  const latestComponents = dividendResult?.latest_components?.length ? dividendResult.latest_components : (dividendResult?.latest ? [dividendResult.latest] : []);
  const providerStatus = caProvider.status || (caProvider.available === true ? 'AVAILABLE' : caProvider.available === false ? 'UNAVAILABLE' : 'NOT_PROBED');

  return <div className="page">
    <AppNav active="operations" locale={locale} />
    <header className="page-head"><div><h1>{text('Operations & Book Controls','Vận hành & Kiểm soát sổ')}</h1><p className="muted">{text('Institutional-lite IBOR: settlement, broker/account lots, reconciliation, corporate actions, security master, NAV controls and exceptions.','IBOR institutional-lite: settlement, lot theo broker/tài khoản, đối soát, quyền doanh nghiệp, security master, kiểm soát NAV và ngoại lệ.')}</p></div></header>

    <div className="metric-grid compact-metrics">
      <div className="metric-card"><span>{text('Book','Loại sổ')}</span><b>{operations.book_type || '-'}</b></div>
      <div className="metric-card"><span>{text('Open exceptions','Ngoại lệ mở')}</span><b>{exceptions.length}</b></div>
      <div className="metric-card"><span>{text('Settled cash','Tiền đã thanh toán')}</span><b>{money(settlement.settled_cash)}</b></div>
      <div className="metric-card"><span>{text('Projected cash','Tiền dự kiến')}</span><b>{money(settlement.projected_cash)}</b></div>
      <div className="metric-card"><span>{text('Audit chain','Chuỗi audit')}</span><b>{operations.activity_integrity?.status || '-'}</b></div>
    </div>

    <section className="card"><h3>{text('Exception queue','Hàng đợi ngoại lệ')}</h3><p className="muted">{text('Resolve operational exceptions before relying on the book.','Xử lý ngoại lệ vận hành trước khi dựa vào sổ.')}</p>{exceptions.length ? <div className="health-flags">{exceptions.map((x,i)=><div className="diag-row" key={`${x.code}-${i}`}><span><b>{x.severity}</b> · {x.code}</span><span>{x.message}</span></div>)}</div> : <div className="empty-state">{text('No open exceptions.','Không có ngoại lệ mở.')}</div>}</section>

    <section className="card"><h3>{text('Settlement book','Sổ settlement')}</h3><div className="table-scroll"><table className="ranking"><thead><tr><th>ID</th><th>Side</th><th>{text('Ticker','Mã')}</th><th>Broker</th><th>Account</th><th>{text('Trade date','Ngày GD')}</th><th>{text('Settlement','Ngày TT')}</th><th>{text('Cash effect','Tác động tiền')}</th><th>Status</th><th>{text('Action','Thao tác')}</th></tr></thead><tbody>{(settlement.trades||[]).map(t=><tr key={t.event_id}><td>{t.event_id}</td><td>{t.side}</td><td>{t.symbol}</td><td>{t.broker_code || 'UNASSIGNED'}</td><td>{t.account_id || 'PRIMARY'}</td><td>{t.trade_date}</td><td>{t.settlement_date}<div className="muted">{t.settlement_date_source}</div></td><td>{money(t.cash_effect)}</td><td>{t.status}</td><td>{t.status==='SETTLED'?'✓':<button className="btn-small" disabled={busy} onClick={()=>run(()=>confirmSettlement(t.event_id,'Confirmed against broker/custodian'))}>{text('Confirm settled','Xác nhận settled')}</button>}</td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('Broker reconciliation','Đối soát broker')}</h3><p className="muted">{text('Choose the exact broker/account book. Only events assigned to that broker/account are compared.','Chọn đúng broker/tài khoản. Chỉ event đã gán cho broker/tài khoản đó được đối soát.')}</p><div className="form-grid">
      <label>Broker<select value={brokerCode} onChange={e=>changeBroker(e.target.value)}>{BROKERS.map(b=><option key={b.code} value={b.code}>{b.name}</option>)}</select></label>
      <label>Account<input value={accountId} onChange={e=>changeAccount(e.target.value)} /></label>
      <label>{text('Broker settled cash','Tiền settled theo broker')}<input value={brokerCash} onChange={e=>setBrokerCash(e.target.value)} placeholder="50tr" /></label>
      <label>{text('As of','Ngày đối soát')}<input value={today} readOnly /></label>
    </div><label>{text('Positions — SYMBOL=QTY per line','Vị thế — mỗi dòng MÃ=SỐ_LƯỢNG')}<textarea className="ops-textarea" value={brokerPositions} onChange={e=>setBrokerPositions(e.target.value)} /></label><div className="button-row"><button className="btn-export" disabled={busy} onClick={()=>run(()=>{ const clean=validateBrokerAccount(brokerCode,accountId,locale); return reconcileBroker({ ...clean, as_of_date:today, cash:parseVndMoneyInput(brokerCash,'broker_cash',locale), positions:parsePositions(brokerPositions), source:'MANUAL_BROKER' }); })}>{text('Run reconciliation','Chạy đối soát')}</button></div>{latestRecon&&<div className="run-message">{latestRecon.broker_code || 'UNASSIGNED'}/{latestRecon.account_id || 'PRIMARY'} · #{latestRecon.id} <b>{latestRecon.status}</b> · cash diff {money(latestRecon.cash_difference)}</div>}</section>

    <section className="card"><h3>{text('Tax lots · FIFO','Tax lot · FIFO')}</h3><p className="muted">{text('A broker-assigned SELL consumes only lots inside the same broker/account.','SELL đã gán broker chỉ xuất lot trong cùng broker/tài khoản.')}</p><div className="table-scroll"><table className="ranking"><thead><tr><th>Lot</th><th>{text('Ticker','Mã')}</th><th>Broker</th><th>Account</th><th>{text('Acquired','Ngày mua')}</th><th>{text('Original','SL gốc')}</th><th>{text('Remaining','Còn lại')}</th><th>{text('Unit cost','Giá vốn/CP')}</th><th>{text('Cost basis','Tổng giá vốn')}</th></tr></thead><tbody>{(operations.tax_lots||[]).map(l=><tr key={l.lot_id}><td>{l.lot_id}</td><td>{l.symbol}</td><td>{l.broker_code || 'UNASSIGNED'}</td><td>{l.account_id}</td><td>{l.acquisition_date}</td><td>{formatShares(l.original_quantity,locale)}</td><td>{formatShares(l.remaining_quantity,locale)}</td><td>{money(l.unit_cost)}</td><td>{money(l.cost_basis)}</td></tr>)}</tbody></table></div></section>

    <section className="card">
      <div className="section-head"><div><h3>{text('Latest dividend lookup','Tra cổ tức mới nhất')}</h3><p className="muted">{text('Read-only provider failover: VPS → CafeF → FireAnt public; Vietcap IQ and the FireAnt OAuth API are late fallbacks. One source event may produce both cash and stock dividend components.','Tra cứu read-only theo fallback: VPS → CafeF → FireAnt public; Vietcap IQ và FireAnt OAuth API chỉ là fallback cuối. Một event nguồn có thể sinh cả quyền tiền mặt và quyền cổ phiếu.')}</p></div></div>
      <div className="form-grid">
        <label>{text('Ticker','Mã cổ phiếu')}<input value={dividendSymbol} onChange={e=>setDividendSymbol(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g,'').slice(0,10))} placeholder="FPT" /></label>
        <label>{text('Action','Thao tác')}<button type="button" className="btn-export" disabled={dividendBusy||!dividendSymbol} onClick={lookupDividend}>{dividendBusy?'…':text('Get latest dividend','Lấy cổ tức mới nhất')}</button></label>
      </div>
      {dividendError&&<div className="run-message">{dividendError}</div>}
      {dividendResult&&!dividendResult.found&&<div className="empty-state">{text('No dividend event was found in the configured lookup window.','Không tìm thấy đợt cổ tức trong khoảng tra cứu.')}{(dividendResult.errors||[]).length>0&&<div className="muted">{dividendResult.errors.map(x=>`${x.provider}: ${x.error}`).join(' · ')}</div>}</div>}
      {latestComponents.length>0&&<><div className="muted">{text('Latest event date','Ngày event mới nhất')}: {dividendResult.latest_event_date || latestComponents[0].effective_event_date || '-'} · {(dividendResult.provider_attempts||[]).map(x=>`${x.provider}:${x.status}`).join(' → ')}</div><div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Ticker','Mã')}</th><th>{text('Type','Loại')}</th><th>{text('Ex-date','Ngày GDKHQ')}</th><th>{text('Record date','Ngày ĐKCC')}</th><th>{text('Payment date','Ngày thanh toán')}</th><th>{text('Value / ratio','Giá trị / tỷ lệ')}</th><th>{text('Source','Nguồn')}</th></tr></thead><tbody>{latestComponents.map((item,index)=><tr key={`${item.source_event_id||'event'}-${item.dividend_type}-${index}`}><td><b>{item.symbol}</b></td><td>{item.dividend_type}</td><td>{item.ex_date||'-'}</td><td>{item.record_date||'-'}</td><td>{item.payment_date||'-'}</td><td>{item.dividend_type==='CASH_DIVIDEND'?(item.cash_per_share!=null?`${money(item.cash_per_share)}/CP`:'-'):(item.stock_ratio_percent!=null?`${item.stock_ratio_percent.toFixed(2)}%`:'-')}</td><td>{item.source}<div className="muted">{item.title||''}</div></td></tr>)}</tbody></table></div></>}
    </section>

    <section className="card"><div className="section-head"><div><h3>{text('Corporate actions','Quyền doanh nghiệp')}</h3><p className="muted">{text('Multi-source discovery stores every dividend installment/component as PROVISIONAL. Verification, receipt and ledger posting remain explicit; detection never changes cash or shares.','Discovery đa nguồn lưu từng đợt/component cổ tức ở trạng thái PROVISIONAL. Xác minh, thực nhận và post ledger vẫn explicit; phát hiện event không tự thay đổi tiền hay cổ phiếu.')}</p></div><button className="btn-export" disabled={busy} onClick={()=>run(()=>syncCorporateActions())}>{text('Sync events','Đồng bộ event')}</button></div><div className="muted">Provider: {caProvider.provider || '-'} · {providerStatus}{caProvider.provider_order?.length?` · ${caProvider.provider_order.join(' → ')}`:''}</div><div className="table-scroll"><table className="ranking corporate-action-table"><thead><tr><th>ID</th><th>{text('Ticker','Mã')}</th><th>{text('Type','Loại')}</th><th>{text('Record date','Ngày ĐKCC')}</th><th>{text('Expected','Dự kiến')}</th><th>{text('Verify source URL','URL xác minh')}</th><th>{text('Actual receipt','Thực nhận')}</th><th>Status</th><th>{text('Actions','Thao tác')}</th></tr></thead><tbody>{actions.map(a=>{const edit=caValue(a);return <tr key={a.id}><td>{a.id}</td><td>{a.symbol}</td><td>{a.action_type}</td><td>{a.record_date||a.ex_date||'-'}</td><td>{a.expected_cash!=null?money(a.expected_cash):a.expected_shares!=null?`${formatShares(a.expected_shares,locale)} shares`:'-'}</td><td><input className="inline-wide" value={edit.source_url} onChange={e=>setCA(a,'source_url',e.target.value)} placeholder="https://vsd.vn/..."/><div className="muted">{a.verification_status}</div></td><td><div className="inline-stack"><input value={edit.actual_cash} onChange={e=>setCA(a,'actual_cash',e.target.value)} placeholder={text('Cash','Tiền')}/><input type="number" min="0" value={edit.actual_shares} onChange={e=>setCA(a,'actual_shares',e.target.value)} placeholder={text('Shares','CP')}/></div></td><td>{a.status}<div className="muted">{a.ledger_posted?`POSTED #${(a.postings||[]).map(p=>p.event_id).join(', #')}`:'NOT POSTED'}</div></td><td><div className="inline-stack"><button className="btn-small" disabled={busy||!edit.source_url.trim()} onClick={()=>run(()=>verifyCorporateAction(a.id,edit.source_url.trim()))}>{text('Verify','Xác minh')}</button><button className="btn-small" disabled={busy} onClick={()=>recordReceipt(a)}>{text('Record receipt','Ghi thực nhận')}</button>{a.status==='RECONCILED'&&a.verification_status==='VERIFIED'&&!a.ledger_posted&&<button className="btn-export btn-small" disabled={busy} onClick={()=>run(()=>postCorporateActionReceipt(a.id))}>{text('Post to ledger','Post vào ledger')}</button>}</div></td></tr>})}</tbody></table></div></section>

    <section className="card"><div className="section-head"><div><h3>{text('Security master','Security master')}</h3><p className="muted">{text('ISIN is not calculated from ticker. QPort resolves the real identifier from reference data and leaves it UNRESOLVED when the provider does not expose it.','ISIN không được tính từ ticker. QPort tra identifier thật từ dữ liệu tham chiếu và để UNRESOLVED nếu nguồn không cung cấp.')}</p></div><button className="btn-variant" disabled={busy} onClick={()=>run(()=>resolveAllSecurities())}>{text('Resolve all master data','Tự tra toàn bộ master data')}</button></div><div className="muted">Provider: {operations.security_reference_provider?.provider || '-'} · {operations.security_reference_provider?.available?'AVAILABLE':'UNAVAILABLE'}</div><div className="table-scroll"><table className="ranking"><thead><tr><th>Security ID</th><th>{text('Ticker','Mã')}</th><th>{text('Name','Tên')}</th><th>{text('Exchange','Sàn')}</th><th>ISIN</th><th>{text('Lot size','Kích thước lot')}</th><th>{text('Master status','Trạng thái')}</th><th>{text('Actions','Thao tác')}</th></tr></thead><tbody>{securities.map(s=>{const edit=securityValue(s);return <tr key={s.security_id}><td>{s.security_id}</td><td><b>{s.symbol}</b></td><td>{s.name||'-'}</td><td><select className="inline-control" value={edit.exchange} onChange={e=>setSecurity(s,'exchange',e.target.value)}><option>UNKNOWN</option><option>HOSE</option><option>HNX</option><option>UPCOM</option></select></td><td><code>{s.isin||'UNRESOLVED'}</code><div className="muted">{s.master_data_source||'-'}</div></td><td><input className="inline-control" type="number" min="1" value={edit.lot_size} onChange={e=>setSecurity(s,'lot_size',e.target.value)} placeholder="100"/></td><td>{s.master_data_status||'UNRESOLVED'}</td><td><div className="row-actions">{securityDirty(s)&&<button className="btn-small" onClick={()=>saveSecurity(s)}>{text('Save','Lưu')}</button>}<button className="btn-variant btn-small" disabled={busy} onClick={()=>run(()=>resolveSecurity(s.symbol))}>{text('Resolve','Tự tra')}</button></div></td></tr>})}</tbody></table></div></section>

    <section className="card"><h3>{text('NAV controls & restatement','Kiểm soát NAV & restatement')}</h3>{restatements.filter(r=>r.status==='OPEN').map(r=><div className="diag-row" key={r.id}><span><b>RESTATEMENT #{r.id}</b> · {r.affected_from_date}<div className="muted">{r.reason}</div></span><button className="btn-small" onClick={()=>run(()=>resolveRestatement(r.id))}>{text('Resolve after review','Đóng sau review')}</button></div>)}<div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Date','Ngày')}</th><th>NAV</th><th>{text('Quality','Chất lượng')}</th><th>Status</th><th>{text('Action','Thao tác')}</th></tr></thead><tbody>{(operations.nav_controls||[]).slice(0,30).map(n=><tr key={n.snapshot_date}><td>{n.snapshot_date}</td><td>{money(n.nav)}</td><td>{n.data_quality}</td><td>{n.nav_status}</td><td>{n.official&&!['LOCKED','RESTATED'].includes(n.nav_status)?<button className="btn-small" onClick={()=>run(()=>lockNav(n.snapshot_date))}>{text('Lock','Khóa')}</button>:'-'}</td></tr>)}</tbody></table></div></section>

    <section className="card"><h3>{text('P/L attribution','Phân rã P/L')}</h3><div className="table-scroll"><table className="ranking"><thead><tr><th>{text('Ticker','Mã')}</th><th>{text('Unrealized','Chưa thực hiện')}</th><th>{text('Realized','Đã thực hiện')}</th><th>{text('Dividends','Cổ tức')}</th><th>{text('Total','Tổng đóng góp')}</th></tr></thead><tbody>{(operations.pnl_attribution||[]).map(a=><tr key={a.symbol}><td>{a.symbol}</td><td>{money(a.unrealized_pnl)}</td><td>{money(a.realized_pnl)}</td><td>{money(a.dividend_income)}</td><td>{money(a.total_contribution_vnd)}</td></tr>)}</tbody></table></div></section>
    {message&&<div className="run-message">{message}</div>}
  </div>;
}
