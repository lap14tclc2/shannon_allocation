#!/usr/bin/env python3
"""Fast end-to-end verification of the SSR server + export endpoint.

Runs the real Handler on an ephemeral (port 0) in-process server and asserts the
page routes return server-rendered HTML, the Export ZIP endpoint works, and the
API responds. No port probing — completes in ~1 second.

Usage:  python verify.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import threading
import urllib.request
import urllib.error
import zipfile

import serve

# Windows console safe output (⬇ etc. would otherwise break cp1252 printing)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def get(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status, resp.read(), resp.headers


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    return ok


def main():
    serve._ensure_ssr_worker()

    server = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    results = []

    def check_ok(name, ok, detail=""):
        results.append(check(name, ok, detail))

    try:
        status, body, _ = get(f"{base}/")
        html = body.decode("utf-8", "replace")
        check_ok("home page returns HTML", status == 200 and "id='root'" in html)
        check_ok("home lists runs", "/runs/" in html and "__PAGE__" in html)
    except Exception as exc:
        check_ok("home page returns HTML", False, str(exc))

    # Find the latest run and test its pages + export.
    try:
        _, body, _ = get(f"{base}/api/runs")
        runs = json.loads(body.decode()).get("runs", [])
    except Exception as exc:
        runs = []
        check_ok("API /api/runs works", False, str(exc))

    if runs:
        rid = runs[0]["run_id"]
        try:
            status, body, _ = get(f"{base}/runs/{rid}")
            html = body.decode("utf-8", "replace")
            check_ok("run page returns HTML", status == 200 and "id='root'" in html)
            check_ok("run page has ranking + export button",
                     "Ranking board" in html and f"/api/runs/{rid}/export" in html)

            # Combo page from the run's index.
            _, idx_body, _ = get(f"{base}/api/runs/{rid}/index")
            combos = [c for c in json.loads(idx_body.decode()).get("combinations", []) if not c.get("error")]
            if combos:
                slug = combos[0]["slug"]
                status, body, _ = get(f"{base}/runs/{rid}/combinations/{slug}")
                html = body.decode("utf-8", "replace")
                check_ok("combo page returns HTML", status == 200 and "id='root'" in html)
                check_ok("combo page has allocation table + chart",
                         "Quarterly allocations" in html and ("viewBox" in html or "<svg" in html))
        except Exception as exc:
            check_ok("run/combo pages", False, str(exc))

        # Export ZIP endpoint.
        try:
            status, body, headers = get(f"{base}/api/runs/{rid}/export")
            ok_zip = status == 200 and headers.get("Content-Type") == "application/zip"
            names = []
            if ok_zip:
                zf = zipfile.ZipFile(io.BytesIO(body))
                names = zf.namelist()
            check_ok("export returns a valid ZIP",
                     ok_zip and len(names) > 0 and "_RUN.md" in names and "_STATS.md" in names)
            check_ok("export zip contains per-combination reports",
                     any(n.endswith(".md") and not n.startswith("_") and n != "ALL_COMBINATIONS.md" for n in names))
        except Exception as exc:
            check_ok("export returns a valid ZIP", False, str(exc))
    else:
        check_ok("run pages + export", False, "no runs available — run the backtest first")

    # DELETE run endpoint — test with a throwaway run so real data is untouched.
    tmp_rid = "__verify_tmp__"
    tmp_dir = os.path.join(serve.RESULTS_DIR, "runs", tmp_rid)
    os.makedirs(tmp_dir, exist_ok=True)
    with open(os.path.join(tmp_dir, "meta.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"run_id": tmp_rid, "generated_at": "2020-01-01T00:00:00"}))
    try:
        req = urllib.request.Request(f"{base}/api/runs/{tmp_rid}", method="DELETE")
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
        results.append(check("DELETE /api/runs removes a run", resp.status == 200 and payload.get("ok") is True))
        results.append(check("deleted run no longer exists on disk", not os.path.isdir(tmp_dir)))
        try:
            urllib.request.urlopen(urllib.request.Request(f"{base}/api/runs/{tmp_rid}", method="DELETE"), timeout=10)
            results.append(check("DELETE missing run returns 404", False))
        except urllib.error.HTTPError as exc:
            results.append(check("DELETE missing run returns 404", exc.code == 404))
    except Exception as exc:
        results.append(check("DELETE /api/runs removes a run", False, str(exc)))
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Optimizer pages + API.
    try:
        _, body, _ = get(f"{base}/api/optimizer")
        exps = json.loads(body.decode()).get("experiments", [])
        results.append(check("optimizer experiments API", isinstance(exps, list)))
        status, body, _ = get(f"{base}/optimizer")
        html = body.decode("utf-8", "replace")
        results.append(check("optimizer list page renders", status == 200 and "Optimizer" in html))
        if exps:
            eid = exps[0]["experiment_id"]
            status, body, _ = get(f"{base}/optimizer/{eid}")
            html = body.decode("utf-8", "replace")
            results.append(check("optimizer detail page renders",
                                 status == 200 and "experiment" in html.lower() or "Best" in html))
            _, body, _ = get(f"{base}/api/optimizer/{eid}")
            exp = json.loads(body.decode())
            results.append(check("optimizer experiment JSON has winners",
                                 bool(exp.get("winners")) and bool(exp.get("meta"))))
            # a report file download
            status, body, _ = get(f"{base}/api/optimizer/{eid}/file?name=candidate_metrics.csv")
            results.append(check("optimizer report file download", status == 200 and len(body) > 0))
    except Exception as exc:
        results.append(check("optimizer pages/API", False, str(exc)))

    server.shutdown()
    server.server_close()
    if serve._ssr_proc:
        serve._ssr_proc.terminate()

    passed = all(results)
    print("\n" + ("VERIFICATION PASSED" if passed else "VERIFICATION FAILED"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())