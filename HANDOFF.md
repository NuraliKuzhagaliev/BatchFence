# Gemma / Evolus continuation — live verification and reliability fixes

Protected public release remains 0.3.0 / 34929d1. Development branch gemma-evolus-0.4, initial checkpoint f50349c. No new installer or public promotion yet.

Implemented all six connected extensions and actual OpenAPI-derived Evolus resources. Owner saved the AMD connection privately; actual catalog key own/gemma-4-31b-it maps to Gemma-4-31B-IT and byok-free pricing 0/0. No own AMD Cloud/vLLM allocation or prize eligibility verified.

Verified direct fresh Gemma workflow: 500 -> 800 applied, two original receipts; ambiguous ancestry remained open; proposed 700 versus applied 800; source change rejected an old recovery approval; separately reviewed 100 recovery acknowledged, leaving 700 applied and original receipts intact. These are synthetic sources and agent-operated reviews, not independent human acceptance. docs/continuation/live/product-flow.json.

Actual Evolus extractor + agent ran in three workflow attempts, all completed at provider with zero Evolus credits reported. First final-output configuration mixed original text with JSON and was rejected; fixed to documented PreviousOutput(0), with execution dictionaries mapped by verified numeric order. Next first notice passed 500. Revised notice returned correct SUP-A/SUP-C plus an invented document-ID claim; rejected. Explicit source correction removed that claim, preserved raw failure, then separate critical scope review/approval produced 800 and two receipts; stale request HTTP409 and receipt idempotence passed. docs/continuation/live/evolus-product-flow.json. Runtime model ID is not returned by the Evolus execution API; configured identity and direct AMD runtime identity remain distinct.

New scope includes the 12 Gemma/MiMo failures: frozen benchmark unchanged, Gemma5/12 versus historical MiMo6/12, not superiority evidence. Full source/actual/expected/behavior audit: docs/continuation/evaluation/twelve-case-audit.md and .json. Version3 uses typed entity roles and affected/excluded/uncertain/mentioned status, bounded strict JSON parsing, exact identifier boundaries, negation/ambiguity and explicit exhaustive-scope checks. Review corrections never overwrite raw quality. Fresh matched held-out pairs are in progress within the existing aggregate48 dispatch cap; no automatic retries.

Checks: 161 full pytest passed before the latest explicit-correction path; production TypeScript/Vite build passed before its latest UI edits; 30 domain cases, 12 preserved web checks, six preserved connected-module groups, eight new shared UI groups previously passed. Repeat affected tests and interface checks before packaging. Physical Windows dialogs and independent language/domain/operator acceptance remain unverified.

Private configuration: existing D:\projects\BatchFence\.env only, all three Evolus variables present; preserve AMD settings. No key values in logs/evidence. Exact setup docs/continuation/setup.md. Actual finite provider evidence docs/continuation/live/. Two evaluation DB ledgers were consolidated after a dotenv override selected the old DB; failed attempts remain counted, no cap reset.

Next: finish bounded held-out scoring and isolated actual Blob-library retrieval; source-correction and workflow-contract regressions; full/shared Windows and restart checks; gated packaging/publication. Run `.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-NEXT`, `npm run build`, `.venv\Scripts\python.exe -m scripts.scope_comparison_report` (offline, no calls). Do not rerun one-shot live scripts or exceed caps. Existing provider failures stay recorded.

---

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

# Enterprise candidate checkpoint — implementation complete, promotion blocked

All four modules and their foundations are implemented as 0.3.0-rc.1. Clean package source: e616ff5b91bbe5716949dc3fc833be290a0802b1. Later evidence/tooling-only commits preserve these application bytes. Draft PR: https://github.com/NuraliKuzhagaliev/BatchFence/pull/1. Public web and Windows remain the protected 0.2.0 release at e70f4a0; no expanded Render rollout or new public release tag.

Actual verification: 102 pytest,30 deterministic cases,12 preserved browser checks,6 connected browser groups; final installed Windows 7 core + 6 module groups,4 named default-pilot checks, offline 700-unit packet with 2 containment receipts plus recovery/module records and no external Node/Python on PATH. Actual PostgreSQL migration, distinct test accounts, connector failure/retry/process restart, idempotent ack and 16-source isolated restore passed. Actual Linux OCR processed 2 scanned pages / 52 word boxes and rejected pre-review narrowing. All review was agent-operated. Public Linux CI 38978907998 and final branch CI 38979895208 passed after correcting source storage to /var/data/sources; no permission broadening. All new model quality remains unmeasured 0/24.

Candidate installer: D:\projects\BatchFence\releases\BatchFence-0.3.0-rc.1-win-x64-setup.exe. Installed: work/installed-0.3.0-rc.1/BatchFence.exe. Source ZIP and SHA256SUMS-0.3.0-rc.1.txt are in releases/. It has a separate candidate app identity and defaults to http://127.0.0.1:8788. The first candidate test installer reused the stable identity and replaced the old test installation; stable 0.2.0 was restored from its unchanged installer. Corrected candidate install verified the stable executable stayed byte-identical. Both local installations now coexist. Public assets were never replaced.

Open local synthetic web: http://127.0.0.1:8794. Private named pilot: http://127.0.0.1:8788. Start pilot with `docker compose -f ops/compose.pilot.yml up --build -d`; provision real users via `docker compose -f ops/compose.pilot.yml exec app python -m scripts.pilot create-user --username YOUR_NAME --org northstar --site plant1 --roles quality_reviewer` and separate release_approver. Do not reuse engineering credentials. Full setup/restore in docs/enterprise/pilot-operations.md. For standalone synthetic mode, use the exact Uvicorn command below and set DATABASE_PATH, SOURCE_STORAGE_PATH, APP_ORIGIN and INFERENCE_MODE=fixture explicitly.

Precise external blocker: configured MiMo-V2.6-Flash and every catalog entry report free=false; documented usage URL404. General free/event FAQ claims do not confirm this account's configured endpoint allowance. Zero new inference calls; no substitutions. Owner must confirm an existing zero-cost allowance for this endpoint/model, or privately configure the exact documented free event endpoint/model/key. Never paste secrets into chat. Cap remains four fresh calls. Then evaluate typed receiving, approved-procedure answers and signal explanations, preserve raw failures versus reviewed corrections, run affected checks, and only then promote a coherent version/tag/installer and existing free Render app.

Other human acceptance: quality professional and 3 unfamiliar operators (currently 0), real distinct users/data-processing approval, off-device restore against owner RPO/RTO, actual Windows chooser/save/reopen. Reference connector is loopback sandbox only; real ERP/enterprise inventory action remains unauthorized. Free public SQLite is ephemeral and Windows is unsigned.

Materials: submission/enterprise has the reviewed 7-slide deck, cover, 50.28-second actual synthetic walkthrough, narration and quickstart. Historical 0.2.0 AMD footage/results are identified as historical. Current public event requirements were checked; authenticated media constraints/cutoff still need owner inspection. No entry saved/submitted, external message or paid resource.

Checks and exact evidence: docs/enterprise/evidence-matrix.md, candidate-artifacts.json, security.md and release-gates.md. npm production 0 findings, full 8 moderate build-tool findings remain; Python follow-up 0 known after local pip update. Publication scan includes known private pilot values and installed ASAR contents without exposing values.

Reproduce from D:\projects\BatchFence:
- `.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-NEW`
- `.venv\Scripts\python.exe -m scripts.evaluate`
- `node scripts/enterprise-browser.cjs` (default8794)
- `node scripts/desktop-pilot.cjs` (installed candidate, default8788, private engineering test configuration)
- Set BATCHFENCE_TEST_EXE/BATCHFENCE_BACKEND_ORIGIN for desktop-smoke.cjs and enterprise-browser.cjs; set BATCHFENCE_OFFLINE_PACKET/BATCHFENCE_EXPECTED_UNITS/BATCHFENCE_EXPECTED_RECEIPTS/BATCHFENCE_ENTERPRISE_PACKET for desktop-offline.cjs.
- `.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8794`

---

# Enterprise 0.3.0-rc.1 engineering candidate — release gate open

Protected public app/Windows release remains e70f4a0 / v0.2.0. All four modules and shared foundations are implemented on enterprise-pilot-0.3. Current candidate is private/local; no claim of production readiness or independent human acceptance.

Verified: 102 pytest passed (one deprecation warning); 30/30 frozen deterministic cases; six connected browser groups and 12 preserved core checks with zero page errors. Actual PostgreSQL named test identities exercised 800 applied / 700 proposed / exact 100 recovery, failed connector then explicit retry, connector process restart/idempotent acknowledgement, immutable original receipts, SQLite migration and isolated restore of all 16 source hashes. Restore 179 ms for this tiny same-device test; owner RPO/RTO unset. Actual Linux OCR 2 pages/52 boxes, pre-review narrowing rejected. Statistical simulation and 500-record microbenchmark are labeled synthetic, not field/capacity evidence.

Fresh AMD: zero new inference calls. Current catalog free=false for every model; documented quota endpoint 404. Keep free-only. See docs/enterprise/release-gates.md and live/preflight.json. All 24 frozen new-task items remain unmeasured by fresh inference. Existing 0.2.0 live evidence remains historical, never relabeled.

Next independent work: installed candidate/package/offline/default-pilot transport, coherent source/container build, dependency/security publication scan, operator/media deliverables. Promotion and Render update wait for new-task AMD gate. See docs/enterprise/evidence-matrix.md and ENTERPRISE_PLAN.md. Exact run commands are in docs/enterprise/pilot-operations.md; local web http://127.0.0.1:8794 and private pilot http://127.0.0.1:8788. Private files remain in ignored work/ and .env, all on D:.

---

# Enterprise client and OCR checkpoint — not yet released

Protected release remains e70f4a0 / v0.2.0; development branch enterprise-pilot-0.3. Local backend checkpoint 28b0b5a follows foundation 84cf9a8. The four module interfaces, proposed/applied quantities, typed receiving review, recovery controls, pilot login, mapped imports, source OCR review, and module packet snapshots are now connected. Desktop IPC explicitly allows the new routes. No new public deployment or installer yet.

Actual checks: 89 full pytest passed before the latest boundary additions; nine additional boundary tests passed. TypeScript/Vite build passed. Existing local Edge browser regression passed all 12 checks with zero page errors after fixing offline/reconnect events. Evidence: docs/enterprise/browser-core.json and ui/core. Narrow-window visual inspection found and fixed unreachable module navigation; synthetic baseline review through the UI showed 1.77% pooled baseline and five signals. This is agent-operated synthetic verification.

Actual private Linux container Tesseract 5.3.0 processed two raster-only pages in 1,391 ms including retained-page fetches; 52 word boxes and original PDF bytes preserved. Narrowing before visual review rejected 422. After agent inspection of both retained page images and explicit review, the fixture parser/review produced a 500-unit proposal with zero applied units. Evidence: docs/enterprise/ocr. No AMD inference was used for this OCR check.

Remaining: connected client acceptance (especially recovery/action transitions), fresh AMD cap-four evaluation, full PostgreSQL recovery/restore and SQLite-to-Postgres migration, actual local connector restart, security/performance review, Windows package/media and gated free Render release. No independent domain/operator validation or enterprise readiness claim. Owner consent PILOT_AMD_DATA_APPROVED defaults false; private pilot inference is blocked until owner authorization.

Next commands: `.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-enterprise-next`; `npm run build`; local server on 8794; pilot container on 8788. OCR: `python -m scripts.verify-ocr upload`, then inspect both saved pages before `review-after-visual-inspection`. Existing release artifacts and source remain recoverable.

---

# Enterprise development checkpoint — backend integration in progress

Protected public release remains e70f4a0 / v0.2.0. Foundation local checkpoint is 84cf9a8; later enterprise work remains on enterprise-pilot-0.3. Nothing from this expansion has been published.

Implemented backend paths now cover mapped inventory/lineage/allocation/inspection imports; bounded local OCR integration and critical-field review; typed receiving review preserving old syntax; frozen p-chart signals and linked investigations; applicable approved-procedure retrieval and exact quoted AMD answers; shared whole-pool hold reasons; distinct-identity recovery and a persisted reference-connector outbox; corrective action, frozen effectiveness criteria and recurrence/reopen. Full web/desktop module UI, fresh AMD evaluation, final security/performance/media/package/deployment gates are still pending. Do not call these modules delivered yet.

Verified since foundation: 83 tests through Signals/Knowledge and shared inventory; four targeted recovery tests pass including actual 800/700/100 API sequence, denied self/revoked approval, overlapping second-incident hold, duplicate execution, failed reference acknowledgement and explicit idempotent retry. Two effectiveness tests plus seven existing record tests pass. Reviews/test identities are agent-operated. OCR engine has been installed in the private Linux image; actual scanned-page test is next. The full latest suite is being rerun; use its actual result rather than summing overlapping test subsets.

Local servers: development Uvicorn 127.0.0.1:8794 was started before the latest backend edits and needs restart for new routes. Private Compose app 127.0.0.1:8788 and PostgreSQL are running from a previous development build. Isolated PostgreSQL evaluator is on 127.0.0.1:55439. All new data/config is under ignored D:\projects\BatchFence\work. Never print private config contents. No existing unrelated containers were changed or deleted.

Next: finish all module UI and integrated acceptance; preserve the verified release until gates pass. Existing native-dialog/human-domain/RPO-RTO acceptance remains pending. Frozen model set is evals/enterprise/frozen-v1.json (24 synthetic agent-labeled items), with a finite cap of four fresh authorized requests; none used yet.

---

# Enterprise upgrade in progress — protected 0.2.0 remains published

Development branch: enterprise-pilot-0.3. Entire enterprise brief read; no existing 0.2.1 work found. Do not publish the expansion until its gates pass. New implementation is currently foundations only, not four delivered modules.

Foundation checkpoint: 73 pytest pass (65 preserved plus 8 new cases); real PostgreSQL 17.11 run verified 500/800, stale rejection, concurrent duplicate execution, runtime privilege restrictions, and isolated backup/restore of one case, two receipts and 11 original sources. Measured restore 168 ms, backup age 0.227 s for this small synthetic drill. All named test identities/reviews are agent-operated. Same-device drill is not disaster recovery; owner RPO/RTO unset. Evidence: docs/enterprise/foundation-postgres.json.

Added incremental SQLite/PostgreSQL repository and version-2 migration, private local identity with scoped roles and revocation, transactionally appended audit, original source storage/download, persisted single-attempt jobs with cancellation/interrupt status, and private loopback pilot Compose/setup/backup tooling. Existing extraction prompt is unchanged; no new AMD requests have been made. Model evaluation set must be frozen before prompt changes.

Commands: `.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-foundation-04`; `.venv\Scripts\python.exe -m scripts.verify-pilot` (requires ignored local evaluation config); `python -m scripts.pilot-config`; `docker compose -f ops/compose.pilot.yml up --build -d`. Operational instructions and boundaries: docs/enterprise/pilot-operations.md. Plan/evidence/risk register: ENTERPRISE_PLAN.md and docs/enterprise.

Next: finish private container profile acceptance, mapped onboarding and typed source review; then Signals/Knowledge, shared-ledger Recovery and Corrective Action in dependency order. All four remain in scope. No cloud deployment, installer replacement, paid resources or real inventory execution in this checkpoint.

---

# BatchFence 0.2.0 handoff

All six core improvements are implemented and verified on the public web application and installed Windows client. Public app: https://batchfence.onrender.com. Windows: https://github.com/NuraliKuzhagaliev/BatchFence/releases/tag/v0.2.0. Existing free Render service only; no purchases, paid disks or account-security changes.

Runtime implementation is 7431360; ebd1402 corrects the Docker frontend COPY and isolates fresh CI artifacts. Later commits contain release evidence, capture tools and an additional exact-failure regression, with no frontend/backend/desktop changes. The immutable Windows tag is v0.2.0 at 7431360. Final published evidence commit/deployment identity is recorded locally in releases/final-verification-0.2.0.json after the final rollout. Recovery checkpoints 2402375 / v0.1.2 and 9a0cc57 remain intact.

## What changed

1. Source-linked causes distinguish unresolved incident scope from actual receiving gaps, merge overlapping questions and count unique inventory.
2. Bounded immutable scenarios compare individual and joint assumptions; complete SUP-B-only FG-C changes 500→400 / 800→700. Partial or inconclusive evidence preserves holds.
3. Linked receiving replies preserve raw output, require explicit source/replacement review, reject weak evidence, recalculate plans and invalidate old authority. A smaller proposal never releases applied holds.
4. Immutable before/after comparison explains SUP-C→FG-D (300 units)→O-104. Offline packets show saved graphs; detailed causal computation requires the owned online case.
5. Guided per-lot unresolved defaults, adjacent quotes, early genealogy, elapsed inference indicator and responsive layouts replace the old CSV-style review flow.
6. Verification separates raw/provider evidence from review and receipts. Six isolated challenges execute actual policy functions without changing the case.

## Actual verification

65 pytest passed; 30 frozen deterministic cases unchanged. Local and public browsers each passed 12 preserved checks plus nine upgrade groups. Public controls passed five groups, no page errors. Installed Windows passed nine upgrade groups locally and seven core checks against its default public backend, plus distribution/IPC checks. It opened this release's fresh AMD packet and both receipts offline with unreachable backend and no external Python/Node in its PATH. Automated native-dialog selection is stubbed. Renderer scales 1.0/1.25 and web widths 1366/1440/1920/390 plus 200% CSS zoom were checked.

Linux CI run 38959067118 passed the real image, dynamic port, 500/800, stale rejection, receipt, isolation and actual named-volume restart. The earlier Docker build failed on missing frontend reply examples; the exact small correction and failure log are retained. No blanket permission changes, resets or container/volume deletion were used.

Four fresh AMD requests on the public 0.2.0 app requested MiMo-V2.6-Flash and returned self-dploy/MiMo-V2.6-Flash. The first two drove reviewed 500/800 receipts and a 409 stale rejection. The first receiving response omitted SUP-B; narrowing failed 422 and inconclusive review kept 800. A clearer separately preserved reply returned SUP-B plus three non-lot IDs. Explicit review selected the source-backed supplier and produced 700 proposed while all 800 applied units remained held. Latencies: 16,026 / 12,791 / 19,718 / 32,413 ms. This is not a general accuracy benchmark; all review was agent-operated, not independent human validation.

Installer: 113,774,692 bytes; SHA256 7fc0b61c1c232394c077d2cc990266972ac0a5dd1bf0095014fa626dcd99979d. Full anonymous public download matches. Installed path: D:\projects\BatchFence\work\installed-0.2.0\BatchFence.exe. No credentials in the packaged renderer or public evidence. Source/history/asset known-value scan passed; npm audit production zero, eight moderate desktop build-tool transitive findings remain documented.

## Open and reproduce

- Public: https://batchfence.onrender.com. Synthetic and historical replay need no key. Live uses the separate private LIVE_DEMO_TOKEN access key, never AMD_API_KEY.
- Local: npm run build; .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787. Configure ignored .env from .env.example privately. Desktop local override: BATCHFENCE_BACKEND_ORIGIN=http://127.0.0.1:8787.
- Tests: .venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-new-run; .venv\Scripts\python.exe -m scripts.evaluate; node scripts/browser-smoke.cjs; node scripts/upgrade-browser.cjs. Choose a new D: test temp directory.
- Public tests: set BATCHFENCE_BASE_URL=https://batchfence.onrender.com and versioned report locations. See DEPLOYMENT.md and scripts' environment options.
- Installed: set BATCHFENCE_TEST_EXE to the path above; node scripts/desktop-smoke.cjs; node scripts/desktop-offline.cjs. New packet path/expected units/receipts are configurable in the offline helper.
- Package: npm run package:desktop. Never overwrite the published v0.2.0 binary with a different build.

Artifacts: docs/release-0.2.0/ (raw evidence, test reports and screenshots); submission/ (versioned video, pitch, cover and current form text); releases/ (installer, checksums and final local deployment manifest). Private session/configuration stays in ignored work/ and .env.

## Remaining limits and human actions

The free host uses ephemeral SQLite: export packets; this is not durable production storage. Complete ancestry replacement uses a bounded explicit record syntax and every superseded parent row. Model omissions and false candidates still require source inspection. Unkeyed packet hashes detect changes but do not authenticate supplier truth. No ERP, machinery or automatic release integration exists.

The Windows installer is unsigned. Complete real OS Import evidence, Save packet and Open packet once on your machine (node scripts/native-dialog-check.cjs), and independently review the quality-domain workflow before operational use. Native automation is unavailable in this environment; no second-machine acceptance is claimed.

The existing authenticated event form's first-step text limits were checked. Media-step constraints and authenticated cutoff still require advancing the team draft; use the current prepared submission files, review them, then submit. No event form was saved or submitted. Optional Gemma and portable recomputation/recovery work was deliberately deferred.

Full claims and exact checks: docs/claims-to-evidence.md. Original evidence and older handoffs remain under docs/history, docs/cloud and docs/ambiguity-fix.

## Final published-build observation

Commit 011502d passed Linux CI run 38962137655 (65 tests, 30 domain cases, container build and named-volume restart) and deployed as dep-db98gstg1s2s73bu200g. Its public JS/CSS hashes exactly matched the tested local build, early genealogy loaded in a new session, and all six real policy challenges passed. See docs/release-0.2.0/published-011502d.json. The corrected 011502d source archive and checksum were added to the existing release and their anonymous full download verified; the Windows binary was not replaced.

Cold-start acceptance remains inconclusive. An existing Chrome tab was open on BatchFence, whose existing connection-status code polls health every 15 seconds. The planned idle wait was cancelled, preserving that tab; the measured 1,075 ms application readiness was warm access, not a cold-start result. To check sleep/wake independently, first export work, close all BatchFence browser/desktop clients, leave the service without client traffic for at least 16 minutes, then reopen it. Other visitors can still keep the public service awake. No external keepalive service was introduced.

The final documentation-only rollout retains identical app and installer bytes. Its final commit/asset verification is stored locally in releases/final-verification-0.2.0.json. The temporary local verification server was stopped; local mode can be started with the documented command.

Final published candidate verification: branch commit9a99a2f passed CI38979895208; default GitHub archive for package commite616ff5 matched every byte of721tracked files in the supplemental source ZIP. Public health still reports0.2.0/e70f4a0; no new deployment or inference. docs/enterprise/finalization.json records the observations. A final metadata-only commit may follow without changing runtime or installer bytes.
