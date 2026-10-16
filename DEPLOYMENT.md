# Free deployment status and operations

Repository: https://github.com/NuraliKuzhagaliev/BatchFence

Public application: **https://batchfence.onrender.com**. Product code verified at 57a82bc; Linux CI passed. Free service ID: srv-db968c7btjjs73fghkog. Health path /api/health; actual auto-deploy trigger checksPass.

## Free-only constraint

The owner requires everything to remain free. The earlier paid proposal was revoked before resource creation. Use only the Free compute plan in the selected Render workspace; no disk, paid service, account upgrade, payment method, purchased inference credit or chargeable add-on is authorized. Existing unrelated services are preserved.

The selected workspace was inspected: free allowances remain and no payment method is configured. Keep this unchanged. Render suspends free services/builds when their applicable allowances are exhausted without a payment method; do not upgrade to restore them. See [Render free limits](https://render.com/docs/free). GitHub source/CI use this public repository's available free allowance. AMD requests may use only the already authorized trial resources; provider accounting metadata is not evidence of a monetary purchase.

## Architecture and storage tradeoff

One Free Render Docker Web Service builds the locked React dependencies and runs FastAPI from the same HTTPS origin. One instance and one Uvicorn worker are required. `backend.serve` binds `0.0.0.0:$PORT`. Health queries SQLite and rejects unsupported schema versions without overwriting them. Internal browser navigation resolves root assets; installed desktop retains relative file URLs.

`DATABASE_PATH=/var/data/batchfence.sqlite3` is an image-writable directory, **not a persistent disk**. `STORAGE_MODE=ephemeral` makes the UI explicitly ask visitors to export packets. SQLite records, receipts, sessions and database usage counters can disappear on sleep, restart or redeployment. The original durable cloud receipt requirement remains unmet. Exported packets can be reopened read-only. Local desktop storage and CI named-volume verification are separate from this cloud limitation.

Free services sleep after inactivity, may take about a minute to start, and share workspace quotas. No keep-alive automation or database migration is introduced. See [Render free services](https://render.com/docs/free).

## Configuration and deployment

`render.yaml` defines only `plan: free`, one Docker web service, Frankfurt, no disk and no previews. The direct connector can create this same free service; then confirm settings in the dashboard. The Blueprint's health path is `/api/health` and auto-deploy preference is passing checks. Never issue a duplicate deploy when a Git push already triggers one.

Set private server environment variables from the existing verified local configuration, without printing or publishing values:

- `AMD_API_BASE_URL`, `AMD_API_KEY`, `AMD_MODEL_ID`, `AMD_PROVIDER_EVIDENCE`, `AMD_API_STYLE`.
- `AMD_JSON_SCHEMA=false` for the verified adapter.
- `LIVE_DEMO_TOKEN`: separate random demonstration key, at least 32 characters. Never distribute the provider key.

`PUBLIC_DEMO=true`, `STORAGE_MODE=ephemeral`, `INFERENCE_MODE=fixture`. `APP_ORIGIN` uses Render's injected HTTPS `RENDER_EXTERNAL_URL`. Public visitors start in Synthetic mode; Live is protected; historical AMD Replay is explicitly labeled and makes no new inference request. No secret is a frontend variable, Docker build argument or installer field. `.env.example` has empty placeholders. `.env`, databases and verification sessions are excluded from the image and Git.

## Public controls

Cookie-owned workspaces use HttpOnly, Secure, SameSite=Strict cookies. Every case read/write/export checks ownership. Live needs a separate access key, retained only in browser page memory, and allows one inference at a time. Failed calls never fall back to fixtures.

Limits: 8 extraction attempts per session, 20 live attempts per current database lifetime, 60 cases, 6 MB per serialized case, 8 MB bounded request bodies and a 15-second body timeout. Failed/interrupted reservations count. **Free storage loss resets database counters; these are not a durable account spending cap.** Provider trial limits and keeping the demo key private remain necessary. API rate ceilings are 300/minute globally and 90/session, excluding health. These counters restart with the process.

Use only synthetic supplier/customer data. Export before closing or losing the session; no public reset/delete endpoint permits deleting another visitor's workspace.

## Actual verification

CI on commit 43abcf8 passed: 48 pytest, 30 frozen domain cases, Linux Docker build, dynamic PORT, synthetic 500 to 800, stale approval rejection, sandbox receipt, session isolation, SPA routing and an actual container restart with the same named volume. Evidence: `docs/cloud/ci-results.json`, `container-results.json`. This establishes neither Render persistence nor cloud live inference.

Earlier local HTTPS verification passed 12 browser workflow checks and five public-mode checks, with no provider calls. Live access was denied correctly before provider use; historical AMD replay was labeled; offline packet import worked. A discovered internal-route asset defect was fixed. Evidence and actual failures are in `docs/cloud/`.

History, working deliverables and built assets were scanned for known private values and credential patterns, including nested presentation archives. This is not a general security audit or OCR scan. Historical raw AMD quality errors remain disclosed; all performed review is agent-operated, not independent human validation.

## Public acceptance procedure (results below)

1. Record real URL, service ID, commit/deploy ID, build/start logs and actual free plan/no disk.
2. Inspect HTTPS UI, temporary-storage notice, assets/internal refresh, protected-live failure and separate sessions.
3. Run fresh live AMD 500/800 and ambiguous notices with raw response preserved before source-specific agent review. Report failures separately; never relabel replay as live.
4. Export/import packets, stale approval rejection, isolation and inspect responses/assets for known secrets.
5. Export all test packets before a controlled real restart. Verify and record ephemeral state loss honestly; reopening the export does not prove cloud persistence.
6. Update this document and HANDOFF with actual results. Durable cloud storage remains unavailable under the current free-only architecture.

## Reproduce checks

    npm ci --ignore-scripts
    npm run build
    python -m pip install -r requirements.txt
    python -m pytest -q
    python -m scripts.evaluate
    python scripts/audit-publication.py

Windows uses `.\.venv\Scripts\python.exe`. `scripts/container-check.py` uses a real Docker container and named volume in CI. `BATCHFENCE_BASE_URL` selects the public origin for `scripts/public-controls.cjs` and `scripts/live-browser-check.cjs`. The latter needs private `BATCHFENCE_DEMO_TOKEN`, a new evidence directory, and pauses for review files after actual model output. Do not prefill review blindly.

## Desktop and release limits

The existing unsigned Windows 0.1.1 installer remains local under `releases/` and targets `127.0.0.1:8787`. Its hash remains verified and it has not been rebuilt or published as a cloud installer. No paid signing, domain or installer hosting is introduced. Native dialog/operator review limitations remain in the historical HANDOFF. This is a demonstrator, not a production release.

## Final public verification

See [cloud evidence index](docs/cloud/README.md) and summary.json. Verified code 57a82bc passed 52 tests, 30 frozen domain cases and rebuilt Linux container checks. The actual public app completed fresh AMD 500/800 flows with two receipts and stale apply rejection under scope-extract-2. Two different ambiguous sources yielded conservative 1,200-unit holds after agent review; raw uncertainty errors are disclosed. Exact source-punctuation defect was fixed and rechecked live. Earlier citation failures under scope-extract-1 remain rejected and preserved.

Public Synthetic browser checks (12), access controls (5), offline live packet import, actual live session isolation and known-secret asset scan passed. Screenshots preserve Live, historical Replay and Synthetic provenance. Eight cloud AMD calls were made with existing authorized trial resources; no purchase or paid service was introduced. Provider usage.cost fields are retained as accounting metadata, not proof of an invoice.

An actual configuration redeploy removed a saved synthetic receipt: the same session got 404 afterward. Its export remains valid. The durability gate is unmet by design under the free-only constraint. Client timestamps are about 80 seconds behind provider HTTP time; raw timestamps are retained with their clock sources.

Verdict: free synthetic demonstrator ready; production/durable-storage and independent domain-review gates remain open. The current private LIVE_DEMO_TOKEN is in ignored work/cloud-demo.env; use only that value for protected live demonstrations.
