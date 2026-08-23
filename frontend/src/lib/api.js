function apiError(data, fallback) {
  const err = new Error(data?.error || fallback);
  err.code = data?.code || 'REQUEST_FAILED';
  err.field = data?.field || null;
  err.details = data;
  return err;
}

async function getJSON(url, signal) {
  const res = await fetch(url, { signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw apiError(data, `Request failed: ${res.status} ${url}`);
  return data;
}

async function sendJSON(url, method, body) {
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: body == null ? undefined : JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw apiError(data, `Request failed: ${res.status} ${url}`);
  return data;
}

export const getPortfolioDashboard = () => getJSON('/api/portfolio');
export async function listPortfolioTransactions() { const d = await getJSON('/api/portfolio/transactions'); return d.transactions || []; }
export async function listPortfolioTransactionAudit() { const d = await getJSON('/api/portfolio/transaction-audit'); return d.corrections || []; }
export const createPortfolioTransaction = (payload) => sendJSON('/api/portfolio/transactions', 'POST', payload);
export const updatePortfolioTransaction = (eventId, payload) => sendJSON(`/api/portfolio/transactions/${Number(eventId)}`, 'PATCH', payload);
export const deletePortfolioTransaction = (eventId, reason) => sendJSON(`/api/portfolio/transactions/${Number(eventId)}`, 'DELETE', { reason });
export const syncPortfolio = () => sendJSON('/api/portfolio/sync', 'POST', {});
export const getPortfolioPerformance = () => getJSON('/api/portfolio/performance');
export const getPortfolioRisk = () => getJSON('/api/portfolio/risk');
export async function listPortfolioSnapshots() { const d = await getJSON('/api/portfolio/snapshots'); return d.snapshots || []; }
export const getPortfolioPreferences = () => getJSON('/api/portfolio/preferences');
export const setReferenceWeights = (weights) => sendJSON('/api/portfolio/reference-weights', 'POST', { weights });
export const setCashReserve = (amount) => sendJSON('/api/portfolio/cash-reserve', 'POST', { amount });

// Institutional-lite operations
export const getPortfolioOperations = () => getJSON('/api/portfolio/operations');
export const reconcileBroker = (payload) => sendJSON('/api/portfolio/reconciliation', 'POST', payload);
export const syncCorporateActions = (payload = {}) => sendJSON('/api/portfolio/corporate-actions/sync', 'POST', payload);
export const verifyCorporateAction = (id, sourceUrl) => sendJSON(`/api/portfolio/corporate-actions/${Number(id)}/verify`, 'POST', { source_url: sourceUrl });
export const recordCorporateActionReceipt = (id, payload) => sendJSON(`/api/portfolio/corporate-actions/${Number(id)}/receipt`, 'POST', payload);
export const postCorporateActionReceipt = (id) => sendJSON('/api/portfolio/corporate-actions/post', 'POST', { action_id: Number(id) });
export const confirmSettlement = (eventId, note = '') => sendJSON(`/api/portfolio/settlements/${Number(eventId)}/confirm`, 'POST', { note });
export const lockNav = (snapshotDate) => sendJSON(`/api/portfolio/nav/${encodeURIComponent(snapshotDate)}/lock`, 'POST', {});
export const resolveRestatement = (id) => sendJSON(`/api/portfolio/restatements/${Number(id)}/resolve`, 'POST', {});
export const updateSecurity = (symbol, payload) => sendJSON(`/api/portfolio/securities/${encodeURIComponent(symbol)}`, 'POST', payload);
