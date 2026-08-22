// Node SSR renderer worker: renders React pages to HTML on request.
// Called by the Python backend (python/serve.py).
//
//   POST /render  { "page": "home"|"run"|"combo", "props": {...} }  -> { "html": "..." }
//   GET  /health  -> { "ok": true }
//
// The SSR bundle (dist-ssr/ssr-entry.mjs) is re-imported whenever it changes on
// disk, so a rebuilt frontend is picked up WITHOUT restarting this worker.
import http from 'node:http';
import { statSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SSR_ENTRY = join(__dirname, '..', 'dist-ssr', 'ssr-entry.mjs');

const HOST = process.env.SSR_HOST || '127.0.0.1';
const PORT = Number(process.env.SSR_PORT || 8099);

let renderPage = null;
let lastMtime = 0;

async function load() {
  const mtime = statSync(SSR_ENTRY).mtimeMs;
  if (renderPage && mtime === lastMtime) return;
  const mod = await import(`${pathToFileURL(SSR_ENTRY).href}?t=${mtime}`);
  renderPage = mod.renderPage;
  lastMtime = mtime;
}

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  const url = req.url || '/';

  if (req.method === 'GET' && url === '/health') {
    return sendJson(res, 200, { ok: true });
  }

  if (req.method === 'POST' && url === '/render') {
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', async () => {
      try {
        await load();
        const { page, props } = JSON.parse(raw || '{}');
        const html = renderPage(page, props);
        if (html === '') {
          return sendJson(res, 400, { error: `Unknown page: ${page}` });
        }
        return sendJson(res, 200, { html });
      } catch (err) {
        return sendJson(res, 500, { error: err && err.stack ? err.stack : String(err) });
      }
    });
    return;
  }

  sendJson(res, 404, { error: 'Not found.' });
});

server.listen(PORT, HOST, () => {
  console.log(`SSR renderer listening on http://${HOST}:${PORT}`);
});