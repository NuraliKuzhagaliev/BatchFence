# Label Photo Verification: fresh acceptance

Fresh live image processing passed through the public web application and installed Windows0.4.0-rc.3 on runtime4978aafaad881452349640136cc28177aa6c800c. Requested model `Gemma-4-31B-IT`, actual runtime `self-dploy/Gemma-4-31B-IT`, direct managed AMD shared endpoint. Gemma text and genuine Evolus workflows, saved connection and credentials were unchanged. No alternate model or automatic fallback was needed.

## Before and diagnosis

Historical success and all original failures remain retained. Prior release imageHTTP500 was safely terminal after a separately reproduced exception-handler fix; no reading or authority was accepted. In this finite phase two new web image failures were preserved under `web-run1/`, following a setup-only415 that made no inference call. Both failed provider requests lack request IDs and error bodies in the older adapter. They cannot establish the original server-side cause.

The image audit confirms valid single-frame RGB PNG, MIME/data-URI agreement, strict base64 round-trip, bounded dimensions/bytes and metadata-free derived input. Historical success used JSON object output. Current paired local diagnostics with JSON mode off/on and the exact application schema all succeeded. No demonstrable payload/configuration defect was found, and a provider-wide outage was not established. Linux PNG compression changes the encoded derived hash relative to Windows; both are recorded separately from the original. This is not evidence of changed source pixels or an encoding defect.

Code now records bounded sanitized error type/code/message, endpoint, payload digest and transmitted image MIME/length/hash. The deployed diagnostic then succeeded (3970ms, request `fb109f7f69954670862c5a59e21ae352`,264 image tokens). No endpoint/key/model/JSON-mode correction preceded recovery. The earlierHTTP500 root cause remains unconfirmed; it is inaccurate to claim a proved upstream-only fault or a proved request-contract fix. Five consecutive deployed image responses succeeded, establishing current bounded availability rather than permanent reliability.

## Actual client results

The four images were frozen before dispatch. Expected IDs were not supplied to the model. Each request contained actual image pixels and the label-reading schema. Original and derived hashes, model outputs, request IDs, timestamps, latency, image-token usage, packet export and screenshots are retained under `web-final/` and `windows-final/`.

| Client/source | Expected and raw actual | Latency | Application behavior |
|---|---|---:|---|
| Public web, readable | BF-00481 |3229ms| Missing visual confirmation rejected; explicit attributed identity/relationship review accepted |
| Public web, document mismatch | BF-00482, while source says BF-00481 |6551ms| Exact reading retained; unsupported association rejected; review remains null |
| Installed Windows, readable | BF-00591 |5069ms| Missing visual confirmation rejected; explicit attributed identity/relationship review accepted |
| Installed Windows, two labels | BF-00591 and BF-00592 |5449ms| Both exact candidates retained; association blocked until an explicit separate crop/reading resolves ambiguity |

Raw candidates exact4/4 in this small set; no raw corrections or transcription substitutes. This does not measure OCR accuracy on physical photographs or prove general reliability. Each negative case tests application containment independently of correct raw text. Agent-operated visual/source review is not independent human validation. Windows used the actual installed executable, restricted IPC and actual UI for inference and review; source import used owned APIs/IPC. Prior native-dialog acceptance is separate and was not repeated.

Both clients started with explicitly labeled synthetic fixture500→800 setup and two sandbox receipts, avoiding unnecessary new text inference. Before/after holds, stock and both receipts compare equal after each image operation. The fixtures are not claimed as fresh model processing. Existing source-review, uncertainty, stale approval and receipt tests remain; prior genuine Gemma/Evolus500→800 evidence is preserved.

## Checks, limits and release

33 affected regressions passed after the contract changes;22 label/continuation tests passed after the final runtime-version correction;4 adapter/version tests passed including health version. Injected500, malformed output, explicit image-only routing, secret redaction and review gates have local coverage. Branch CI39079226828 and main CI39079389694 passed, including full suite/domain/Linux real-volume restart. Production TypeScript/Vite build and unsigned installer build/install passed. Installed ASAR scan8886entries/33 known private needles: zero findings. Screenshots were visually inspected. One Starlette/httpx deprecation warning remains.

All64 conservative reservations of the existing campaign are now used; some historical reservations did not dispatch. This phase used10 actual image requests:3 local successes,2 retained public failures,1 deployed diagnostic success and4 final client successes. No further live requests, benchmark reruns or allowance reset. Shared daily credits were verified under the existing free-event boundary; no purchase, secret change, new hosting or actual inventory action.

Current free proof expires18October2026 16:00UTC. Free hosted SQLite is ephemeral; export before restart/redeploy. The Windows installer is unsigned. Existing independent quality/language/physical-photo/operator acceptance and own ADC/vLLM eligibility remain open. This closes the fresh label-inference availability gap for these engineering cases; it does not turn all six extensions into independently accepted enterprise capabilities. IfHTTP500 recurs, retain the new sanitized metadata and original, keep association unreviewed, and investigate once under a new bounded authorized plan rather than retrying unchanged requests.
