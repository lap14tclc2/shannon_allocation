import { parseVndMoneyInput } from './validation.js';

export const IMPORT_EVENT_TYPES = [
  'POSITION_IMPORT', 'CASH_DEPOSIT', 'BUY', 'SELL', 'RIGHTS_ISSUE',
  'CASH_WITHDRAW', 'CASH_DIVIDEND', 'STOCK_DIVIDEND', 'SPLIT', 'FEE',
];

const HEADER_ALIASES = {
  date: 'event_date', ngay: 'event_date', event_date: 'event_date',
  type: 'event_type', loai: 'event_type', event_type: 'event_type',
  ticker: 'symbol', ma: 'symbol', symbol: 'symbol',
  qty: 'quantity', sl: 'quantity', so_luong: 'quantity', quantity: 'quantity',
  gia: 'price', gia_von: 'price', price: 'price',
  amount: 'amount', so_tien: 'amount', tien: 'amount',
  ratio: 'ratio', ty_le: 'ratio',
  fee: 'fee', phi: 'fee', tax: 'tax', thue: 'tax',
  broker: 'broker_code', ctck: 'broker_code', broker_code: 'broker_code',
  account: 'account_id', tai_khoan: 'account_id', account_id: 'account_id',
  note: 'note', ghi_chu: 'note',
};

function key(value) {
  return String(value || '').trim().toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd')
    .replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
}

function splitLine(line, delimiter) {
  const cells = [];
  let value = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (quoted && line[i + 1] === '"') { value += '"'; i += 1; }
      else quoted = !quoted;
    } else if (char === delimiter && !quoted) {
      cells.push(value.trim()); value = '';
    } else value += char;
  }
  cells.push(value.trim());
  return cells;
}

function detectDelimiter(line) {
  if (line.includes('\t')) return '\t';
  const semicolons = (line.match(/;/g) || []).length;
  const commas = (line.match(/,/g) || []).length;
  return semicolons > commas ? ';' : ',';
}

function compactNumber(value, field) {
  const text = String(value ?? '').trim();
  if (!text) return 0;
  if (field === 'price' || field === 'amount' || field === 'fee' || field === 'tax') {
    return parseVndMoneyInput(text, field, 'vi');
  }
  const normalized = text.replace(/\s/g, '');
  if (/^\d{1,3}([.,])\d{3}(?:\1\d{3})*$/.test(normalized)) return Number(normalized.replace(/[.,]/g, ''));
  const decimal = Number(normalized.replace(',', '.'));
  if (!Number.isFinite(decimal)) throw new Error(`${field}: “${text}” không phải là số hợp lệ.`);
  return decimal;
}

function normalizeRow(source, lineNumber, mode, today) {
  const eventType = String(source.event_type || (mode === 'CURRENT' ? 'POSITION_IMPORT' : '')).trim().toUpperCase();
  if (!IMPORT_EVENT_TYPES.includes(eventType)) throw new Error(`Dòng ${lineNumber}: loại giao dịch “${eventType || '-'}” không hợp lệ.`);
  const row = {
    event_type: eventType,
    event_date: mode === 'CURRENT' ? today : String(source.event_date || '').trim(),
    symbol: String(source.symbol || '').trim().toUpperCase(),
    quantity: compactNumber(source.quantity, 'quantity'),
    price: compactNumber(source.price, 'price'),
    amount: compactNumber(source.amount, 'amount'),
    ratio: compactNumber(source.ratio, 'ratio'),
    fee: compactNumber(source.fee, 'fee'),
    tax: compactNumber(source.tax, 'tax'),
    broker_code: String(source.broker_code || 'UNASSIGNED').trim().toUpperCase(),
    account_id: String(source.account_id || 'PRIMARY').trim().toUpperCase(),
    note: String(source.note || '').trim(),
  };
  return row;
}

export function parseQuickImport(text, { mode = 'CURRENT', today = '' } = {}) {
  const lines = String(text || '').split(/\r?\n/).map(line => line.trim()).filter(line => line && !line.startsWith('#'));
  if (!lines.length) throw new Error('Hãy dán ít nhất một dòng dữ liệu.');
  const delimiter = detectDelimiter(lines[0]);
  const first = splitLine(lines[0], delimiter);
  const mappedHeaders = first.map(cell => HEADER_ALIASES[key(cell)] || null);
  const hasHeader = mappedHeaders.some(Boolean) && (mappedHeaders.includes('symbol') || mappedHeaders.includes('event_type'));
  const dataLines = hasHeader ? lines.slice(1) : lines;
  if (!dataLines.length) throw new Error('Tệp chỉ có tiêu đề, chưa có dữ liệu.');

  return dataLines.map((line, index) => {
    const cells = splitLine(line, delimiter);
    const raw = {};
    if (hasHeader) mappedHeaders.forEach((header, cellIndex) => { if (header) raw[header] = cells[cellIndex] || ''; });
    else if (mode === 'CURRENT') {
      [raw.symbol, raw.quantity, raw.price, raw.broker_code, raw.account_id, raw.note] = cells;
      raw.event_type = 'POSITION_IMPORT';
    } else {
      [raw.event_date, raw.event_type, raw.symbol, raw.quantity, raw.price, raw.amount, raw.ratio, raw.fee, raw.tax, raw.broker_code, raw.account_id, raw.note] = cells;
    }
    return normalizeRow(raw, index + (hasHeader ? 2 : 1), mode, today);
  });
}

export function importTemplate(mode = 'CURRENT') {
  if (mode === 'CURRENT') return 'FPT,1000,92000,TCBS,PRIMARY\nHPG,500,26500,SSI,PRIMARY';
  return 'event_date,event_type,symbol,quantity,price,amount,ratio,fee,tax,broker_code,account_id,note\n2024-01-02,CASH_DEPOSIT,,,,100tr,,,,UNASSIGNED,PRIMARY,Nạp vốn\n2024-01-03,BUY,FPT,1000,92000,,,15000,0,TCBS,PRIMARY,Mua FPT';
}
