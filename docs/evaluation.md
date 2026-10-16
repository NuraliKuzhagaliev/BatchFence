# Evaluation

All observations concern synthetic records. No model accuracy, customer outcomes or production reliability are inferred from them.

## Domain and action integrity

Current unit/API suite: **28 passing checks**. Coverage includes exact v1/v2 units/cents/order counts, unknown provenance, complete-scope failures, whole-pool merges, confirmed-path precedence, duplicate/reordered paths, widening, shipped review, invalid quantities/cycles/references/allocations, stale evidence/inventory, modified/unsupported actions, cross-session access, concurrent revision/apply, duplicate execution, packet promotion, malformed uploads, unsupported scans and no automatic release after uncertainty resolution.

Frozen graph evaluation: **30/30**, consisting of **18/18 development** and **12/12 held-out** cases, five per six buckets. Across 29 documented stock-pool labels in non-invalid first scopes: zero missed documented pools. Zero wrong outside-scope classifications. Designed invalid graphs are rejected. All expected units/cents reconcile from literal truth membership. Revised scenarios also compare expected new sets. Exact case IDs, hashes, denominators and timings are in evaluation-results.json. These timings are CPU-domain measurements, not end-to-end AMD latency.

The pack was frozen before its first run. Held-out outcomes were then inspected; no model tuning used them. One author created and reviewed the synthetic truth. There was no independent manufacturing-domain audit.

## Browser and desktop

browser-results.json records twelve completed checks in Microsoft Edge through Playwright, with no page errors: real UI/API data flow, exact source passage, queue value, order counts, policy/stale conflicts, receipt/export, refresh persistence, responsive overflow and read-only packet behavior.

desktop-results.json records seven installed-executable checks with no page errors, including v1/v2, stale rejection, normalized web/desktop parity, file byte handling, transport restrictions and invalid packet rejection. Dialog selections were stubbed for repeatability. They do not establish actual Windows open/save dialog interaction.

desktop-offline-results.json records a separate installed launch against an unreachable backend with PATH limited to C:\Windows\System32. The exported 800-unit packet and receipt remained readable, inference/action controls were disabled, and external Node/Python were not required by the installed renderer. The local online backend still requires Python until hosted deployment is authorized.

## Model evaluation and baselines

Raw AMD extraction exact match, extra/missed IDs, semantic citation quality, ambiguity performance, success/timeout/repair rates and end-to-end median/p95: **not measured**. AMD preflight recorded zero live HTTP calls due missing private configuration. No genuine recorded mode exists.

Broad-hold baseline is calculated from the same on-site stock: 1,200 units / в‚¬48,000. Reviewed graph output is 500 / в‚¬20,000 under v1 and 800 / в‚¬32,000 under v2. Direct-model-answer baseline is **not run**. Fixture extraction is not a substitute for that baseline.

Do not describe 12/12 held-out synthetic graphs as universal accuracy. A failed live gate remains failed even when every deterministic test passes.

## Reproduce

    npm run build
    .\.venv\Scripts\python.exe -m pytest -q --basetemp work\pytest-verify
    .\.venv\Scripts\python.exe -m scripts.evaluate
    node scripts\browser-smoke.cjs
    node scripts\desktop-smoke.cjs
    node scripts\desktop-offline.cjs

Start the server before browser/online desktop checks. Build/install the current Windows release under work/installed before the installed tests. Test reports include actual timestamps and do not claim an external audit.

Additional final evidence: real text-PDF and multiline CSV source-span tests pass. docs/pytest-results.xml retains all28 test cases. Native/web draft-copy checks, five malformed shared-packet cases, real backend restart and1.0/1.25 renderer-scale checks passed. The initial installed copy failure and its correction remain documented. Production dependency audit reported zero advisories; eight moderate packaging-development advisories remain.
