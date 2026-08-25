import assert from 'node:assert/strict';
import { IMPORT_EVENT_TYPES, parseQuickImport } from '../src/lib/quickImport.js';

const current = parseQuickImport('FPT,1.000,92k,TCBS,PRIMARY\nHPG,500,26.5k,SSI,PRIMARY', { mode: 'CURRENT', today: '2026-08-25' });
assert.equal(current[0].quantity, 1000);
assert.equal(current[0].price, 92000);
assert.equal(current[1].price, 26500);
assert.equal(current[0].event_date, '2026-08-25');

const history = parseQuickImport('event_date,event_type,symbol,quantity,price,amount,ratio,fee,tax,broker_code,account_id,note\n2024-01-01,CASH_DEPOSIT,,,,100tr,,,,UNASSIGNED,PRIMARY,Nạp vốn\n2024-01-02,CASH_DIVIDEND,FPT,,,2tr,,,100k,TCBS,PRIMARY,Cổ tức', { mode: 'HISTORICAL', today: '2026-08-25' });
assert.equal(history[0].amount, 100_000_000);
assert.equal(history[1].amount, 2_000_000);
assert.equal(history[1].tax, 100_000);
assert.deepEqual(new Set(IMPORT_EVENT_TYPES), new Set(['POSITION_IMPORT', 'CASH_DEPOSIT', 'BUY', 'SELL', 'RIGHTS_ISSUE', 'CASH_WITHDRAW', 'CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'FEE']));

console.log('quick-import contract: ok');
