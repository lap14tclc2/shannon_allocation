import React from 'react';
import PortfolioDashboardPage from './PortfolioDashboardPage.jsx';

/** Compatibility page key for older SSR payloads.
 * The product home is now the buy-and-hold Portfolio Dashboard.
 */
export default function HomePage({ dashboard = {} }) {
  return <PortfolioDashboardPage dashboard={dashboard} />;
}
