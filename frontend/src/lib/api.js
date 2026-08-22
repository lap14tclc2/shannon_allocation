async function getJSON(url, signal) {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`Request failed: ${res.status} ${url}`);
  return res.json();
}

export async function listRuns() {
  const data = await getJSON('/api/runs');
  return data.runs || [];
}

export async function getRunIndex(runId) {
  return getJSON(`/api/runs/${encodeURIComponent(runId)}/index`);
}

export async function getRunMeta(runId) {
  return getJSON(`/api/runs/${encodeURIComponent(runId)}/meta`);
}

export async function getCombination(runId, slug) {
  return getJSON(`/api/runs/${encodeURIComponent(runId)}/combinations/${encodeURIComponent(slug)}`);
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
  const res = await fetch('/api/combination/health', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbols: symbols || [],
      include_suggestions: Boolean(includeSuggestions),
      suggestion_limit: 5,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Combination analysis failed: ${res.status}`);
  return data;
}

export async function listOptimizerExperiments() {
  const data = await getJSON('/api/optimizer');
  return data.experiments || [];
}

export async function getOptimizerExperiment(experimentId) {
  return getJSON(`/api/optimizer/${encodeURIComponent(experimentId)}`);
}

export function optimizerDownloadAllUrl(experimentId) {
  return `/api/optimizer/${encodeURIComponent(experimentId)}/download`;
}

export function optimizerFileUrl(experimentId, name) {
  return `/api/optimizer/${encodeURIComponent(experimentId)}/file?name=${encodeURIComponent(name)}`;
}

export async function startOptimizerRun(cfg) {
  const res = await fetch('/api/optimizer/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cfg || {}),
  });
  return res.json();
}

export async function getOptimizerStatus() {
  const data = await getJSON('/api/optimizer/status');
  return data.runs || [];
}

export async function deleteOptimizerExperiment(experimentId) {
  const res = await fetch(`/api/optimizer/${encodeURIComponent(experimentId)}`, { method: 'DELETE' });
  return res.json();
}

export async function getCandidateHistory(experimentId, symbols, allocationDays, signal) {
  const days = allocationDays.join(',');
  return getJSON(
    `/api/optimizer/${encodeURIComponent(experimentId)}/candidate?symbols=${encodeURIComponent(symbols.join(','))}&days=${encodeURIComponent(days)}`,
    signal
  );
}
