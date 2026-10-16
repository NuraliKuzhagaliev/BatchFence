# Deployment status and operations

Repository: https://github.com/NuraliKuzhagaliev/BatchFence

Public application: **not deployed**. A paid durable service has not been provisioned. Cloud AMD connectivity, public HTTPS workflows and cloud restart persistence remain unverified. Local results below are explicitly local.

## Selected architecture

One Render Docker Web Service builds React with the locked npm dependencies, then runs FastAPI and serves both the UI and API from the same origin. SQLite, its WAL and receipts live at `/var/data/batchfence.sqlite3` on a 1 GB persistent disk. One service instance and one Uvicorn worker are required. No Vercel split or database migration is needed.

`backend.serve` binds `0.0.0.0:$PORT`, limits concurrent connections to 24, and starts the existing database schema without overwriting an unknown version. Health checks query the database; inaccessible/unsupported storage returns 503. Internal browser navigation resolves root asset URLs; the installed desktop keeps relative file URLs. Docker runs as UID 10001. Disk write access must be verified in the actual Render runtime, not assumed from a successful build.

Render disks require paid compute, are available only at runtime, and attach to a single instance. Disk deployments have a brief outage. Ephemeral storage does not preserve receipts. See [persistent disks](https://render.com/docs/disks) and [Blueprint specification](https://render.com/docs/blueprint-spec).

## Proposed cost; approval pending

Current pricing checked 2026-10-16: `0.5c-512mb` compute is **US$7/month** and a 1 GB disk is **US$0.25/month**, totaling **US$7.25/month baseline**, before taxes or an existing workspace subscription. A Hobby workspace adds no subscription fee; no workspace upgrade is proposed. [Render pricing](https://render.com/pricing).

Hobby includes 5 GB outbound bandwidth and 500 standard build minutes per month, shared with other services. Overage is $0.15/GB and $5 per additional 1,000 build minutes. Actual remaining workspace allowance must be inspected before provisioning; no unlimited overage budget is assumed. AMD usage is separate and remains within the existing authorized key's limits. [Workspace pricing](https://render.com/blog/better-pricing-for-fast-growing-teams), [build pipeline](https://render.com/docs/build-pipeline).

The connector lists one workspace, `Kuzhagaliev Nurali's workspace`, but explicitly requires user confirmation before selecting its ID. Existing services/billing have not yet been inspected. Do not infer that there are no reusable resources.

## Configuration and deployment

After workspace selection and cost approval, inspect existing services first. Apply `render.yaml` to the authorized repository's `main` branch. It specifies Frankfurt, the paid compute tier, one instance, a 1 GB disk and `/api/health`. No preview resources are configured. CI on GitHub builds/tests the application and runs a Linux container workflow; Render auto-deploy is configured for passing checks. The local Docker socket failure is unrelated to a remote Git build.

Set these privately in Render's protected server environment, using the already verified local configuration; never paste values into issues, logs or chat:

- `AMD_API_BASE_URL`, `AMD_API_KEY`, `AMD_MODEL_ID`, `AMD_PROVIDER_EVIDENCE`, `AMD_API_STYLE`.
- `AMD_JSON_SCHEMA=false` for the currently verified adapter configuration.
- `LIVE_DEMO_TOKEN`: a random value of at least 32 characters, kept separate from the provider key. Blueprint generates it. Transfer privately to authorized demonstrators only.

`PUBLIC_DEMO=true` enables the public limits. `DATABASE_PATH=/var/data/batchfence.sqlite3`. `APP_ORIGIN` defaults to Render's injected HTTPS `RENDER_EXTERNAL_URL`; use the exact custom origin if one is later configured. Never set it to localhost on Render. Public visitors default to `INFERENCE_MODE=fixture`, accurately labeled Synthetic; protected Live remains selectable. The historical replay contains actual prior local AMD output and agent review, with no new inference claim.

No secret is a Docker build argument, a frontend variable or an installer field. `.env.example` contains empty placeholders only. The container copies neither `.env`, local databases nor private verification sessions.

## Public demo controls

- Cookie-owned workspaces; HttpOnly, Secure, SameSite=Strict. Each read/write/export checks ownership. Desktop capability transport remains supported.
- Live inference requires the demonstration key in a header over HTTPS. The UI retains it only in page memory. Failure remains visible; no fixture fallback.
- At most one live request at once; 8 extraction attempts per session and 20 live attempts across the entire persistent database. Failed and interrupted reservations count. Restart does not reset that total. Exhaustion requires an intentional owner decision; no automated reset or retry loop.
- 300 API requests/minute globally and 90/session, excluding health checks. These single-process minute counters restart with the process. Session rotation cannot evade the global ceiling. This is bounded demo protection, not a DDoS service.
- 8 MB bounded request body, 15-second body timeout; existing 2 MB/file and 24-document limits. 60 stored cases, maximum serialized case size 6 MB. Capacity returns a clear error; no visitor can delete another workspace to free space.
- Public data is synthetic. Do not upload real supplier/customer records. Session loss means that visitor cannot recover their private workspace; exported packets remain readable.

## Actual checks so far

Local Windows build passed. 48 pytest checks passed, including existing ambiguity, stale approval, exact actions, packet hashing and isolation regressions plus live-access/concurrency/budget/rate/body/storage/readiness checks. The frozen deterministic evaluation passed 30/30, with zero missed documented stock and zero wrong outside classifications. These are not model-quality measurements.

Against the isolated **local** HTTPS server: 12 browser workflow checks passed, including 500/800 synthetic plans, receipt and offline packet behavior. Five additional browser control checks passed: internal refresh/assets/API 404, labeled historical AMD replay, denied live requests before any provider call, independent-session isolation and usable protected-live errors. No live calls were made in these tests. The internal-route asset defect found during testing was fixed. See `docs/cloud/`.

Git history and current deliverables were scanned for known private values, credential literals, private paths, databases and installers, including nested presentation parts. This is not a general security audit or OCR scan. All previous raw AMD evidence remains historical and agent-reviewed; independent human validation has not occurred.

## Cloud acceptance gate — still pending

1. Record actual service URL, service/commit/deploy IDs and successful remote build/startup logs. Confirm DB writable under the mounted disk and one service instance.
2. Run `BATCHFENCE_BASE_URL=<actual HTTPS URL> node scripts/public-controls.cjs` (PowerShell: set the environment variable separately). Never bypass certificate verification for the public host.
3. Run `scripts/live-browser-check.cjs` against the public origin with a privately supplied `BATCHFENCE_DEMO_TOKEN`, a new `BATCHFENCE_EVIDENCE_DIR` and private review directory. The script pauses after each raw model response. Inspect the exact source/proposals and provide source-specific review files; do not prefill model output. Record agent-operated review accurately.
4. Complete actual live 500 → 800 plans, stale apply rejection and sandbox receipts; run an ambiguous notice and record raw errors separately from reviewed outcomes. Keep failures, timestamps, model/request IDs and latency. Never turn failed extraction into a successful replay.
5. Verify packet export/import, two browser sessions and no known server secrets in responses/assets. Store cookies and access keys only under ignored `work/` or private environment configuration.
6. Restart/redeploy the real Render service; use the same private browser session to compare saved receipts, stock, runs and review state. A second HTTP client without a process restart is insufficient.
7. Update this document with actual results. Until these pass, the public release is incomplete.

## Reproduce independent checks

    npm ci --ignore-scripts
    npm run build
    python -m pip install -r requirements.txt
    python -m pytest -q
    python -m scripts.evaluate
    python scripts/audit-publication.py

Windows uses `.\.venv\Scripts\python.exe` for the Python commands. CI additionally builds Docker and runs `scripts/container-check.py`, which performs a real container restart with a named volume. CI synthetic success does not establish Render persistence or live AMD connectivity.

## Recovery and desktop

Use SQLite's backup API for a consistent backup while the service is running; keep it private. Do not copy only the main SQLite file while WAL writes are active. Test any backup restoration separately before relying on it. No automatic retention/deletion/reset is implemented. Disk snapshots alone do not establish a tested database recovery process.

The existing unsigned Windows 0.1.1 installer and checksums remain local in `releases/`; it targets a local backend at `127.0.0.1:8787`. It is not advertised as a cloud-connected installer and no GitHub binary release has been published. The hosted frontend changes do not modify that existing installer. No signing, OS protection changes or new desktop integration are assumed.
