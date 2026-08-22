import React, { useEffect, useState } from 'react';
import OptimizerListPage from './OptimizerListPage.jsx';
import { listOptimizerExperiments } from '../lib/api.js';

/**
 * Application start page.
 *
 * `/` intentionally renders the same Growth Optimizer experience as `/optimizer`.
 * The Python SSR route still supplies the legacy `home` page key for backward
 * compatibility, so this lightweight adapter keeps root navigation stable while
 * making the optimizer the actual product landing page.
 */
export default function HomePage() {
  const [experiments, setExperiments] = useState(null);

  useEffect(() => {
    let active = true;
    document.title = 'Growth Optimizer · Shannon/ERC';

    listOptimizerExperiments()
      .then((items) => {
        if (active) setExperiments(items || []);
      })
      .catch(() => {
        if (active) setExperiments([]);
      });

    return () => { active = false; };
  }, []);

  // OptimizerListPage owns an internal experiment list initialized from props.
  // Remount once the API response arrives so `/` receives the same populated
  // experiment history that `/optimizer` gets directly from SSR.
  const loaded = experiments !== null;
  return (
    <div className="optimizer-start-page">
      <style>{`.optimizer-start-page > .page > .breadcrumb { display: none; }`}</style>
      <OptimizerListPage
        key={loaded ? 'optimizer-loaded' : 'optimizer-bootstrap'}
        experiments={experiments || []}
      />
    </div>
  );
}
