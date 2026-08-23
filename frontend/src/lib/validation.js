const SYMBOL_RE = /^[A-Z0-9]{2,10}$/;
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
  if (String(value ?? '').trim() === '') {
    throw new FormValidationError(field, `${field} is required.`, `${field} là bắt buộc.`, locale);
  }
  const n = Number(value);
  if (!Number.isFinite(n)) {
    throw new FormValidationError(field, `${field} must be a valid number.`, `${field} phải là số hợp lệ.`, locale);
  }
  if (positive && n <= 0) {
    throw new FormValidationError(field, `${field} must be greater than 0.`, `${field} phải lớn hơn 0.`, locale);
  }
  if (min != null && n < min) {
    throw new FormValidationError(field, `${field} must be at least ${min}.`, `${field} phải ít nhất ${min}.`, locale);
  }
  if (max != null && n > max) {
    throw new FormValidationError(field, `${field} is too large.`, `${field} vượt giới hạn cho phép.`, locale);
  }
  return n;
}

export function validateCashAmount(value, locale = 'en') {
  return number(value, 'amount', locale, { positive: true, max: MAX_MONEY });
}

export function validateCashReserveInput(value, locale = 'en') {
  if (String(value ?? '').trim() === '') {
    throw new FormValidationError('cash_reserve', 'Enter a cash reserve. Use 0 if you intentionally want no reserve.', 'Nhập mức tiền mặt dự trữ. Dùng 0 nếu bạn chủ động không giữ dự trữ.', locale);
  }
  return number(value, 'cash_reserve', locale, { min: 0, max: MAX_MONEY });
}

export function validateTransactionForm(type, form, today, locale = 'en') {
  const requiredSymbol = ['POSITION_IMPORT', 'BUY', 'SELL', 'STOCK_DIVIDEND', 'SPLIT', 'CASH_DIVIDEND'].includes(type);
  const requiredQuantity = ['POSITION_IMPORT', 'BUY', 'SELL', 'STOCK_DIVIDEND'].includes(type);
  const requiredPrice = ['POSITION_IMPORT', 'BUY', 'SELL'].includes(type);
  const requiredAmount = ['CASH_DEPOSIT', 'CASH_WITHDRAW', 'CASH_DIVIDEND', 'FEE'].includes(type);

  if (!form.event_date) {
    throw new FormValidationError('event_date', 'Date is required.', 'Ngày là bắt buộc.', locale);
  }
  if (today && form.event_date > today) {
    throw new FormValidationError('event_date', 'Future dates are not allowed.', 'Không được nhập ngày trong tương lai.', locale);
  }

  const symbol = String(form.symbol || '').trim().toUpperCase();
  if (requiredSymbol && !SYMBOL_RE.test(symbol)) {
    throw new FormValidationError('symbol', 'Ticker must contain 2–10 letters/digits, for example FPT.', 'Mã cổ phiếu phải gồm 2–10 ký tự chữ/số, ví dụ FPT.', locale);
  }

  const quantity = requiredQuantity ? number(form.quantity, 'quantity', locale, { positive: true, max: MAX_SHARES }) : 0;
  const price = requiredPrice ? number(form.price, 'price', locale, { positive: true, max: MAX_PRICE }) : 0;
  if (requiredPrice && price < MIN_PRICE) {
    throw new FormValidationError('price', 'Enter the full VND price per share, for example 72,000 instead of 72.', 'Nhập giá đầy đủ theo VND/cổ phiếu, ví dụ 72.000 thay vì 72.', locale);
  }

  const amount = requiredAmount ? number(form.amount, 'amount', locale, { positive: true, max: MAX_MONEY }) : 0;
  const ratio = type === 'SPLIT' ? number(form.ratio, 'ratio', locale, { positive: true, max: 100 }) : 0;
  const fee = ['BUY', 'SELL'].includes(type) && String(form.fee || '').trim() !== '' ? number(form.fee, 'fee', locale, { min: 0, max: MAX_MONEY }) : 0;
  const tax = ['BUY', 'SELL'].includes(type) && String(form.tax || '').trim() !== '' ? number(form.tax, 'tax', locale, { min: 0, max: MAX_MONEY }) : 0;
  if (['BUY', 'SELL'].includes(type) && fee + tax > quantity * price) {
    throw new FormValidationError('fee', 'Fee + tax cannot exceed gross trade value.', 'Phí + thuế không được lớn hơn giá trị giao dịch.', locale);
  }

  const note = String(form.note || '').trim();
  if (note.length > MAX_NOTE) {
    throw new FormValidationError('note', `Note must be at most ${MAX_NOTE} characters.`, `Ghi chú tối đa ${MAX_NOTE} ký tự.`, locale);
  }

  return {
    event_type: type,
    event_date: form.event_date,
    symbol: requiredSymbol ? symbol : undefined,
    quantity,
    price,
    amount,
    ratio,
    fee,
    tax,
    note,
  };
}

export function validateReferenceWeightInputs(weights, symbols, locale = 'en') {
  const clean = {};
  let total = 0;
  for (const symbol of symbols) {
    const raw = weights[symbol];
    if (String(raw ?? '').trim() === '') {
      throw new FormValidationError(symbol, `Enter a target weight for ${symbol}.`, `Nhập tỷ trọng mục tiêu cho ${symbol}.`, locale);
    }
    const pct = number(raw, symbol, locale, { min: 0.01, max: 100 });
    clean[symbol] = pct / 100;
    total += pct;
  }
  if (Math.abs(total - 100) > 0.001) {
    throw new FormValidationError('weights', `Target weights must total 100%; current total is ${total.toFixed(2)}%.`, `Tỷ trọng mục tiêu phải cộng bằng 100%; hiện tại là ${total.toFixed(2)}%.`, locale);
  }
  return clean;
}
