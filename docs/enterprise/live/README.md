# Fresh AMD evaluation, 17 October 2026

The authenticated event manual confirmed the configured shared endpoint and MiMo-V2.6-Flash allowance at zero additional monetary charge. Its points are nonmonetary. The general catalog still said `free=false`; that conflict is retained in `access-recheck.json`, with the event-specific evidence. No endpoint, key or model was substituted, no purchase made, and no automatic retry or fixture fallback occurred.

The owner explicitly approved up to 24 additional calls, 30 total. **27 attempts were sent: 26 HTTP 200 responses and one 45.964-second read timeout.** Three authorized requests remain unused. Median measured attempt latency was 17.233 seconds. Requested model: `MiMo-V2.6-Flash`; returned model: `self-dploy/MiMo-V2.6-Flash`. Raw timestamps, input hashes, request IDs, token accounting and failures are adjacent JSON. Accounting may settle a timed-out request later; quota snapshots are not invoices.

## Raw quality

The original 24 agent-authored synthetic items and hash remain unchanged. All 24 passed through the actual application routes: 20 made a fresh model request, four abstained in deterministic retrieval before inference. KNW-01 reuses its original integrated request, counted once. No independent human labeling or manufacturing accuracy is claimed.

| Measure | Actual result |
|---|---|
| Extraction source/schema accepted | 11/12 |
| Exact supplier entities and affected disposition | 6/12 |
| Supplier entity precision / recall | 15/22 proposed entities; 15/15 expected entities |
| Affected-lot precision / recall | 6/13 affected proposals; 6/6 expected affected lots |
| Knowledge pipeline frozen-label matches | 11/12, including four deterministic abstentions |
| Knowledge model-only label matches | 7/8 |
| Answerable questions with expected source | 4/4 |
| Nonanswerable questions abstained | 7/8: four retrieval-only, three model responses |
| Typed receiving source/schema validation | Original 0/2; same-input context-fix retests 2/2 |

Extraction mistakes include non-lot record IDs, provisional lots marked affected, unresolved contradiction and OCR alternatives marked affected. EXT-08 failed exact citation validation. KNW-12 selected exact prerequisite passages but failed the expected insufficient-evidence flag. Its conservative quotations do not authorize recovery; the error is retained. Completeness accuracy is not measured because the extraction schema does not predict completeness and the frozen labels mix notice and ancestry support. At least 12 entity/disposition edits would be needed to match extraction labels; this is label-derived effort, not measured human productivity.

## Product behavior and fixes

Original typed receiving responses echoed internal document/line IDs as if they were supplier entities. Exact-source validation rejected both. Partial review preserved 800 held. An explicitly disclosed structured-record correction allowed a 700 proposal, then distinct named engineering identities approved exactly 100 units of sandbox recovery. Original receipts remained unchanged.

The receiving context now supplies source passages without internal metadata. The same two sources produced valid typed drafts. Partial ancestry remained unresolved and held 800. The complete SUP-B draft drove explicit source, completeness and superseded-row review: 700 proposed while 800 applied, followed by separate exact 100 recovery and one idempotent receipt. These are retests, not new holdout cases. `fresh/receiving-v2/final-packet.json` retains the genuine response and reviewed workflow.

The original signal response mislabeled STABLE rows as the baseline. A non-signal investigation was rejected with 422. The first context correction timed out. The final bounded context retained exact baseline IDs and the five actual signals, including counts, limits and source references. The fresh response matched all five observations and disclosed 20 omitted follow-ups. One successful check does not establish general semantic reliability. Full chart calculation and action authority remain deterministic.

Frozen EXT-07 exposed a missing explicit-conflict guard. Review policy 3 now also catches an unresolved contradiction and explicitly unconfirmed identifiers. Recorded regressions for EXT-04/07/11 reject copied model flags and keep an unresolved plan at 1,200 units, zero outside. Old policy approvals become stale; recalculating a historical policy-2 plan conservatively widens its proposal while retaining the already applied 800 and original receipts. Bounded English guards do not replace responsible review.

## Evidence and reproduction

- `../model-evaluation.json`: exact numerators, denominators, item-level errors and provenance.
- `fresh/`: original four requests, explicit corrections and receipt workflow.
- `fresh/receiving-v2/`: two successful typed context retests and exact recovery.
- `frozen/`: unchanged 24 inputs/labels beside actual responses; signal timeout and final response.
- `ui/`: actual read-only display of original persisted fresh results. No inference ran during capture.
- `pytest-final.xml`: final project regression report. Recorded replay tests make no model requests.

Offline scoring: `.venv\Scripts\python.exe -m scripts.score-enterprise-live`.
Regression replay: `.venv\Scripts\python.exe -m pytest -q tests/test_enterprise_live_regressions.py tests/test_ambiguity.py --basetemp work/pytest-new-run`.

Do not rerun the live scripts merely to reproduce a screenshot or improve a score. Each script reserves dispatches and preserves failed attempts. Every source is synthetic, every review and named test identity is operated by the agent, and no physical inventory or enterprise connector action occurred. Independent quality-professional and operator acceptance remains pending.
