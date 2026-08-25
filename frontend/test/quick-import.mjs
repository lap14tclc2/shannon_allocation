import assert from 'node:assert/strict';
import { IMPORT_EVENT_TYPES, importTemplate, parseQuickImport } from '../src/lib/quickImport.js';

const current = parseQuickImport('FPT,1.000,92k,TCBS,PRIMARY\nHPG,500,26.5k,SSI,PRIMARY', { today: '2026-08-25' });
assert.equal(current[0].quantity, 1000);
assert.equal(current[0].price, 92000);
assert.equal(current[1].price, 26500);
assert.equal(current[0].event_date, '2026-08-25');
assert.deepEqual(IMPORT_EVENT_TYPES, ['POSITION_IMPORT', 'CASH_DEPOSIT']);
assert.equal(importTemplate().includes('event_date'), false);
assert.throws(
  () => parseQuickImport('2024-01-01,BUY,FPT,100,92000', { mode: 'HISTORICAL', today: '2026-08-25' }),
  /không còn được hỗ trợ/,
);

console.log('quick-import current-balance contract: ok');
