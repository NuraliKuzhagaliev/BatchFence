# AMD evidence — 2026-10-16

**Genuine AMD-backed local workflow observed. Overall hosted/submission release acceptance remains incomplete.**

The original preflight was blocked with zero calls. After the user signed in, the authenticated Token Factory User Manual and Models catalog confirmed endpoint/model. The key was transferred without displaying it into ignored .env. No secret appeared in inspected portal panels, screenshots or logs.

Provider evidence: https://notebooks.amd.com/tokenfactory → User Manual; sanitized findings and the observed 12-model list are in live-verification/provider-documentation.md. The manual identifies the shared service as AMD-run inference on AMD GPUs. Physical GPU identity and serving configuration were not independently measured.

Requested model: **Gemma-4-31B-IT**. Returned model: **self-dploy/Gemma-4-31B-IT**. Base: https://developer.amd.com.cn/radeon/api/v1. The existing OpenAI-chat adapter worked unchanged. Strict JSON schema is not documented for Gemma, so AMD_JSON_SCHEMA=false. Prompt-requested JSON passed local schema/exact-quote validation. No alternate provider, repair or fixture substitution.

Seven sequential requests succeeded technically: four capability probes, one initial workflow request before a test-selector failure, and two completed workflow requests. Each preserved request ID, UTC start, model ID, usage, elapsed milliseconds and extracted facts. Observed range 5,294–12,261 ms, median 7,666 ms. Small mixed-prompt sample with cached tokens; no controlled benchmark or general accuracy claim.

## Raw extraction versus reviewed behavior

Clean, adversarial-document and changed-ID capability probes produced expected supported lot facts. The ambiguous probe is **not** a semantic pass: "may be affected" SUP-R became affected=true; unresolved SUP-S became affected=false. The unresolved-scope qualifier survived, but those booleans do not establish certainty. This probe was not corrected or executed as a product plan.

Two new workflow notices were frozen before inference with renamed batches and independent expected sets. Both were uploaded as supplier-message.txt. First raw affected set: MC-7421-X. Revised set: BZ-9187, MC-7421-X. NX-6130-Z was explicitly excluded in both. Exact source passages support all five candidate facts. Missing/extra affected IDs: zero; operator ID corrections: zero.

Codex inspected sources, exclusions, supersession and synthetic genealogy, then the browser harness exercised explicit review/approval controls. This is an agent-operated acceptance check, **not independent human validation**. The model proposed facts; CPU code calculated scope; explicit reviewed/approved state authorized sandbox execution.

Observed results: 400 documented +100 uncertain =500 held units; revised 700+100=800. The second transaction retained 500 existing held units and newly held 300. Receipts:

- TX-4e1ba674d3624fdd845efb5afea0b6a3
- TX-cb299057cde940038a42ccec0c4d8fe0

Both persisted after refresh and an actual process restart. An old-plan request failed with 409 STALE_APPROVAL. See live-verification/browser-results.json, packet-1.json, packet-2.json and restart-results.json. Test-selector failures are preserved separately and were not classified as model failures.

## Scope of the claim

AMD output genuinely powered the local workflow on synthetic input. Raw results, review choices, actions and receipts are inspectable. Ambiguity quality, broader narrative accuracy and independent reviewer performance remain unproven. No production/customer benefit, physical GPU model, prize eligibility or public deployment is claimed. Recorded mode is still not enabled; preserved live evidence is not silently replayed as live inference.
