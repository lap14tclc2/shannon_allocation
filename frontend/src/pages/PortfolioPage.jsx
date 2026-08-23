import React from 'react';
import PortfolioDashboardPage from './PortfolioDashboardPage.jsx';
import ReceivedDividendsPanel from '../components/ReceivedDividendsPanel.jsx';
import '../received-dividends.css';

export default function PortfolioPage(props) {
  return <>
    <PortfolioDashboardPage {...props} />
    <div className="page portfolio-received-supplement">
      <ReceivedDividendsPanel locale={props.locale || 'en'} />
    </div>
  </>;
}
