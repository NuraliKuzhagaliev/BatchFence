# Public cloud evidence — 2026-10-16

App: https://batchfence.onrender.com. Product code verified: `57a82bc299c9c1a76decac0529403b8ca03b6712`. Hosting is Render Free, one Docker service, same-origin FastAPI/React, temporary SQLite. No paid disk, service, upgrade or payment method was added.

## Outcome

The free synthetic demonstrator works. Fresh AMD responses drove 500 and 800 held units, two real sandbox receipts and stale-approval rejection. Public receipt persistence across redeployment is **not** available; a real redeploy lost the stored test case, while its exported packet remained valid. This is not production readiness.

All notices, inventories and suppliers are synthetic. Codex inspected source and raw proposals and operated review/approval. No independent human or customer validation occurred. A successful model request alone is not counted as a successful product workflow.

## Raw responses versus reviewed behavior

| Observation | Raw model / application result | After review |
|---|---|---|
| Clear notice, prompt v1 | Valid QL-6304-P=true, CZ-8031=false; ambiguous ancestry qualifier | Agent separated supplier boundary from warehouse ancestry; 500-unit receipt |
| Revised notice, prompt v1 | Correct proposed identifiers but additional quotes lacked their lot ID; validator rejected | Review 422, stale apply 409; no new receipt |
| One explicit v1 retry | Same frozen source; same citation failure, retained raw rejected output | Still blocked; no further unchanged retry |
| Uncertain involvement notice | Potential QL-6304-P proposed true, pending UT-5529 false | Both reviewed unresolved; 1,200 held, zero excluded |
| Confirmed-plus-pending notice, before patch | Valid structured output, but source review rejected QL-6304-P followed by a period | No receipt; exact defect reproduced by regression |
| Clear and revised notices, prompt v2 | Same frozen notices, valid per-lot citations; lot IDs needed no correction | Qualifier interpretation corrected by agent; 500/800 receipts, stale apply 409 |
| Exact pending notice after punctuation fix | Model proposed UT-5529=true despite pending tests | Reviewed uncertain; narrowed scope rejected; 1,200 held, 400 documented, 800 uncertain, zero excluded |

Eight cloud requests: six structurally accepted, two rejected. These are a small mixed-prompt sample, not an accuracy rate or performance benchmark. Returned model: `self-dploy/MiMo-V2.6-Flash`. Each raw run retains request ID, prompt version, server timestamp, latency, usage and failures. Provider cost fields are accounting metadata, not proof of an invoice. Local client timestamps run about 80 seconds behind provider HTTP time; originals are retained.

Prompt v2 only clarifies the already-enforced rule that every evidence quote must contain that fact's lot ID. Server citation validation was not weakened; both old rejected outputs remain rejected in tests. The review fix accepts terminal punctuation without admitting longer dotted/suffixed identifiers. Unresolved scope/ancestry guards remain in server/domain code.

## Evidence index

- `summary.json`: concise actual results and every request ID/timing.
- `live/`: frozen original inputs, first 500 receipt, revised failure and explicit failed retry. `failure-containment.json` proves blocked review/stale execution.
- `live-v2/browser-results.json`: fresh actual public browser workflow, raw runs, source-specific agent review, 500/800 calculation/receipts and stale rejection.
- `live-v2/packet-2.json`: final live case and both receipts; open with the app's Open packet control. Historical read-only when reopened.
- `live-v2/final-ui-results.json`: fresh export validation, refresh, read-only import and two-session isolation; zero new model calls.
- `ambiguity/results.json`: both initial ambiguous sources and raw outputs; first conservative receipt, second source-match failure.
- `ambiguity-after-punctuation/results.json`: exact affected source rerun after the fix, corrected disposition and 1,200 receipt.
- `punctuation-before.txt`: two failing regressions before the source-match fix; they pass afterward.
- `public-synthetic-results.json`, `synthetic-screenshots/`: 12 actual public browser checks; Fixture only.
- `public-controls.json`: five actual public checks, including protected Live 403 and private-case/export isolation. No model call.
- `public-asset-audit.json`: known configured secrets absent from sampled HTML, JS, CSS and public API responses. Not a general security audit.
- `storage-results.json`, `storage-test-packet.json`: actual redeployment data loss and valid retained export; no durability claim.
- `final-ci-results.json`: 52 pytest, Linux build and real container restart with a named volume. This separate volume result does not establish Render persistence.
- `render-deployment.json`: free service and deployment provenance. No credentials.

## Media provenance

`live-v2/01-live-candidates.png`, `01-reviewed-scope.png`, `01-sandbox-receipt.png`, `02-live-candidates.png`, `02-reviewed-scope.png`, `02-sandbox-receipt.png` are actual public browser captures from fresh AMD calls, followed by agent review. Password fields are masked; provider keys never reach this UI.

`live/03-failed-live-revision.png` is the actual earlier rejection, not a fabricated failure screen. `public-replay.png` is explicitly historical local AMD replay. `synthetic-screenshots/` uses fixtures and makes no live claim. Earlier submission videos remain historical local recordings; no new cloud video or independent human demonstration is claimed.

## Limitations and next actions

Export before idle/restart/redeploy. Do not keep confidential manufacturing data in this public demonstration. Use the private LIVE_DEMO_TOKEN for live testing; the AMD key stays server-side. No upgrade/payment is needed for this free demo. Domain/operator validation and native desktop dialog/distribution acceptance remain human gates. Durable cloud storage is outside this free architecture.
