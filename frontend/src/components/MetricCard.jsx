import React from 'react';

export default function MetricCard({ label, value, note, tone = '', dataSensitive }) {
  const className = ['metric-card', tone].filter(Boolean).join(' ');
  return (
    <div className={className}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" data-sensitive={dataSensitive}>{value}</div>
      {note && <div className="metric-note">{note}</div>}
    </div>
  );
}

export { MetricCard as Metric };
