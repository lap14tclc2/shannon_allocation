import React, { useMemo } from 'react';
import { formatMoney } from '../lib/format.js';

// Pure, SSR-safe SVG line chart (no measurement / effects) — renders identically
// on the server and after hydration.
export default function EquityChart({ data, width = 760, height = 280, pad = { top: 16, right: 20, bottom: 26, left: 64 } }) {
  const geom = useMemo(() => {
    if (!data || data.length < 2) return null;
    const w = width - pad.left - pad.right;
    const h = height - pad.top - pad.bottom;
    const min = Math.min(...data.map((d) => d.nav));
    const max = Math.max(...data.map((d) => d.nav));
    const span = max - min || 1;
    const px = (i) => pad.left + (i / (data.length - 1)) * w;
    const py = (v) => pad.top + h - ((v - min) / span) * h;
    const pts = data.map((d, i) => `${px(i).toFixed(1)},${py(d.nav).toFixed(1)}`);
    // Y axis ticks (nice numbers)
    const ticks = 4;
    const yTicks = Array.from({ length: ticks + 1 }, (_, i) => min + (span * i) / ticks);
    const last = data.length - 1;
    return { w, h, pts, yTicks, min, max, px, py, last, firstIdx: 0 };
  }, [data, width, height, pad]);

  if (!geom) return <div className="muted">Insufficient NAV data.</div>;

  const xTicks = [0, Math.floor(geom.last / 2), geom.last];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="equity-chart" role="img" aria-label="NAV over time">
      {geom.yTicks.map((t) => (
        <g key={t}>
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={geom.py(t)}
            y2={geom.py(t)}
            stroke="var(--border)"
            strokeWidth={1}
          />
          <text x={pad.left - 6} y={geom.py(t) + 3} textAnchor="end" className="axis-text">
            {formatMoney(t, true)}
          </text>
        </g>
      ))}
      {xTicks.map((i) => (
        <text key={i} x={geom.px(i)} y={height - 6} textAnchor="middle" className="axis-text">
          {data[i].date}
        </text>
      ))}
      <polyline
        points={geom.pts.join(' ')}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={2}
      />
      <circle cx={geom.px(geom.last)} cy={geom.py(data[geom.last].nav)} r={3.5} fill="var(--accent)" />
    </svg>
  );
}