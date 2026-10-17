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

# Active enterprise expansion

See ENTERPRISE_PLAN.md for all four modules and required foundations. Protected release remains e70f4a0 / v0.2.0. Foundation checkpoint: 73 tests plus real PostgreSQL restore/workflow checks pass; expansion not published. Complete mapped onboarding, modules, full release acceptance before main push.

---

# BatchFence 0.2.0 upgrade

Protected release: `2402375b6dd3aecae2e1cd691b51639a07f8dac7` (web); Windows `v0.1.2` at `45280e8`. Preserve these and frozen 500/800 fixtures. The research brief predates the verified Windows download; retain it until a new verified installer exists.

Dependency order and gates:

1. Cause-aware queue and shared graph semantics. Reproduce boundary/receiving confusion and unresolved intermediate nodes; distinguish actual missing records from source review. Deduplicate causes and pool totals.
2. Read-only impact planner. Verify 500→400 / 800→700 conditional complete SUP-B identity, unchanged exposure/inconclusive cases, overlapping and joint assumptions, preservation of real approvals/holds.
3. Linked reply reconciliation and immutable causal comparison. Exact citations, explicit replacement review, inconclusive/conflicting evidence stays open, stale approval rejection, 300-unit SUP-C→FG-D→O-104 path.
4. Per-lot review, early genealogy, guided steps, elapsed inference time, responsive/reduced-motion presentation. No automatic acknowledgements or authority from playback.
5. Executable verification challenges, full regressions, web/desktop acceptance, free Render deployment, sanitized release/media and checksums.

All reviews in automated verification are agent-operated, not independent human validation. Live AMD, historical replay and synthetic cases stay distinct. No paid resources, optional model experiments, or architecture rewrite. Free storage remains temporary; workspace holds never automatically release.

Status: all six core implementations and behavior gates pass. Public web 0.2.0, installed Windows and fresh AMD workflow verified. Optional experiments deferred. Remaining human-only checks are physical OS dialogs, independent domain acceptance and event form completion.

Commands: `.venv\Scripts\python.exe -m pytest -q`; `npm run build`; `node scripts/browser-smoke.cjs`; `npm run package:desktop`. Versioned evidence will be recorded under `docs/release-0.2.0/` and `releases/`.

Release milestone: all six implementations and local web/installed checks pass; Windows v0.2.0 published with verified full-download hash. First Linux gate found missing frontend-stage reply examples; Docker COPY fixed in ebd1402. The corrected Linux gate passed and Render deployed ebd1402. Public and installed-hosted checks passed. Four fresh AMD responses, including an omitted-parent failure and adaptive clarification, are preserved. The final evidence-only commit will use the same automatic check/deploy route; its actual identity is recorded in releases/final-verification-0.2.0.json.

Final regression milestone: 65 passing tests including replay of the exact fresh receiving omission. Both old and new offline packet/receipt checks pass. Finalize media checksums and sanitized evidence publication, then verify the deployed commit without additional AMD calls.

Publication milestone: 011502d passed final Linux checks, deployed, and matched tested asset hashes; six policy challenges passed on that build. Cold-start measurement is inconclusive because an existing client polls health. Final metadata-only rollout is tracked in releases/final-verification-0.2.0.json; core work is complete, remaining human acceptance is documented in HANDOFF.md.

Integrated candidate milestone: 102 tests, 30 domain cases, six connected browser groups, actual PostgreSQL recovery/connector restart/migration/16-source restore, actual OCR, statistical and bounded performance evidence. New-task live gate blocked at 0/24 by free-only catalog/quota conflict. Preserve main0.2.0. Candidate0.3.0-rc.1 packaging/publication preparation continues independently.

Candidate gate milestone: final side-by-side Windows install passes core7/module6/default-pilot4 and offline module checks. LinuxCI38978907998 passes source+SQLite restart. Clean package sourcee616ff5, version0.3.0-rc.1. Required review materials prepared, known-value installed asset scan clean. New-task AMD0/24 remains blocked on zero-cost allowance; preserve public0.2.0 and no release/tag/Render promotion. Human pilot acceptance pending as documented.

Final branch CI38979895208 passed for9a99a2f. All721source files in the default GitHub commit archive match the packaged source ZIP. Public0.2.0 remains unchanged. Await only the specific AMD free-access unblock before new inference/promotion; independent human pilot acceptance remains pending.
