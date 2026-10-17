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

# Enterprise pilot implementation checkpoint

Protected public release: e70f4a0 / Windows v0.2.0 (immutable). Development branch: enterprise-pilot-0.3. No main push or expanded release before gates pass. No 0.2.1 work found; planned next application version 0.3.0.

## Dependency order
1. Baseline and risk/evidence register. Baseline: 65 pytest pass (2026-10-17); no uncommitted work or applicable AGENTS.md found.
2. Incremental SQLite/PostgreSQL repository, named local identities, membership/roles, append-only transactional audit, persistent sources, migration/isolated restore. Preserve legacy snapshots as anonymous historical records.
3. Guided mapped imports and typed receiving review; source-preserving bounded OCR; separate proposed/applied/pending/confirmed quantities.
4. Frozen p-chart signals and applicable approved knowledge, linked to the existing incident.
5. Shared whole-pool hold ledger, distinct recovery approval, transactional sandbox execution and reference connector/outbox.
6. Corrective-action lifecycle, frozen effectiveness criteria, sufficient/insufficient follow-up and recurrence.
7. Frozen 24-item model set, bounded live budget, domain/security/concurrency/performance and web/Windows checks; critical integrated review.
8. Coherent clean tag/archive/installer, local pilot restore, existing free Render deployment, media and published verification.

## Operating decisions
Single-organization private pilot, tested against a second organization. Local bootstrap only; no default credentials. PostgreSQL pilot and SQLite demo share versioned snapshots via a small repository adapter. Serial committing transactions favor correctness within measured bounds; no claims of unlimited throughput. External model work occurs outside write locks. Whole-pool recovery only. Reference connector is local sandbox, never real enterprise execution. Confidential data requires separate owner approval before external inference.

## Evidence and ownership
Engineering owner: Codex (agent-operated checks, not independent human). Human acceptance owner: repository owner plus a quality professional and independent participants, pending. Each gate is tracked in docs/enterprise/evidence-matrix.md. Risk register: docs/enterprise/risks.md.

## Current checkpoint
Baseline inspected; entire enterprise brief read. First implementation phase: persistence, identities, data contracts and restore tooling. Existing public 0.2.0 is unchanged.

Foundation milestone: 73 tests pass; actual PostgreSQL migration/runtime restrictions, 500/800/stale/concurrent duplicate and 11-source isolated restore pass. Private Compose build acceptance in progress. Named users are test identities; no independent human acceptance. No AMD calls/prompt changes.

Backend integration milestone: all four module server workflows are implemented with targeted synthetic checks; full client integration and release acceptance remain pending. 800→700→100 recovery checks preserve other incident holds. Frozen effectiveness plan and recurrence mechanics pass targeted tests. Raw fresh AMD evaluation not yet run.

Client/OCR milestone: six workspace navigation sections and all four module forms are connected. Existing 12 browser checks pass after event-based reconnect correction. Nine new boundary tests pass. Actual local container OCR preserved two pages/52 boxes, rejected pre-visual narrowing, and allowed a 500-unit proposal only after agent-operated page review. Expanded module browser, fresh AMD, larger-data, PostgreSQL/recovery/restore, desktop and deployment gates remain open.

Integrated candidate milestone: 102 tests, 30 domain cases, six connected browser groups, actual PostgreSQL recovery/connector restart/migration/16-source restore, actual OCR, statistical and bounded performance evidence. New-task live gate blocked at 0/24 by free-only catalog/quota conflict. Preserve main0.2.0. Candidate0.3.0-rc.1 packaging/publication preparation continues independently.

Candidate gate milestone: final side-by-side Windows install passes core7/module6/default-pilot4 and offline module checks. LinuxCI38978907998 passes source+SQLite restart. Clean package sourcee616ff5, version0.3.0-rc.1. Required review materials prepared, known-value installed asset scan clean. New-task AMD0/24 remains blocked on zero-cost allowance; preserve public0.2.0 and no release/tag/Render promotion. Human pilot acceptance pending as documented.
