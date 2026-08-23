async function getJSON(url, signal) {
  const res = await fetch(url, { signal });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed: ${res.status} ${url}`);
  return data;
}

async function sendJSON(url, method, body) {
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body == null ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed: ${res.status} ${url}`);
  return data;
}

export async function getPortfolioDashboard() {
  return getJSON('/api/portfolio');
}

export async function listPortfolioTransactions() {
  const data = await getJSON('/api/portfolio/transactions');
  return data.transactions || [];
}

export async function createPortfolioTransaction(payload) {
  return sendJSON('/api/portfolio/transactions', 'POST', payload);
}

export async function syncPortfolio() {
  return sendJSON('/api/portfolio/sync', 'POST', {});
}

export async function getPortfolioPerformance() {
  return getJSON('/api/portfolio/performance');
}

export async function getPortfolioRisk() {
  return getJSON('/api/portfolio/risk');
}

export async function listPortfolioSnapshots() {
  const data = await getJSON('/api/portfolio/snapshots');
  return data.snapshots || [];
}

export async function setReferenceWeights(weights) {
  return sendJSON('/api/portfolio/reference-weights', 'POST', { weights });
}
