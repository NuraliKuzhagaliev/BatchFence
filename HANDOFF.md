# BatchFence 0.2.0 upgrade checkpoint

Protected public baseline: 2402375 (web) and Windows v0.1.2. New recoverable foundation checkpoint: 9a0cc57. Current implementation is local; public 0.2.0 verification and installer publication are still pending at this checkpoint.

All six core improvements are implemented: source-linked shared causes, immutable impact scenarios, explicit receiving-reply reconciliation, immutable causal revisions, per-lot guided review/early genealogy, and executable verification challenges. Existing containment, approvals, receipts, isolation and historical packets are preserved.

Actual local checks: 64 pytest pass (one upstream Starlette warning); 30 frozen deterministic cases pass unchanged; 12 existing browser checks pass; nine new browser acceptance groups pass, including six executed policy challenges. Screens checked at 1366×768, 1440×900, 1920×1080, 390×844 and 200% CSS zoom. All review is agent-operated. No fresh AMD calls for this upgrade yet.

Core results: shared unresolved boundary holds 1,200 without inventing five missing receiving records. Explicit complete SUP-B-only FG-C scenario gives 500→400 / 800→700. Inconclusive or partial evidence stays held. Reviewed complete reconciliation preserves all 800 already-applied units while proposing 700. SUP-C→FG-D→O-104 explains the added 300 units and fourth order. Stale approval and uncertainty-removal attempts remain rejected.

Run: `.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8793`; `npm run build`; `.venv\Scripts\python.exe -m pytest -q`; `node scripts/upgrade-browser.cjs`; `npm run package:desktop`. Use BATCHFENCE_BASE_URL and BATCHFENCE_UPGRADE_REPORT_DIR for public/versioned browser evidence.

Next: install/test final Windows build, audit source/artifacts, publish release and source, wait for Linux CI and existing free Render deployment, verify public functionality with bounded fresh AMD requests, then refresh actual-screen media and final delivery evidence.

Limits: complete receiving replacement accepts a documented explicit record syntax and exact superseded row IDs. Arbitrary prose that does not meet it stays unresolved. Free hosted SQLite remains temporary. Unsigned Windows package; physical native open/save selection and second-machine acceptance are not automated here. No independent manufacturing validation. Event public page displays Oct 18, 3:00 PM KT; authenticated submission form/media limits unavailable in the current browser session. Optional extra-model experiments deferred.

Older handoffs are preserved under docs/history/; they describe historical versions, not current release readiness.
