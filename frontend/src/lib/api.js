let authRedirectInProgress = false;
const getCache = new Map();

function apiError(data, fallback) {
  const err = new Error(data?.error || fallback);
  err.code = data?.code || 'REQUEST_FAILED';
  err.field = data?.field || null;
  err.details = data;
  return err;
}

function redirectExpiredSession(res, data) {
  if (res.status !== 401 || data?.code !== 'AUTH_REQUIRED') return false;
  if (typeof window === 'undefined') return false;
  if (window.location.pathname === '/login') return false;
  if (authRedirectInProgress) return true;

  authRedirectInProgress = true;
  const next = `${window.location.pathname}${window.location.search || ''}`;
  const params = new URLSearchParams({ reason: 'session_expired' });
  if (next && next !== '/' && !next.startsWith('/login')) params.set('next', next);
  window.location.replace(`/login?${params.toString()}`);
  return true;
}

async function handleResponse(res, url) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    redirectExpiredSession(res, data);
    throw apiError(data, `Request failed: ${res.status} ${url}`);
  }
  return data;
}

async function getJSON(url, signal) {
  const res = await fetch(url, { signal });
  return handleResponse(res, url);
}

async function getJSONCached(url, ttlMs = 60_000, { bypass = false } = {}) {
  const now = Date.now();
  const cached = getCache.get(url);
  if (!bypass && cached && cached.expiresAt > now) return cached.value;

  // Reuse one in-flight request so multiple components do not fan out the same call.
  if (!bypass && cached?.promise) return cached.promise;
  const promise = getJSON(url)
    .then(value => {
      getCache.set(url, { value, expiresAt: Date.now() + Math.max(0, ttlMs), promise: null });
      return value;
    })
    .catch(error => {
      getCache.delete(url);
      throw error;
    });
  getCache.set(url, { value: cached?.value, expiresAt: cached?.expiresAt || 0, promise });
  return promise;
}

async function sendJSON(url, method, body) {
  const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: body == null ? undefined : JSON.stringify(body) });
  return handleResponse(res, url);
}

// Authentication
export const getCurrentUser = () => getJSON('/api/auth/me');
export const loginUser = (username, password = '') => sendJSON('/api/auth/login', 'POST', { username, password });
export const registerUser = (username) => sendJSON('/api/auth/register', 'POST', { username });
export const logoutUser = () => sendJSON('/api/auth/logout', 'POST', {});
export const listUsers = () => getJSON('/api/auth/users');
export const removeUser = (userId) => sendJSON(`/api/auth/users/${Number(userId)}`, 'DELETE', {});
export const changeAdminPassword = (currentPassword, newPassword) => sendJSON('/api/auth/admin/password', 'POST', { current_password: currentPassword, new_password: newPassword });

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
export const getActivityLog = () => getJSON('/api/portfolio/logs');
export const logClientActivity = (action, details = {}) => sendJSON('/api/portfolio/activity', 'POST', { action, details });

// Institutional-lite operations
export const getPortfolioOperations = () => getJSON('/api/portfolio/operations');
export const reconcileBroker = (payload) => sendJSON('/api/portfolio/reconciliation', 'POST', payload);
export const syncCorporateActions = (payload = {}) => sendJSON('/api/portfolio/corporate-actions/sync', 'POST', payload);
export const getDividendHistory = (symbol, options = {}) => {
  const ticker = encodeURIComponent(String(symbol || '').toUpperCase());
  const refresh = Boolean(options?.refresh);
  const url = `/api/portfolio/dividends/latest/${ticker}${refresh ? '?refresh=1' : ''}`;
  return refresh ? getJSON(url) : getJSONCached(url, 5 * 60_000);
};
// Backward-compatible name. The backend response already contains the full history.
export const getLatestDividend = getDividendHistory;
export const getDividendProviderHealth = () => getJSON('/api/portfolio/dividends/health');
export const verifyCorporateAction = (id, sourceUrl) => sendJSON(`/api/portfolio/corporate-actions/${Number(id)}/verify`, 'POST', { source_url: sourceUrl });
export const recordCorporateActionReceipt = (id, payload) => sendJSON(`/api/portfolio/corporate-actions/${Number(id)}/receipt`, 'POST', payload);
export const postCorporateActionReceipt = (id) => sendJSON('/api/portfolio/corporate-actions/post', 'POST', { action_id: Number(id) });
export const confirmSettlement = (eventId, note = '') => sendJSON(`/api/portfolio/settlements/${Number(eventId)}/confirm`, 'POST', { note });
export const lockNav = (snapshotDate) => sendJSON(`/api/portfolio/nav/${encodeURIComponent(snapshotDate)}/lock`, 'POST', {});
export const resolveRestatement = (id) => sendJSON(`/api/portfolio/restatements/${Number(id)}/resolve`, 'POST', {});
export const updateSecurity = (symbol, payload) => sendJSON(`/api/portfolio/securities/${encodeURIComponent(symbol)}`, 'POST', payload);
export const resolveSecurity = (symbol) => sendJSON(`/api/portfolio/securities/${encodeURIComponent(symbol)}/resolve`, 'POST', {});
export const resolveAllSecurities = () => sendJSON('/api/portfolio/securities/resolve', 'POST', {});
