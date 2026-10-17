# BatchFence 0.3.0 released and verified

Web: https://batchfence.onrender.com. Windows: https://github.com/NuraliKuzhagaliev/BatchFence/releases/tag/v0.3.0. Installer/source tag v0.3.0 is effa9fd0bc2c6f32b24ea4d51e6da31359707818. Full public workflow checks passed at merge dd06d974a2cc721ed9366724853e14078567f6f8. Subsequent evidence-only commits preserve application bytes; latest observed served identity is retained in releases/final-publication-0.3.0.json. Existing Render service remains one Free instance, ephemeral storage. Previous releases are preserved.

All four connected modules and foundations are implemented: Quality Signals, Approved Knowledge, Controlled Recovery, and Corrective Action with Effectiveness. A reviewed proposal can narrow to 700 while 800 remain applied; separate distinct approval recovers exactly 100 with its own receipt. Original containment receipts and other incident holds remain. Unresolved ancestry/scope stays conservative, and old approvals are stale.

Fresh AMD evaluation is complete: 27 attempts of the authorized maximum 30, 26 HTTP 200, one timeout,no automatic retries or fixture substitution. All 24 frozen synthetic items exercised, 20 model requests and four retrieval abstentions. Raw extraction exact 6/12, knowledge pipeline 11/12 (model-only 7/8). Source-only receiving retests 2/2 drove the reviewed recovery, and one compact signal response matched five calculated observations. All raw failures remain. Every review and named test account was agent-operated. No independent human validation is claimed. Fresh calls used the local release implementation; public deployment verification used fixtures/retained packets, not new cloud inference. No more inference is needed for this release.

Actual checks: 110 pytest, 30 deterministic domain cases; public 12 core checks, six connected module groups, five access/control groups, four distribution groups, zero browser errors. Installed Windows passed seven core, six module, four named pilot groups, offline real-response packet with 700 held / 100 recovered / two original receipts, and 100% / 125% renderer scales. Actual GitHub tag archive built on Linux and passed eight checks including 500/800, stale 409, source isolation,and SQLite volume persistence across restart. Windows/Linux/public frontend bytes match. PostgreSQL migration,connector failure/retry/restart/idempotency,and isolated restore of 16 source hashes passed. Tiny same-device restore 225 ms is not an RPO/RTO claim. Branch and main Linux CI passed. Publication/ASAR scan found zero known private values across 21 needles.

Installer: D:\projects\BatchFence\releases\BatchFence-0.3.0-win-x64-setup.exe. Installed test app: work/installed-0.3.0/BatchFence.exe. SHA256 908d09e1c1b627f043567478cbad9dc766531dda252c8d1acf0eb88b466aae7f, 113788538 bytes. The full anonymous public download matches. Matching sourceZIP and SHA256SUMS-0.3.0.txt are in releases/. New submission/enterprise materials include the seven-slide 0.3.0 deck, 81.8-second captioned video, presenter script and quickstart. Retained fresh AMD screens and synthetic replay are explicitly separated. No entry was submitted.

Reproduce from D:\projects\BatchFence:
- `.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-NEW`
- `.venv\Scripts\python.exe -m scripts.evaluate`
- `.venv\Scripts\python.exe -m scripts.score-enterprise-live` (offline scoring; no provider calls)
- `npm run build`
- Set `BATCHFENCE_BASE_URL=https://batchfence.onrender.com`, then `node scripts/browser-smoke.cjs` or `node scripts/enterprise-browser.cjs` (synthetic test workspaces).
- `docker compose -f ops/compose.pilot.yml up --build -d` starts the existing persistent private pilot at http://127.0.0.1:8788. Preserve its private config. Setup/users/backups: docs/enterprise/pilot-operations.md.
- Windows defaults to the public backend. Set `BATCHFENCE_BACKEND_ORIGIN=http://127.0.0.1:8788` before launch to use the local pilot. Saved packets work offline without external Node/Python.

Verdict: ready for synthetic public use and a controlled engineering pilot; production acceptance remains open. Precise human actions: privately rotate the provider key exposed by the portal during inspection and update private local/Render settings; test actual Windows chooser/save/reopen and unsigned-installer prompts; complete quality-professional and three-operator acceptance; provision real scoped identities/approve intended AMD data; set off-device backup and RPO/RTO and observe restore. Native dialogs were stubbed in engineering automation. Public storage is temporary, Windows unsigned, real ERP integration unavailable, eight moderate build-tool findings remain. No purchases, real inventory actions or external messages occurred.

All current evidence: docs/enterprise/final-release.json,release-artifacts.json,live/README.md,release-public/,release-desktop/,release-container/. Next useful work is the documented human acceptance, not feature expansion or score-chasing inference.

---

Historical checkpoints below describe their state at that time.

## Historical operating notes

# Candidate deployment boundary

The enterprise-pilot-0.3 branch is a 0.3.0-rc.1 local/private candidate. Follow docs/enterprise/pilot-operations.md and release-gates.md. The public 0.2.0 destination below remains protected. The candidate Windows default is loopback8788 and requires the private Compose backend. Do not point it at public0.2.0 for new modules. No new cloud service or paid resource.

---

# BatchFence deployment and operations

Public app: https://batchfence.onrender.com · repository: https://github.com/NuraliKuzhagaliev/BatchFence

0.2.0 is published on the existing free service. Linux CI run 38959067118 and Render deploy dep-db9857jm8hqs73fcakm0 verified runtime ebd1402. Source 7431360 is the immutable Windows v0.2.0 tag; ebd1402 fixes its Docker frontend COPY without changing desktop code. Build the container from main, which includes that fix. Final evidence-only rollout identity is recorded in the local releases/final-verification-0.2.0.json after deployment.

## Free-only infrastructure

Use only the existing Render Free Docker service `srv-db968c7btjjs73fghkog`, workspace `tea-d3pt0sbipnbc73a5v810`. One instance, Frankfurt, no paid disk, no add-ons, no payment or plan changes. GitHub main pushes run the existing Linux checks; passing checks trigger Render automatically. Do not create a duplicate service or duplicate manual deploy.

FastAPI serves the built React app and SQLite from one HTTPS origin. One Uvicorn worker; dynamic PORT via backend.serve; health /api/health includes version and injected Git commit. Render storage at /var/data/batchfence.sqlite3 is **ephemeral**, not a persistent disk. Sleep, restart or redeploy can erase cases, receipts and usage counters. Export decision packets. A successful named-volume CI restart does not prove Render durability. No artificial keep-alive traffic.

## Private configuration

Existing server-only variables: AMD_API_BASE_URL, AMD_API_KEY, AMD_MODEL_ID, AMD_PROVIDER_EVIDENCE, AMD_API_STYLE, AMD_JSON_SCHEMA. Use actual provider documentation/catalog values; never invent endpoints or models. Existing verified adapter uses openai-chat and JSON schema response mode disabled. The provider key is never entered into the app or packaged in desktop.

PUBLIC_DEMO=true; STORAGE_MODE=ephemeral; INFERENCE_MODE=fixture. APP_ORIGIN uses Render's injected HTTPS RENDER_EXTERNAL_URL. LIVE_DEMO_TOKEN is the separate private Live access key; browser and desktop retain it only in memory. Local .env and work/cloud-demo.env are ignored and must never be published or printed.

Security remains: HttpOnly/Secure/SameSite=Strict cookie ownership; fixed HTTPS desktop backend and constrained IPC; per-session ownership; CSRF/body limits; 8 interpretation attempts/session, 20 live attempts per database lifetime, one live request at a time, 60 cases, 6 MB case/8 MB request, rate limits. Failed live calls reserve budget and never fall back. Ephemeral counters are not a durable spending cap; retain private access and provider trial limits.

## Upgrade behavior

Simulations are bounded immutable copies with no approval endpoint. Reconciliation needs an exact reply, source candidate and explicit review. A complete replacement uses `POOL complete ancestry: LOT only. Supersedes ROW-1, ROW-2.` with every current parent row. Inconclusive/conflicting replies preserve uncertainty. Receiving candidates cannot replace incident scope. All prior holds remain; no release integration exists.

The Windows 0.2.0 package is a local Electron renderer that defaults to this hosted backend. Set BATCHFENCE_BACKEND_ORIGIN=http://127.0.0.1:8787 for the existing local mode. Offline saved packets are read-only, with no inference or execution. The installer is unsigned; do not buy signing or claim OS trust.

## Reproduce

```
npm ci --ignore-scripts
python -m pip install -r requirements.txt
npm run build
python -m pytest -q --basetemp work/pytest-new-run
python -m scripts.evaluate
python scripts/audit-publication.py
```

Windows uses .venv\Scripts\python.exe. `scripts/upgrade-browser.cjs` checks new UI workflows; `scripts/browser-smoke.cjs` checks the preserved workflow; `scripts/public-controls.cjs` checks public protections. `scripts/desktop-smoke.cjs`, `desktop-offline.cjs`, and `desktop-scale-check.cjs` accept BATCHFENCE_TEST_EXE. Real OS dialog selection uses `scripts/native-dialog-check.cjs` and requires an operator. The automated checks stub selection and do not establish physical-dialog acceptance.

The existing GitHub workflow builds the real Linux container and verifies 500/800, stale approval, receipts, isolation and restart with a named volume. Local Windows Docker's earlier socket failure is historical; no permissions/reset/container deletion is needed to use this established CI route.

Earlier deployment logs and evidence remain under docs/cloud/ and docs/history/DEPLOYMENT-through-0.1.2.md. Treat them as historical, not fresh 0.2.0 verification.

## Actual live sequence and limitations

Four fresh hosted requests used the existing private MiMo configuration and event resources; no services or credits were purchased. See docs/release-0.2.0/live/summary.json. Fresh model responses powered real reviewed scope and workspace receipts, including rejection of an omitted parent. Interpretation is fallible; no autonomous ancestry replacement is claimed.

The first observed health access took 705 ms on a recently deployed instance; that is not a confirmed sleeping-instance cold start. Free hosting can display Render's loading page while waking. No artificial keepalive is configured. Physical Windows open/save/reopen is the remaining manual platform acceptance: run `node scripts/native-dialog-check.cjs` with BATCHFENCE_TEST_EXE pointing to the installed v0.2.0 executable, select fixtures/demo/supplier_notice_v2.txt, save work/native-dialog-packet.json, then reopen it. The helper waits for actual dialogs; it does not dismiss OS warnings.

Local verification commands should choose a new D: basetemp directory. Public browser helpers support BATCHFENCE_BASE_URL=https://batchfence.onrender.com and versioned output paths. `scripts/upgrade-live.py` is a staged evidence tool: inspect each raw result before running a review stage. It uses ignored work/cloud-demo.env and work/upgrade-live-session.json; do not print, commit or distribute either file. A saved session can expire when ephemeral storage resets.

Cold-start follow-up: an existing open client polls health every 15 seconds, so autosleep was not established. The final public access measurement was warm (1,075 ms). Export and close all BatchFence clients before attempting a natural sleep/wake test; other public visitors remain outside our control. See docs/release-0.2.0/published-011502d.json.
