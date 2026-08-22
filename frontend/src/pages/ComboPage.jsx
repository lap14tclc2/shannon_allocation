import React from 'react';
import CombinationDetail from '../components/CombinationDetail.jsx';

export default function ComboPage({ combo, runId }) {
  return (
    <div className="page">
      <div className="breadcrumb">
        <a href="/">All runs</a> <span>/</span>
        <a href={`/runs/${runId}`}>{runId}</a> <span>/</span>
        {combo.symbols?.join(' ')}
      </div>
      <CombinationDetail combo={combo} />
    </div>
  );
}