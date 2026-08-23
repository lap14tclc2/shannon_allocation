import {
  FormValidationError,
  parseVndMoneyInput,
  validateCashAmount,
  validateCashReserveInput,
  validateReferenceWeightInputs,
  validateTransactionForm,
} from '../src/lib/validation.js';

function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) process.exitCode = 1;
}

function rejects(field, fn) {
  try { fn(); return false; } catch (err) { return err instanceof FormValidationError && err.field === field; }
}

const base = { event_date: '2026-08-23', symbol: 'FPT', quantity: '100', price: '72000', amount: '', ratio: '', fee: '', tax: '', note: '' };
check('valid trade is normalized', validateTransactionForm('BUY', base, '2026-08-23', 'en').price === 72000);
check('reject future date', rejects('event_date', () => validateTransactionForm('BUY', { ...base, event_date: '2026-08-24' }, '2026-08-23', 'en')));
check('reject suspicious thousand-unit price', rejects('price', () => validateTransactionForm('BUY', { ...base, price: '72' }, '2026-08-23', 'en')));
check('reject bad ticker', rejects('symbol', () => validateTransactionForm('BUY', { ...base, symbol: 'FP!' }, '2026-08-23', 'en')));
check('reject zero quantity', rejects('quantity', () => validateTransactionForm('BUY', { ...base, quantity: '0' }, '2026-08-23', 'en')));
check('cash amount positive', validateCashAmount('50000000', 'en') === 50000000);
check('cash reserve allows explicit zero', validateCashReserveInput('0', 'en') === 0);
check('parse 20tr', parseVndMoneyInput('20tr', 'cash_reserve', 'vi') === 20_000_000);
check('parse 20m', parseVndMoneyInput('20m', 'cash_reserve', 'en') === 20_000_000);
check('parse Vietnamese grouped VND', parseVndMoneyInput('20.000.000', 'cash_reserve', 'vi') === 20_000_000);
check('parse comma grouped VND', parseVndMoneyInput('20,000,000', 'cash_reserve', 'en') === 20_000_000);
check('parse decimal million suffix', parseVndMoneyInput('20,5tr', 'cash_reserve', 'vi') === 20_500_000);
check('reject malformed money', rejects('cash_reserve', () => parseVndMoneyInput('20..000', 'cash_reserve', 'vi')));
check('reference weights require 100%', rejects('weights', () => validateReferenceWeightInputs({ ACB: 40, DGC: 40, FPT: 10 }, ['ACB', 'DGC', 'FPT'], 'en')));
check('reference weights normalize', validateReferenceWeightInputs({ ACB: 40, DGC: 30, FPT: 30 }, ['ACB', 'DGC', 'FPT'], 'en').ACB === 0.4);

if (!process.exitCode) console.log('\nCLIENT VALIDATION TEST PASSED');
