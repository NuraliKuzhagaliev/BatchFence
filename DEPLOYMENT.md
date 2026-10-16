# BatchFence deployment and operations

Public app: https://batchfence.onrender.com · repository: https://github.com/NuraliKuzhagaliev/BatchFence

The 0.2.0 upgrade is being verified locally. The protected public release remains 0.1.2 until the existing checks-pass deployment completes. See HANDOFF.md and docs/release-0.2.0/ for current evidence.

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
python -m pytest -q
python -m scripts.evaluate
python scripts/audit-publication.py
```

Windows uses .venv\Scripts\python.exe. `scripts/upgrade-browser.cjs` checks new UI workflows; `scripts/browser-smoke.cjs` checks the preserved workflow; `scripts/public-controls.cjs` checks public protections. `scripts/desktop-smoke.cjs`, `desktop-offline.cjs`, and `desktop-scale-check.cjs` accept BATCHFENCE_TEST_EXE. Real OS dialog selection uses `scripts/native-dialog-check.cjs` and requires an operator. The automated checks stub selection and do not establish physical-dialog acceptance.

The existing GitHub workflow builds the real Linux container and verifies 500/800, stale approval, receipts, isolation and restart with a named volume. Local Windows Docker's earlier socket failure is historical; no permissions/reset/container deletion is needed to use this established CI route.

Earlier deployment logs and evidence remain under docs/cloud/ and docs/history/DEPLOYMENT-through-0.1.2.md. Treat them as historical, not fresh 0.2.0 verification.
