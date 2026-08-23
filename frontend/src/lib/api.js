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

// ---- Operational buy-and-hold portfolio APIs ----
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

// ---- Legacy research APIs (explicitly isolated from the live ledger) ----
export async function listRuns() {
  const data = await getJSON('/api/research/runs');
  return data.runs || [];
}

export async function getRunIndex(runId) {
  return getJSON(`/api/research/runs/${encodeURIComponent(runId)}/index`);
}

export async function getRunMeta(runId) {
  return getJSON(`/api/research/runs/${encodeURIComponent(runId)}/meta`);
}

export async function getCombination(runId, slug) {
  return getJSON(`/api/research/runs/${encodeURIComponent(runId)}/combinations/${encodeURIComponent(slug)}`);
}

export async function listAvailableSymbols() {
  const data = await getJSON('/api/symbols');
  return {
    symbols: data.symbols || [],
    minSelected: Number(data.min_selected || 5),
    maxSelected: Number(data.max_selected || 10),
  };
}

export async function analyzeCombination(symbols, includeSuggestions = true) {
  return sendJSON('/api/combination/health', 'POST', {
    symbols: symbols || [],
    include_suggestions: Boolean(includeSuggestions),
    suggestion_limit: 5,
  });
}

export async function listOptimizerExperiments() {
  const data = await getJSON('/api/research/optimizer');
  return data.experiments || [];
}

export async function getOptimizerExperiment(experimentId) {
  return getJSON(`/api/research/optimizer/${encodeURIComponent(experimentId)}`);
}

export function optimizerDownloadAllUrl(experimentId) {
  return `/api/research/optimizer/${encodeURIComponent(experimentId)}/download`;
}

export function optimizerFileUrl(experimentId, name) {
  return `/api/research/optimizer/${encodeURIComponent(experimentId)}/file?name=${encodeURIComponent(name)}`;
}

export async function startOptimizerRun(cfg) {
  return sendJSON('/api/research/optimizer/run', 'POST', cfg || {});
}

export async function getOptimizerStatus() {
  const data = await getJSON('/api/research/optimizer/status');
  return data.runs || [];
}

export async function deleteOptimizerExperiment(experimentId) {
  const res = await fetch(`/api/research/optimizer/${encodeURIComponent(experimentId)}`, { method: 'DELETE' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Delete failed: ${res.status}`);
  return data;
}

export async function getCandidateHistory(experimentId, symbols, allocationDays, signal) {
  const days = allocationDays.join(',');
  return getJSON(
    `/api/research/optimizer/${encodeURIComponent(experimentId)}/candidate?symbols=${encodeURIComponent(symbols.join(','))}&days=${encodeURIComponent(days)}`,
    signal
  );
}
