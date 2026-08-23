import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { syncPortfolio } from '../lib/api.js';

const LEASE_MS = 10 * 60 * 1000;

function initialSnapshot(dashboard, positions) {
  const history = dashboard?.market_data?.history || {};
  const quality = dashboard?.risk?.quality || {};
  const total = Number(history.total_symbols ?? positions.length ?? 0);
  const ready = Number(history.ready_symbols ?? quality.eligible_symbols ?? 0);
  const symbols = Array.isArray(history.symbols) ? history.symbols : [];
  const missing = Array.isArray(quality.missing_symbols) ? quality.missing_symbols : [];
  const providers = [...new Set(symbols.map(row => row.source).filter(Boolean))];
  const state = total === 0 ? 'NO_HOLDINGS' : ready >= total && total > 0 ? 'READY' : 'BUILDING';
  return { state, total, ready, symbols, missing, providers };
}

export default function MarketHistoryIndicator({ dashboard = {}, locale = 'en' }) {
  const text = (en, vi) => locale === 'vi' ? vi : en;
  const positions = dashboard?.portfolio?.positions || [];
  const initial = useMemo(() => initialSnapshot(dashboard, positions), [dashboard, positions]);
  const [target, setTarget] = useState(null);
  const [snapshot, setSnapshot] = useState(initial);
  const [phase, setPhase] = useState(initial.state);
  const [error, setError] = useState('');

  const symbolKey = positions.map(row => String(row.symbol || '').toUpperCase()).filter(Boolean).sort().join(',');
  const leaseKey = `qport:d1-backfill:${symbolKey}`;

  useEffect(() => {
    if (typeof document !== 'undefined') setTarget(document.querySelector('.hero-meta'));
  }, []);

  async function runBackfill({ automatic = false } = {}) {
    if (!positions.length || phase === 'SYNCING') return;
    setPhase('SYNCING');
    setError('');
    try {
      if (typeof window !== 'undefined') window.localStorage.setItem(leaseKey, String(Date.now()));
      const result = await syncPortfolio();
      const history = result?.history_status || {};
      const rows = Array.isArray(history.symbols) ? history.symbols : [];
      const total = Number(history.total_symbols ?? positions.length);
      const ready = Number(history.ready_symbols ?? rows.filter(row => row.risk_ready).length);
      const providers = [...new Set(rows.map(row => row.source).filter(Boolean))];
      const next = {
        state: ready >= total && total > 0 ? 'READY' : (result?.errors?.length ? 'PARTIAL' : 'BUILDING'),
        total,
        ready,
        symbols: rows,
        missing: rows.filter(row => !row.risk_ready).map(row => row.symbol),
        providers,
      };
      setSnapshot(next);
      setPhase(next.state);
      if (typeof window !== 'undefined') {
        if (next.state === 'READY') window.localStorage.removeItem(leaseKey);
        else window.localStorage.setItem(leaseKey, String(Date.now()));
        window.setTimeout(() => window.location.reload(), 700);
      }
    } catch (err) {
      setPhase('ERROR');
      setError(err?.message || text('D1 history sync failed.', 'Đồng bộ lịch sử D1 thất bại.'));
      if (!automatic && typeof window !== 'undefined') window.localStorage.removeItem(leaseKey);
    }
  }

  useEffect(() => {
    if (!target || !positions.length || initial.state === 'READY') return;
    let leasedRecently = false;
    try {
      const last = Number(window.localStorage.getItem(leaseKey) || 0);
      leasedRecently = last > 0 && Date.now() - last < LEASE_MS;
      if (!leasedRecently) window.localStorage.setItem(leaseKey, String(Date.now()));
    } catch { /* storage may be unavailable */ }
    if (!leasedRecently) runBackfill({ automatic: true });
    // Run once for the current holding set. A complete sync reloads the dashboard;
    // partial histories keep a short lease so newly listed symbols cannot loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, symbolKey]);

  if (!target || !positions.length) return null;

  const total = snapshot.total || positions.length;
  const ready = Math.min(total, snapshot.ready || 0);
  const providers = snapshot.providers?.length ? snapshot.providers.map(value => String(value).toUpperCase()).join(' / ') : '';
  const label = phase === 'SYNCING'
    ? text('D1 HISTORY · SYNCING', 'LỊCH SỬ D1 · ĐANG TẢI')
    : phase === 'READY'
      ? text('D1 HISTORY · READY', 'LỊCH SỬ D1 · SẴN SÀNG')
      : phase === 'ERROR'
        ? text('D1 HISTORY · ERROR', 'LỊCH SỬ D1 · LỖI')
        : phase === 'PARTIAL'
          ? text('D1 HISTORY · PARTIAL', 'LỊCH SỬ D1 · MỘT PHẦN')
          : text('D1 HISTORY · BUILDING', 'LỊCH SỬ D1 · ĐANG XÂY DỰNG');

  const title = error || (snapshot.missing?.length
    ? text(`Missing/short history: ${snapshot.missing.join(', ')}`, `Thiếu/chưa đủ lịch sử: ${snapshot.missing.join(', ')}`)
    : text('Stored D1 history used for risk diagnostics.', 'Lịch sử D1 đã lưu dùng cho chẩn đoán rủi ro.'));

  return createPortal(
    <span className={`market-history-indicator market-history-${phase.toLowerCase()}`} title={title} aria-live="polite">
      <span className="market-history-dot" aria-hidden="true" />
      <b>{label}</b>
      <span>{ready}/{total}</span>
      {providers && phase === 'READY' && <span className="market-history-provider">{providers}</span>}
      {(phase === 'ERROR' || phase === 'PARTIAL' || (phase === 'BUILDING' && ready < total)) && (
        <button type="button" onClick={() => runBackfill()} disabled={phase === 'SYNCING'}>{text('Retry', 'Thử lại')}</button>
      )}
    </span>,
    target,
  );
}
