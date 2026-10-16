# BatchFence handoff — live AMD follow-up, 2026-10-16

Continued from 54745c5 in D:\projects\BatchFence. Product implementation and architecture are unchanged. Genuine AMD responses now drive the local web workflow. Actual Windows file dialogs passed. Container/hosted publication gates remain open.

## Open

Web: http://127.0.0.1:8787. The server runs with private AMD configuration and INFERENCE_MODE=live. Reload existing clients to read the new default mode. Installed app: D:\projects\BatchFence\work\installed\BatchFence.exe.

To inspect the verified result in any client, choose Open packet and select:

    D:\projects\BatchFence\docs\live-verification\packet-2.json

It includes two actual model runs, reviews, plans and sandbox receipts; it opens read-only. Browser and desktop sessions are separate, so the automated test case is not automatically listed in another browser session.

If the backend stops:

    cd D:\projects\BatchFence
    .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

Private .env is configured and ignored by Git. The key was transferred directly from the authenticated portal's Copy control without displaying it, then that clipboard value was cleared. Do not print .env or include it in deployment artifacts.

## Actual verification

- Authenticated AMD manual/catalog confirmed Gemma-4-31B-IT. Responses identified self-dploy/Gemma-4-31B-IT. Provider documentation says the service runs on AMD GPUs; physical hardware was not independently measured.
- Seven sequential live calls: four capability probes, one initial workflow call, then the two-call completed fresh/revised walkthrough. All passed JSON/schema/exact-quote validation; zero transport failures, repairs or fixture fallback. Observed request times 5.294–12.261 seconds, median 7.666 seconds. This tiny mixed-prompt sample is not a benchmark.
- Fresh/revised notices used new batch IDs and the identical uploaded filename supplier-message.txt. Raw affected IDs matched frozen truth: MC-7421-X, then BZ-9187 plus MC-7421-X. NX-6130-Z was correctly excluded. Zero ID corrections.
- Those responses drove review controls, deterministic 500/800-unit plans, exact approvals and two real SQLite sandbox receipts. The revision preserved 500 held units and added 300; the uncertain 100-unit pool remained held. Old-plan execution returned 409 STALE_APPROVAL.
- Live receipts, stock and inference records survived refresh and an actual backend process restart.
- Actual installed Windows Import evidence, Save decision packet and Open offline decision packet dialogs completed without stubs. The reopened packet was read-only. Computer-use mouse/keyboard performed selection; this was not an independent human usability study.
- All 28 existing pytest cases passed after live configuration, with the existing non-failing Starlette deprecation warning. Prior 30-case domain evaluation, 12 browser and 7 installed checks remain historical evidence, not new live tests.

Review/approval controls were operated by the test harness after Codex inspected exact passages. No independent human/customer validation occurred. Raw model output is retained separately from accepted facts and deterministic results.

## Limitations and retained failures

The ambiguity probe is not a semantic pass: a possibly affected lot was marked true and another unresolved lot false, although an unresolved-scope qualifier survived. Exact quotes alone do not establish semantic certainty. Ambiguous input requires conservative human review; no production accuracy claim is justified.

Two live-test selectors assumed status/receipt text was unique. The underlying model-driven transactions succeeded. Initial reports are retained; the second failure was recovered through the same saved private session without another model call. The native test also had a duplicate-heading assertion failure after successful import, then passed after correction. No product code fix was needed.

Docker Desktop fails during startup: initializing its Ingest server cannot rename AppData/Local/Docker/run/sailor-ingest.sock to sailor-ingest.sock.stale ("The file cannot be accessed by the system"). The Linux-engine pipe is absent. WSL reports default distribution docker-desktop and default version 2. No socket deletion, factory reset, diagnostic upload or system setting change occurred. Container build/run remains unverified.

## Evidence and artifacts

docs/amd-probe.json and docs/live-verification contain provider provenance, frozen notice hashes/truth, raw runs with request IDs/timestamps/usage/latency, source passages, reviewed results, packets, real screenshots, restart/native results, regression report and preserved harness failures. summary.json is the compact machine-readable result.

Original unsigned installer, unchanged:

    releases/BatchFence-0.1.0-win-x64-setup.exe
    SHA256 37bd0d13878d11632ca3cd90538df1aa43299e636893770526a0106378ec7e80

Follow-up source/evidence archives and checksums: releases/followup-manifest.json. The original release-manifest.json describes checkpoint 54745c5. No private configuration or browser-session capability is in source/evidence bundles.

The earlier pitch/video are fixture-era materials, not live AMD evidence. Updated live screenshots/packets are separate; refresh the submission demonstration before publishing. No public repository, host, installer download or submission exists.

## Next actions

1. Resolve Docker Desktop's specific startup failure through normal troubleshooting, then run docker info, docker build -t batchfence:0.1.0 ., and the persistent-volume run in docs/deployment.md. Do not reset/delete unrelated Docker data routinely.
2. Approve a concrete hosting/public-repository/download destination and existing resource budget before publication. Set APP_ORIGIN and BATCHFENCE_BACKEND_ORIGIN to the authorized HTTPS origin, configure server secrets privately, package a new installer for that origin, and verify hosted persistence/downloads.
3. Review ambiguous-source behavior and live evidence yourself; confirm authenticated event form/deadline/eligibility. Refresh pitch/demo and submit only after remaining release gates pass.

## Reproduce

    .\.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-next
    .\.venv\Scripts\python.exe -m scripts.probe_amd
    node scripts/live-browser-check.cjs new-review-session
    node scripts/native-dialog-check.cjs

Probe consumes four live calls. Browser script consumes two and pauses after each response: inspect browser-results.json, then place review-N.json containing run_id, source_hash and accepted_lots in its printed private review directory. Never reuse a marker for another run. Native script consumes zero model calls and needs real OS selection. Existing fixture browser/desktop smoke scripts must use a fixture-configured test server or explicitly select fixture mode; the normal server now defaults to live.
