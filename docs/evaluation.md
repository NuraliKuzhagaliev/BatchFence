# Public cloud follow-up — 2026-10-16

Actual free public app: https://batchfence.onrender.com. Current verified product code 57a82bc. [Cloud evidence](cloud/README.md) separates every raw response, failure, agent review and resulting receipt. Eight cloud AMD requests: six structurally accepted and two citation-rejected; this is not an accuracy rate. Prompt-v2 responses drove 500/800 receipts and stale rejection on the unchanged frozen inputs. Two different ambiguous notices ended in conservative 1,200-unit holds; the second required fixing a terminal-period source-match defect and a fresh rerun. Raw booleans remain unreliable for pending involvement. No independent human validation.

52 regression tests, 30 frozen domain cases, Linux image/container restart checks, 12 public Synthetic browser checks and five public controls pass. Free Render storage is ephemeral; actual redeploy lost the test receipt while its export remained valid. Full metadata and limitations are in cloud/summary.json. Earlier local evidence below remains historical and is not relabeled as cloud verification.

---

# Evaluation — 0.1.1

All inputs are synthetic. Codex authored/inspected review choices; no independent human or manufacturing-domain validation occurred.

| Check | Actual result | Evidence |
|---|---|---|
| Unit/API/provider/hash regression | 40 passed; one existing Starlette HTTPX deprecation warning | ambiguity-fix/pytest-results.xml |
| Frozen deterministic evaluation | 30/30: 18 development, 12 held-out; 0 wrong outside labels; 0 missed documented pools across 29 labels | evaluation-results.json |
| Browser fixture workflow | 12 checks, zero page errors | browser-results.json |
| Installed Windows 0.1.1 fixture workflow | 7 checks, zero page errors; packaged executable | desktop-results.json |
| Live clear workflow | 500 then 800 units; two receipts; stale apply 409 | ambiguity-fix/clear-live/browser-results.json |
| Two new live ambiguous notices | One broad 1,200 receipt, one citation failure blocked before review | ambiguity-fix/live-ambiguity.json |
| Real backend restart | Exact runs/scope/plans/receipts/stocks/history preserved for all three cases | ambiguity-fix/restart-results.json |
| Packet and persisted-error UI | Fresh export validated, browser read-only packet accepted, failure visible after reload | ambiguity-fix/final-ui-results.json |
| Packet corruption | Valid packet accepted; 5 malformed/cyclic mutations rejected despite recomputed hashes | scripts/packet-tests.cjs |
| Installed offline live packet | Actual packaged client, unreachable backend, external Node/Python absent from child PATH; dialog selection stubbed | ambiguity-fix/installed-live-packet.png; submission/demo-video-evidence-0.1.1.json |

The exact original Gemma failure was reproduced against old code: review/approval/apply accepted an unsupported SUP-S branch exclusion. New regressions reject that route, require explicit dispositions and scope resolution, preserve possible ancestry beyond selected affected branches, and invalidate legacy approvals. Two different ambiguous wordings with deliberately bad qualifier-free proposals are included. Prompt/schema were not strengthened to claim a fix.

Raw model quality remains separate: MiMo repeated the unresolved boolean error; one other notice failed citation validation. Clear-notice IDs were correct, while qualifiers conflated supplier scope with warehouse ancestry and required agent interpretation. Eight current attempts and seven historical requests are separate populations. There is no general accuracy rate, p95, customer benefit, direct-model-answer baseline or independent review success rate.

The deterministic pack was frozen before its first run. Held-out results were then inspected; no model tuning used them. Domain timing is CPU-only, not AMD latency. Whole-pool containment, merges/splits, unknown sources, invalid cycles/quantities, allocations, stale and modified actions, concurrency/idempotency, ownership, persistence and no automatic release remain checked. Original literal 500/800 expected units and carrying values are unchanged.

Observed additional failures: browser assertions needed changed reason text and a reconnect wait; first video launch lacked the configured Playwright ffmpeg cache path; media review exposed a real disappearing failure message, now fixed; installed media exposed real packet hash incompatibility, now fixed. A restart verifier initially waited on inherited Windows capture pipes; file-based output resolved the harness wait. Original live request failures and original rejected exports remain preserved. See ambiguity-fix/verification-history.json.

Historical actual Windows dialogs passed at ed6a2b0 on 0.1.0 without stubs. Current 0.1.1 automated checks/capture use dialog stubs. No new physical-machine or independent human acceptance is claimed.

Commands from D:\projects\BatchFence:

    .\.venv\Scripts\python.exe -m pytest -q --basetemp work/pytest-verify
    .\.venv\Scripts\python.exe -m scripts.evaluate
    node scripts/browser-smoke.cjs
    $env:BATCHFENCE_TEST_EXE='D:\projects\BatchFence\work\installed-0.1.1\BatchFence.exe'
    node scripts/desktop-smoke.cjs
    node scripts/desktop-offline.cjs
    node scripts/packet-tests.cjs
    node scripts/live-evidence-check.cjs
    .\.venv\Scripts\python.exe scripts/restart-live-check.py

The last two require ignored local private verification sessions and existing cases; they make zero inference calls. Fresh AMD probes consume quota and should be run only when useful. Browser/desktop smoke scripts explicitly select fixture mode. Docker/container/hosted checks remain blocked/unrun.
