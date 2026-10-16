# BatchFence

Evidence-backed lot containment for a small manufacturer's quality manager. A supplier notice becomes a reviewed scope, a deterministic hold plan and a real **sandbox** receipt. Changed evidence invalidates approval.

**Working local web and installed Windows x64 prototype with synthetic fixtures. AMD live verification, hosted distribution and final submission remain incomplete.** No live model performance, customer validation or savings are claimed.

![Actual synthetic workbench](docs/screenshots/03-exposure-1440.png)

## Open

Project: D:\projects\BatchFence.

    cd D:\projects\BatchFence
    .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787

Open **http://127.0.0.1:8787**. Health: /api/health. API schema: /openapi.json.

Windows installer: releases/BatchFence-0.1.0-win-x64-setup.exe. Version 0.1.0, Windows 11 x64, **unsigned**. See [desktop release](docs/desktop_release.md) and releases/SHA256SUMS.txt. Installed verification executable: work/installed/BatchFence.exe.

The desktop uses the local backend at 127.0.0.1:8787. Its installed renderer opens saved packets offline without external Node/Python. New analysis/actions need the backend. Public web/download URLs await authorized hosting. This local installer is not advertised as a cloud release for another person's machine.

## Walkthrough

1. Load the labeled synthetic incident and select its supplier notice.
2. Extract in Fixture mode. Inspect the exact quote, review lot IDs/completeness, then confirm.
3. Inspect 500 held units: 400 documented and 100 uncertain. Open requests and order review.
4. Approve. Test excluding uncertain stock to see server policy rejection.
5. Add supplier v2 and test stale approval. Extract/review the revised notice.
6. The new scope produces 800 held units and four open orders needing review. Approve/apply.
7. Export the packet with its genuine sandbox receipt. Open on desktop for offline read-only review.

The blanket comparison is 1,200 units /в‚¬48,000. Under v1,в‚¬28,000 of carrying value is outside the proposed broad hold. This is not measured cash savings.

## Setup

Tested with Windows 11 build 26200, Node 22.20.0 and Python 3.13.2. Lockfiles pin installed dependencies. Source, cache, virtual environment and release files reside on D:.

    npm ci --cache .cache/npm
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --cache-dir .cache/pip -r requirements.txt
    npm run build

Run the server above. Optional scripts/setup.ps1 and scripts/start.ps1 work when allowed by existing shell policy. No policy change is required. npm run dev starts Vite with a proxy to the same backend.

## AMD

Copy .env.example to a private .env. From authenticated AMD documentation, set AMD_API_BASE_URL, AMD_API_KEY, AMD_MODEL_ID and AMD_PROVIDER_EVIDENCE. Confirm AMD_API_STYLE=openai-chat only if documented. Set INFERENCE_MODE=live. Enable AMD_JSON_SCHEMA only after support is verified.

    .\.venv\Scripts\python.exe -m scripts.probe_amd

This makes four bounded synthetic probes once configured. Inspect semantics/citations, then run a fresh notice and a changed notice through the application. Credentials stay server-side. Never use VITE_ secrets or commit .env.

Follow-up (2026-10-16): genuine AMD Gemma inference now drives two fresh/revised workflows through sandbox receipts, with 500 then 800 held units. Seven live requests are recorded; ambiguity remains a semantic limitation. Actual Windows open/save/reopen dialogs passed. See [AMD evidence](docs/amd_evidence.md) and [current handoff](HANDOFF.md). The original video/deck remain fixture-era materials.

## Inputs

UTF-8 TXT, strict CSV and selectable-text PDF: 2 MB/file, 24 documents/case, 80,000 normalized characters/document. Image-only PDFs receive an unsupported result. CSV headers are in fixtures/demo. Dataset replacements remain pending until review, reconcile quantities and preserve existing holds.

Native choose/save/open exposes bounded file bytes. Installed tests verified the bridge using dialog-result stubs; actual OS dialog selection remains an acceptance item.

Packets preserve historical evidence, reviews and receipts without session authority. Hashes detect changes and do not authenticate suppliers. Offline packets cannot infer/approve/apply/queue writes. Reconnection reloads current state. Promotion creates a new draft.

## Verify

    npm run build
    .\.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-verify
    .\.venv\Scripts\python.exe -m scripts.evaluate
    node scripts/browser-smoke.cjs
    node scripts/desktop-smoke.cjs
    node scripts/desktop-offline.cjs

Start the server first. Browser tests use installed Microsoft Edge. Desktop tests use the real installer installed under work/installed, with stubbed dialogs for repeatability.

Observed: 28 pytest checks,30/30 frozen domain cases (18 development, 12 held out), real web/installed workflows and offline review without external Node/Python on child PATH. Exact results are in docs/*results.json. [Evaluation](docs/evaluation.md) separates these from unmeasured model performance.

Windows packaging:

    $env:ELECTRON_CACHE='D:\projects\BatchFence\.cache\electron'
    $env:ELECTRON_BUILDER_CACHE='D:\projects\BatchFence\.cache\electron-builder'
    npm run package:desktop

The build is unsigned. Do not disable OS protections. Signing/distribution require authorized configuration.

## Materials

[Architecture](docs/architecture.md), [acceptance](docs/feature_acceptance.md), [visual review](docs/visual_review.md), [AMD evidence](docs/amd_evidence.md), [limitations](docs/limitations.md), [deployment](docs/deployment.md), [provenance](docs/data_provenance.md).

Submission drafts, a six-slide PowerPoint, actual cover screenshot and recording guide are under submission/. Repository publication, hosting, video upload and final submission have not occurred. Confirm the authenticated deadline and form.

Original code: MIT. Dependencies retain their licenses. See [notices](docs/third_party_notices.md). No model weights are redistributed.

Media: submission/BatchFence-demo.mp4 is a silent113.73-second real application recording with selectable captions, under2MB. Source and native-dialog limitations are disclosed in the captions. The1920×1080 cover is an actual screen capture. Set a public BATCHFENCE_BACKEND_ORIGIN before packaging an authorized remote desktop release; AMD credentials are never baked.
