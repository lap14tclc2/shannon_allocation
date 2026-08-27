import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = readFileSync(join(root, 'src/pages/FinanceDataPage.jsx'), 'utf8');

let pass = true;
function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) pass = false;
}

check('Finance Data uses a bounded polling interval', source.includes('const FINANCE_DATA_REFRESH_INTERVAL_MS = 10_000') && source.includes('window.setInterval(poll, FINANCE_DATA_REFRESH_INTERVAL_MS)'));
check('polling refreshes data silently without loading flicker', source.includes('refresh({ silent: true, isCancelled: () => disposed })'));
check('polling avoids overlapping requests', source.includes('if (disposed || document.visibilityState === \'hidden\' || pollInFlight) return;'));
check('hidden tabs pause polling', source.includes('document.visibilityState === \'hidden\''));
check('visible tabs refresh immediately', source.includes('document.visibilityState === \'visible\'') && source.includes('document.addEventListener(\'visibilitychange\', handleVisibilityChange)'));
check('polling timer is cleaned up', source.includes('window.clearInterval(timer)'));
check('visibility listener is cleaned up', source.includes('document.removeEventListener(\'visibilitychange\', handleVisibilityChange)'));
check('external refresh never forces a full-page reload', !source.includes('window.location.reload') && !source.includes('location.reload'));
check('user can see automatic refresh status', source.includes('Tự động cập nhật mỗi 10 giây'));

if (pass) console.log('\nFINANCE DATA REFRESH CONTRACT PASSED');
process.exit(pass ? 0 : 1);
