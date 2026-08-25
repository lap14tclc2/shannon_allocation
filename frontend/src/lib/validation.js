import { BROKER_CODES } from './brokers.js';

const SYMBOL_RE = /^[A-Z0-9]{2,10}$/;
const ACCOUNT_RE = /^[A-Z0-9_.-]{1,32}$/;
const MAX_NOTE = 500;
const MIN_PRICE = 1000;
const MAX_PRICE = 10_000_000;
const MAX_MONEY = 10_000_000_000_000_000;
const MAX_SHARES = 1_000_000_000;

export class FormValidationError extends Error {
  constructor(field, en, vi, locale = 'en') {
    super(locale === 'vi' ? vi : en);
    this.field = field;
    this.code = 'CLIENT_VALIDATION';
  }
}

function number(value, field, locale, { min = null, max = null, positive = false } = {}) {
  if (String(value ?? '').trim() === '') throw new FormValidationError(field, `${field} is required.`, `${field} là bắt buộc.`, locale);
  const n = Number(value);
  if (!Number.isFinite(n)) throw new FormValidationError(field, `${field} must be a valid number.`, `${field} phải là số hợp lệ.`, locale);
  if (positive && n <= 0) throw new FormValidationError(field, `${field} must be greater than 0.`, `${field} phải lớn hơn 0.`, locale);
  if (min != null && n < min) throw new FormValidationError(field, `${field} must be at least ${min}.`, `${field} phải ít nhất ${min}.`, locale);
  if (max != null && n > max) throw new FormValidationError(field, `${field} is too large.`, `${field} vượt giới hạn cho phép.`, locale);
  return n;
}

export function parseVndMoneyInput(value, field = 'amount', locale = 'en') {
  const original = String(value ?? '').trim();
  if (!original) throw new FormValidationError(field, `${field} is required.`, `${field} là bắt buộc.`, locale);
  let text = original.toLowerCase().replace(/\s+/g, '');
  let multiplier = 1;
  let hasSuffix = false;
  if (/(triệu|tr|m)$/.test(text)) { text = text.replace(/(triệu|tr|m)$/, ''); multiplier = 1_000_000; hasSuffix = true; }
  if (!text) throw new FormValidationError(field, 'Enter a valid VND amount.', 'Nhập số tiền VND hợp lệ.', locale);
  let normalized;
  if (hasSuffix) {
    if (!/^\d+(?:[.,]\d+)?$/.test(text)) throw new FormValidationError(field, 'Enter a valid VND amount, for example 20m or 20,000,000.', 'Nhập số tiền VND hợp lệ, ví dụ 20tr hoặc 20.000.000.', locale);
    normalized = text.replace(',', '.');
  } else if (/^\d+$/.test(text)) {
    normalized = text;
  } else {
    // Without a magnitude suffix, punctuation is a thousands separator only.
    // Require one consistent separator and exactly three digits per group so
    // malformed values such as "20..000" cannot silently become 20,000 VND.
    const grouped = text.match(/^\d{1,3}([.,])\d{3}(?:\1\d{3})*$/);
    if (!grouped) throw new FormValidationError(field, 'Enter a valid VND amount, for example 20m or 20,000,000.', 'Nhập số tiền VND hợp lệ, ví dụ 20tr hoặc 20.000.000.', locale);
    normalized = text.split(grouped[1]).join('');
  }
  const n = Number(normalized) * multiplier;
  if (!Number.isFinite(n) || n < 0 || n > MAX_MONEY) throw new FormValidationError(field, 'VND amount is outside the allowed range.', 'Số tiền VND vượt phạm vi cho phép.', locale);
  if (!Number.isInteger(n)) throw new FormValidationError(field, 'VND amount must resolve to a whole number of đồng.', 'Số tiền VND phải quy đổi thành số nguyên đồng.', locale);
  return n;
}

export function validateCashAmount(value, locale = 'en') {
  const n = parseVndMoneyInput(value, 'amount', locale);
  if (n <= 0) throw new FormValidationError('amount', 'amount must be greater than 0.', 'amount phải lớn hơn 0.', locale);
  return n;
}

export function validateCashReserveInput(value, locale = 'en') {
  if (String(value ?? '').trim() === '') throw new FormValidationError('cash_reserve', 'Enter a cash reserve. Use 0 if you intentionally want no reserve.', 'Nhập mức tiền mặt dự trữ. Dùng 0 nếu bạn chủ động không giữ dự trữ.', locale);
  return parseVndMoneyInput(value, 'cash_reserve', locale);
}

export function validateBrokerAccount(brokerValue, accountValue, locale = 'en') {
  const brokerCode = String(brokerValue || 'UNASSIGNED').trim().toUpperCase();
  if (!BROKER_CODES.has(brokerCode)) throw new FormValidationError('broker_code', 'Select a supported broker.', 'Chọn công ty chứng khoán hợp lệ.', locale);
  const accountId = String(accountValue || 'PRIMARY').trim().toUpperCase();
  if (!ACCOUNT_RE.test(accountId)) throw new FormValidationError('account_id', 'Invalid account ID.', 'Mã tài khoản không hợp lệ.', locale);
  return { broker_code: brokerCode, account_id: accountId };
}

export function validateTransactionForm(type, form, today, locale = 'en') {
  const requiredSymbol = ['POSITION_IMPORT', 'BUY', 'RIGHTS_ISSUE', 'SELL', 'STOCK_DIVIDEND', 'SPLIT', 'CASH_DIVIDEND'].includes(type);
  const requiredQuantity = ['POSITION_IMPORT', 'BUY', 'RIGHTS_ISSUE', 'SELL', 'STOCK_DIVIDEND'].includes(type);
  const requiredPrice = ['POSITION_IMPORT', 'BUY', 'RIGHTS_ISSUE', 'SELL'].includes(type);
  const requiredAmount = ['CASH_DEPOSIT', 'CASH_WITHDRAW', 'CASH_DIVIDEND', 'FEE'].includes(type);
  const isTrade = ['BUY', 'RIGHTS_ISSUE', 'SELL'].includes(type);

  if (!form.event_date) throw new FormValidationError('event_date', 'Date is required.', 'Ngày là bắt buộc.', locale);
  if (today && form.event_date > today) throw new FormValidationError('event_date', 'Future dates are not allowed.', 'Không được nhập ngày trong tương lai.', locale);

  const symbol = String(form.symbol || '').trim().toUpperCase();
  if (requiredSymbol && !SYMBOL_RE.test(symbol)) throw new FormValidationError('symbol', 'Ticker must contain 2–10 letters/digits, for example FPT.', 'Mã cổ phiếu phải gồm 2–10 ký tự chữ/số, ví dụ FPT.', locale);

  const quantity = requiredQuantity ? number(form.quantity, 'quantity', locale, { positive: true, max: MAX_SHARES }) : 0;
  const price = requiredPrice ? number(form.price, 'price', locale, { positive: true, max: MAX_PRICE }) : 0;
  if (requiredPrice && price < MIN_PRICE) throw new FormValidationError('price', 'Enter the full VND price per share, for example 72,000 instead of 72.', 'Nhập giá đầy đủ theo VND/cổ phiếu, ví dụ 72.000 thay vì 72.', locale);
  const amount = requiredAmount ? validateCashAmount(form.amount, locale) : 0;
  const ratio = type === 'SPLIT' ? number(form.ratio, 'ratio', locale, { positive: true, max: 100 }) : 0;
  const fee = isTrade && String(form.fee || '').trim() !== '' ? number(form.fee, 'fee', locale, { min: 0, max: MAX_MONEY }) : 0;
  const tax = isTrade && String(form.tax || '').trim() !== '' ? number(form.tax, 'tax', locale, { min: 0, max: MAX_MONEY }) : 0;
  if (isTrade && fee + tax > quantity * price) throw new FormValidationError('fee', 'Fee + tax cannot exceed gross trade value.', 'Phí + thuế không được lớn hơn giá trị giao dịch.', locale);

  const note = String(form.note || '').trim();
  if (note.length > MAX_NOTE) throw new FormValidationError('note', `Note must be at most ${MAX_NOTE} characters.`, `Ghi chú tối đa ${MAX_NOTE} ký tự.`, locale);

  const brokerAccount = validateBrokerAccount(form.broker_code, form.account_id, locale);
  const metadata = { ...brokerAccount };
  if (isTrade) {
    const settlement = String(form.settlement_date || '').trim();
    if (settlement && settlement < form.event_date) throw new FormValidationError('settlement_date', 'Settlement date cannot be before trade date.', 'Ngày thanh toán không được trước ngày giao dịch.', locale);
    if (settlement) metadata.settlement_date = settlement;
  }

  return {
    event_type: type,
    event_date: form.event_date,
    symbol: requiredSymbol ? symbol : undefined,
    quantity, price, amount, ratio, fee, tax, note,
    broker_code: brokerAccount.broker_code,
    account_id: brokerAccount.account_id,
    metadata,
  };
}

export function validateReferenceWeightInputs(weights, symbols, locale = 'en') {
  const clean = {};
  let total = 0;
  for (const symbol of symbols) {
    const raw = weights[symbol];
    if (String(raw ?? '').trim() === '') throw new FormValidationError(symbol, `Enter a target weight for ${symbol}.`, `Nhập tỷ trọng mục tiêu cho ${symbol}.`, locale);
    const pct = number(raw, symbol, locale, { min: 0.01, max: 100 });
    clean[symbol] = pct / 100; total += pct;
  }
  if (Math.abs(total - 100) > 0.001) throw new FormValidationError('weights', `Target weights must total 100%; current total is ${total.toFixed(2)}%.`, `Tỷ trọng mục tiêu phải cộng bằng 100%; hiện tại là ${total.toFixed(2)}%.`, locale);
  return clean;
}
