import assert from 'node:assert/strict';
import { deriveHoldingBooks, findHoldingBook } from '../src/lib/holdingBooks.js';

const rows = [
  {
    id: 1,
    event_type: 'POSITION_IMPORT',
    event_date: '2026-01-01',
    symbol: 'FPT',
    quantity: 1000,
    metadata: { broker_code: 'DNSE', account_id: 'PRIMARY' },
  },
  {
    id: 2,
    event_type: 'POSITION_IMPORT',
    event_date: '2026-01-01',
    symbol: 'FPT',
    quantity: 500,
    metadata: { broker_code: 'TCBS', account_id: 'PRIMARY' },
  },
  {
    id: 3,
    event_type: 'STOCK_DIVIDEND',
    event_date: '2026-01-20',
    symbol: 'FPT',
    quantity: 150,
    metadata: { broker_code: 'UNASSIGNED', account_id: 'PRIMARY' },
  },
  {
    id: 4,
    event_type: 'SELL',
    event_date: '2026-02-01',
    symbol: 'FPT',
    quantity: 200,
    metadata: { broker_code: 'DNSE', account_id: 'PRIMARY' },
  },
  {
    id: 5,
    event_type: 'BUY',
    event_date: '2026-03-01',
    symbol: 'ACB',
    quantity: 300,
    metadata: { broker_code: 'DNSE', account_id: 'MARGIN' },
  },
];

const books = deriveHoldingBooks(rows);
const fptDnse = findHoldingBook(books, 'FPT', 'DNSE', 'PRIMARY');
const fptTcbs = findHoldingBook(books, 'FPT', 'TCBS', 'PRIMARY');
const acbDnse = findHoldingBook(books, 'ACB', 'DNSE', 'MARGIN');

// 150 dividend shares are allocated 100/50 because the open books were 1000/500.
assert.equal(fptDnse?.shares, 900, 'DNSE FPT receives its dividend allocation then only DNSE is reduced by the DNSE sell');
assert.equal(fptTcbs?.shares, 550, 'TCBS FPT receives its dividend allocation and stays untouched by a DNSE sell');
assert.equal(acbDnse?.shares, 300);

const legacyRows = [
  {
    id: 1,
    event_type: 'BUY',
    event_date: '2026-01-01',
    symbol: 'REE',
    quantity: 100,
    metadata: { broker_code: 'DNSE', account_id: 'PRIMARY' },
  },
  {
    id: 2,
    event_type: 'BUY',
    event_date: '2026-01-02',
    symbol: 'REE',
    quantity: 100,
    metadata: { broker_code: 'TCBS', account_id: 'PRIMARY' },
  },
  {
    id: 3,
    event_type: 'SELL',
    event_date: '2026-01-03',
    symbol: 'REE',
    quantity: 120,
    metadata: { broker_code: 'UNASSIGNED', account_id: 'PRIMARY' },
  },
];

const legacyBooks = deriveHoldingBooks(legacyRows);
assert.equal(findHoldingBook(legacyBooks, 'REE', 'DNSE', 'PRIMARY'), null, 'legacy consolidated sell consumes oldest lot first');
assert.equal(findHoldingBook(legacyBooks, 'REE', 'TCBS', 'PRIMARY')?.shares, 80);

const discardedBooks = deriveHoldingBooks([
  {
    id: 10,
    event_type: 'BUY',
    event_date: '2026-04-01',
    symbol: 'VCB',
    quantity: 200,
    status: 'SOFT_DELETED',
    metadata: { broker_code: 'DNSE', account_id: 'PRIMARY' },
  },
]);
assert.equal(
  findHoldingBook(discardedBooks, 'VCB', 'DNSE', 'PRIMARY'),
  null,
  'soft-deleted transactions must not create effective holding books',
);

console.log('holding-books contract: ok');
