# Evaluation

All input records are synthetic. The narrow live-model observations below do not establish general accuracy, customer outcomes or production reliability.

## Domain and action integrity

Current unit/API suite: **28 passing checks**. Coverage includes exact v1/v2 units/cents/order counts, unknown provenance, complete-scope failures, whole-pool merges, confirmed-path precedence, duplicate/reordered paths, widening, shipped review, invalid quantities/cycles/references/allocations, stale evidence/inventory, modified/unsupported actions, cross-session access, concurrent revision/apply, duplicate execution, packet promotion, malformed uploads, unsupported scans and no automatic release after uncertainty resolution.

Frozen graph evaluation: **30/30**, consisting of **18/18 development** and **12/12 held-out** cases, five per six buckets. Across 29 documented stock-pool labels in non-invalid first scopes: zero missed documented pools. Zero wrong outside-scope classifications. Designed invalid graphs are rejected. All expected units/cents reconcile from literal truth membership. Revised scenarios also compare expected new sets. Exact case IDs, hashes, denominators and timings are in evaluation-results.json. These timings are CPU-domain measurements, not end-to-end AMD latency.

The pack was frozen before its first run. Held-out outcomes were then inspected; no model tuning used them. One author created and reviewed the synthetic truth. There was no independent manufacturing-domain audit.

## Browser and desktop

browser-results.json records twelve completed checks in Microsoft Edge through Playwright, with no page errors: real UI/API data flow, exact source passage, queue value, order counts, policy/stale conflicts, receipt/export, refresh persistence, responsive overflow and read-only packet behavior.

desktop-results.json retains the prior seven installed-executable checks with dialog stubs. The new live-verification/native-dialog-results.json separately records actual Windows evidence selection, save, reopen and read-only packet behavior through computer-use input, with no stubs.

desktop-offline-results.json records a separate installed launch against an unreachable backend with PATH limited to C:\Windows\System32. The exported 800-unit packet and receipt remained readable, inference/action controls were disabled, and external Node/Python were not required by the installed renderer. The local online backend still requires Python until hosted deployment is authorized.

## Model evaluation and baselines

Follow-up: seven actual AMD requests, all valid JSON/schema/exact quotes, no transport failure, repair or fallback. Three clear capability probes passed their expected facts; the ambiguous probe did not establish correct certainty (SUP-R=true for “may”, SUP-S=false for unresolved, qualifier retained). Two unique fresh/revised workflow notices had zero missing/extra affected IDs and zero operator corrections. The initial first-notice call was repeated after a test-only selector failure; it is included in the seven-call denominator. Requested Gemma-4-31B-IT; returned self-dploy/Gemma-4-31B-IT. See live-verification/summary.json and raw reports. No model prompt tuning occurred.

Broad-hold baseline is calculated from the same on-site stock: 1,200 units / EUR 48,000. Reviewed graph output is 500 / EUR 20,000 under v1 and 800 / EUR 32,000 under v2. Direct-model-answer baseline is **not run**. Fixture extraction is not a substitute for that baseline.

Do not describe 12/12 held-out synthetic graphs as universal accuracy. A failed live gate remains failed even when every deterministic test passes.

## Reproduce

    npm run build
    .\.venv\Scripts\python.exe -m pytest -q --basetemp work\pytest-verify
    .\.venv\Scripts\python.exe -m scripts.evaluate
    node scripts\browser-smoke.cjs
    node scripts\desktop-smoke.cjs
    node scripts\desktop-offline.cjs

Start the server before browser/online desktop checks. The historical browser/desktop smoke scripts require a fixture-configured test server or explicit fixture selection; the normal server now defaults to live. Build/install the current Windows release under work/installed before the installed tests. Test reports include actual timestamps and do not claim an external audit.

Additional final evidence: real text-PDF and multiline CSV source-span tests pass. docs/pytest-results.xml retains all28 test cases. Native/web draft-copy checks, five malformed shared-packet cases, real backend restart and1.0/1.25 renderer-scale checks passed. The initial installed copy failure and its correction remain documented. Production dependency audit reported zero advisories; eight moderate packaging-development advisories remain.

## Live workflow follow-up

Fresh/revised inputs and literal truth were frozen at 2026-10-16T08:28:11Z. Both uploads used supplier-message.txt, while batch IDs differed from the original fixture parser. Raw extracted facts and exact passages were inspected before review markers allowed the UI to proceed. Codex was the test operator; review/approval clicks were automated and no independent human validation is claimed. Plans held 500 then 800 units, preserving the uncertain 100 and adding 300 newly held units. Two real receipts survived refresh and actual server restart. Reusing an old plan with a new execution key returned 409 STALE_APPROVAL.

Live request elapsed times: min 5,294 ms, median 7,666 ms, max 12,261 ms across seven mixed prompts. Cached tokens are reported by the provider. This is neither a latency benchmark nor a reliable p95 estimate. Two browser-test duplicate-label selectors and one native-test selector failed after successful application behavior; failures are retained and selectors corrected. Recovery of the final receipts used zero extra inference calls. All 28 pytest cases were rerun after private live configuration and passed (one existing deprecation warning).
