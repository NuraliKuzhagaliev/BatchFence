# Ambiguity containment audit — 0.1.1

Continued from ed6a2b0 on 2026-10-16. The old failure was unsafe; the exact regression is now contained. This is a local synthetic prototype, not independent manufacturing or human validation.

## Exact observed failure and old propagation

Input: `Lot SUP-R may be affected. We cannot determine whether SUP-S is implicated. Scope remains unresolved.`

Expected: SUP-R and SUP-S both have unresolved involvement; the incident boundary is unresolved. Neither statement supports excluding SUP-S descendants.

Actual original Gemma output: SUP-R `affected=true`, quote `Lot SUP-R may be affected.`; SUP-S `affected=false`, quote `We cannot determine whether SUP-S is implicated.` A qualifier said `Scope remains unresolved for SUP-R and SUP-S`. See ../amd-probe.json, ambiguous run 798d318b-e0cd-458b-a18f-32e91e7515bd, requested model Gemma-4-31B-IT, returned self-dploy/Gemma-4-31B-IT, 2026-10-16T08:25:45Z, 7,676 ms.

The response passed structural and exact-quote validation. Those checks did not establish semantic certainty. Old UI selection copied positive booleans into the affected set; a generic scope/completeness acknowledgement omitted SUP-S. The server accepted that review. Deterministic traversal then treated SUP-S's complete branch as outside the selected scope; exact-plan approval and execution succeeded. They checked plan integrity, not the validity of the omitted premise.

Before changing code, the exact stored response was replayed into an isolated copy of the demo lineage, renaming SUP-A to SUP-R and SUP-C to SUP-S. Review, approval and application returned 200, held 500 units, and classified FG-D's 300 SUP-S-descendant units outside scope. This replay made no AMD call. Full request/result/receipt: before-regression.json. It demonstrates a reachable unsupported exclusion, not a past customer incident.

## Fix and downstream behavior

- Every model candidate begins unresolved. Review records affected, unresolved and explicitly excluded groups separately; omissions, overlaps and IDs absent from the selected source fail.
- Incident scope starts unresolved. Narrowing needs an explicit resolved-boundary review, an exact quote and an explanation. Conservative server-side English source checks reject explicit unresolved scope or uncertain lots being forced into affected/excluded groups. A clarifying notice is needed; a generic checkbox cannot override the detected contradiction.
- An unresolved incident produces a broad hold with zero outside-scope stock. Possible ancestry is uncertain even when its edge originates outside the currently affected seed set; uncertainty propagates through intermediate events. Confirmed affected paths retain precedence.
- Reviewed scope, explanations and source references are distinct from immutable model proposals. Review-policy version 2 participates in plan inputs; legacy approvals cannot execute. Revisions still invalidate approvals, and exact transactional hold actions/idempotency checks remain in place.
- Failed extraction cannot authorize review. Its persisted error now remains visible after reload. Structured rejected output is retained, bounded and redacted, on future citation-validation failures; it is never promoted to accepted output.

No stronger extraction prompt was used: scope-extract-1 and the boolean schema are unchanged. The application now treats that schema as a proposal, not a certainty representation.

## New live observations

The catalog still listed Gemma and MiMo. Three Gemma attempts failed: the first generic network/provider failure after 46.650 s, then explicit transport timeouts at 45.972 and 47.262 s. The first run did not retain a typed exception, so its precise cause is unknown. No result or fallback was used. After a read-only catalog check, MiMo-V2.6-Flash was selected explicitly and the private local setting was updated; this was not automatic fallback. The same AMD endpoint/key/style remain in use.

An explicit MiMo probe reproduced the original boolean error. Two further, differently worded notices were then sent through the application with changed IDs and the same filename supplier-message.txt:

| Notice | Raw live result | Application result after review |
|---|---|---|
| MC-7421-X may be affected; cannot determine BZ-9187; scope unresolved, incomplete list | MC=true/BZ=false; qualifier incorrectly treated BZ as merely mentioned. 26.728 s. | Codex placed both in unresolved. Narrowing attempt rejected with 422 UNRESOLVED_SCOPE. Actual approved broad plan/receipt held 1,200, outside 0, documented 0. |
| MC confirmed; BZ awaiting laboratory results and not cleared; list not final; NX explicitly excluded | HTTP 200, but local validation rejected `Lot identifier absent from cited quote`. 17.219 s. | Review rejected 422 REVIEW_REQUIRED; no plan, approval or receipt. No corrected model result claimed. |

Exact sources, frozen truth, hashes, model IDs/request IDs/timestamps/usage and all failed attempts are in live-ambiguity.json. The second response's invalid JSON payload was not retained by the then-current adapter; its metadata/error are preserved. The later rejected_output change improves future evidence and cannot recover that missing payload. Raw quality is not a pass just because the safety checks passed.

Two fresh clear notices also used MiMo. The raw affected/excluded IDs matched all five expected facts with zero ID corrections, at 21.497 and 27.885 s. Both outputs overstated ambiguity by conflating uncertain warehouse ancestry with an explicit complete supplier boundary. Codex corrected that interpretation through the separate source-backed review. Plans held 500 then 800, retaining 100 uncertain units; two real receipts persisted and old approval execution returned 409 STALE_APPROVAL. See clear-live/browser-results.json. Agent-operated review and automated approval clicks are not independent human validation.

## Additional discovered packet defect

During installed live-packet capture, integrity validation rejected genuine exports. Python serialized AMD usage costs such as 8.33e-5 differently from JavaScript's 0.0000833. The integrity guard correctly refused the mismatch. Python now uses pinned rfc8785 0.1.4 to match ECMAScript number formatting and UTF-16 key ordering. Cross-runtime tests cover the actual packets, numeric thresholds and Unicode keys. See [library source](https://github.com/trailofbits/rfc8785.py) and [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).

Original failed exports remain in pre-fix-packets. Three envelopes were reissued with corrected hashes; their case payloads, model responses and receipts are exactly unchanged. packet-reissue.json records old/new hashes. A fresh server export and browser/installed offline import now pass. This is an export compatibility fix, not a new model response or execution.

## Checks and limits

40 pytest checks, 30 frozen graph cases, 12 browser checks and 7 installed-app checks passed. Exact failure replay, two distinct ambiguous wordings without model qualifiers, independent possible ancestry, default uncertainty, invalid scope bases and legacy approval rejection are covered. Five malformed/cyclic packet mutations still fail. Three additional final UI/export checks pass. A real verified backend process restart preserved exact runs, reviews, plans, stock and all three live receipts; the failed case remained without a plan. See restart-results.json and final-ui-results.json.

The source rules are bounded English heuristics over source blocks, not a general semantic entailment system. They can miss different phrasing or over-block a line containing both confirmed and uncertain statements. Every candidate still needs explicit disposition and every narrowed scope explicit review. An exact quote plus explanation does not prove the reviewer understood it. Missing model candidates, incomplete exports, dishonest review, broader languages and independent domain correctness remain limits. No verified enterprise identity or real ERP action exists. Unresolved scope broad holds may over-contain; outside-scope labels never certify safety.

Docker container execution, hosted deployment, signing, second-machine acceptance and independent operator review remain open. This release is suitable for local demonstration and review, not production or public-release acceptance.

Final offline provenance correction: the disabled mode selector now shows the packet’s recorded model mode, with an explicit historical/no-new-inference caption. It no longer displays a default fixture selection for a live AMD packet.
