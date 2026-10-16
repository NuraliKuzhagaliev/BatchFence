# Morning handoff

BatchFence is implemented under D:\projects\BatchFence. The working local web and installed Windows prototype use clearly labeled synthetic fixtures. Full live/hosted release acceptance is not complete.

## Open

Web: http://127.0.0.1:8787. The backend was left running locally. If stopped:

    cd D:\projects\BatchFence
    .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

Installed app: D:\projects\BatchFence\work\installed\BatchFence.exe

Installer: D:\projects\BatchFence\releases\BatchFence-0.1.0-win-x64-setup.exe

Version 0.1.0, Windows 11 x64, unsigned. The exact final SHA-256 and local checkpoint are in releases/SHA256SUMS.txt and releases/release-manifest.json. Source backup: releases/BatchFence-0.1.0-source.zip.

## What works

Evidence intake and exact quotes; critical scope review; selectable exposure graph and table; 500 then800 units; 100-unit/в‚¬4,000 evidence request; 3 then4 open orders needing review; revision history; exact approval; stale/edited/duplicate request safeguards; genuine sandbox database receipt; restart persistence; native file byte handling; portable read-only packets and offline installed review. No automatic release or real inventory-system action exists.

Actual checks: 28 passing pytest cases,30/30 frozen domain cases (18 development,12 initially held out),12 browser checks and7 installed checks with zero page errors. Both clients' results match. Native and web request-copy actions pass. Five malformed/cyclic packet cases fail safely. Actual backend restart preserved its exact receipt. Installed offline launch worked with external Node/Python absent from child PATH. Renderer-scale 1.0/1.25 checks passed without changing OS settings.

One non-failing Starlette test-client deprecation warning remains. Initial copy failure and its fix are recorded. Sources, receipts and frontend assets were scanned for credential-like material; see docs/secret-scan.json for scope and result. These are synthetic tests, not production or customer validation.

## AMD and remaining gates

**No model has actually run on AMD.** The portal showed sign-in; endpoint/model/key/provider provenance were absent. There is no genuine recorded inference. Fixture mode is a deterministic parser and is never labeled live AI. The server adapter is implemented; model quality and latency are unmeasured.

1. Sign in to the AMD portal yourself. Set AMD_API_BASE_URL,AMD_API_KEY,AMD_MODEL_ID,AMD_PROVIDER_EVIDENCE privately in D:\projects\BatchFence\.env using authenticated documentation. Confirm AMD_API_STYLE only if supported. Run .\.venv\Scripts\python.exe -m scripts.probe_amd, then complete a fresh and changed-notice live walkthrough. Do not put a key in chat.
2. On the installed app, complete actual OS file selection, native Save and native packet reopen. Automated byte-transfer tests used dialog-result stubs. OS dialog interaction is still unverified.
3. Authorize the public repository/hosting/download route after reviewing the artifacts. Nothing was published or submitted. The installer currently uses the local backend. Its public HTTPS origin can be baked through BATCHFENCE_BACKEND_ORIGIN when packaging.
4. Open Docker Desktop and resolve its normal Linux-engine startup requirements until docker info succeeds. Its pipe was still absent after launch; container build/run remains unverified. The Dockerfile is prepared with persistent /data storage.
5. Confirm the participant deadline/form, review the actual UI and submission materials, then perform authorized publication/submission. The supplied deadline remains 2026-10-18 15:00 Asia/Qyzylorda, with the internal target 2026-10-17 18:00; authenticated confirmation is pending.

No customer interview, independent usability test, physical GPU identity, Google/Gemma/Evolus eligibility, hosted URL, public installer download, code signing or submission acceptance is claimed.

## Submission assets

D:\projects\BatchFence\submission contains the editable six-slide PowerPoint, actual 1920Г—1080 cover, silent recorded demo with embedded/selectable captions and sidecar SRT/VTT, the demo's actual decision packet, descriptions, recording guide and checklist. The desktop recording discloses its stubbed dialog selection. It does not pretend to prove a manual file-dialog test or live AMD inference.

Detailed feature states, architecture, evaluation, release, visuals, provenance and limitations are in docs. Implementation and all deliverables are on D:.
