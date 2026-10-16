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
