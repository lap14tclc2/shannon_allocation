import React from 'react';
import PerformancePage from './PerformancePage.jsx';
import PerformanceHistoryPanel from '../components/PerformanceHistoryPanel.jsx';

export default function PerformancePageV2(props) {
  return <>
    <PerformancePage {...props} />
    <div className="page performance-history-supplement">
      <PerformanceHistoryPanel performance={props.performance || {}} locale={props.locale || 'en'} />
    </div>
  </>;
}
