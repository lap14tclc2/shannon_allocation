let authRedirectInProgress = false;
const getCache = new Map();
const PORTFOLIO_SCOPE_KEY = 'qport.activePortfolioId';
let portfolioScopeId = (() => {
  if (typeof window === 'undefined') return '';
  return String(window.localStorage.getItem(PORTFOLIO_SCOPE_KEY) || '');
})();

function setPortfolioScope(value) {
  portfolioScopeId = value ? String(value) : '';
  if (typeof window === 'undefined') return;
  if (portfolioScopeId) window.localStorage.setItem(PORTFOLIO_SCOPE_KEY, portfolioScopeId);
  else window.localStorage.removeItem(PORTFOLIO_SCOPE_KEY);
}

function scopedHeaders(headers = {}) {
  return portfolioScopeId
    ? { ...headers, 'X-QPort-Portfolio-Id': portfolioScopeId }
    : headers;
}

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
    const error = apiError(data, `Request failed: ${res.status} ${url}`);
    error.invalidPortfolioScope = res.status === 404 && data?.code === 'PORTFOLIO_NOT_FOUND';
    throw error;
  }
  return data;
}

async function getJSON(url, signal, retryScope = true) {
  const res = await fetch(url, { signal, cache: 'no-store', headers: scopedHeaders({
    'Cache-Control': 'no-cache',
    Pragma: 'no-cache',
  }) });
  try {
    return await handleResponse(res, url);
  } catch (error) {
    if (retryScope && portfolioScopeId && error.invalidPortfolioScope) {
      setPortfolioScope('');
      clearGetCache();
      return getJSON(url, signal, false);
    }
    throw error;
  }
}

async function getJSONCached(url, ttlMs = 60_000, { bypass = false } = {}) {
  const now = Date.now();
  const cached = getCache.get(url);
  if (!bypass && cached && cached.expiresAt > now) return cached.value;
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

function clearGetCache() {
  getCache.clear();
}

async function sendJSON(url, method, body) {
  const res = await fetch(url, { method, headers: scopedHeaders({ 'Content-Type': 'application/json' }), body: body == null ? undefined : JSON.stringify(body) });
  const data = await handleResponse(res, url);
  if (method !== 'GET') clearGetCache();
  return data;
}

// Authentication
export const getCurrentUser = () => getJSONCached('/api/auth/me', 60_000);
export async function loginUser(username, password = '') {
  const result = await sendJSON('/api/auth/login', 'POST', { username, password });
  setPortfolioScope('');
  return result;
}
export async function registerUser(username) {
  const result = await sendJSON('/api/auth/register', 'POST', { username });
  setPortfolioScope('');
  return result;
}
export async function logoutUser() {
  try {
    return await sendJSON('/api/auth/logout', 'POST', {});
  } finally {
    setPortfolioScope('');
  }
}
export const listUsers = () => getJSON('/api/auth/users');
export const removeUser = (userId) => sendJSON(`/api/auth/users/${Number(userId)}`, 'DELETE', {});
export const changeAdminPassword = (currentPassword, newPassword) => sendJSON('/api/auth/admin/password', 'POST', { current_password: currentPassword, new_password: newPassword });
export const getAdminUserPortfolio = (userId) => getJSON(`/api/admin/users/${Number(userId)}/portfolio`);
export const getAdminFinanceData = (params = {}) => {
  const query = new URLSearchParams();
  if (params.offset != null) query.set('offset', String(params.offset));
  if (params.limit != null) query.set('limit', String(params.limit));
  if (params.exchange) query.set('exchange', String(params.exchange));
  return getJSON(`/api/admin/finance-data${query.toString() ? `?${query}` : ''}`);
};
export const crawlAdminFinanceUniverse = () => sendJSON('/api/admin/finance-data/universe', 'POST', {});
export const queueAdminFinanceCrawl = (exchange = '') => sendJSON('/api/admin/finance-data/crawl-all', 'POST', exchange ? { exchange } : {});
export const crawlAdminFinanceData = (symbol) => sendJSON('/api/admin/finance-data/crawl', 'POST', { symbol });
export const retryAdminFinanceData = (symbol) => sendJSON(`/api/admin/finance-data/${encodeURIComponent(String(symbol).toUpperCase())}/retry`, 'POST', {});
export const getPortfolioFinanceData = (symbol) => getJSON(`/api/portfolio/finance-data/${encodeURIComponent(String(symbol).toUpperCase())}`);

// Multi-portfolio registry. The active portfolio is persisted server-side per user,
// so all existing portfolio endpoints remain safely scoped without client headers.
export async function listPortfolios() {
  const result = await getJSON('/api/portfolios');
  if (result.active_portfolio_id) setPortfolioScope(result.active_portfolio_id);
  return result;
}
export const createPortfolio = (name) => sendJSON('/api/portfolios', 'POST', { name });
export const renamePortfolio = (portfolioId, name) => sendJSON(`/api/portfolios/${Number(portfolioId)}`, 'PATCH', { name });
export async function activatePortfolio(portfolioId) {
  const result = await sendJSON(`/api/portfolios/${Number(portfolioId)}/select`, 'POST', {});
  setPortfolioScope(result.active_portfolio_id || portfolioId);
  clearGetCache();
  return result;
}
export async function removePortfolio(portfolioId, confirmation) {
  const result = await sendJSON(`/api/portfolios/${Number(portfolioId)}`, 'DELETE', { confirmation });
  if (result.portfolio?.next_active_portfolio_id) {
    setPortfolioScope(result.portfolio.next_active_portfolio_id);
  }
  clearGetCache();
  return result;
}

export const getPortfolioDashboard = () => getJSON('/api/portfolio');
export async function getPortfolioHoldingSymbols() {
  const data = await getJSON('/api/portfolio/holding-symbols');
  return data.symbols || [];
}
export async function listPortfolioTransactions() { const d = await getJSON('/api/portfolio/transactions'); return d.transactions || []; }
export async function listPortfolioTransactionAudit() { const d = await getJSON('/api/portfolio/transaction-audit'); return d.corrections || []; }
export const createPortfolioTransaction = (payload) => sendJSON('/api/portfolio/transactions', 'POST', payload);
export const previewPortfolioImport = (payload) => sendJSON('/api/portfolio/transactions/import/preview', 'POST', payload);
export const commitPortfolioImport = (payload) => sendJSON('/api/portfolio/transactions/import', 'POST', payload);
export const updatePortfolioTransaction = (eventId, payload) => sendJSON(`/api/portfolio/transactions/${Number(eventId)}`, 'PATCH', payload);
export const discardPortfolioTransaction = (eventId, reason) => sendJSON(`/api/portfolio/transactions/${Number(eventId)}`, 'DELETE', { reason });
// Backward-compatible alias for older clients. The server never physically deletes the ledger row.
export const deletePortfolioTransaction = discardPortfolioTransaction;
export const deletePortfolio = (confirmation) => sendJSON('/api/portfolio', 'DELETE', { confirmation });
export const syncPortfolio = () => sendJSON('/api/portfolio/sync', 'POST', {});
export const getPortfolioPerformance = () => getJSON('/api/portfolio/performance');
export const getPortfolioRisk = () => getJSON('/api/portfolio/risk');
export async function listPortfolioSnapshots() { const d = await getJSON('/api/portfolio/snapshots'); return d.snapshots || []; }
export const getPortfolioPreferences = () => getJSON('/api/portfolio/preferences');
export const setReferenceWeights = (weights) => sendJSON('/api/portfolio/reference-weights', 'POST', { weights });
export const setCashReserve = (amount) => sendJSON('/api/portfolio/cash-reserve', 'POST', { amount });
export const getActivityLog = (params = {}) => {
  const query = new URLSearchParams();
  for (const key of ['page', 'page_size', 'category', 'actor_type', 'status', 'q']) {
    if (params[key] != null && params[key] !== '' && params[key] !== 'ALL') query.set(key, String(params[key]));
  }
  return getJSON(`/api/admin/logs${query.toString() ? `?${query}` : ''}`);
};
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

export const getValuationReport = (symbol) => {
  const ticker = encodeURIComponent(String(symbol || '').toUpperCase());
  return getJSON(`/api/portfolio/valuation/${ticker}?fresh=${Date.now()}`);
};

export async function getValuationReports(symbols) {
  const unique = [...new Set((symbols || []).map(symbol => String(symbol || '').toUpperCase()).filter(Boolean))];
  const reports = {};
  const errors = {};
  let cursor = 0;
  async function worker() {
    while (cursor < unique.length) {
      const symbol = unique[cursor++];
      try {
        const res = await getValuationReport(symbol);
        if (res?.ok && res.report) reports[symbol] = res.report;
        else errors[symbol] = { code: res?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: res?.error || 'Nguồn dữ liệu không trả về báo cáo.' };
      } catch (error) {
        errors[symbol] = { code: error?.code || 'VALUATION_SOURCE_UNAVAILABLE', message: error?.message || 'Không thể tải dữ liệu định giá.' };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(2, unique.length) }, () => worker()));
  return { reports, errors };
}

export async function getDividendHistories(symbols, options = {}) {
  const unique = [...new Set((symbols || []).map(symbol => String(symbol || '').toUpperCase()).filter(Boolean))];
  const concurrency = Math.max(1, Math.min(Number(options.concurrency) || 6, 10));
  const results = new Array(unique.length);
  let cursor = 0;

  async function worker() {
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= unique.length) return;
      const symbol = unique[index];
      try {
        results[index] = { symbol, result: await getDividendHistory(symbol, { refresh: Boolean(options.refresh) }), error: null };
      } catch (error) {
        results[index] = { symbol, result: null, error: error.message || 'Không thể tải dữ liệu cổ tức.' };
      }
      if (typeof options.onResult === 'function') options.onResult(results[index], index);
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, unique.length) }, () => worker()));
  return results;
}

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
