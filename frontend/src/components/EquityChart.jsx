import React, { useMemo, useState } from 'react';
import { formatMoney } from '../lib/format.js';

function pct(value) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value) >= 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}%`;
}

const DEFAULT_PAD = { top: 20, right: 20, bottom: 30, left: 70 };

export default function EquityChart({ data, benchmark = [], width = 760, height = 300, pad = DEFAULT_PAD }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const geom = useMemo(() => {
    if (!data || data.length < 2) return null;
    const w = width - pad.left - pad.right;
    const h = height - pad.top - pad.bottom;
    const benchmarkByDate = new Map((benchmark || []).map(row => [row.date, row]));
    let lastBenchmark = (benchmark || []).filter(row => String(row.date) <= String(data[0].date)).at(-1) || null;
    let benchmarkBase = lastBenchmark?.index ? Number(lastBenchmark.index) : null;
    const firstNav = Number(data[0].nav);
    const points = data.map(row => {
      if (benchmarkByDate.has(row.date)) lastBenchmark = benchmarkByDate.get(row.date);
      if (benchmarkBase == null && lastBenchmark?.index) benchmarkBase = Number(lastBenchmark.index);
      const benchmarkIndex = lastBenchmark?.index && benchmarkBase ? Number(lastBenchmark.index) / benchmarkBase : null;
      return { ...row, benchmarkNav: benchmarkIndex ? firstNav * benchmarkIndex : null, benchmarkIndex };
    });
    const values = points.flatMap(point => [Number(point.nav), point.benchmarkNav].filter(value => Number.isFinite(value)));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const px = index => pad.left + (index / (points.length - 1)) * w;
    const py = value => pad.top + h - ((value - min) / span) * h;
    const portfolioPoints = points.map((point, index) => `${px(index).toFixed(1)},${py(point.nav).toFixed(1)}`);
    const benchmarkPoints = points.map((point, index) => point.benchmarkNav == null ? null : `${px(index).toFixed(1)},${py(point.benchmarkNav).toFixed(1)}`).filter(Boolean);
    const yTicks = Array.from({ length: 5 }, (_, index) => min + (span * index) / 4);
    return { w, h, points, portfolioPoints, benchmarkPoints, yTicks, px, py, last: points.length - 1 };
  }, [data, benchmark, width, height, pad]);

  if (!geom) return <div className="muted">Chưa đủ dữ liệu NAV.</div>;
  const xTicks = [...new Set([0, Math.floor(geom.last / 2), geom.last])];
  const active = activeIndex == null ? null : geom.points[activeIndex];
  const activeX = activeIndex == null ? null : geom.px(activeIndex);

  function move(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const viewX = ((event.clientX - rect.left) / rect.width) * width;
    const ratio = Math.max(0, Math.min(1, (viewX - pad.left) / geom.w));
    setActiveIndex(Math.round(ratio * geom.last));
  }

  return <div className="interactive-equity-chart">
    <svg viewBox={`0 0 ${width} ${height}`} className="equity-chart" role="img" aria-label="NAV và VN-Index theo thời gian" onPointerMove={move} onPointerDown={move} onPointerLeave={() => setActiveIndex(null)}>
      <defs><filter id="qport-chart-glow"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
      {geom.yTicks.map(tick => <g key={tick}>
        <line x1={pad.left} x2={width - pad.right} y1={geom.py(tick)} y2={geom.py(tick)} stroke="var(--border)" strokeWidth={1} />
        <text x={pad.left - 7} y={geom.py(tick) + 3} textAnchor="end" className="axis-text">{formatMoney(tick, true)}</text>
      </g>)}
      {xTicks.map(index => <text key={index} x={geom.px(index)} y={height - 7} textAnchor="middle" className="axis-text">{geom.points[index].date}</text>)}
      {geom.benchmarkPoints.length > 1 && <polyline className="benchmark-line" points={geom.benchmarkPoints.join(' ')} fill="none" stroke="var(--warning)" strokeWidth={1.6} strokeDasharray="6 5" />}
      <polyline className="portfolio-line" points={geom.portfolioPoints.join(' ')} fill="none" stroke="var(--accent)" strokeWidth={2.2} />
      {active && <g className="chart-crosshair">
        <line x1={activeX} x2={activeX} y1={pad.top} y2={height - pad.bottom} stroke="var(--text-secondary)" strokeWidth={1} strokeDasharray="3 4" />
        <circle cx={activeX} cy={geom.py(active.nav)} r={5} fill="var(--accent)" filter="url(#qport-chart-glow)" />
      </g>}
      <rect className="chart-pointer-capture" x={pad.left} y={pad.top} width={geom.w} height={geom.h} fill="transparent" />
    </svg>
    {active && <div className={`chart-tooltip ${activeIndex > geom.last * .62 ? 'align-right' : ''}`} style={{ left: `${(activeX / width) * 100}%` }} role="status">
      <b>{active.date}</b><span>NAV <strong>{formatMoney(active.nav, false)} ₫</strong></span>
      <span>Phiên <strong className={Number(active.daily_return) >= 0 ? 'pos' : 'neg'}>{pct(active.daily_return)}</strong></span>
      {active.benchmarkIndex != null && <span>VN-Index <strong>{pct(active.benchmarkIndex - 1)}</strong></span>}
    </div>}
  </div>;
}
