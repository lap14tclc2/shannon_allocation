const EPSILON = 1e-8;

function brokerOf(row) {
  return String(row?.metadata?.broker_code || row?.broker_code || 'UNASSIGNED').toUpperCase();
}

function accountOf(row) {
  return String(row?.metadata?.account_id || row?.account_id || 'PRIMARY').toUpperCase();
}

function quantityOf(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number : 0;
}

function sortEvents(rows) {
  return [...(rows || [])].sort((a, b) => {
    const date = String(a?.event_date || '').localeCompare(String(b?.event_date || ''));
    if (date !== 0) return date;
    return Number(a?.id || 0) - Number(b?.id || 0);
  });
}

function eligibleLots(lots, symbol, brokerCode, accountId) {
  const assigned = brokerCode && brokerCode !== 'UNASSIGNED';
  return lots
    .filter(lot => lot.symbol === symbol && lot.remaining > EPSILON)
    .filter(lot => !assigned || (lot.broker_code === brokerCode && lot.account_id === accountId))
    .sort((a, b) => {
      const date = String(a.acquisition_date).localeCompare(String(b.acquisition_date));
      return date !== 0 ? date : a.sequence - b.sequence;
    });
}

function consumeLots(lots, symbol, quantity, brokerCode, accountId) {
  let remaining = quantity;
  for (const lot of eligibleLots(lots, symbol, brokerCode, accountId)) {
    if (remaining <= EPSILON) break;
    const take = Math.min(lot.remaining, remaining);
    lot.remaining -= take;
    remaining -= take;
  }
}

function allocateStockDividend(lots, symbol, quantity, brokerCode, accountId) {
  const matching = eligibleLots(lots, symbol, brokerCode, accountId);
  const before = matching.reduce((sum, lot) => sum + lot.remaining, 0);
  if (before <= EPSILON) return;

  let allocated = 0;
  matching.forEach((lot, index) => {
    const addition = index === matching.length - 1
      ? quantity - allocated
      : quantity * (lot.remaining / before);
    lot.remaining += addition;
    allocated += addition;
  });
}

/**
 * Replays the effective transaction ledger into broker/account-specific lots.
 * The rules intentionally mirror python/portfolio/accounting.py: assigned SELL
 * events consume only the matching broker/account FIFO book; UNASSIGNED legacy
 * sells consume the consolidated FIFO book; stock dividends are distributed
 * pro-rata across the same eligible open lots.
 */
export function deriveHoldingBooks(transactions = []) {
  const lots = [];
  let sequence = 0;

  for (const row of sortEvents(transactions)) {
    const type = String(row?.event_type || '').toUpperCase();
    const symbol = String(row?.symbol || '').toUpperCase();
    if (!symbol) continue;

    const brokerCode = brokerOf(row);
    const accountId = accountOf(row);
    const quantity = quantityOf(row?.quantity);

    if ((type === 'POSITION_IMPORT' || type === 'BUY') && quantity > EPSILON) {
      lots.push({
        symbol,
        broker_code: brokerCode,
        account_id: accountId,
        remaining: quantity,
        acquisition_date: row.event_date || '',
        sequence: sequence++,
      });
      continue;
    }

    if (type === 'STOCK_DIVIDEND' && quantity > EPSILON) {
      allocateStockDividend(lots, symbol, quantity, brokerCode, accountId);
      continue;
    }

    if (type === 'SELL' && quantity > EPSILON) {
      consumeLots(lots, symbol, quantity, brokerCode, accountId);
      continue;
    }

    if (type === 'SPLIT') {
      const ratio = Number(row?.ratio || 0);
      if (!Number.isFinite(ratio) || ratio <= 0) continue;
      for (const lot of eligibleLots(lots, symbol, brokerCode, accountId)) {
        lot.remaining *= ratio;
      }
    }
  }

  const grouped = new Map();
  for (const lot of lots) {
    if (lot.remaining <= EPSILON) continue;
    const key = `${lot.symbol}|${lot.broker_code}|${lot.account_id}`;
    const current = grouped.get(key) || {
      symbol: lot.symbol,
      broker_code: lot.broker_code,
      account_id: lot.account_id,
      shares: 0,
    };
    current.shares += lot.remaining;
    grouped.set(key, current);
  }

  return [...grouped.values()]
    .filter(row => row.shares > EPSILON)
    .sort((a, b) => {
      const symbol = a.symbol.localeCompare(b.symbol);
      if (symbol !== 0) return symbol;
      const broker = a.broker_code.localeCompare(b.broker_code);
      return broker !== 0 ? broker : a.account_id.localeCompare(b.account_id);
    });
}

export function holdingBookKey(row) {
  return `${String(row?.symbol || '').toUpperCase()}|${String(row?.broker_code || 'UNASSIGNED').toUpperCase()}|${String(row?.account_id || 'PRIMARY').toUpperCase()}`;
}

export function findHoldingBook(rows, symbol, brokerCode, accountId) {
  const target = `${String(symbol || '').toUpperCase()}|${String(brokerCode || 'UNASSIGNED').toUpperCase()}|${String(accountId || 'PRIMARY').toUpperCase()}`;
  return (rows || []).find(row => holdingBookKey(row) === target) || null;
}
