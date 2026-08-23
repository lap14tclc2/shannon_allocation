import React from 'react';
import PerformancePage from './PerformancePage.jsx';
import PerformanceHistoryPanel from '../components/PerformanceHistoryPanel.jsx';

export default function PerformancePageV2(props) {
  const performance = props.performance || {};
  const hasTrackedSeries = Array.isArray(performance.series) && performance.series.length > 0;
  return <>
    <PerformancePage {...props} />
    {hasTrackedSeries && <div className="page performance-history-supplement">
      <PerformanceHistoryPanel performance={performance} locale={props.locale || 'en'} />
    </div>}
  </>;
}
