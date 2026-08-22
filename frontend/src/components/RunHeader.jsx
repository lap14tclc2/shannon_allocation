import React from 'react';
import { formatMoney } from '../lib/format.js';

export default function RunHeader({ meta }) {
  const p = meta?.params || {};
  return (
    <div className="run-header">
      <span className="run-title">Run {meta?.run_id}</span>
      <span>generated {meta?.generated_at}</span>
      <span>start {formatMoney(p.initial_balance)} VND · deposit {formatMoney(p.annual_deposit)} VND/yr</span>
      <span>allocation {p.allocation_frequency} · lookback {p.lookback_days} days</span>
    </div>
  );
}