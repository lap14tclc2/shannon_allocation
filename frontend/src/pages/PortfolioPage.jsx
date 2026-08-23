import React from 'react';
import PortfolioDashboardPage from './PortfolioDashboardPage.jsx';
import PortfolioAssessmentEnhancer from '../components/PortfolioAssessmentEnhancer.jsx';
import ReceivedDividendsPanel from '../components/ReceivedDividendsPanel.jsx';
import '../received-dividends.css';

export default function PortfolioPage(props) {
  return <>
    <PortfolioDashboardPage {...props} />
    <PortfolioAssessmentEnhancer dashboard={props.dashboard || {}} locale={props.locale || 'en'} />
    <ReceivedDividendsPanel locale={props.locale || 'en'} />
  </>;
}
