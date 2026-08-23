// SSR + hydration smoke test for bilingual institutional-lite QPort.
import { JSDOM } from 'jsdom';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname=dirname(fileURLToPath(import.meta.url)); const root=join(__dirname,'..');
const position={symbol:'FPT',shares:200,average_cost:65000,price:70000,price_date:'2026-08-21',price_source:'vnstock',cost_value:13000000,market_value:14000000,weight:14/24,equity_weight:1,unrealized_pnl:1000000,unrealized_return:1/13,risk_contribution:1,erc_reference_weight:1,status:'HOLD'};
const performance={returns:{daily:.01,mtd:.03,ytd:.1,since_inception:.12},annualized_twr:.14,xirr:.11,xirr_status:'AVAILABLE',cashflow_history_quality:'COMPLETE',history_status:'SUFFICIENT',total_pnl:1000000,accounting_return:1/23,unrealized_pnl:1000000,realized_pnl:0,dividend_income:200000,fees_and_taxes:10000,net_external_contributions:23000000,cash:10000000,equity_value:14000000,nav:24000000,current_drawdown:-.02,max_drawdown:-.08,snapshot_count:120,official_snapshot_count:118,first_date:'2026-01-02',latest_date:'2026-08-21',best_day:.035,worst_day:-.028,positive_day_ratio:.54,latest:{nav:24000000},series:[{date:'2026-08-20',nav:23700000},{date:'2026-08-21',nav:24000000}],methodology_policy:{policy_version:'QPORT_PERF_V2',cost_method:'FIFO_TAX_LOTS'}};
const risk={status:'VALID',volatility_63:.21,volatility_252:.24,volatility_ratio:.875,max_position_weight:.5833,max_equity_weight:1,equity_hhi:1,effective_positions:1,effective_position_ratio:1,average_correlation:null,max_correlation:null,diversification_ratio:1,daily_var_95:-.021,daily_cvar_95:-.031,max_daily_loss:-.049,downside_volatility:.19,positive_day_ratio:.54,return_observations:240,largest_risk_symbol:'FPT',largest_risk_contribution:1,equal_risk_contribution:1,risk_concentration_ratio:1,risk_contribution_hhi:1,risk_contributions:{FPT:1},erc_reference_weights:{FPT:1},quality:{coverage_weight:1},methodology:{concentration_basis:'equity_normalized'}};
const health={status:'HEALTHY',flags:[],accounting_return:1/23,performance_history_status:'SUFFICIENT',current_drawdown:-.02,max_drawdown:-.08,effective_positions:1,effective_position_ratio:1,equity_hhi:1,max_equity_weight:1,largest_risk_symbol:'FPT',largest_risk_contribution:1,risk_coverage:1,daily_var_95:-.021,daily_cvar_95:-.031,official_snapshot_count:118,cash_weight:10/24};
const dashboard={philosophy:'BUY_AND_HOLD_INFORMATION_SYSTEM',today:'2026-08-23',portfolio:{cash:10000000,equity_value:14000000,nav:24000000,cost_value:13000000,total_pnl:1000000,accounting_return:1/23,unrealized_pnl:1000000,realized_pnl:0,reference_weights:{FPT:1},positions:[position]},preferences:{cash_reserve_configured:true,cash_reserve:5000000,reference_weights:{FPT:1}},performance_summary:performance,risk,health,market_data:{status:'VALID',market_date:'2026-08-21',aligned:true,calendar_age_days:2,provider:{provider:'auto'}},data_lineage:{analytics:{status:'UNVERIFIED'}},contribution_suggestions:{available_cash:10000000,strategic_cash_reserve:5000000,deployable_cash:0,policy:'EXPLICIT_REFERENCE_WEIGHT_DEFICITS',suggestions:[]}};
const snapshots=[{snapshot_date:'2026-08-21',official:true,data_quality:'VALID',nav:24000000,cash:10000000,equity_value:14000000,daily_pnl:200000,daily_return:.0084,current_drawdown:-.02,volatility_252:.24,positions:[position]}];
const transactions=[{id:1,event_date:'2026-01-02',event_type:'POSITION_IMPORT',symbol:'FPT',quantity:200,price:65000,fee:0,tax:0,amount:0,created_by:'local',metadata:{broker_code:'TCBS',account_id:'PRIMARY'}}];
const operations={
  book_type:'INSTITUTIONAL_LITE_IBOR', accounting_cost_method:'FIFO_TAX_LOTS', position_recognition:'TRADE_DATE', activity_integrity:{status:'VERIFIED',records:3},
  settlement:{settled_cash:10000000,projected_cash:10000000,unsettled_receivable:0,unsettled_payable:0,strategic_reserve:5000000,available_to_invest:5000000,trades:[]},
  exceptions:[{severity:'INFO',code:'NO_RECONCILIATION',message:'No broker reconciliation has been recorded yet.'}],
  tax_lots:[{lot_id:'FPT:1',symbol:'FPT',broker_code:'TCBS',account_id:'PRIMARY',acquisition_date:'2026-01-02',original_quantity:200,remaining_quantity:200,unit_cost:65000,cost_basis:13000000}],
  reconciliations:[], corporate_action_provider:{provider:'vnstock',available:true}, corporate_actions:[], security_reference_provider:{provider:'vnstock',available:true},
  securities:[{security_id:'VN-EQ-FPT',symbol:'FPT',name:'FPT Corporation',exchange:'HOSE',isin:'VN000000FPT1',currency:'VND',asset_type:'EQUITY',lot_size:100,master_data_source:'vnstock',master_data_status:'RESOLVED'}],
  nav_controls:[{...snapshots[0],nav_status:'OFFICIAL'}], restatements:[],
  pnl_attribution:[{symbol:'FPT',unrealized_pnl:1000000,realized_pnl:0,dividend_income:200000,total_contribution_vnd:1200000}],
};
const activity={integrity:{status:'VERIFIED',records:3,head_hash:'abcdef1234567890'},logs:[{id:3,occurred_at:'2026-08-23T07:00:00Z',actor_type:'USER',actor_id:'local',category:'LEDGER',action:'TRANSACTION_CORRECTED',entity_type:'TRANSACTION',entity_id:'1',status:'SUCCESS',summary:'Corrected transaction #1.',details:{broker_code:'TCBS'}}]};

let pass=true; function check(name,ok){console.log(`${ok?'PASS':'FAIL'}  ${name}`);if(!ok)pass=false;}
const ssrEntry=join(root,'dist-ssr','ssr-entry.mjs'); check('SSR bundle exists',existsSync(ssrEntry)); let renderPage=null;
if(existsSync(ssrEntry)){
  ({renderPage}=await import(`file://${ssrEntry.replace(/\\/g,'/')}`));
  const portfolioHtml=renderPage('portfolio',{dashboard,locale:'en'});
  check('portfolio renders live accounting and AI export',portfolioHtml.includes('Total portfolio')&&portfolioHtml.includes('1,000,000 VND')&&portfolioHtml.includes('Export for AI'));
  check('portfolio has Operations and Logs navigation',portfolioHtml.includes('href="/operations"')&&portfolioHtml.includes('href="/logs"'));
  check('portfolio has no research navigation',!portfolioHtml.includes('Research Lab')&&!portfolioHtml.includes('Optimizer'));
  const perfHtml=renderPage('performance',{performance,locale:'en'}); check('performance renders controlled history',perfHtml.includes('Total P/L')&&perfHtml.includes('Current drawdown')&&perfHtml.includes('History quality'));
  const riskHtml=renderPage('risk',{risk,locale:'en'}); check('risk renders concentration and tail risk',riskHtml.includes('Equity HHI')&&riskHtml.includes('Daily CVaR 95%'));
  const snapshotHtml=renderPage('snapshots',{snapshots,locale:'en'}); check('snapshots render official checkpoints',snapshotHtml.includes('OFFICIAL'));
  const settingsHtml=renderPage('settings',{dashboard,locale:'en'}); check('settings render cash policy',settingsHtml.includes('Cash policy')&&settingsHtml.includes('Strategic cash reserve'));
  const txHtml=renderPage('transactions',{transactions,corrections:[],today:'2026-08-23',locale:'en'});
  check('transactions expose inline broker controls',txHtml.includes('Broker')&&txHtml.includes('TCBS')&&txHtml.includes('Inline edits create audited corrections'));
  check('transactions do not render browser prompt text',!txHtml.includes('Why should transaction'));
  const opsHtml=renderPage('operations',{operations,today:'2026-08-23',locale:'en'});
  check('operations renders institutional book',opsHtml.includes('Operations &amp; Book Controls')&&opsHtml.includes('Settlement book')&&opsHtml.includes('Tax lots · FIFO')&&opsHtml.includes('Broker reconciliation')&&opsHtml.includes('Corporate actions')&&opsHtml.includes('NAV controls &amp; restatement'));
  check('operations renders automatic master resolution',opsHtml.includes('Resolve all master data')&&opsHtml.includes('VN000000FPT1')&&opsHtml.includes('ISIN is not calculated from ticker'));
  const logsHtml=renderPage('logs',{activity,locale:'en'});
  check('logs page renders audit integrity and records',logsHtml.includes('Activity Log')&&logsHtml.includes('VERIFIED')&&logsHtml.includes('TRANSACTION_CORRECTED')&&logsHtml.includes('hash chain'));
  const viOps=renderPage('operations',{operations,today:'2026-08-23',locale:'vi'}); check('Vietnamese operations renders',viOps.includes('Vận hành')&&viOps.includes('Đối soát broker'));
  const viLogs=renderPage('logs',{activity,locale:'vi'}); check('Vietnamese logs renders',viLogs.includes('Nhật ký hoạt động')&&viLogs.includes('Toàn vẹn'));
  const guideHtml=renderPage('guide',{locale:'en'}); check('guide still renders',guideHtml.includes('Data integrity rules'));
  check('removed research page cannot render',renderPage('research',{locale:'en'})==='');
  check('removed optimizer page cannot render',renderPage('optimizer_list',{locale:'en'})==='');
}
const clientJs=join(root,'dist','assets','client.js'); check('client bundle exists',existsSync(clientJs));
if(existsSync(clientJs)&&renderPage){
  const dom=new JSDOM('<html><body><div id="root"></div></body></html>',{url:'http://localhost:8080/',pretendToBeVisual:true}); const {window}=dom;
  globalThis.window=window;globalThis.document=window.document;Object.defineProperty(globalThis,'navigator',{value:window.navigator,configurable:true});globalThis.HTMLElement=window.HTMLElement;globalThis.MutationObserver=window.MutationObserver;globalThis.requestAnimationFrame=window.requestAnimationFrame?.bind(window)||((cb)=>setTimeout(cb,16));globalThis.fetch=async()=>({ok:true,json:async()=>({})});
  const errors=[];window.addEventListener('error',e=>errors.push(e.message));window.document.getElementById('root').innerHTML=renderPage('portfolio',{dashboard,locale:'vi'});window.__PAGE__={page:'portfolio',props:{dashboard,locale:'vi'}};eval(readFileSync(clientJs,'utf8'));await new Promise(r=>setTimeout(r,300));
  check('Vietnamese hydration rendered',window.document.getElementById('root').textContent.includes('FPT')); check('no hydration errors',errors.length===0);
}
console.log(pass?'\nSMOKE TEST PASSED':'\nSMOKE TEST FAILED');process.exit(pass?0:1);
