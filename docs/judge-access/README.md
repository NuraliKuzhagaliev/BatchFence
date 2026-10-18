# Public document review — verified rc7 judging workflow

**Public URL:** https://batchfence.onrender.com/

**Deployed version:** 0.4.0-rc.7, runtime [`becdb4b`](https://github.com/NuraliKuzhagaliev/BatchFence/commit/becdb4b3335a5ea334be7db463cb915c6a6bd7ef), Render deploy `dep-dbaaonavcj2c73a18icg` on the existing Free service. Anonymous deployed acceptance passed in two clean browser contexts. This is agent-operated fictional engineering verification, not independent judge/domain acceptance.

## Judge steps

1. Open the public site in a private/new browser window. Click **Analyze your document** to start an editable isolated review. No owner token or provider account is required.
2. Click **Upload your document**. Use a nonsensitive supplier/quality notice, batch record or receiving evidence as **UTF-8 TXT or readable native-text PDF**. Maximum 2 MB; PDF 1–8 pages. Source context must fit the existing 18,000-character interpretation envelope including metadata and the adapter's 20 KB serialized request bound. Larger inputs reject without silent truncation. CSV mapping, DOCX, image-only scans and general unrelated documents are not supported by this visitor route.
3. Inspect the retained original, confirm external-processing consent, then click **Analyze with AMD Gemma**. Uploading, processing, completed/review-required, unsupported input, provider-unavailable and exhausted/limited states are explicit. Failures never substitute fixtures or historical results.
4. Inspect the original beside model-proposed statuses, exact source quotes, unresolved references and raw response/provenance. Record source inspection if appropriate. The model interpretation is not a reviewed stock fact: every visitor lot disposition and incident/inventory scope stays unresolved. Supply reviewed quantities, lineage and allocations in an authorized workspace before any later containment calculation.
5. Export the packet and keep your original files before leaving. Free server storage is temporary. Historical packets are read-only and grant no approval/action authority.

## Actual acceptance evidence

The new [Helio PDF](inputs/supplier-quality-helio.pdf) is outside the existing sample and contains three unfamiliar lots, an explicit exclusion and unresolved shipment context. Its original hash matched the uploaded bytes; `synthetic=false`; no sample inventory or relationships were loaded.

| Check | Actual result |
| --- | --- |
| Clean visitor | Empty browser storage, no existing cases and no owner/provider token in browser API requests. |
| Genuine analysis | Direct AMD shared Gemma, actual model `self-dploy/Gemma-4-31B-IT`; HTTP 200; request `cda7667045ce40ddb408c92921826672`; 37,091 ms; server response at 18 October 2026 11:27:44.802 UTC. |
| Visible workflow | Original PDF preview, source-grounded proposals and all three new IDs visible; explicit original-source inspection recorded. All inventory relationships/scope remain unresolved. |
| Unrelated document | Garden newsletter rejected with HTTP 422 / `UNRELATED_INPUT` before inference. No additional model record. |
| Session isolation | Second clean context listed no first-session cases. Read, proposals and export returned 404; foreign upload also returned 404. |
| Authority and staleness | No stocks, lineage, plan or receipts created. Approval/execution returned 403. Adding unrelated evidence made the preceding result stale. |
| Interface | 1440px and 390px review captures inspected; narrow view had no horizontal overflow; zero page errors. |
| Historical packet | Actual post-test packet exported; integrity hash and shared web/Windows packet shape verified. It records the later stale state, not an invented earlier snapshot. |

[Acceptance result](public/result.json) · [actual response](public/fresh-analysis.json) · [raw quality versus guarded state](public/raw-quality.json) · [actual post-test packet](public/final-packet.json) · [desktop-width capture](public/fresh-review-1440.png) · [390px capture](public/fresh-review-390.png) · [unrelated rejection](public/unrelated-rejection.png)

### Retained failures and application fixes

**Three conservative model attempts total; no automatic retries or broad model benchmark rerun.** The plan was expanded once for each demonstrated application defect, with earlier attempts retained.

1. [First attempt](public/attempt-1-failure.json): provider unavailable after approximately 40.7 seconds; no proposals accepted and no fixture fallback. The old catch did not retain its exact transport exception, so its original network cause remains unconfirmed. Its [read-only packet](public/attempt-1-packet.json) is preserved.
2. [Second attempt](public/attempt-2-validation-failure.json): genuine valid structured response in 49,806 ms, request `dcc73c205f0b43baa1caa7e81ca197b3`. Exact citations were rejected by the action-level vocabulary because it did not recognise “has a coating adhesion defect.” Its [original packet](public/attempt-2-packet.json) is preserved. The observed latency also demonstrates why a 40-second client window can be too short; it does not retrospectively prove the exact first failure.
3. [Final attempt](public/fresh-analysis.json): the deployed workflow passed after the visitor-only bounded 90-second response window and source-only proposal boundary fixes. Existing protected calls retain their 40-second default. Transport failures now preserve sanitized exception/request fingerprints. Original action validators, grounding checks and approval controls are unchanged.

The raw model still labels HELIO-733 `mentioned`, although its disposition is `uncertain`; the expected incident status is `uncertain`. Exact incident-status labels match 2/3 on this single notice. The application keeps that lot, and every other visitor lot, unresolved instead of granting an exclusion. Source identity grounding and application containment are not proof of general model correctness. No labels or original benchmark expectations were changed, and no model-superiority claim is made. Local replay and two additional misleading/conflicting notices are synthetic regression checks, not fresh inference.

## Cost, access, privacy and limits

The unchanged server-side key uses the documented AMD shared endpoint and configured Gemma model. The authenticated manual identifies shared models as free: the generic catalog `free=false` and pricing metadata represent nonmonetary shared-event points. The provider enforces its daily cap. Each dispatch rechecks the actual authenticated catalog and usage; missing entitlement, removed model or exhausted/low allowance stops before inference. There is no paid/dedicated fallback or unrestricted provider proxy. This route uses direct AMD processing; existing Evolus workflows remain protected and no new Evolus indexing was needed.

Free entitlement was checked on the server at **18 October 2026 11:27:07.604 UTC**, with **0.993072119075805 nonmonetary points** before the final call. The quota resets at **18 October 2026 16:00 UTC /21:00 Qyzylorda**. **That reset is not an access expiry.** The current provider manual/API publish no event-key end date; access/models may be withdrawn. No availability beyond actual verified entitlement is promised. See [provider preflight](provider-preflight.json) and the per-call entitlement in the actual response.

Four persisted AI attempts per session, including failures; six analysis starts per minute globally and two per observed source IP; one shared concurrent inference. Existing request/body/file/page/session/storage limits remain. Session counters use temporary storage; the upstream daily cap remains the spending boundary. Only nonsensitive documents may be uploaded. The provider documents about two days of prompt/output retention. Keep credentials and personal, health, financial or confidential enterprise data out of uploads.

The historical **18/18 engineering ledger is byte-preserved** and does not gate this visitor route. Existing owner/workspace live routes still require their private token and retain their prior controls. No keys were rotated, no services purchased/upgraded, no real inventory actions taken and no hackathon entry submitted or changed.

## Release verification and remaining boundaries

[Main CI 39122820283](https://github.com/NuraliKuzhagaliev/BatchFence/actions/runs/39122820283) passed **510 regressions**, 30 deterministic domain cases, build/audit, eight actual Linux container checks and five packaged Windows UI/transport checks. [Final CI record](final-ci.json). The final affected local set passed **99 checks**. [Local report](proposal-boundary-tests.xml). Public/local JS and CSS bytes match. [Publication record](publication.json).

The published rc6 Windows installer/release and original evidence remain unchanged. The new entry is web-only; current shared code was packaged and transport-checked in CI, with no new installed Windows live acceptance or replacement installer claim. Independent operator/domain acceptance, general language/scan/photo reliability and production durability are not established.

Client-side capture timestamps use an unsynchronised local clock (observed about 81 seconds behind the server). They are retained as recorded; use server UTC and monotonic request latency for provider evidence. No clock settings were changed. Earlier pending diagnosis/checkpoint records describe their own stages and are superseded by this final record. No further engineering inference is planned.
