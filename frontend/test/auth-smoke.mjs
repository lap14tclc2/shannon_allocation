import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const ssrEntry = join(root, 'dist-ssr', 'ssr-entry.mjs');
const forbiddenCredential = 'abc' + '123';

let pass = true;
function check(name, ok) {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (!ok) pass = false;
}

check('SSR bundle exists', existsSync(ssrEntry));
if (existsSync(ssrEntry)) {
  const { renderPage } = await import(`file://${ssrEntry.replace(/\\/g, '/')}`);
  const authHtml = renderPage('auth', { locale: 'en' });
  check('start page renders username login', authHtml.includes('Sign in with your username') && authHtml.includes('Username') && authHtml.includes('Sign in'));
  check('normal start page does not show admin password input', !authHtml.includes('Admin password'));
  check('start page never renders known bootstrap credential', !authHtml.includes(forbiddenCredential));
  check('start page does not advertise default credentials', !authHtml.includes('Default admin'));

  const viAuth = renderPage('auth', { locale: 'vi' });
  check('Vietnamese auth renders', viAuth.includes('Đăng nhập bằng username'));
  check('Vietnamese auth does not leak bootstrap credential', !viAuth.includes(forbiddenCredential));

  const adminHtml = renderPage('admin', { locale: 'en' });
  check('admin user board renders', adminHtml.includes('Users &amp; access') && adminHtml.includes('Registered users'));
  check('admin password panel renders', adminHtml.includes('Update admin password') && adminHtml.includes('Current password'));
  check('admin delete wording is explicit', adminHtml.includes('Remove user + data'));
  check('admin page never renders known bootstrap credential', !adminHtml.includes(forbiddenCredential));
}

console.log(pass ? '\nAUTH SMOKE PASSED' : '\nAUTH SMOKE FAILED');
process.exit(pass ? 0 : 1);
