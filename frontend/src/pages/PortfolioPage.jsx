import React from 'react';
import PortfolioDashboardPage from './PortfolioDashboardPage.jsx';
import PortfolioAssessmentEnhancer from '../components/PortfolioAssessmentEnhancer.jsx';
import ReceivedDividendsPanel from '../components/ReceivedDividendsPanel.jsx';
import MarketHistoryIndicator from '../components/MarketHistoryIndicator.jsx';
import '../received-dividends.css';

export default function PortfolioPage(props) {
  const dashboard = props.dashboard || {};
  const locale = props.locale || 'en';
  return <>
    <PortfolioDashboardPage {...props} />
    <MarketHistoryIndicator dashboard={dashboard} locale={locale} />
    <PortfolioAssessmentEnhancer dashboard={dashboard} locale={locale} />
    <ReceivedDividendsPanel locale={locale} />
  </>;
}
